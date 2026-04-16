from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.ma_sqlalchemy import TestResultRequiredItemSchema
from app.services.test_result_service import (
    create_test_result,
    start_test_result,
    finalize_test_result,
    get_test_results_by_qc_work_order,
    get_test_results_by_doc_entry,
    get_test_result_by_id,
    update_test_result,
    delete_test_result,
    add_required_item,
    get_required_items_for_test_result,
    delete_required_item,
)


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
        result = start_test_result(test_result_id)
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
