from flask import Flask, request, jsonify,g
from config import connectdb
from flask_cors import CORS, cross_origin
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from functools import wraps


app = Flask(__name__)

CORS(app)  # เปิดการเชื่อมต่อจากทุกโดเมน
# LoggerMiddleware(app, project_id="tms-api")
app.config['SQLALCHEMY_DATABASE_URI'] = connectdb  # กําหนด URI ของฐานข้อมูล
app.config['JSON_SORT_KEYS'] = False  # แก้ไขการสะกดผิด
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

db = SQLAlchemy(app)
ma = Marshmallow(app)

with app.app_context():
    db.create_all()

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
        if Tokenlist.query.filter_by(jwt_id=jti).first():
            return jsonify({"message": "Token revoked"}), 401
        g.username = decoded.get("username")
        return f(*args, **kwargs)
    return decorated

def decode_and_verify_module_token(authorizes=[]):
    def decorator(f):
        @wraps(f)
        def wrapper_decode_and_verify_module_token(*args, **kwargs):
            data = request.get_json(silent=True) or {}
            permission_signature = data.get("permission_signature")
            permission_tree_encoded = data.get("permission_tree_encoded")
            # If client didn't send permission info, skip verification and continue.
            if not permission_signature or not permission_tree_encoded:
                g.permission_tree = None
                return f(*args, **kwargs)

            # Verify signature
            verify_res, verify_code = verify_module_signature(permission_tree_encoded, permission_signature)
            if verify_code != 200 or not verify_res.get("valid"):
                return jsonify({"error": "Invalid or unverifiable permission signature"}), 401
            try:
                decoded = base64.b64decode(permission_tree_encoded)
                print(f"[permission-debug] Decoded permission tree: {decoded.decode('utf-8')}")
                # validate permissions (raises ValueError on failure)
                try:
                    check_true_permissions(authorizes, json.loads(decoded))
                    g.permission_tree = json.loads(decoded)
                except ValueError as ve:
                    return jsonify({"error": "Permission denied", "details": str(ve)}), 403
            except Exception as e:
                return jsonify({"error": "Failed to decode/validate permission_tree_encoded", "details": str(e)}), 400
            return f(*args, **kwargs)

        return wrapper_decode_and_verify_module_token
    return decorator