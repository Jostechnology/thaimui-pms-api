from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.ma_sqlalchemy import QCCertificateSchema, QCCertificateSchemaDetail
from app.services.test_certificate_service import create_test_certificate, get_test_certificate_list, get_test_certificate_by_id, update_test_certificate


@app.route("/api/test_certificate/create", methods=["POST"])
@verify_required
def api_create_test_certificate():
    data = request.get_json()
    result = create_test_certificate(data)
    return jsonify({"data": QCCertificateSchema().dump(result), "success": True}), 201


@app.route("/api/test_certificate/get_list", methods=["GET"])
@verify_required
def api_get_test_certificate_list():
    search = request.args.get("search", "", type=str)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    result = get_test_certificate_list(page, per_page, search)
    items = QCCertificateSchema(many=True).dump(result["items"])
    pagination = {"total": result["total"], "page": result["page"], "pages": result["pages"]}

    return jsonify({
        "data": {"items": items},
        "pagination": pagination,
        "success": True,
    }), 200


@app.route("/api/test_certificate/get/<int:id>", methods=["GET"])
@verify_required
def api_get_test_certificate_by_id(id):
    result = get_test_certificate_by_id(id)
    return jsonify({"data": QCCertificateSchemaDetail().dump(result), "success": True}), 200


@app.route("/api/test_certificate/update/<int:id>", methods=["PUT"])
@verify_required
def api_update_test_certificate(id):
    data = request.get_json()
    result = update_test_certificate(id, data)
    return jsonify({"data": QCCertificateSchema().dump(result), "success": True}), 200
