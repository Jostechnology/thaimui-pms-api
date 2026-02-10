import traceback
from app.exception import AppException
from flask import Flask, jsonify
from app.config import connectdb
from flask_cors import CORS, cross_origin
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from functools import wraps
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)


limiter = Limiter(
    key_func=get_remote_address, #ระบุตัวตนผู้ใช้จาก IP
    strategy="fixed-window",
    storage_uri="memory://",
)
limiter.init_app(app)

CORS(app)  # เปิดการเชื่อมต่อจากทุกโดเมน
# LoggerMiddleware(app, project_id="tms-api")
app.config['SQLALCHEMY_DATABASE_URI'] = connectdb  # กําหนด URI ของฐานข้อมูล
app.config['JSON_SORT_KEYS'] = False  # แก้ไขการสะกดผิด
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

db = SQLAlchemy(app)
migrate = Migrate(app, db)
ma = Marshmallow(app)

@app.errorhandler(AppException)
def handle_app_exception(e):
    traceback.print_exc()
    return jsonify({
        "error": e.message,
        "status": e.status_code
    }), e.status_code

@app.errorhandler(429)
def handle_ratelimit_error(e):
    return jsonify({
        "success": False,
        "error": "Too Many Requests",
        "message": e.description #ล็อกอินเกินกำหนด
    }), 429

@app.errorhandler(Exception)
def handle_generic_exception(e):
    traceback.print_exc()
    return jsonify({
        "error": "Internal server error"
    }), 500

from .controllers import auth_controller
from .controllers import user_controller
from .controllers import work_order_controller
from .controllers import employee_controller

with app.app_context():
    db.create_all()

@app.route('/api/health_check', methods=['POST'])
def health_check():
    return jsonify({"success" : True}), 200

# def decode_and_verify_module_token(authorizes=[]):
#     def decorator(f):
#         @wraps(f)
#         def wrapper_decode_and_verify_module_token(*args, **kwargs):
#             data = request.get_json(silent=True) or {}
#             permission_signature = data.get("permission_signature")
#             permission_tree_encoded = data.get("permission_tree_encoded")
#             # If client didn't send permission info, skip verification and continue.
#             if not permission_signature or not permission_tree_encoded:
#                 g.permission_tree = None
#                 return f(*args, **kwargs)

#             # Verify signature
#             verify_res, verify_code = verify_module_signature(permission_tree_encoded, permission_signature)
#             if verify_code != 200 or not verify_res.get("valid"):
#                 return jsonify({"error": "Invalid or unverifiable permission signature"}), 401
#             try:
#                 decoded = base64.b64decode(permission_tree_encoded)
#                 print(f"[permission-debug] Decoded permission tree: {decoded.decode('utf-8')}")
#                 # validate permissions (raises ValueError on failure)
#                 try:
#                     check_true_permissions(authorizes, json.loads(decoded))
#                     g.permission_tree = json.loads(decoded)
#                 except ValueError as ve:
#                     return jsonify({"error": "Permission denied", "details": str(ve)}), 403
#             except Exception as e:
#                 return jsonify({"error": "Failed to decode/validate permission_tree_encoded", "details": str(e)}), 400
#             return f(*args, **kwargs)

#         return wrapper_decode_and_verify_module_token
#     return decorator