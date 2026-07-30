from app.con_sqlalchemy import MaterialList, MaterialTransaction, MaterialTransactionType, WorkRun, WorkRunTransaction, WorkRunTransactionType
from app.app import db
from app.exception import ValidationError
from app.utils import QTY_EPS


def create_init_material_transaction(material_list: MaterialList, document: str):
    """Create the first INIT transaction when a material first arrives (positive amount = original_num)."""
    material_list.transactions.append(MaterialTransaction(
        amount=material_list.quantity,
        type=MaterialTransactionType.INIT,
        related_document_code=document,
    ))


def create_material_transaction(material_list: MaterialList, document: str, transaction_type, quantity: float, **kwargs):
    """
    Create a MaterialTransaction linked to the given document.
    - ADD: stores positive amount
    - REMOVE: validates availability then stores negative amount
    Accepts either MaterialTransactionType enum or the equivalent string value.
    """
    try:
        if isinstance(transaction_type, str):
            transaction_type = MaterialTransactionType[transaction_type.upper()]
        if transaction_type == MaterialTransactionType.REMOVE:
            available = material_list.remaining_num
            if quantity > available + QTY_EPS:
                raise ValidationError(
                    f"วัสดุ '{material_list.item_name}' (ID: {material_list.material_list_id}) ไม่เพียงพอ "
                    f"คงเหลือ: {available}, ต้องการ: {quantity}"
                )
            signed_amount = -quantity
        else:
            signed_amount = quantity

        db.session.add(MaterialTransaction(
            material_list_id=material_list.material_list_id,
            amount=signed_amount,
            type=transaction_type,
            related_document_code=document,
        ))
    except Exception:
        raise

def create_work_run_transaction(work_run: WorkRun, transaction_type: WorkRunTransactionType, quantity: float, document: str):
    """Append an item-movement record to a WorkRun's audit log."""
    try:
        db.session.add(WorkRunTransaction(
            work_run_id=work_run.work_run_id,
            quantity=quantity,
            type=transaction_type,
            related_document_code=document,
        ))
    except Exception:
        raise