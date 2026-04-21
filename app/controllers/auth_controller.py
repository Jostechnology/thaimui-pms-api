from app.app import app, db
from flask import request, jsonify
from app.services import auth_service
from app.app import limiter


@app.route('/api/login', methods=['POST'])
@limiter.limit("5 per minute", error_message="คุณล็อกอินเกินกำหนด กรุณาลองใหม่ในอีก 1 นาที")
def login_controller():
    data = request.get_json()
    branch_select_token, user_branches, has_all_branch_access = auth_service.login_service(data)
    return jsonify({
        "branch_select_token": branch_select_token,
        "user_branches": user_branches,
        "has_all_branch_access": has_all_branch_access,
        "success": True
    }), 200


@app.route('/api/select-branch', methods=['POST'])
def select_branch_controller():
    data = request.get_json()
    access_token, refresh_token = auth_service.select_branch_service(data)
    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "success": True
    }), 200


@app.route('/api/select-all-branch', methods=['POST'])
def select_all_branch_controller():
    data = request.get_json()
    access_token, refresh_token = auth_service.select_all_branch_service(data)
    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "success": True
    }), 200


@app.route('/api/register', methods=['POST'])
@limiter.limit("10 per hour")
def register_controller():
    data = request.get_json()
    new_user = auth_service.register_service(data)
    return jsonify({"data": new_user, "success": True}), 200


@app.route('/api/logout', methods=['POST'])
def logout_controller():
    data = request.get_json()
    refresh_token = data.get('refresh_token')
    if not refresh_token:
        return jsonify({"message": "Refresh token is required", "success": False}), 400
    result = auth_service.logout_service(refresh_token)
    return jsonify({"data": result, "success": True}), 200

@app.route('/api/sso-login', methods=['POST'])
def sso_login_controller():
    data = request.get_json()
    branch_select_token, user_branches, has_all_branch_access = auth_service.sso_login_service(data)
    return jsonify({
        "branch_select_token": branch_select_token,
        "user_branches": user_branches,
        "has_all_branch_access": has_all_branch_access,
        "success": True
    }), 200

@app.route('/api/refresh-token', methods=['POST'])
def refresh_token_controller():
    data = request.get_json()
    refresh_token = data.get('refresh_token')
    if not refresh_token:
        return jsonify({"message": "Refresh token is required", "success": False}), 400
    new_access_token, new_refresh_token = auth_service.refresh_token_service(refresh_token)
    return jsonify({
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "success": True
    }), 200
