import traceback
from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.services.test_certificate_service import create_test_certificate

@app.route("/api/test_certificate/create", methods=["POST"])
@verify_required
def api_create_test_certificate():
    data = request.get_json()
    result = create_test_certificate(data)
    return jsonify({"data": result, "success": True}), 201