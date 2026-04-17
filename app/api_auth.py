from app.con_sqlalchemy import Tokenlist
from app.config import CENTER_ACCESS_KEY
from app.utils import decode_token, check_true_permissions
from functools import wraps
from flask import request, jsonify, g
import base64
import json
import time
import logging

logger = logging.getLogger(__name__)

ENABLE_TIMING = False

def _log_timer(label: str, elapsed_ms: float, note: str = "", timing=ENABLE_TIMING):
    """Logs timing info only when ENABLE_TIMING is True."""
    if timing:
        suffix = f" ({note})" if note else ""
        log = (f"[timer] {label} → {elapsed_ms:.2f}ms{suffix}")
        logger.info(log)
        print(log)


def verify_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        _start = time.perf_counter()
        if request.method == "OPTIONS":
            return f(*args, **kwargs)

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
            _log_timer("verify_required", (time.perf_counter() - _start) * 1000, "early exit: missing token")
            return jsonify({"message": "Missing token"}), 401

        decoded = decode_token(token)
        if not decoded:
            _log_timer("verify_required", (time.perf_counter() - _start) * 1000, "early exit: invalid token")
            return jsonify({"message": "Invalid or expired token"}), 401

        jti = decoded.get("jti")
        if not Tokenlist.query.filter_by(jwt_id=jti).first():
            _log_timer("verify_required", (time.perf_counter() - _start) * 1000, "early exit: token not in DB")
            return jsonify({"message": "Token ไม่ถูกต้องหรือหมดอายุ"}), 401

        if decoded.get("type") == "branch_select":
            _log_timer("verify_required", (time.perf_counter() - _start) * 1000, "early exit: branch_select token rejected")
            return jsonify({"message": "Token ประเภทไม่ถูกต้อง"}), 401

        branch_id = decoded.get("branch_id")
        if branch_id is None:
            _log_timer("verify_required", (time.perf_counter() - _start) * 1000, "early exit: missing branch_id in token")
            return jsonify({"message": "Token ไม่มีข้อมูลสาขา กรุณาเลือกสาขาใหม่"}), 401

        role_id = decoded.get("role_id")
        if role_id is None:
            return jsonify({"message": "ไม่พบ Role ของผู้ใช้"}), 401
        
        g.username = decoded.get("username")
        g.branch_id = branch_id
        g.role_id = role_id
        _log_timer("verify_required", (time.perf_counter() - _start) * 1000, f"user: {g.username}, branch: {g.branch_id}")
        return f(*args, **kwargs)
    return decorated


def verify_required_center(f):
    """Like verify_required, but also accepts CENTER_ACCESS_KEY as a valid token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        _start = time.perf_counter()
        if request.method == "OPTIONS":
            return f(*args, **kwargs)

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
            _log_timer("verify_required_center", (time.perf_counter() - _start) * 1000, "early exit: missing token")
            return jsonify({"message": "Missing token"}), 401

        if token == CENTER_ACCESS_KEY:
            g.username = "SYSTEM_CENTER"
            _log_timer("verify_required_center", (time.perf_counter() - _start) * 1000, "SYSTEM_CENTER shortcut")
            return f(*args, **kwargs)

        decoded = decode_token(token)
        if not decoded:
            _log_timer("verify_required_center", (time.perf_counter() - _start) * 1000, "early exit: invalid token")
            return jsonify({"message": "Invalid or expired token"}), 401

        jti = decoded.get("jti")
        if not Tokenlist.query.filter_by(jwt_id=jti).first():
            _log_timer("verify_required_center", (time.perf_counter() - _start) * 1000, "early exit: token not in DB")
            return jsonify({"message": "Token ไม่ถูกต้องหรือหมดอายุ"}), 401

        if decoded.get("type") == "branch_select":
            _log_timer("verify_required_center", (time.perf_counter() - _start) * 1000, "early exit: branch_select token rejected")
            return jsonify({"message": "Token ประเภทไม่ถูกต้อง"}), 401

        branch_id = decoded.get("branch_id")
        if branch_id is None:
            _log_timer("verify_required_center", (time.perf_counter() - _start) * 1000, "early exit: missing branch_id in token")
            return jsonify({"message": "Token ไม่มีข้อมูลสาขา กรุณาเลือกสาขาใหม่"}), 401

        g.username = decoded.get("username")
        g.branch_id = branch_id
        _log_timer("verify_required_center", (time.perf_counter() - _start) * 1000, f"user: {g.username}, branch: {g.branch_id}")
        return f(*args, **kwargs)
    return decorated

def verify_required_center_only(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        _start = time.perf_counter()
        if request.method == "OPTIONS":
            return f(*args, **kwargs)

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
            _log_timer("verify_required_center", (time.perf_counter() - _start) * 1000, "early exit: missing token")
            return jsonify({"message": "Missing token"}), 401

        if token == CENTER_ACCESS_KEY:
            g.username = "SYSTEM_CENTER"
            _log_timer("verify_required_center", (time.perf_counter() - _start) * 1000, "SYSTEM_CENTER shortcut")
            return f(*args, **kwargs)

        else:
            _log_timer("verify_required_center", (time.perf_counter() - _start) * 1000, "early exit: invalid token")
            return jsonify({"message": "Invalid or expired token"}), 401

    return decorated

def get_requests_permission(request):
    data = request.get_json(silent=True) or {}
    if "X-Permission-Token" in request.headers:
        permission_token = request.headers["X-Permission-Token"]
    else:
        permission_token = data.get("permission_token") or request.args.get("permission_token")
    
    return permission_token


def decode_and_verify_permission_jwt(authorizes=[]):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            _start = time.perf_counter()
            label = f"decode_and_verify_permission_jwt ({f.__name__})"

            permission_token = get_requests_permission(request)

            if not permission_token:
                if authorizes:
                    _log_timer(label, (time.perf_counter() - _start) * 1000, "early exit: missing token")
                    return jsonify({"error": "Missing permission token"}), 401
                g.permission_tree = None
                _log_timer(label, (time.perf_counter() - _start) * 1000, "no token, no authorizes")
                return f(*args, **kwargs)

            decoded_payload = decode_token(permission_token)
            if not decoded_payload:
                _log_timer(label, (time.perf_counter() - _start) * 1000, "early exit: invalid token")
                return jsonify({"error": "Invalid or expired permission token"}), 401

            try:
                signed_permission_tree = decoded_payload.get("signed_permission_tree")
                if not signed_permission_tree:
                    _log_timer(label, (time.perf_counter() - _start) * 1000, "early exit: missing signed_permission_tree")
                    return jsonify({"error": "Missing signed_permission_tree in token"}), 400

                permission_tree_bytes = base64.b64decode(signed_permission_tree)
                permission_tree = json.loads(permission_tree_bytes.decode("utf-8"))

                print(f"[permission-debug] Decoded permission tree from JWT")

                if authorizes:
                    try:
                        check_true_permissions(authorizes, permission_tree)
                    except ValueError as ve:
                        _log_timer(label, (time.perf_counter() - _start) * 1000, "early exit: permission denied")
                        return jsonify({"error": "Permission denied", "details": str(ve)}), 403

                g.permission_tree = permission_tree

            except Exception as e:
                print(f"[permission-error] Failed to decode permission tree: {e}")
                _log_timer(label, (time.perf_counter() - _start) * 1000, "early exit: decode error")
                return jsonify({"error": "Failed to decode permission token", "details": str(e)}), 400

            _log_timer(label, (time.perf_counter() - _start) * 1000, "success")
            return f(*args, **kwargs)
        return wrapper
    return decorator