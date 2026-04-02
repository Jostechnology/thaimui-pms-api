from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.services.employee_service import delete_employee, get_all_employees, create_employee, get_employee_by_id, update_employee


@app.route("/api/get_employee_list", methods=["GET"])
@verify_required
def api_get_employee_list():
    try:
        search = request.args.get("search", "", type=str)
        status = request.args.get("status", "", type=str)
        data = {"search": search, "status": status}
        result = get_all_employees(data)
        return jsonify({"data": result, "success": True}), 200
    except Exception:
        raise


@app.route("/api/get_employee_id/<int:employee_id>", methods=["GET"])
@verify_required
def api_get_employee_by_id(employee_id):
    try:
        result = get_employee_by_id(employee_id)
        return jsonify({"data": result, "success": True}), 200
    except Exception:
        raise


@app.route("/api/create_employee", methods=["POST"])
@verify_required
def api_create_employee():
    try:
        data = request.get_json()
        result = create_employee(data)
        return jsonify({"data": result, "success": True}), 200
    except Exception:
        raise


@app.route("/api/update_employee/<int:employee_id>", methods=["PUT"])
@verify_required
def api_update_employee(employee_id):
    try:
        data = request.get_json() or {}
        result = update_employee(employee_id, data)
        return jsonify({"data": result, "success": True}), 200
    except Exception:
        raise


@app.route("/api/delete_employee/<int:employee_id>", methods=["DELETE"])
@verify_required
def api_delete_employee(employee_id):
    try:
        data = request.get_json() or {}
        employee_ids = data.get("employee_ids")
        if employee_ids:
            results = []
            for eid in employee_ids:
                results.append(delete_employee(eid))
            result = {"deleted": len(results)}
        else:
            result = delete_employee(employee_id)
        return jsonify({"data": result, "success": True}), 200
    except Exception:
        raise
