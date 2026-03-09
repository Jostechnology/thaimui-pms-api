from flask import request, jsonify
from app.app import app
from app.api_auth import verify_required
from app.services.material_stock_service import (
    get_all_tracking_service,
    get_stock_summary_service,
    get_usage_detail_service,
    validate_material_stock_service,
    get_transactions_service,
)


@app.route("/api/material_stock/tracking", methods=["GET", "OPTIONS"])
@verify_required
def api_material_stock_tracking():
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200
    try:
        search = request.args.get("search", None)
        tracking_type = request.args.get("type", None)
        result = get_all_tracking_service(search=search, tracking_type=tracking_type)
        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/material_stock/summary/<int:sales_item_id>", methods=["GET", "OPTIONS"])
@verify_required
def api_material_stock_summary(sales_item_id):
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200
    try:
        result = get_stock_summary_service(sales_item_id)
        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/material_stock/usage_detail/<int:material_list_id>", methods=["GET", "OPTIONS"])
@verify_required
def api_material_stock_usage_detail(material_list_id):
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200
    try:
        result = get_usage_detail_service(material_list_id)
        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/material_stock/validate", methods=["POST", "OPTIONS"])
@verify_required
def api_material_stock_validate():
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200
    try:
        data = request.get_json()
        items = data.get("items", [])
        if not items:
            return jsonify({"success": False, "message": "ไม่มีรายการวัตถุดิบที่ต้องตรวจสอบ"}), 400
        result = validate_material_stock_service(items)
        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/material_stock/transactions/<int:sales_item_id>", methods=["GET", "OPTIONS"])
@verify_required
def api_material_stock_transactions(sales_item_id):
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200
    try:
        tx_type = request.args.get("type", None)
        result = get_transactions_service(sales_item_id, tx_type)
        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
