from app.con_sqlalchemy import Tokenlist
from app.config import CENTER_ACCESS_KEY
from app.utils import decode_token, check_true_permissions
from functools import wraps
from flask import request, jsonify, g
import base64
import json

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
        
        if token == CENTER_ACCESS_KEY:
            g.username = "SYSTEM_CENTER"
            return f(*args, **kwargs)

        decoded = decode_token(token)
        if not decoded:
            return jsonify({"message": "Invalid or expired token"}), 401

        jti = decoded.get("jti")
        
        if not Tokenlist.query.filter_by(jwt_id=jti).first():
            return jsonify({"message": "Token ไม่ถูกต้องหรือหมดอายุ"}), 401
            
        g.username = decoded.get("username")
        return f(*args, **kwargs)
    return decorated


def decode_and_verify_permission_jwt(authorizes=[]):
    """
    Decorator ที่ใช้ JWT verify เพื่อตรวจสอบ permission token จาก frontend
    Frontend ส่ง permission_token (JWT) มาใน request body
    Backend จะ verify และดึง permission_tree ออกมาจาก payload
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            data = request.get_json(silent=True) or {}
            permission_token = data.get("permission_token")
            
            # If client didn't send permission token
            if not permission_token:
                # ถ้ามี authorizes ที่ต้องเช็ค → ต้องบล็อก
                if authorizes:
                    return jsonify({"error": "Missing permission token"}), 401
                g.permission_tree = None
                return f(*args, **kwargs)

            # Verify JWT and decode payload
            decoded_payload = decode_token(permission_token)
            if not decoded_payload:
                return jsonify({"error": "Invalid or expired permission token"}), 401
            
            try:
                # Get signed_permission_tree from JWT payload (base64 encoded)
                signed_permission_tree = decoded_payload.get("signed_permission_tree")
                if not signed_permission_tree:
                    return jsonify({"error": "Missing signed_permission_tree in token"}), 400
                
                # Decode base64 to get permission tree JSON
                permission_tree_bytes = base64.b64decode(signed_permission_tree)
                permission_tree = json.loads(permission_tree_bytes.decode("utf-8"))
                
                print(f"[permission-debug] Decoded permission tree from JWT")
                
                # Validate permissions if authorizes are specified
                if authorizes:
                    try:
                        check_true_permissions(authorizes, permission_tree)
                    except ValueError as ve:
                        return jsonify({"error": "Permission denied", "details": str(ve)}), 403
                
                g.permission_tree = permission_tree
                
            except Exception as e:
                print(f"[permission-error] Failed to decode permission tree: {e}")
                return jsonify({"error": "Failed to decode permission token", "details": str(e)}), 400
            
            return f(*args, **kwargs)
        return wrapper
    return decorator