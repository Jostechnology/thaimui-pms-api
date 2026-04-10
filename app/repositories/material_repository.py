from sqlalchemy import func, case, or_
from sqlalchemy.orm import selectinload
from app.con_sqlalchemy import MaterialList, MaterialTransaction, ComponentMaterialUsage, ItemComponent, SalesItem, WorkOrder
from app.app import db

def get_material_by_id(material_list_id):
    # Pre-load transactions so remaining_num property doesn't fire a lazy query
    return (
        db.session.query(MaterialList)
        .options(selectinload(MaterialList.transactions))
        .filter(MaterialList.material_list_id == material_list_id)
        .first()
    )

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
        MaterialList.quantity.label('planned_qty'),
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


def get_all_tracking(search=None, tracking_type=None):
    """ดึงวัตถุดิบทั้งหมดพร้อมสรุป total_used จาก MaterialTransaction"""
    usage_sub = db.session.query(
        MaterialTransaction.material_list_id,
        func.coalesce(
            func.sum(case((MaterialTransaction.type == 'REMOVE', MaterialTransaction.amount), else_=0)) -
            func.sum(case((MaterialTransaction.type == 'ADD', MaterialTransaction.amount), else_=0)),
            0
        ).label('total_used')
    ).group_by(MaterialTransaction.material_list_id).subquery()

    query = db.session.query(
        MaterialList.material_list_id,
        MaterialList.sales_item_id,
        MaterialList.item_code,
        MaterialList.item_name,
        MaterialList.item_description,
        MaterialList.quantity.label('total_quantity'),
        func.coalesce(usage_sub.c.total_used, 0).label('total_used'),
    ).outerjoin(
        usage_sub, MaterialList.material_list_id == usage_sub.c.material_list_id
    )

    if search:
        query = query.filter(or_(
            MaterialList.item_code.ilike(f'%{search}%'),
            MaterialList.item_name.ilike(f'%{search}%')
        ))

    if tracking_type:
        query = query.filter(usage_sub.c.total_used > 0)

    return query.all()


def get_material_stock_summary(sales_item_id):
    """ดึงสรุปยอดคงเหลือของวัตถุดิบทั้งหมดใน Sales Item"""
    production_sub = db.session.query(
        ComponentMaterialUsage.material_list_id,
        func.coalesce(func.sum(ComponentMaterialUsage.quantity_used), 0).label('used_in_production')
    ).group_by(ComponentMaterialUsage.material_list_id).subquery()

    testing_sub = db.session.query(
        MaterialTransaction.material_list_id,
        func.coalesce(func.sum(
            case((MaterialTransaction.type == 'REMOVE', MaterialTransaction.amount), else_=0)
        ), 0).label('used_in_testing')
    ).group_by(MaterialTransaction.material_list_id).subquery()

    return db.session.query(
        MaterialList.material_list_id,
        MaterialList.sales_item_id,
        MaterialList.item_code,
        MaterialList.item_name,
        MaterialList.item_description,
        MaterialList.quantity.label('total_quantity'),
        func.coalesce(production_sub.c.used_in_production, 0).label('used_in_production'),
        func.coalesce(testing_sub.c.used_in_testing, 0).label('used_in_testing'),
    ).outerjoin(
        production_sub, MaterialList.material_list_id == production_sub.c.material_list_id
    ).outerjoin(
        testing_sub, MaterialList.material_list_id == testing_sub.c.material_list_id
    ).filter(
        MaterialList.sales_item_id == sales_item_id
    ).all()


def get_usage_detail(material_list_id):
    """ดึงรายละเอียดการใช้วัตถุดิบจาก MaterialTransaction"""
    material = (
        db.session.query(MaterialList)
        .options(selectinload(MaterialList.transactions))
        .filter(MaterialList.material_list_id == material_list_id)
        .first()
    )
    if not material:
        return None

    transactions = MaterialTransaction.query.filter_by(
        material_list_id=material_list_id
    ).order_by(MaterialTransaction.created_date.desc()).all()

    return {
        'material': material,
        'transactions': transactions
    }


def get_transactions_by_sales_item(sales_item_id, tx_type=None):
    """ดึง transactions ทั้งหมดของวัตถุดิบใน Sales Item"""
    query = db.session.query(MaterialTransaction).join(
        MaterialList, MaterialTransaction.material_list_id == MaterialList.material_list_id
    ).filter(MaterialList.sales_item_id == sales_item_id)

    if tx_type:
        query = query.filter(MaterialTransaction.type == tx_type.upper())

    return query.order_by(MaterialTransaction.created_date.desc()).all()

def get_material_list_from_doc_entry(doc_entry):
    try:
        query = db.session.query(MaterialList).join(SalesItem, SalesItem.sales_item_id == MaterialList.sales_item_id).filter(SalesItem.doc_entry == doc_entry)
        sales_items = query.all()
        return sales_items
    except Exception:
        raise
