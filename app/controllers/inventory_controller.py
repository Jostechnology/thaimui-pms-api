from flask import request, jsonify
from app.app import app
from app.api_auth import verify_required
from app.services.inventory_service import record_material_usage_service, get_material_tracking_summary,get_material_history_service

#API สำหรับ "จดประวัติ (เบิกออก/รับคืน)"
@app.route("/api/material/transaction", methods=["POST", "OPTIONS"])
@verify_required
def api_record_material_transaction():
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200

    try:
        data = request.get_json()
        
        material_list_id = data.get("material_list_id")
        amount = data.get("amount")
        action_type = data.get("type") # ส่งค่า "ADD" หรือ "REMOVE"
        document_code = data.get("related_document_code")

        # เช็คว่าส่งข้อมูลมาครบไหม
        if not all([material_list_id, amount, action_type, document_code]):
            return jsonify({"success": False, "message": "ส่งข้อมูลไม่ครบถ้วน!"}), 400

        user_name = "Admin_Camp" # สมมติชื่อคนทำรายการ

        # โยนให้ Service จัดการจดลงสมุด
        result = record_material_usage_service(
            material_list_id=int(material_list_id), 
            amount=int(amount), 
            action_type=action_type.upper(), 
            document_code=document_code, 
            user_name=user_name
        )
        
        status_code = 200 if result["success"] else 400
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/material/summary/<int:sales_item_id>", methods=["GET", "OPTIONS"])
@verify_required
def api_get_material_summary(sales_item_id):
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200

    try:
        result = get_material_tracking_summary(sales_item_id)
        
        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/material/history/<int:material_list_id>", methods=["GET", "OPTIONS"])
@verify_required
def api_get_material_history(material_list_id):
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200

    try:
        result = get_material_history_service(material_list_id)
        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500