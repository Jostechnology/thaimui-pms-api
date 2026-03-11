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

    resolved_code = code if code is not None else _resolve_document_code(document)
    db.session.add(MaterialTransaction(
        material_list_id=material_list.material_list_id,
        amount=quantity,
        type=transaction_type,
        related_document_code=resolved_code,
    ))


def create_sales_item_transaction(sales_item: SalesItem, document, transaction_type: SalesItemTransactionType, quantity: int):
    """
    Create a SalesItemTransaction linked to the given document.

    Hard constraints:
    - PRODUCED: quantity must not exceed sales_item.item_num
    - QUEUED_FOR_TEST: cumulative queued quantity must not exceed total produced
    """
    txns = sales_item.sales_item_transactions

    if transaction_type == SalesItemTransactionType.PRODUCED:
        if quantity > sales_item.item_num:
            raise ValidationError(
                f"จำนวนที่ผลิต ({quantity}) เกินจำนวนใน Sales Item ({sales_item.item_num})"
            )

    elif transaction_type == SalesItemTransactionType.QUEUED_FOR_TEST:
        total_queued = sum(t.quantity for t in txns if t.type == SalesItemTransactionType.QUEUED_FOR_TEST)
        if total_queued + quantity > sales_item.item_num:
            raise ValidationError(
                f"จำนวนที่ส่งทดสอบรวม ({total_queued + quantity}) "
                f"เกินจำนวนใน Sales Item ({sales_item.item_num})"
            )

    code = _resolve_document_code(document)
    db.session.add(SalesItemTransaction(
        sales_item_id=sales_item.sales_item_id,
        quantity=quantity,
        type=transaction_type,
        related_document_code=code,
    ))
