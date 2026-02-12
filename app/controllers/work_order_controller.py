from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.services.work_order_service import get_all_work_orders, create_work_order, get_work_order_by_id

@app.route("/api/get_work_order_list", methods=["GET"])
@verify_required
def api_get_work_order_list():
    try:
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 10, type=int)
        search = request.args.get("search", "", type=str)
        data = {"page": page, "limit": limit, "search": search}
        
        result = get_all_work_orders(data)
        return jsonify({"data": result, "success": True}), 200  
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500



@app.route("/api/get_work_order_by_id/<int:work_order_id>", methods=["GET"])
@verify_required
def api_get_work_order_by_id(work_order_id):
    try:
        result = get_work_order_by_id(work_order_id)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@app.route("/api/create_work_order", methods=["POST"])
@verify_required
def api_create_work_order():
    try:
        data = request.get_json()
        result = create_work_order(data)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500