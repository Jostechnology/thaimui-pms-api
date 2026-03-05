import datetime
from app.con_sqlalchemy import MaterialTransaction
from app.repositories import material_repository 

def record_material_usage_service(material_list_id, amount, action_type, document_code, user_name="System"):
    try:
        mat = material_repository.get_material_by_id(material_list_id)
        if not mat:
            return {"success": False, "message": f"ไม่พบรายการวัสดุ ID: {material_list_id}"}

        if amount <= 0:
            return {"success": False, "message": "จำนวนต้องมากกว่า 0"}
        if action_type not in ["ADD", "REMOVE"]:
            return {"success": False, "message": "ประเภทต้องเป็น ADD หรือ REMOVE เท่านั้น"}

        transaction = MaterialTransaction(
            material_list_id=material_list_id,
            amount=amount,
            type=action_type, 
            related_document_code=document_code,
            created_by=user_name,
            created_date=datetime.datetime.now()
        )
        
        material_repository.save_material_transaction(transaction)

        action_text = "เบิกออก" if action_type == "REMOVE" else "รับคืน"
        return {"success": True, "message": f"บันทึกประวัติการ{action_text} จำนวน {amount} ชิ้น สำเร็จ!"}

    except Exception as e:
        material_repository.rollback_transaction()
        return {"success": False, "message": f"เกิดข้อผิดพลาด: {str(e)}"}


def get_material_tracking_summary(sales_item_id):
    try:
        summary_query = material_repository.get_tracking_summary_query(sales_item_id)

        result = []
        for row in summary_query:
            actual_used = int(row.total_removed - row.total_added)
            variance = int(actual_used - row.planned_qty)
            result.append({
                "material_list_id": row.material_list_id,
                "item_code": row.item_code,
                "item_name": row.item_name,
                "planned_qty": row.planned_qty,
                "actual_used": actual_used,
                "variance": variance
            })

        return {"success": True, "data": result}

    except Exception as e:
        return {"success": False, "message": f"เกิดข้อผิดพลาดในการดึงข้อมูล: {str(e)}"}