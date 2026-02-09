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

@app.route("/api/create_user", methods=["POST"]) #add_limiter??
def api_create_user():
    data = request.get_json()
    res = user_service.create_user(data)
    return jsonify({"data" : res, "success" : True}), 200 

@app.route("/api/get_user_list", methods=["GET"])
def api_get_user_list():
    try:
        data = {
            "page": request.args.get("page", 1, type=int),
            "pageConfig": request.args.get("pageConfig", 10, type=int),
            "search": request.args.get("search", ""),
            "filter": request.args.get("filter", None)
        }
        res = user_service.get_user_list(data)
        return jsonify({"data": res, "success": True}), 200
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
