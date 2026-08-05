import traceback
from app.exception import AppException
from app.extensions import init_center_service, init_document_generator_service, init_storage_service, init_cache_service, init_wms_service
from flask import Flask, jsonify
from app.config import (
    CENTER_ACCESS_KEY, CENTER_URL, DOCUMENT_GENERATOR_URL, connectdb,
    MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET, MINIO_SECURE,
    REDIS_URL, WMS_URL,
)
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
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 280,
}
app.config['UPLOAD_FOLDER'] = 'uploads'

db = SQLAlchemy(app)
migrate = Migrate(app, db)
ma = Marshmallow(app)

init_center_service(CENTER_ACCESS_KEY, CENTER_URL)
init_document_generator_service(DOCUMENT_GENERATOR_URL)
if MINIO_ENDPOINT:
    init_storage_service(MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET, MINIO_SECURE)
if REDIS_URL:
    init_cache_service(REDIS_URL)
init_wms_service(WMS_URL, CENTER_ACCESS_KEY)


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

@app.errorhandler(404)
def handle_not_found(e):
    return jsonify({
        "success": False,
        "error": "Can't find endpoint / data",
        "message": e.description #ล็อกอินเกินกำหนด
    }), 404

@app.errorhandler(Exception)
def handle_generic_exception(e):
    traceback.print_exc()
    return jsonify({
        "error": f"Error : {str(e)}",
        "success" : False
    }), 500

from .controllers import auth_controller
from .controllers import user_controller
from .controllers import work_order_controller
from .controllers import employee_controller
from .controllers import sales_item_controller
from .controllers import material_list_controller
from .controllers import sales_order_controller
from .controllers import employee_salary
from .controllers import qc_work_order_controller
from .controllers import test_certificate_controller
from .controllers import test_result_controller
from .controllers import item_component_controller
from .controllers import component_edit_request_controller
from .controllers import operation_cost_monthly_controller
from .controllers import work_run_controller
from .controllers import machine_controller
from .controllers import pm_machine_controller
from .controllers import picking_request_controller
from .controllers import document_code_controller
from .controllers import branch_controller
from .controllers import component_template_controller
from .controllers import machine_type_controller
from .controllers import phase_template_controller
from .controllers import all_branch_controller
from .controllers import shift_controller
from .controllers import employee_shift_controller
from .controllers import holiday_controller
from .controllers import report_controller
from .controllers import item_decode_controller

from app.cli import register_cli
register_cli(app)

# with app.app_context():
#     db.create_all()

@app.route('/api/health_check', methods=['POST'])
def health_check():
    return jsonify({"success" : True}), 200