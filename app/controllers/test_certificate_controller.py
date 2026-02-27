import traceback
from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.services.test_certificate_service import create_test_certificate, get_test_certificate_list, get_test_certificate_by_id

@app.route("/api/test_certificate/create", methods=["POST"])
@verify_required
def api_create_test_certificate():
    data = request.get_json()
    result = create_test_certificate(data)
    return jsonify({"data": result, "success": True}), 201

@app.route("/api/test_certificate/get_list", methods=["GET"])
@verify_required
def api_get_test_certificate_list():
    try:
        search = request.args.get("search", "", type=str)
        result = get_test_certificate_list(search)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/test_certificate/get/<int:id>", methods=["GET"])
@verify_required
def api_get_test_certificate_by_id(id):
    try:
        result = get_test_certificate_by_id(id)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
