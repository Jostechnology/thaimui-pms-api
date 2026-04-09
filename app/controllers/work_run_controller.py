from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.ma_sqlalchemy import WorkRunDisplaySchema, WorkRunSchema
from app.services.work_run_service import (
    create_work_run,
    complete_work_run,
    get_work_run_by_id,
    get_work_runs_by_work_order,
    get_work_run_detail,
    start_work_run,
    pause_work_run,
    resume_work_run,
    assign_employee,
    unassign_employee,
    assign_machine,
    unassign_machine,
)


@app.route("/api/work_run/<int:work_run_id>", methods=["GET"])
@verify_required
def api_get_work_run(work_run_id):
    result = get_work_run_by_id(work_run_id)
    return jsonify({"data": WorkRunDisplaySchema().dump(result), "success": True}), 200


@app.route("/api/work_run/<int:work_run_id>/detail", methods=["GET"])
@verify_required
def api_get_work_run_detail(work_run_id):
    result = get_work_run_detail(work_run_id)
    return jsonify({"data": result, "success": True}), 200


@app.route("/api/work_order/<int:work_order_id>/work_run/create", methods=["POST"])
@verify_required
def api_create_work_run(work_order_id):
    data = request.get_json() or {}
    result = create_work_run(work_order_id, data)
    return jsonify({"data": WorkRunSchema().dump(result), "success": True}), 201


@app.route("/api/work_order/<int:work_order_id>/work_runs", methods=["GET"])
@verify_required
def api_get_work_runs(work_order_id):
    result = get_work_runs_by_work_order(work_order_id)
    return jsonify({"data": WorkRunDisplaySchema(many=True).dump(result), "success": True}), 200


@app.route("/api/work_run/<int:work_run_id>/start", methods=["POST"])
@verify_required
def api_start_work_run(work_run_id):
    result = start_work_run(work_run_id)
    return jsonify({"data": WorkRunDisplaySchema().dump(result), "success": True}), 200


@app.route("/api/work_run/<int:work_run_id>/pause", methods=["POST"])
@verify_required
def api_pause_work_run(work_run_id):
    data = request.get_json() or {}
    result = pause_work_run(work_run_id, data)
    return jsonify({"data": WorkRunDisplaySchema().dump(result), "success": True}), 200


@app.route("/api/work_run/<int:work_run_id>/resume", methods=["POST"])
@verify_required
def api_resume_work_run(work_run_id):
    result = resume_work_run(work_run_id)
    return jsonify({"data": WorkRunDisplaySchema().dump(result), "success": True}), 200


@app.route("/api/work_run/<int:work_run_id>/complete", methods=["PUT"])
@verify_required
def api_complete_work_run(work_run_id):
    data = request.get_json() or {}
    result = complete_work_run(work_run_id, data)
    return jsonify({"data": WorkRunSchema().dump(result), "success": True}), 200


@app.route("/api/work_run/<int:work_run_id>/assign_employee", methods=["POST"])
@verify_required
def api_assign_employee(work_run_id):
    data = request.get_json() or {}
    employee_id = data.get("employee_id")
    if not employee_id:
        from app.exception import MissingFieldsError
        raise MissingFieldsError("employee_id is required")
    result = assign_employee(work_run_id, employee_id)
    return jsonify({"data": WorkRunDisplaySchema().dump(result), "success": True}), 200


@app.route("/api/work_run/<int:work_run_id>/unassign_employee", methods=["POST"])
@verify_required
def api_unassign_employee(work_run_id):
    data = request.get_json() or {}
    employee_id = data.get("employee_id")
    if not employee_id:
        from app.exception import MissingFieldsError
        raise MissingFieldsError("employee_id is required")
    result = unassign_employee(work_run_id, employee_id)
    return jsonify({"data": WorkRunDisplaySchema().dump(result), "success": True}), 200


@app.route("/api/work_run/<int:work_run_id>/assign_machine", methods=["POST"])
@verify_required
def api_assign_machine(work_run_id):
    data = request.get_json() or {}
    machine_id = data.get("machine_id")
    if not machine_id:
        from app.exception import MissingFieldsError
        raise MissingFieldsError("machine_id is required")
    result = assign_machine(work_run_id, machine_id)
    return jsonify({"data": WorkRunDisplaySchema().dump(result), "success": True}), 200


@app.route("/api/work_run/<int:work_run_id>/unassign_machine", methods=["POST"])
@verify_required
def api_unassign_machine(work_run_id):
    data = request.get_json() or {}
    machine_id = data.get("machine_id")
    if not machine_id:
        from app.exception import MissingFieldsError
        raise MissingFieldsError("machine_id is required")
    result = unassign_machine(work_run_id, machine_id)
    return jsonify({"data": WorkRunDisplaySchema().dump(result), "success": True}), 200
