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
