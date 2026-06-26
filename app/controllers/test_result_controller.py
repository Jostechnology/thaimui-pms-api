from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.ma_sqlalchemy import TestResultRequiredItemSchema, TestResultSchema, PickingRequestFullDetailSchema
from app.services.test_result_service import (
    create_test_result,
    start_test_result,
    finalize_test_result,
    get_test_results_by_qc_work_order,
    get_test_results_cost_by_qc_work_order,
    get_test_results_by_doc_entry,
    get_test_result_by_id,
    update_test_result,
    delete_test_result,
    add_required_item,
    get_required_items_for_test_result,
    get_inspection_checklist,
    delete_required_item,
    get_pick_requests_for_test_result,
    assign_employee,
    unassign_employee,
    assign_machine,
    unassign_machine,
    pause_test_result,
    resume_test_result,
)


@app.route("/api/test_result/checklist", methods=["GET"])
@verify_required
def api_get_inspection_checklist():
    try:
        item_group = request.args.get("item_group", None, type=str)
        test_type = request.args.get("test_type", None, type=str)
        checks = get_inspection_checklist(item_group, test_type)
        return jsonify({"data": checks, "success": True}), 200
    except Exception:
        raise


@app.route("/api/qc_work_order/<int:qc_work_order_id>/test_result/create", methods=["POST"])
@verify_required
def api_create_test_result(qc_work_order_id):
    try:
        data = request.get_json()
        result = create_test_result(qc_work_order_id, data)
        return jsonify({"data": "", "success": True}), 201
    except Exception:
        raise


@app.route("/api/test_result/<int:test_result_id>/start", methods=["POST"])
@verify_required
def api_start_test_result(test_result_id):
    try:
        data = request.get_json() or {}
        start_test_result(test_result_id, data)
        return jsonify({"data": "Cool !!", "success": True}), 200
    except Exception:
        raise


@app.route("/api/test_result/<int:test_result_id>/finalize", methods=["PUT"])
@verify_required
def api_finalize_test_result(test_result_id):
    try:
        data = request.get_json()
        result = finalize_test_result(test_result_id, data)
        return jsonify({"data": "Cool!", "success": True}), 200
    except Exception:
        raise


@app.route("/api/qc_work_order/<int:qc_work_order_id>/test_result/list", methods=["GET"])
@verify_required
def api_get_test_results_by_qc_work_order(qc_work_order_id):
    try:
        result = get_test_results_by_qc_work_order(qc_work_order_id)
        return jsonify({"data": result, "success": True}), 200
    except Exception:
        raise


@app.route("/api/qc_work_order/<int:qc_work_order_id>/test_results/cost", methods=["GET"])
@verify_required
def api_get_test_results_cost_by_qc_work_order(qc_work_order_id):
    try:
        result = get_test_results_cost_by_qc_work_order(qc_work_order_id)
        return jsonify({"data": result, "success": True}), 200
    except Exception:
        raise


@app.route("/api/sales_order/<int:doc_entry>/test_result/list", methods=["GET"])
@verify_required
def api_get_test_results_by_doc_entry(doc_entry):
    try:
        result = get_test_results_by_doc_entry(doc_entry)
        return jsonify({"data": result, "success": True}), 200
    except Exception:
        raise


@app.route("/api/test_result/<int:test_result_id>", methods=["GET"])
@verify_required
def api_get_test_result_by_id(test_result_id):
    try:
        result = get_test_result_by_id(test_result_id)
        return jsonify({"data": result, "success": True}), 200
    except Exception:
        raise


@app.route("/api/test_result/<int:test_result_id>/update", methods=["PUT"])
@verify_required
def api_update_test_result(test_result_id):
    try:
        data = request.get_json()
        result = update_test_result(test_result_id, data)
        return jsonify({"data": result, "success": True}), 200
    except Exception:
        raise


@app.route("/api/test_result/<int:test_result_id>/delete", methods=["DELETE"])
@verify_required
def api_delete_test_result(test_result_id):
    try:
        result = delete_test_result(test_result_id)
        return jsonify({"data": result, "success": True}), 200
    except Exception:
        raise


