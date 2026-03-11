from app.api_auth import verify_required, decode_and_verify_permission_jwt
from app.app import app, db
from flask import request, jsonify, g
from app.services import user_service
from app.repositories import role_repository, user_repository
from sqlalchemy.exc import IntegrityError

@app.route("/api/get_all_roles", methods=["GET", "POST"])
def api_get_all_roles():
    roles = user_service.get_all_roles()
    return jsonify({"data" : roles, "success" : True}), 200

@app.route("/api/create_role", methods=["POST"])
@verify_required
@decode_and_verify_permission_jwt(authorizes=[{"module_code": "ROLE_MANAGEMENT", "method": "create"}])
def api_create_role():
    data = request.get_json()
    try:
        res = user_service.create_role(data)
        return jsonify({"data" : res, "success" : True}), 200
    except IntegrityError:
        return jsonify({"success": False, "error": "ชื่อบทบาทนี้มีอยู่ในระบบแล้ว"}), 400
    except Exception as e:
        error_msg = str(e)
        
        return jsonify({"success": False, "error": f"เกิดข้อผิดพลาด: {error_msg}"}), 500

@app.route("/api/get_module_tree", methods=["POST"])
@verify_required
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
@verify_required
@decode_and_verify_permission_jwt(authorizes=[{"module_code": "MODULE_MANAGEMENT", "method": "create"}])
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
@verify_required
@decode_and_verify_permission_jwt(authorizes=[{"module_code": "ROLE_MANAGEMENT", "method": "edit"}])
def upsert_role_permission():
    data = request.get_json()
    res = user_service.upsert_role_permission(data)
    return jsonify({"data" : res, "success" : True}), 200


@app.route("/api/create_user", methods=["POST"]) #add_limiter??
@verify_required
def api_create_user():
    data = request.get_json()
    res = user_service.create_user(data)
    return jsonify({"data" : res, "success" : True}), 200 

@app.route("/api/get_user_list", methods=["GET"])
def api_get_user_list():
    try:
        data = {
            "page": request.args.get("page", 1, type=int),
            "per_page": request.args.get("per_page", 10, type=int),
            "search": request.args.get("search", ""),
            "filter": request.args.get("filter", None)
        }
        res = user_service.get_user_list(data)
        return jsonify({
            "data": {"items": res["items"]},
            "pagination": {"total": res["total"], "page": res["page"], "pages": res["pages"]},
            "success": True,
        }), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/change_user_role", methods=["PUT"])
def api_change_user_role():
    try:
        data = request.get_json()
        res = user_service.change_user_role(data)
        return jsonify({"data": res, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@app.route("/api/change_user_password", methods=["PUT"])
def api_change_user_password():
    try:
        data = request.get_json()
        res = user_service.change_user_password(data)
        return jsonify({"data": res, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500    

@app.route("/api/ban_user", methods=["PUT"])
def api_ban_user():
    try:
        data = request.get_json()
        res = user_service.ban_user(data)
        return jsonify({"data": res, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500    

@app.route('/api/edit_module/<int:module_id>', methods=['PUT'])
@verify_required
@decode_and_verify_permission_jwt(authorizes=[{"module_code": "MODULE_MANAGEMENT", "method": "edit"}])
def api_edit_module(module_id=None):
    data = request.get_json()
    if module_id is None:
        module_id = data.get("module_id")
    res = user_service.edit_module(module_id, data)
    return jsonify({"data" : res, "success" : True}), 200



@app.route('/api/delete_module/<int:module_id>', methods=['DELETE'])
@verify_required
@decode_and_verify_permission_jwt(authorizes=[{"module_code": "MODULE_MANAGEMENT", "method": "delete"}])
def api_delete_module(module_id=None):
    data = request.get_json()
    if module_id is None:
        module_id = data.get("module_id")
    res = user_service.delete_module(module_id)
    return jsonify({"data" : res, "success" : True}), 200
