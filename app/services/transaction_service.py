from app.con_sqlalchemy import MaterialList, MaterialTransaction
from app.app import db
from app.exception import ValidationError


def create_material_transaction(material_list: MaterialList, document : str, transaction_type: str, quantity: int):
    """
    Create a MaterialTransaction linked to the given document.
    For REMOVE, validates that sufficient quantity is available.
    Pass code directly if you already have the document code as a string.
    """
    try:
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
            related_document_code=document,
        ))
    except Exception:
        raise
