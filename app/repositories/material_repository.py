from sqlalchemy import func, case, or_
from app.con_sqlalchemy import MaterialList, MaterialTransaction, ComponentMaterialUsage, ItemComponent, WorkOrder
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


def get_all_tracking(search=None, tracking_type=None):
    """ดึงวัตถุดิบทั้งหมดพร้อมสรุป used_in_production, used_in_testing"""
    # Sub-query: SUM ของ component_material_usage (ใช้ในผลิต)
    production_sub = db.session.query(
        ComponentMaterialUsage.material_list_id,
        func.coalesce(func.sum(ComponentMaterialUsage.quantity_used), 0).label('used_in_production')
    ).group_by(ComponentMaterialUsage.material_list_id).subquery()

    # Sub-query: SUM ของ material_transaction REMOVE (ใช้ในเทส/อื่นๆ)
    testing_sub = db.session.query(
        MaterialTransaction.material_list_id,
        func.coalesce(func.sum(
            case((MaterialTransaction.type == 'REMOVE', MaterialTransaction.amount), else_=0)
        ), 0).label('used_in_testing')
    ).group_by(MaterialTransaction.material_list_id).subquery()

    query = db.session.query(
        MaterialList.material_list_id,
        MaterialList.sales_item_id,
        MaterialList.item_code,
        MaterialList.item_name,
        MaterialList.item_description,
        MaterialList.item_num.label('total_quantity'),
        func.coalesce(production_sub.c.used_in_production, 0).label('used_in_production'),
        func.coalesce(testing_sub.c.used_in_testing, 0).label('used_in_testing'),
    ).outerjoin(
        production_sub, MaterialList.material_list_id == production_sub.c.material_list_id
    ).outerjoin(
        testing_sub, MaterialList.material_list_id == testing_sub.c.material_list_id
    )

    if search:
        query = query.filter(or_(
            MaterialList.item_code.ilike(f'%{search}%'),
            MaterialList.item_name.ilike(f'%{search}%')
        ))

    # กรองตามประเภท: test = มี transaction REMOVE, production = มี component_material_usage
    if tracking_type == 'test':
        query = query.filter(testing_sub.c.used_in_testing > 0)
    elif tracking_type == 'production':
        query = query.filter(production_sub.c.used_in_production > 0)

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
        MaterialList.item_num.label('total_quantity'),
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
    """ดึงรายละเอียดการใช้วัตถุดิบ — production_usages + transactions"""
    material = MaterialList.query.get(material_list_id)
    if not material:
        return None

    # production usages: join component_material_usage → item_component → work_order
    production_usages = db.session.query(
        ComponentMaterialUsage.usage_id,
        WorkOrder.doc_num.label('work_order_doc_num'),
        WorkOrder.status.label('work_order_status'),
        ItemComponent.component_name,
        ComponentMaterialUsage.quantity_used,
        ComponentMaterialUsage.created_date
    ).join(
        ItemComponent, ComponentMaterialUsage.item_component_id == ItemComponent.item_component_id
    ).join(
        WorkOrder, ItemComponent.work_order_id == WorkOrder.work_order_id
    ).filter(
        ComponentMaterialUsage.material_list_id == material_list_id
    ).order_by(ComponentMaterialUsage.created_date.desc()).all()

    # transactions (REMOVE = test/อื่นๆ)
    transactions = MaterialTransaction.query.filter_by(
        material_list_id=material_list_id
    ).order_by(MaterialTransaction.created_date.desc()).all()

    return {
        'material': material,
        'production_usages': production_usages,
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