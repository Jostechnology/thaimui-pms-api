from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
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
