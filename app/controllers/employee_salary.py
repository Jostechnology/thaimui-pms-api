from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.services.employee_salary_service import (
    get_employee_salary_list,
    get_employee_salary_history,
    update_employee_salary,
)


@app.route("/api/get_employee_salary_list", methods=["GET"])
@verify_required
def api_get_employee_salary_list():
    try:
        search = request.args.get("search", "", type=str)
        data = {"search": search}
        result = get_employee_salary_list(data)
        return jsonify({"data": result, "success": True}), 200
    except Exception:
        raise


@app.route("/api/get_employee_salary_history/<int:employee_id>", methods=["GET"])
@verify_required
def api_get_employee_salary_history(employee_id):
    try:
        month = request.args.get("month", "", type=str)
        data = {"employee_id": employee_id, "month": month}
        result = get_employee_salary_history(data)
        return jsonify({"data": result, "success": True}), 200
    except Exception:
        raise


@app.route("/api/update_employee_salary/<int:employee_id>", methods=["PUT"])
@verify_required
def api_update_employee_salary(employee_id):
    try:
        data = request.get_json() or {}
        result = update_employee_salary(employee_id, data)
        return jsonify({"data": result, "success": True}), 200
    except Exception:
        raise
