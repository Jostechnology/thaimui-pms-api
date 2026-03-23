from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.services import document_code_service


@app.route("/api/document_code/get", methods=["GET"])
@verify_required
def get_doc_codes():
    result = document_code_service.get_document_code_list()
    return jsonify({**result, "success": True}), 200


@app.route("/api/document_code/create", methods=["POST"])
@verify_required
def create_doc_codes():
    data = request.json.get("data")
    document_code_service.create_document_code(data)
    return jsonify({"success": True}), 200


@app.route("/api/document_code/edit", methods=["PUT"])
@verify_required
def edit_doc_codes():
    data = request.json.get("data")
    gen_number_id = data.get("gen_number_id")
    document_code_service.edit_document_code(gen_number_id, data)
    return jsonify({"success": True}), 200


@app.route("/api/generate_number", methods=["POST"])
@verify_required
def api_generate_number():
    data = request.get_json()
    gen_number_type = data.get("gen_number_type")
    count = data.get("count", 1)
    result = document_code_service.generate_number(gen_number_type, count)
    if count == 1:
        return jsonify({"data": {"gen_number": result}, "success": True}), 200
    return jsonify({"data": {"gen_numbers": result}, "success": True}), 200