@app.route("/api/test_result/<int:test_result_id>/pick_requests", methods=["GET"])
@verify_required
def api_test_result_pick_requests(test_result_id):
    result = get_pick_requests_for_test_result(test_result_id)
    return jsonify({"data": PickingRequestFullDetailSchema(many=True).dump(result), "success": True}), 200


@app.route("/api/test_result/<int:test_result_id>/required_items", methods=["GET"])
@verify_required
def api_test_result_get_required_items(test_result_id):
    try:
        result = get_required_items_for_test_result(test_result_id)
        return jsonify({"data": TestResultRequiredItemSchema(many=True).dump(result), "success": True}), 200
    except Exception:
        raise


@app.route("/api/test_result/<int:test_result_id>/required_items", methods=["POST"])
@verify_required
def api_test_result_add_required_item(test_result_id):
    try:
        payload = request.get_json() or {}
        data = payload.get("data", [])
        if not isinstance(data, list):
            data = [data]
        result = add_required_item(test_result_id, data)
        return jsonify({"data": TestResultRequiredItemSchema(many=True).dump(result), "success": True}), 201
    except Exception:
        raise


@app.route("/api/test_result/<int:test_result_id>/required_items/<int:required_item_id>", methods=["DELETE"])
@verify_required
def api_delete_required_item(test_result_id, required_item_id):
    try:
        result = delete_required_item(test_result_id, required_item_id)
        return jsonify({"data": TestResultRequiredItemSchema(many=True).dump(result), "success": True}), 200
    except Exception:
        raise


@app.route("/api/test_result/<int:test_result_id>/assign_employee", methods=["POST"])
@verify_required
def api_assign_employee_to_test_result(test_result_id):
    data = request.get_json() or {}
    employee_id = data.get("employee_id")
    if not employee_id:
        from app.exception import MissingFieldsError
        raise MissingFieldsError("employee_id is required")
    result = assign_employee(test_result_id, employee_id)
    return jsonify({"data": TestResultSchema().dump(result), "success": True}), 200


@app.route("/api/test_result/<int:test_result_id>/unassign_employee", methods=["POST"])
@verify_required
def api_unassign_employee_from_test_result(test_result_id):
    data = request.get_json() or {}
    employee_id = data.get("employee_id")
    if not employee_id:
        from app.exception import MissingFieldsError
        raise MissingFieldsError("employee_id is required")
    result = unassign_employee(test_result_id, employee_id)
    return jsonify({"data": TestResultSchema().dump(result), "success": True}), 200


@app.route("/api/test_result/<int:test_result_id>/assign_machine", methods=["POST"])
@verify_required
def api_assign_machine_to_test_result(test_result_id):
    data = request.get_json() or {}
    machine_id = data.get("machine_id")
    if not machine_id:
        from app.exception import MissingFieldsError
        raise MissingFieldsError("machine_id is required")
    result = assign_machine(test_result_id, machine_id)
    return jsonify({"data": TestResultSchema().dump(result), "success": True}), 200


@app.route("/api/test_result/<int:test_result_id>/unassign_machine", methods=["POST"])
@verify_required
def api_unassign_machine_from_test_result(test_result_id):
    data = request.get_json() or {}
    machine_id = data.get("machine_id")
    if not machine_id:
        from app.exception import MissingFieldsError
        raise MissingFieldsError("machine_id is required")
    result = unassign_machine(test_result_id, machine_id)
    return jsonify({"data": TestResultSchema().dump(result), "success": True}), 200


@app.route("/api/test_result/<int:test_result_id>/pause", methods=["POST"])
@verify_required
def api_pause_test_result(test_result_id):
    data = request.get_json() or {}
    result = pause_test_result(test_result_id, data)
    return jsonify({"data": TestResultSchema().dump(result), "success": True}), 200


@app.route("/api/test_result/<int:test_result_id>/resume", methods=["POST"])
@verify_required
def api_resume_test_result(test_result_id):
    result = resume_test_result(test_result_id)
    return jsonify({"data": TestResultSchema().dump(result), "success": True}), 200
