import traceback
from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.services.test_result_service import (
    create_test_result,
    get_test_results_by_qc_work_order,
    get_test_results_by_doc_entry,
    get_test_result_by_id,
    update_test_result,
    delete_test_result,
)


@app.route("/api/work_run/<int:work_run_id>/test_result/create", methods=["POST"])
@verify_required
def api_create_test_result(work_run_id):
    try:
        data = request.get_json()
        result = create_test_result(work_run_id, data)
        return jsonify({"data": result, "success": True}), 201
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/qc_work_order/<int:qc_work_order_id>/test_result/list", methods=["GET"])
@verify_required
def api_get_test_results_by_qc_work_order(qc_work_order_id):
    try:
        result = get_test_results_by_qc_work_order(qc_work_order_id)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/sales_order/<int:doc_entry>/test_result/list", methods=["GET"])
@verify_required
def api_get_test_results_by_doc_entry(doc_entry):
    try:
        result = get_test_results_by_doc_entry(doc_entry)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/test_result/<int:test_result_id>", methods=["GET"])
@verify_required
def api_get_test_result_by_id(test_result_id):
    try:
        result = get_test_result_by_id(test_result_id)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/test_result/<int:test_result_id>/update", methods=["PUT"])
@verify_required
def api_update_test_result(test_result_id):
    try:
        data = request.get_json()
        result = update_test_result(test_result_id, data)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/test_result/<int:test_result_id>/delete", methods=["DELETE"])
@verify_required
def api_delete_test_result(test_result_id):
    try:
        result = delete_test_result(test_result_id)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
