from app.repositories import material_repository


def get_all_tracking_service(search=None, tracking_type=None):
    try:
        rows = material_repository.get_all_tracking(search=search, tracking_type=tracking_type)
        data = []
        for row in rows:
            total = int(row.total_quantity or 0)
            prod = int(row.used_in_production or 0)
            test = int(row.used_in_testing or 0)
            remaining = total - prod - test
            data.append({
                "material_list_id": row.material_list_id,
                "sales_item_id": row.sales_item_id,
                "item_code": row.item_code,
                "item_name": row.item_name,
                "item_description": row.item_description or "",
                "total_quantity": total,
                "used_in_production": prod,
                "used_in_testing": test,
                "remaining_quantity": remaining
            })
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "message": f"เกิดข้อผิดพลาด: {str(e)}"}


def get_stock_summary_service(sales_item_id):
    try:
        rows = material_repository.get_material_stock_summary(sales_item_id)
        data = []
        for row in rows:
            total = int(row.total_quantity or 0)
            prod = int(row.used_in_production or 0)
            test = int(row.used_in_testing or 0)
            remaining = total - prod - test
            data.append({
                "material_list_id": row.material_list_id,
                "sales_item_id": row.sales_item_id,
                "item_code": row.item_code,
                "item_name": row.item_name,
                "item_description": row.item_description or "",
                "total_quantity": total,
                "used_in_production": prod,
                "used_in_testing": test,
                "remaining_quantity": remaining
            })
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "message": f"เกิดข้อผิดพลาด: {str(e)}"}


def get_usage_detail_service(material_list_id):
    try:
        result = material_repository.get_usage_detail(material_list_id)
        if result is None:
            return {"success": False, "message": f"ไม่พบวัตถุดิบ ID: {material_list_id}"}

        mat = result['material']
        prod_usages = result['production_usages']
        txns = result['transactions']

        # คำนวณ used_in_production, used_in_testing
        used_in_production = sum(u.quantity_used for u in prod_usages)
        used_in_testing = sum(t.amount for t in txns if t.type == 'REMOVE')
        total = mat.item_num or 0
        remaining = total - used_in_production - used_in_testing

        production_list = []
        for u in prod_usages:
            production_list.append({
                "usage_id": u.usage_id,
                "work_order_doc_num": str(u.work_order_doc_num) if u.work_order_doc_num else "",
                "work_order_status": u.work_order_status.value if hasattr(u.work_order_status, 'value') else str(u.work_order_status),
                "component_name": u.component_name,
                "quantity_used": u.quantity_used,
                "created_date": u.created_date.strftime("%Y-%m-%d %H:%M:%S") if u.created_date else None
            })

        transaction_list = []
        for t in txns:
            transaction_list.append({
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

        data = {
            "material_list_id": mat.material_list_id,
            "item_code": mat.item_code,
            "item_name": mat.item_name,
            "item_description": mat.item_description or "",
            "total_quantity": total,
            "used_in_production": used_in_production,
            "used_in_testing": used_in_testing,
            "remaining_quantity": remaining,
            "production_usages": production_list,
            "transactions": transaction_list
        }
        return {"success": True, "data": data}
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

            total = mat.item_num or 0
            prod_used = sum(u.quantity_used for u in mat.component_usages)
            test_used = sum(t.amount for t in mat.transactions if t.type == 'REMOVE')
            available = total - prod_used - test_used

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
