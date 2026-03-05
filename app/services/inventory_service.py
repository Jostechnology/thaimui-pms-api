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

        if action_type == "REMOVE":
            #หาว่า แผนให้มากี่ชิ้น?
            planned_qty = mat.item_num 
            
            # หาว่า เคยเบิกไปแล้วกี่ชิ้น?
            total_removed = sum([t.amount for t in mat.transactions if t.type == 'REMOVE'])
            total_added = sum([t.amount for t in mat.transactions if t.type == 'ADD'])
            actual_used = total_removed - total_added
            
            # คำนวณ "โควต้าคงเหลือ"
            remaining_quota = planned_qty - actual_used

            if amount > remaining_quota:
                return {
                    "success": False, 
                    "message": f"เบิกไม่ได้! โควต้าเหลือแค่ {remaining_quota} ชิ้น (แผน: {planned_qty}, ใช้ไปแล้ว: {actual_used})"
                }
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

def get_material_history_service(material_list_id):
    try:
        # ดึงประวัติของ Material นี้มาทั้งหมด เรียงจากล่าสุดไปเก่าสุด
        transactions = MaterialTransaction.query.filter_by(
            material_list_id=material_list_id
        ).order_by(MaterialTransaction.created_date.desc()).all()

        history_list = []
        for t in transactions:
            history_list.append({
                "transaction_id": t.transaction_id,
                "action_type": "เบิกใช้งาน" if t.type == "REMOVE" else "รับคืนคลัง",
                "amount": t.amount,
                "document_code": t.related_document_code,
                "action_date": t.created_date.strftime("%Y-%m-%d %H:%M:%S") if t.created_date else None,
                "action_by": t.created_by
            })

        return {"success": True, "data": history_list}
    except Exception as e:
        return {"success": False, "message": f"เกิดข้อผิดพลาด: {str(e)}"}