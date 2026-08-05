from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify, Response
from app.services import item_decode_service
from app.exception import ValidationError


@app.route("/api/decode_item_codes", methods=["POST"])
@verify_required
def decode_item_codes():
    data = request.get_json(silent=True) or {}
    items = data.get("items", [])
    results = item_decode_service.decode_items(items)
    return jsonify({"results": results}), 200


@app.route("/api/upload_item_decode", methods=["POST"])
@verify_required
def upload_item_decode():
    file = request.files.get("file")
    if file is None or not file.filename:
        raise ValidationError("file is required")
    report = item_decode_service.import_workbook(file)
    return jsonify(report), 200


@app.route("/api/get_item_decode_overview", methods=["GET"])
@verify_required
def get_item_decode_overview():
    result = item_decode_service.get_item_decode_overview()
    return jsonify(result), 200


@app.route("/api/get_item_reference_list", methods=["GET"])
@verify_required
def get_item_reference_list():
    data = {
        "page": request.args.get("page", 1, type=int),
        "per_page": request.args.get("per_page", 25, type=int),
        "search": request.args.get("search"),
    }
    result = item_decode_service.get_item_reference_list(data)
    return jsonify(result), 200


@app.route("/api/export_item_decode", methods=["GET"])
@verify_required
def export_item_decode():
    content = item_decode_service.export_workbook()
    return Response(
        content,
        status=200,
        headers={
            "Content-Type": item_decode_service.XLSX_CONTENT_TYPE,
            "Content-Disposition": (
                f'attachment; filename="{item_decode_service.EXPORT_FILENAME}"'
            ),
        },
    )
