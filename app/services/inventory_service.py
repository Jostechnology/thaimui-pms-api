from app.con_sqlalchemy import ProductBackofficeInventory, PBI_Transaction,Product
from app.repositories import inventory_repository
from app.app import db
from sqlalchemy import func
import datetime

def remove_inventory(inventory_id, amount, document_code):
    try:
        inv = inventory_repository.get_inventory_by_id(inventory_id)
        if not inv:
            raise Exception(f"ไม่พบข้อมูลสต๊อก ID: {inventory_id}")

        if inv.current_num < amount:
            raise Exception(f"สต๊อกไม่พอเบิก! มีของเหลือแค่ {inv.current_num} ชิ้น แต่พยายามเบิก {amount} ชิ้น")

        #ลงมือตัดสต๊อกตารางแม่
        inv.current_num -= amount

        #ลงมือจดสมุดประวัติ
        transaction = PBI_Transaction(
            product_backoffice_inventory_id=inventory_id,
            amount=amount,
            type="REMOVE", # ระบุให้ชัดเจนว่าเป็นการเบิกออก
            related_document_code=document_code
        )
        
        # จับยัดประวัติลง Database
        db.session.add(transaction)

        db.session.commit()

        return {
            "success": True, 
            "message": f"เบิกสินค้าสำเร็จ เลหือสต๊อก {inv.current_num} ชิ้น",
            "transaction_id": transaction.pbi_transaction_id
        }

    except Exception as e:
        db.session.rollback()
        raise Exception(str(e))

def get_material_usage_summary(document_code):
    try:
        # โดยจัดกลุ่มตามสินค้า (inventory_id)
        usage_data = db.session.query(
            PBI_Transaction.product_backoffice_inventory_id,
            func.sum(PBI_Transaction.amount).label('total_used')
        ).filter(
            PBI_Transaction.related_document_code == document_code,
            PBI_Transaction.type == 'REMOVE'
        ).group_by(
            PBI_Transaction.product_backoffice_inventory_id
        ).all()

        # จัดฟอร์แมต JSON เตรียมส่งให้เพื่อนเอาไปวาดกราฟ หรือลงตาราง
        result = []
        for row in usage_data:
            result.append({
                "inventory_id": row.product_backoffice_inventory_id,
                "total_used": row.total_used 
            })

        return result
    except Exception as e:
        raise Exception(f"ไม่สามารถดึงข้อมูลสรุปได้: {str(e)}")
    
def get_inventory_summary_service(document_code):
    try:
        summary_query = db.session.query(
            PBI_Transaction.product_backoffice_inventory_id,
            ProductBackofficeInventory.product_backoffice_inventory_code,
            Product.product_code,
            Product.product_name,
            PBI_Transaction.type,
            func.sum(PBI_Transaction.amount).label('total_amount')
        ).join(
            ProductBackofficeInventory,
            PBI_Transaction.product_backoffice_inventory_id == ProductBackofficeInventory.product_backoffice_inventory_id
        ).join(
            Product,
            ProductBackofficeInventory.product_id == Product.product_id
        ).filter(
            PBI_Transaction.related_document_code == document_code
        ).group_by(
            PBI_Transaction.product_backoffice_inventory_id,
            ProductBackofficeInventory.product_backoffice_inventory_code,
            Product.product_code,
            Product.product_name,
            PBI_Transaction.type
        ).all()

        #นำข้อมูลมาจัดหมวดหมู่และคำนวณ (เบิก - คืน = ใช้จริง)
        results = {}
        for row in summary_query:
            inv_id = row.product_backoffice_inventory_id
            
            # ถ้ายังไม่มีสินค้านี้ใน Dictionary ให้สร้างโครงเปล่าๆ รอก่อน
            if inv_id not in results:
                results[inv_id] = {
                    "inventory_id": inv_id,
                    "inventory_code": row.product_backoffice_inventory_code,
                    "product_code": row.product_code,
                    "product_name": row.product_name,
                    "total_removed": 0,  # ยอดเบิกออก
                    "total_added": 0,    # ยอดรับคืน
                    "net_used": 0        # ยอดใช้จริง
                }

            # จับตัวเลขใส่ให้ถูกช่อง
            if row.type == 'REMOVE':
                results[inv_id]['total_removed'] += int(row.total_amount)
            elif row.type == 'ADD':
                results[inv_id]['total_added'] += int(row.total_amount)

        #คำนวณยอดใช้จริง (net_used) สรุปสุดท้าย
        final_list = []
        for inv_id, data in results.items():
            data['net_used'] = data['total_removed'] - data['total_added']
            final_list.append(data)

        return {"success": True, "data": final_list, "document_code": document_code}

    except Exception as e:
        return {"success": False, "message": f"เกิดข้อผิดพลาดในการดึงสรุปยอด: {str(e)}"}
    
def remove_inventory_service(inventory_id, amount, document_code, user_name="System"):
    try:
        inv = ProductBackofficeInventory.query.get(inventory_id)
        if not inv:
            return {"success": False, "message": f"ไม่พบข้อมูล Inventory ID: {inventory_id}"}

        if inv.current_num < amount:
            return {
                "success": False, 
                "message": f"สต๊อกไม่พอ! มีของเหลือแค่ {inv.current_num} ชิ้น แต่ต้องการเบิก {amount} ชิ้น"
            }

        inv.current_num -= amount
        inv.updated_by = user_name
        inv.updated_date = datetime.datetime.now()

        
        transaction = PBI_Transaction(
            product_backoffice_inventory_id=inventory_id,
            amount=amount,
            type="REMOVE", # ระบุชัดเจนว่าเอาออก
            related_document_code=document_code,
            created_by=user_name,
            created_date=datetime.datetime.now(),
            updated_by=user_name,
            updated_date=datetime.datetime.now()
        )
        db.session.add(transaction)
        db.session.commit()

        return {
            "success": True, 
            "message": f"ตัดสต๊อกสำเร็จ! สินค้าเหลือ {inv.current_num} ชิ้น",
            "transaction_id": transaction.pbi_transaction_id
        }

    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": f"เกิดข้อผิดพลาด: {str(e)}"}

def add_inventory_service(inventory_id, amount, document_code, user_name="System"):
    try:
        inv = ProductBackofficeInventory.query.get(inventory_id)
        if not inv:
            return {"success": False, "message": f"ไม่พบข้อมูล Inventory ID: {inventory_id}"}

        # ดักจับเผื่อเผลอส่งค่าติดลบมา
        if amount <= 0:
            return {"success": False, "message": "จำนวนที่รับเข้าต้องมากกว่า 0 ชิ้น"}

        inv.current_num += amount
        inv.updated_by = user_name
        inv.updated_date = datetime.datetime.now()

        # (INSERT ลงตารางลูก)
        transaction = PBI_Transaction(
            product_backoffice_inventory_id=inventory_id,
            amount=amount,
            type="ADD", # เปลี่ยนจาก REMOVE เป็น ADD
            related_document_code=document_code,
            created_by=user_name,
            created_date=datetime.datetime.now(),
            updated_by=user_name,
            updated_date=datetime.datetime.now()
        )
        db.session.add(transaction)

        # ซฟลง Database 
        db.session.commit()

        return {
            "success": True, 
            "message": f"รับของเข้าสำเร็จ! สินค้าเพิ่มเป็น {inv.current_num} ชิ้น",
            "transaction_id": transaction.pbi_transaction_id
        }

    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": f"เกิดข้อผิดพลาด: {str(e)}"}