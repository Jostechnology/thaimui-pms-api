from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.services.operation_cost_monthly_service import (
    get_all_operation_cost_monthly,
    create_operation_cost_monthly,
    update_operation_cost_monthly,
    delete_operation_cost_monthly,
)


@app.route("/api/get_operation_cost_monthly", methods=["GET"])
@verify_required
def api_get_all_operation_cost_monthly():
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        search = request.args.get("search", "", type=str)
        month = request.args.get("month", "", type=str)
        data = {"page": page, "per_page": per_page, "search": search, "month": month}
        
        result = get_all_operation_cost_monthly(data)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)}), 500


@app.route("/api/create_operation_cost_monthly", methods=["POST"])
@verify_required
def api_create_operation_cost_monthly():
    try:
        data = request.get_json()
        result = create_operation_cost_monthly(data)
        return jsonify({"data": result, "success": True}), 201
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)}), 500


@app.route("/api/update_operation_cost_monthly/<int:operation_cost_monthly_id>", methods=["PUT"])
@verify_required
def api_update_operation_cost_monthly(operation_cost_monthly_id):
    try:
        data = request.get_json()
        result = update_operation_cost_monthly(operation_cost_monthly_id, data)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)}), 500


@app.route("/api/delete_operation_cost_monthly/<int:operation_cost_monthly_id>", methods=["DELETE"])
@verify_required
def api_delete_operation_cost_monthly(operation_cost_monthly_id):
    try:
        result = delete_operation_cost_monthly(operation_cost_monthly_id)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)}), 500

