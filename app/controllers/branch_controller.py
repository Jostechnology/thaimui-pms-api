from app.api_auth import verify_required, decode_and_verify_permission_jwt
from app.app import app, db
from flask import request, jsonify, g
from app.services import branch_service

@app.route("/api/get_all_branchs", methods=["GET", "POST"])
def api_get_all_branchs():
    branchs = branch_service.get_all_branchs()
    return jsonify({"data" : branchs, "success" : True}), 200


@app.route("/api/create_branch", methods=["POST"])
@verify_required
def api_create_branch():
    try:
        data = request.get_json()
        result = branch_service.create_branch(data)
        return jsonify({"data" : result, "success" : True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error" : str(e)}), 500

@app.route("/api/update_branch/<int:branch_id>", methods=["PUT"])
@verify_required
def api_update_branch(branch_id):
    try:
        data = request.get_json()
        result = branch_service.update_branch(branch_id, data)
        return jsonify({"data" : result, "success" : True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error" : str(e)}), 500

@app.route("/api/delete_branch/<int:branch_id>", methods=["DELETE"])
@verify_required
def api_delete_branch(branch_id):
    try:
        data = request.get_json()
        result = branch_service.delete_branch(branch_id)
        return jsonify({"data" : result, "success" : True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error" : str(e)}), 500

    
