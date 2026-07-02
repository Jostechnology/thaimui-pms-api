from app.con_sqlalchemy import Tokenlist
from app.config import CENTER_ACCESS_KEY
from app.utils import decode_token, check_true_permissions
from app.services import cache_service
from functools import wraps
from flask import request, jsonify, g
import base64
import json
import time
import logging


# Redis-backed JTI existence cache. Sub-millisecond replacement for the
# `SELECT FROM t_token_list WHERE jwt_id = ?` on every authenticated request.
# MySQL remains source-of-truth; cache is invalidated on logout / refresh /
# token rotation so revocation propagates immediately.
JTI_CACHE_PREFIX = "jti:"


def jti_cache_key(jti: str) -> str:
    return f"{JTI_CACHE_PREFIX}{jti}"


def _jti_cache_ttl_from_exp(decoded: dict, fallback: int = 3600) -> int:
    """TTL seconds remaining until the token's own exp. Clamp 1min..7d."""
    exp = decoded.get("exp") if decoded else None
    if not exp:
        return fallback
    remaining = int(exp) - int(time.time())
    return max(60, min(remaining, 7 * 24 * 3600))


def _verify_jti_alive(jti: str, decoded: dict) -> bool:
    """Cache-first JTI existence check. Returns True if token is in Tokenlist."""
    key = jti_cache_key(jti)
    cached = cache_service.get(key)
    if cached is not None:
        return True
    if not Tokenlist.query.filter_by(jwt_id=jti).first():
        return False
    cache_service.set(key, True, ttl=_jti_cache_ttl_from_exp(decoded))
    return True


logger = logging.getLogger(__name__)

ENABLE_TIMING = True

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
        if not _verify_jti_alive(jti, decoded):
            _log_timer("verify_required", (time.perf_counter() - _start) * 1000, "early exit: token not in DB")
            return jsonify({"message": "Token ไม่ถูกต้องหรือหมดอายุ"}), 401

        if decoded.get("type") in ("branch_select"):
            _log_timer("verify_required", (time.perf_counter() - _start) * 1000, f"early exit: {decoded.get('type')} token rejected")
            return jsonify({"message": "Token ประเภทไม่ถูกต้อง"}), 401

        branch_id = decoded.get("branch_id")
        if (branch_id is None) and decoded.get("type") != "all_branch":
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


def verify_required_all_branch(f):
    """Like verify_required, but only accepts all_branch tokens. Read-only cross-branch access."""
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
            _log_timer("verify_required_all_branch", (time.perf_counter() - _start) * 1000, "early exit: missing token")
            return jsonify({"message": "Missing token"}), 401

        decoded = decode_token(token)
        if not decoded:
            _log_timer("verify_required_all_branch", (time.perf_counter() - _start) * 1000, "early exit: invalid token")
            return jsonify({"message": "Invalid or expired token"}), 401

        jti = decoded.get("jti")
        if not _verify_jti_alive(jti, decoded):
            _log_timer("verify_required_all_branch", (time.perf_counter() - _start) * 1000, "early exit: token not in DB")
            return jsonify({"message": "Token ไม่ถูกต้องหรือหมดอายุ"}), 401

        if decoded.get("type") != "all_branch":
            _log_timer("verify_required_all_branch", (time.perf_counter() - _start) * 1000, "early exit: wrong token type")
            return jsonify({"message": "ต้องใช้ Token แบบ All Branch เท่านั้น"}), 401

        if not decoded.get("all_branch_mode"):
            _log_timer("verify_required_all_branch", (time.perf_counter() - _start) * 1000, "early exit: missing all_branch_mode")
            return jsonify({"message": "Token ไม่มีสิทธิ์ All Branch"}), 401

        role_id = decoded.get("role_id")
        if role_id is None:
            return jsonify({"message": "ไม่พบ Role ของผู้ใช้"}), 401

        g.username = decoded.get("username")
        g.branch_id = None
        g.role_id = role_id
        g.all_branch_mode = True
        _log_timer("verify_required_all_branch", (time.perf_counter() - _start) * 1000, f"user: {g.username}, all_branch_mode")
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
        if not _verify_jti_alive(jti, decoded):
            _log_timer("verify_required_center", (time.perf_counter() - _start) * 1000, "early exit: token not in DB")
            return jsonify({"message": "Token ไม่ถูกต้องหรือหมดอายุ"}), 401

        if decoded.get("type") == "branch_select":
            _log_timer("verify_required_center", (time.perf_counter() - _start) * 1000, "early exit: branch_select token rejected")
            return jsonify({"message": "Token ประเภทไม่ถูกต้อง"}), 401

        branch_id = decoded.get("branch_id")
        if (branch_id is None) and decoded.get("type") != "all_branch":
            _log_timer("verify_required_center", (time.perf_counter() - _start) * 1000, "early exit: missing branch_id in token")
            return jsonify({"message": "Token ไม่มีข้อมูลสาขา กรุณาเลือกสาขาใหม่"}), 401

        g.username = decoded.get("username")
        g.branch_id = branch_id
        g.role_id = decoded.get("role_id")
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
    """Legacy shim. The permission token was removed — authorization now
    resolves from the JWT's role_id via Redis. Kept so existing imports work."""
    return None


def verify_permission(authorizes=[]):
    """Resolve the caller's permission tree from Redis by role_id (set by a
    preceding verify_required*), then enforce `authorizes`. No permission
    token is read from the request anymore."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            _start = time.perf_counter()
            label = f"verify_permission ({f.__name__})"

            # Trusted system-to-system caller (CENTER_ACCESS_KEY) has no role — bypass.
            if getattr(g, "username", None) == "SYSTEM_CENTER":
                g.permission_tree = ["*"]
                _log_timer(label, (time.perf_counter() - _start) * 1000, "SYSTEM_CENTER bypass")
                return f(*args, **kwargs)

            role_id = getattr(g, "role_id", None)
            if role_id is None:
                _log_timer(label, (time.perf_counter() - _start) * 1000, "early exit: missing role_id (decorator order)")
                return jsonify({"error": "Authentication context missing"}), 401

            # Lazy import avoids an import cycle at module load time.
            from app.services.user_service import load_permission_tree
            permission_tree = load_permission_tree(role_id)
            g.permission_tree = permission_tree

            if authorizes:
                try:
                    check_true_permissions(authorizes, permission_tree)
                except ValueError as ve:
                    _log_timer(label, (time.perf_counter() - _start) * 1000, "early exit: permission denied")
                    return jsonify({"error": "Permission denied", "details": str(ve)}), 403

            _log_timer(label, (time.perf_counter() - _start) * 1000, "success")
            return f(*args, **kwargs)
        return wrapper
    return decorator


# Backward-compatible alias for existing route decorators.
decode_and_verify_permission_jwt = verify_permission