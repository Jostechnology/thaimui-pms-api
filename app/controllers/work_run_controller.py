from app.api_auth import verify_required
from app.app import app
from app.exception import AppException
from flask import request, jsonify
from app.ma_sqlalchemy import WorkRunSchema
from app.services.work_run_service import create_work_run, complete_work_run, get_work_runs_by_work_order


@app.route("/api/work_order/<int:work_order_id>/work_run/create", methods=["POST"])
@verify_required
def api_create_work_run(work_order_id):
    try:
        data = request.get_json()
        result = create_work_run(work_order_id, data)
        return jsonify({"data": WorkRunSchema().dump(result), "success": True}), 201
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/work_order/<int:work_order_id>/work_runs", methods=["GET"])
@verify_required
def api_get_work_runs(work_order_id):
    try:
        result = get_work_runs_by_work_order(work_order_id)
        return jsonify({"data": WorkRunSchema(many=True).dump(result), "success": True}), 200
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/work_run/<int:work_run_id>/complete", methods=["PUT"])
@verify_required
def api_complete_work_run(work_run_id):
    try:
        result = complete_work_run(work_run_id)
        return jsonify({"data": WorkRunSchema().dump(result), "success": True}), 200
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500
