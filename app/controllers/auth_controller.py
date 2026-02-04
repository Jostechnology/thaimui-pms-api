from app.app import app, db
from flask import request, jsonify
from app.services import auth_service
from app.app import limiter

@app.route('/api/login', methods=['POST'])
@limiter.limit("5 per minute", error_message="คุณล็อกอินเกินกำหนด กรุณาลองใหม่ในอีก 1 นาที")
def login_controller():
    data = request.get_json()
    access_token, refresh_token = auth_service.login_service(data)

    return jsonify({"access_token" : access_token, "refresh_token" : refresh_token, "success" : True}), 200
    
@app.route('/api/register', methods=['POST'])
@limiter.limit("10 per hour")
def register_controller():
    data = request.get_json()
    new_user = auth_service.register_service(data)

    return jsonify({"data" : new_user, "success" : True}), 200
