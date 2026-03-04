from app.con_sqlalchemy import ProductBackofficeInventory, PBI_Transaction
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

def remove_inventory_service(inventory_id, amount, document_code, user_name="System"):
    try:
        # 1. ค้นหากระบะสินค้าที่ต้องการเบิก
        inv = ProductBackofficeInventory.query.get(inventory_id)
        if not inv:
            return {"success": False, "message": f"ไม่พบข้อมูล Inventory ID: {inventory_id}"}

        # 2. เช็คว่าของพอให้เบิกไหม? (ป้องกันของติดลบ)
        if inv.current_num < amount:
            return {
                "success": False, 
                "message": f"สต๊อกไม่พอ! มีของเหลือแค่ {inv.current_num} ชิ้น แต่ต้องการเบิก {amount} ชิ้น"
            }

        # 3. 🌟 ลงมือตัดสต๊อก (อัปเดตตารางแม่)
        inv.current_num -= amount
        inv.updated_by = user_name
        inv.updated_date = datetime.datetime.now()

        # 4. 🌟 จดสมุดประวัติ (INSERT ลงตารางลูก)
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

        # 5. เซฟลง Database รวดเดียว!
        db.session.commit()

        return {
            "success": True, 
            "message": f"ตัดสต๊อกสำเร็จ! สินค้าเหลือ {inv.current_num} ชิ้น",
            "transaction_id": transaction.pbi_transaction_id
        }

    except Exception as e:
        db.session.rollback() # ถ้ามี Error ให้ย้อนกลับข้อมูลทั้งหมด (Safety First)
        return {"success": False, "message": f"เกิดข้อผิดพลาด: {str(e)}"}