from flask import request, jsonify

from app.api_auth import verify_required
from app.app import app
from app.services import report_service


@app.route("/api/get_report_definitions", methods=["GET"])
@verify_required
def api_get_report_definitions():
    try:
        result = report_service.list_definitions()
        return jsonify({"data": result, "success": True}), 200
    except Exception:
        raise


@app.route("/api/get_report_run/<string:run_id>", methods=["GET"])
@verify_required
def api_get_report_run(run_id):
    try:
        result = report_service.get_run(run_id)
        return jsonify({"data": result, "success": True}), 200
    except Exception:
        raise


@app.route("/api/get_report_runs", methods=["GET"])
@verify_required
def api_get_report_runs():
    try:
        data = {
            "page": request.args.get("page", 1, type=int),
            "per_page": request.args.get("per_page", 20, type=int),
            "code": request.args.get("code", None, type=str) or None,
            "requested_by": request.args.get("requested_by", None, type=str) or None,
            "status": request.args.get("status", None, type=str) or None,
        }
        result = report_service.list_runs(data)
        return jsonify({"data": result, "success": True}), 200
    except Exception:
        raise


@app.route("/api/create_report_run", methods=["POST"])
@verify_required
def api_create_report_run():
    try:
        payload = request.get_json() or {}
        code = payload.get("code")
        params = payload.get("params") or {}
        formats = payload.get("formats") or ["json"]
        result = report_service.create_run(code, params, formats)
        return jsonify({"data": result, "success": True}), 201
    except Exception:
        raise


@app.route("/api/preview_report", methods=["POST"])
@verify_required
def api_preview_report():
    try:
        payload = request.get_json() or {}
        code = payload.get("code")
        params = payload.get("params") or {}
        page = payload.get("page")
        per_page = payload.get("per_page")
        result = report_service.preview_run(code, params, page=page, per_page=per_page)
        return jsonify({"data": result, "success": True}), 200
    except Exception:
        raise
