from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.ma_sqlalchemy import EmployeeShiftSchema
from app.services import employee_shift_service


@app.route("/api/get_employee_shift/<int:employee_id>", methods=["GET"])
@verify_required
def api_get_employee_shift(employee_id):
    shift = employee_shift_service.get_employee_shift(employee_id)
    return jsonify({"data": EmployeeShiftSchema().dump(shift) if shift else None, "success": True}), 200


@app.route("/api/upsert_employee_shift/<int:employee_id>", methods=["POST", "PUT"])
@verify_required
def api_upsert_employee_shift(employee_id):
    data = request.get_json() or {}
    shift = employee_shift_service.upsert_employee_shift(employee_id, data)
    return jsonify({"data": EmployeeShiftSchema().dump(shift), "success": True}), 200


@app.route("/api/delete_employee_shift/<int:employee_id>", methods=["DELETE"])
@verify_required
def api_delete_employee_shift(employee_id):
    result = employee_shift_service.delete_employee_shift(employee_id)
    return jsonify({"data": result, "success": True}), 200
