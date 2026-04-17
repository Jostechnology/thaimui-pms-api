from app.api_auth import verify_required, verify_required_center
from app.app import app
from flask import request, jsonify
from app.services import branch_service, cache_service
from app.ma_sqlalchemy import BranchSchema

def _branch_key(branch_id):
    return f"branch_{branch_id}"

def _all_branch_key():
    return "all_branch"

BRANCH_TTL = 7200

@app.route("/api/get_all_branchs", methods=["GET", "POST"])
@verify_required_center
def api_get_all_branchs():
    key = _all_branch_key()
    cached = cache_service.get(key)
    if cached:
        return jsonify(cached), 200
    branchs = branch_service.get_all_branchs()
    branches_data = BranchSchema(many=True).dump(branchs)
    response_dict = {"data": branches_data, "success": True}
    cache_service.set(key, response_dict, ttl=BRANCH_TTL)
    return jsonify(response_dict), 200


@app.route("/api/create_branch", methods=["POST"])
@verify_required
def api_create_branch():
    data = request.get_json()
    result = branch_service.create_branch(data)
    key = _all_branch_key()
    cache_service.delete(key)
    return jsonify({"data": BranchSchema().dump(result), "success": True}), 200


@app.route("/api/update_branch/<int:branch_id>", methods=["PUT"])
@verify_required
def api_update_branch(branch_id):
    data = request.get_json()
    result = branch_service.update_branch(branch_id, data)
    key = _all_branch_key()
    cache_service.delete(key)
    return jsonify({"data": BranchSchema().dump(result), "success": True}), 200


@app.route("/api/delete_branch/<int:branch_id>", methods=["PUT"])
@verify_required
def api_delete_branch(branch_id):
    data = request.get_json()
    is_active = data.get("is_active", False) if data else False
    branch = branch_service.delete_branch(branch_id, is_active)
    status_text = "เปิดการใช้งาน" if is_active else "ปิดการใช้งาน"
    key = _all_branch_key()
    cache_service.delete(key)
    return jsonify({"data": {"message": f"{status_text}สาขา {branch.branch_name} สำเร็จ"}, "success": True}), 200
