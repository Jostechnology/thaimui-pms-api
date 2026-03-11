from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.ma_sqlalchemy import WorkOrderSchema, WorkOrderSchemaDetail
from app.services.work_order_service import get_all_work_orders, create_work_order, get_work_order_by_id
from app.con_sqlalchemy import WorkOrderStatus

@app.route("/api/get_work_order_list", methods=["GET"])
@verify_required
def api_get_work_order_list():
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        search = request.args.get("search", "", type=str)
        filter = request.args.get("filter", None, type=WorkOrderStatus)
        month = request.args.get("month", "", type=str)
        data = {"page": page, "per_page": per_page, "search": search, "filter": filter, "month": month}
        result = get_all_work_orders(data)
        return jsonify({
            "data": {"items": WorkOrderSchema(many=True).dump(result["items"])},
            "pagination": {"total": result["total"], "page": result["page"], "pages": result["pages"]},
            "success": True,
        }), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500



@app.route("/api/get_work_order_by_id/<int:work_order_id>", methods=["GET"])
@verify_required
def api_get_work_order_by_id(work_order_id):
    try:
        result = get_work_order_by_id(work_order_id)
        return jsonify({"data": WorkOrderSchemaDetail().dump(result), "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/create_work_order", methods=["POST"])
@verify_required
def api_create_work_order():
    try:
        data = request.get_json()
        result = create_work_order(data)
        return jsonify({"data": {"item": WorkOrderSchema().dump(result)}, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500