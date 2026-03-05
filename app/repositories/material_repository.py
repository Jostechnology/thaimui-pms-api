from sqlalchemy import func, case
from app.con_sqlalchemy import MaterialList, MaterialTransaction
from app.app import db

def get_material_by_id(material_list_id):
    return MaterialList.query.get(material_list_id)

def save_material_transaction(transaction):
    db.session.add(transaction)
    db.session.commit()
    return transaction

def rollback_transaction():
    db.session.rollback()

def get_tracking_summary_query(sales_item_id):
    sum_removed = func.coalesce(func.sum(case((MaterialTransaction.type == 'REMOVE', MaterialTransaction.amount), else_=0)), 0)
    sum_added = func.coalesce(func.sum(case((MaterialTransaction.type == 'ADD', MaterialTransaction.amount), else_=0)), 0)

    return db.session.query(
        MaterialList.material_list_id,
        MaterialList.item_code,
        MaterialList.item_name,
        MaterialList.item_num.label('planned_qty'),
        sum_removed.label('total_removed'),
        sum_added.label('total_added')
    ).outerjoin(
        MaterialTransaction, 
        MaterialList.material_list_id == MaterialTransaction.material_list_id
    ).filter(
        MaterialList.sales_item_id == sales_item_id
    ).group_by(
        MaterialList.material_list_id
    ).all()