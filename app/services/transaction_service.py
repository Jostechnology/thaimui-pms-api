from app.con_sqlalchemy import (
    MaterialList, MaterialTransaction,
    SalesItem, SalesItemTransaction, SalesItemTransactionType,
)
from app.app import db
from app.exception import ValidationError


def _resolve_document_code(document) -> str:
    """Use doc_num if present, otherwise fall back to the primary key value."""
    if hasattr(document, 'doc_num') and document.doc_num is not None:
        return str(document.doc_num)
    mapper = document.__class__.__mapper__
    pk_col_name = mapper.primary_key[0].name
    return str(getattr(document, pk_col_name))


def create_material_transaction(material_list: MaterialList, document, transaction_type: str, quantity: int, code: str = None):
    try:
        """
        Create a MaterialTransaction linked to the given document.
        For REMOVE, validates that sufficient quantity is available.
        Pass code directly if you already have the document code as a string.
        """
        if transaction_type == 'REMOVE':
            available = material_list.remaining_num
            if quantity > available:
                raise ValidationError(
                    f"วัสดุ '{material_list.item_name}' (ID: {material_list.material_list_id}) ไม่เพียงพอ "
                    f"คงเหลือ: {available}, ต้องการ: {quantity}"
                )

        db.session.add(MaterialTransaction(
            material_list_id=material_list.material_list_id,
            amount=quantity,
            type=transaction_type,
            related_document_code=code,
        ))
    except Exception:
        raise


def create_sales_item_transaction(sales_item: SalesItem, document, transaction_type: SalesItemTransactionType, quantity: int):
    """
    Create a SalesItemTransaction linked to the given document.

    - PRODUCED: fires when a WorkRun is completed, quantity = usable_qty
    - TESTED_PASSED: fires when TestResult created/updated, quantity = passing item count
    - TESTED_FAILED: fires when TestResult created/updated, quantity = failing item count
    """
    try:
        db.session.add(SalesItemTransaction(
            sales_item_id=sales_item.sales_item_id,
            quantity=quantity,
            type=transaction_type,
            related_document_code=document,
        ))
    except Exception:
        raise
