from app.repositories import material_repository
from app.services import transaction_service
from app.app import db
from app.exception import ValidationError


def record_material_usage_service(material_list_id, amount, action_type, document_code, user_name="System"):
    try:
        mat = material_repository.get_material_by_id(material_list_id)
        if not mat:
            return {"success": False, "message": f"ไม่พบรายการวัสดุ ID: {material_list_id}"}

        if amount <= 0:
            return {"success": False, "message": "จำนวนต้องมากกว่า 0"}
        if action_type not in ["ADD", "REMOVE"]:
            return {"success": False, "message": "ประเภทต้องเป็น ADD หรือ REMOVE เท่านั้น"}

        transaction_service.create_material_transaction(mat, None, action_type, amount, code=document_code)
        db.session.commit()

        action_text = "เบิกออก" if action_type == "REMOVE" else "รับคืน"
        return {"success": True, "message": f"บันทึกประวัติการ{action_text} จำนวน {amount} ชิ้น สำเร็จ!"}

    except ValidationError as e:
        db.session.rollback()
        return {"success": False, "message": e.message}
    except Exception as e:
        db.session.rollback()
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

def get_all_material_tracking_service(search=None, tracking_type=None):
    try:
        rows = material_repository.get_all_tracking(search=search, tracking_type=tracking_type)
        result = []
        for row in rows:
            total_qty = int(row.total_quantity)
            total_used = int(row.total_used)
            result.append({
                "material_list_id": row.material_list_id,
                "sales_item_id": row.sales_item_id,
                "item_code": row.item_code,
                "item_name": row.item_name,
                "item_description": row.item_description,
                "total_quantity": total_qty,
                "total_used": total_used,
                "remaining_quantity": total_qty - total_used,
            })
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "message": f"เกิดข้อผิดพลาดในการดึงข้อมูล: {str(e)}"}


def get_material_history_service(material_list_id):
    try:
        usage_detail = material_repository.get_usage_detail(material_list_id)
        if not usage_detail:
            return {"success": False, "message": f"ไม่พบรายการวัสดุ ID: {material_list_id}"}

        history_list = []
        for t in usage_detail['transactions']:
            history_list.append({
                "transaction_id": t.transaction_id,
                "action_type": t.type.value if t.type else None,
                "amount": t.amount,
                "document_code": t.related_document_code,
                "action_date": t.created_date.strftime("%Y-%m-%d %H:%M:%S") if t.created_date else None,
                "action_by": t.created_by
            })

        return {"success": True, "data": history_list}
    except Exception as e:
        return {"success": False, "message": f"เกิดข้อผิดพลาด: {str(e)}"}


def validate_material_stock_service(items):
    """ตรวจสอบจำนวนวัตถุดิบว่าเพียงพอหรือไม่"""
    try:
        results = []
        all_valid = True
        for item in items:
            mid = item.get('material_list_id')
            requested = item.get('quantity', 0)

            mat = material_repository.get_material_by_id(mid)
            if not mat:
                results.append({
                    "is_valid": False,
                    "material_list_id": mid,
                    "item_name": "ไม่พบข้อมูล",
                    "requested_quantity": requested,
                    "available_quantity": 0,
                    "shortage": requested,
                    "message": f"ไม่พบวัตถุดิบ ID: {mid}"
                })
                all_valid = False
                continue

            total = mat.quantity or 0
            total_removed = sum(t.amount for t in mat.transactions if t.type == 'REMOVE')
            total_added = sum(t.amount for t in mat.transactions if t.type == 'ADD')
            available = total - (total_removed - total_added)

            is_valid = requested <= available
            if not is_valid:
                all_valid = False

            results.append({
                "is_valid": is_valid,
                "material_list_id": mid,
                "item_name": mat.item_name,
                "requested_quantity": requested,
                "available_quantity": available,
                "shortage": max(0, requested - available),
                "message": "เพียงพอ" if is_valid else f"ไม่เพียงพอ — ขาดอีก {requested - available} ชิ้น"
            })

        return {
            "success": True,
            "data": {
                "is_valid": all_valid,
                "results": results
            }
        }
    except Exception as e:
        return {"success": False, "message": f"เกิดข้อผิดพลาด: {str(e)}"}


def get_transactions_service(sales_item_id, tx_type=None):
    try:
        txns = material_repository.get_transactions_by_sales_item(sales_item_id, tx_type)
        data = []
        for t in txns:
            data.append({
                "transaction_id": t.transaction_id,
                "material_list_id": t.material_list_id,
                "amount": t.amount,
                "type": t.type,
                "related_document_code": t.related_document_code,
                "created_by": t.created_by,
                "updated_by": t.updated_by,
                "created_date": t.created_date.strftime("%Y-%m-%d %H:%M:%S") if t.created_date else None,
                "updated_date": t.updated_date.strftime("%Y-%m-%d %H:%M:%S") if t.updated_date else None
            })
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "message": f"เกิดข้อผิดพลาด: {str(e)}"}