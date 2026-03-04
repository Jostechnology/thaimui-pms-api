from app.con_sqlalchemy import ProductBackofficeInventory, PBI_Transaction
from app.app import db

def get_inventory_by_id(inventory_id):
    # ดึงข้อมูลกระบะสต๊อกเป้าหมายขึ้นมา
    return ProductBackofficeInventory.query.get(inventory_id)

def get_inventory_by_code(inventory_code):
    # เผื่ออนาคตอยากค้นหาจากรหัสล็อตสินค้า
    return ProductBackofficeInventory.query.filter_by(product_backoffice_inventory_code=inventory_code).first()