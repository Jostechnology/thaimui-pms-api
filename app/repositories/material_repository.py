from app.con_sqlalchemy import MaterialList, SalesItem
from app.app import db

def get_material_by_id(material_list_id):
    query = db.session.query(MaterialList).filter(MaterialList.material_list_id == material_list_id)
    return query.first()

def get_material_list_from_doc_entry(doc_entry):
    try:
        query = db.session.query(MaterialList).join(SalesItem, SalesItem.sales_item_id == MaterialList.sales_item_id).filter(SalesItem.doc_entry == doc_entry)
        sales_items = query.all()
        return sales_items
    except Exception:
        raise
