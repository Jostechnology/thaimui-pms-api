from app.con_sqlalchemy import Tokenlist
from app.utils import decode_token
from functools import wraps
from flask import request, jsonify, g

def verify_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if "Authorization" in request.headers:
            parts = request.headers["Authorization"].split(" ")
            if len(parts) == 2 and parts[0] == "Bearer":
                token = parts[1]

        if not token:
            try:
                body = request.get_json(silent=True)
                if body and "token" in body:
                    token = body["token"]
            except Exception:
                pass

        if not token:
            return jsonify({"message": "Missing token"}), 401

        decoded = decode_token(token)
        if not decoded:
            return jsonify({"message": "Invalid or expired token"}), 401

        jti = decoded.get("jti")
        
        if not Tokenlist.query.filter_by(jwt_id=jti).first():
            return jsonify({"message": "Token ไม่ถูกต้องหรือหมดอายุ"}), 401
            
        g.username = decoded.get("username")
        return f(*args, **kwargs)
    return decorated