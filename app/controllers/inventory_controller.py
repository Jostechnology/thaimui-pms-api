from flask import request, jsonify
from app.app import app
from app.api_auth import verify_required
from app.services.inventory_service import remove_inventory_service
from app.api_auth import verify_required

@app.route("/api/inventory/remove", methods=["POST", "OPTIONS"])
@verify_required
def api_remove_inventory():
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200

    try:
        data = request.get_json()
        
        inventory_id = data.get("product_backoffice_inventory_id")
        amount = data.get("amount")
        document_code = data.get("related_document_code")
        
        if not inventory_id or not amount or not document_code:
            return jsonify({"success": False, "message": "ส่งข้อมูลไม่ครบถ้วน!"}), 400
            
        user_name = "Admin_Camp" 

        result = remove_inventory_service(inventory_id, int(amount), document_code, user_name)
        
        status_code = 200 if result["success"] else 400
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@verify_required
def process_remove_inventory():
    try:
        data = request.get_json()
        
        inventory_id = data.get("product_backoffice_inventory_id")
        amount = data.get("amount")
        document_code = data.get("related_document_code")
        
        if not inventory_id or not amount or not document_code:
            return jsonify({
                "success": False, 
                "message": "ข้อมูลไม่ครบถ้วน (ต้องการ inventory_id, amount, related_document_code)"
            }), 400
            
        result = inventory_service.remove_inventory(inventory_id, int(amount), document_code)
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500