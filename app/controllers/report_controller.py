from flask import jsonify, request, send_file
from io import BytesIO

from app.api_auth import verify_required
from app.app import app
from app.services import report_service


@app.route("/api/reports/definitions", methods=["GET"])
@verify_required
def api_get_report_definitions():
    return jsonify({"data": {"items": report_service.list_definitions()}, "success": True}), 200


@app.route("/api/reports/preview", methods=["POST"])
@verify_required
def api_preview_report():
    body = request.get_json(silent=True) or {}
    result = report_service.preview(
        code=body.get("code"),
        params=body.get("params") or {},
        page=body.get("page", 1),
        per_page=body.get("per_page", 25),
    )
    return jsonify({"data": result, "success": True}), 200


@app.route("/api/reports/export", methods=["POST"])
@verify_required
def api_export_report():
    body = request.get_json(silent=True) or {}
    payload, mime, filename = report_service.export(
        code=body.get("code"),
        params=body.get("params") or {},
        fmt=body.get("format", "xlsx"),
    )
    if mime == "application/json":
        return jsonify({"data": payload, "success": True}), 200
    return send_file(
        BytesIO(payload),
        mimetype=mime,
        as_attachment=True,
        download_name=filename,
    )
