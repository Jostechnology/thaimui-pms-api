from app.app import app, db
from flask import request, jsonify
from app.services import auth_service

@app.route('/api/login', methods=['POST'])
def login_controller():
    data = request.get_json()
    access_token, refresh_token = auth_service.login_service(data)

    return jsonify({"access_token" : access_token, "refresh_token" : refresh_token, "success" : True}), 200
    
@app.route('/api/register', methods=['POST'])
def register_controller():
    data = request.get_json()
    new_user = auth_service.register_service(data)

    return jsonify({"data" : new_user, "success" : True}), 200

@app.route('/api/logout', methods=['POST'])
def logout_controller():
    """Logout - revoke refresh token"""
    data = request.get_json()
    refresh_token = data.get('refresh_token')
    
    if not refresh_token:
        return jsonify({"message": "Refresh token is required", "success": False}), 400
    
    result = auth_service.logout_service(refresh_token)
    return jsonify({"data": result, "success": True}), 200

@app.route('/api/refresh-token', methods=['POST'])
def refresh_token_controller():
    data = request.get_json()
    refresh_token = data.get('refresh_token')
    
    if not refresh_token:
        return jsonify({"message": "Refresh token is required", "success": False}), 400
    
    new_access_token, new_refresh_token = auth_service.refresh_token_service(refresh_token)
    return jsonify({
        "access_token": new_access_token, 
        "refresh_token": new_refresh_token,  # ← คืน refresh token ใหม่ด้วย
        "success": True
    }), 200