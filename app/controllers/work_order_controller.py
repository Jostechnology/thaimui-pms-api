from app.api_auth import get_requests_permission, verify_required, verify_required_center
from app.app import app
from flask import request, jsonify
from app.controllers.sales_order_controller import _has_unassigned_sales_order_create_permission
from app.ma_sqlalchemy import WorkOrderSchema, WorkOrderSchemaDetail
from app.services.work_order_service import get_all_work_orders, create_work_order, get_work_order_by_id, get_work_order_by_center_sales_item_id
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
        start_date = request.args.get("start_date", None, type=str)
        end_date = request.args.get("end_date", None, type=str)
        data = {"page": page, "per_page": per_page, "search": search, "filter": filter, "month": month, "start_date": start_date, "end_date": end_date}
        result = get_all_work_orders(data)
        return jsonify({
            "data": {"items": WorkOrderSchema(many=True).dump(result["items"])},
            "pagination": {"total": result["total"], "page": result["page"], "pages": result["pages"]},
            "success": True,
        }), 200
    except Exception:
        raise


@app.route("/api/get_work_order_by_id/<int:work_order_id>", methods=["GET"])
@verify_required
def api_get_work_order_by_id(work_order_id):
    try:
        result = get_work_order_by_id(work_order_id)
        return jsonify({"data": WorkOrderSchemaDetail().dump(result), "success": True}), 200
    except Exception:
        raise

@app.route("/api/get_work_order_by_center_sales_item_id/<int:center_sales_item_id>", methods=["GET"])
@verify_required_center
def api_get_work_order_by_center_sales_item_id(center_sales_item_id):
    try:
        result = get_work_order_by_center_sales_item_id(center_sales_item_id)
        return jsonify({"data": WorkOrderSchemaDetail().dump(result) if result else None, "success": True}), 200
    except Exception:
        raise


@app.route("/api/create_work_order", methods=["POST"])
@verify_required
def api_create_work_order():
    try:
        data = request.get_json()
        unassigned_permission = _has_unassigned_sales_order_create_permission()
        result = create_work_order(data, unassigned_permission)
        return jsonify({"data": {"item": WorkOrderSchemaDetail().dump(result)}, "success": True}), 200
    except Exception:
        raise
