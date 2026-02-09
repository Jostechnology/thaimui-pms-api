from app.api_auth import verify_required
from app.app import app, db
from flask import request, jsonify
from app.services import user_service

@app.route("/api/get_all_roles", methods=["GET", "POST"])
def api_get_all_roles():
    roles = user_service.get_all_roles()
    return jsonify({"data" : roles, "success" : True}), 200

@app.route("/api/get_module_tree", methods=["POST"])
def api_get_module_tree():
    module_tree = user_service.get_module_tree()
    return jsonify({"data" : module_tree, "success" : True}), 200 

@app.route("/api/get_role_permission", methods=["POST"])
def api_get_role_permission():
    data = request.get_json()
    username = data.get("username")
    role_id = data.get("role_id")
    module_tree, signature = user_service.get_role_permission(username, role_id)
    return jsonify({"data" : {"module_tree" : module_tree, "signature" : signature, "success" : True}}), 200 

@app.route("/api/create_module", methods=["POST"])
def api_create_module():
    data = request.get_json()
    res = user_service.create_module(data)
    return jsonify({"data" : res, "success" : True}), 200 

@app.route('/api/get_module/<int:module_id>', methods=['POST'])
def api_get_module(module_id):
    res = user_service.get_module(module_id)
    return jsonify({"data" : res, "success" : True}), 200

@app.route('/api/get_modules_main', methods=['GET', 'POST'])
def api_get_modules_main():
    res = user_service.get_modules_main()
    return jsonify({"data" : res, "success" : True}), 200

@app.route('/api/get_module_sorted', methods=['GET', 'POST'])
def api_get_module_sorted():
    module_id = request.args.get("module_id")
    res = user_service.get_module_sorted(module_id)
    return jsonify({"data" : res + 1, "success" : True}), 200

@app.route('/api/upsert_role_permission', methods=['PUT'])
def upsert_role_permission():
    data = request.get_json()
    res = user_service.upsert_role_permission(data)
    return jsonify({"data" : res, "success" : True}), 200


@app.route('/api/edit_module/<int:module_id>', methods=['PUT'])
def api_edit_module(module_id=None):
    data = request.get_json()
    if module_id is None:
        module_id = data.get("module_id")
    res = user_service.edit_module(module_id, data)
    return jsonify({"data" : res, "success" : True}), 200



@app.route('/api/delete_module/<int:module_id>', methods=['DELETE'])
def api_delete_module(module_id=None):
    data = request.get_json()
    if module_id is None:
        module_id = data.get("module_id")
    res = user_service.delete_module(module_id)
    return jsonify({"data" : res, "success" : True}), 200
