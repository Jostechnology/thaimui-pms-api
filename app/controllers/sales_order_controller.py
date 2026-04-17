from app.api_auth import decode_and_verify_permission_jwt, get_requests_permission, verify_required, verify_required_center, verify_required_center_only
from app.app import app
from flask import request, jsonify, g
from app.exception import DisabledAction
from app.ma_sqlalchemy import MaterialListSchema, SalesItemSchema, SalesOrderSchema, SalesOrderSearchSchema
from app.services import cache_service
from app.services.sales_order_service import get_test_sales_order, search_sales_order, get_sales_order_detail, get_all_sales_orders, get_sales_items_from_sales_order, create_sales_order_routine, assign_branch_to_sales_order
from app.services.storage_service import PRESIGNED_CACHE_TTL
from app.utils import decode_token, check_true_permissions
import base64, json
from datetime import datetime, timedelta

def _sales_order_page_cache(page, per_page, branch_code):
    return f"sales_order_{page}_{per_page}_{branch_code}"

def _sales_order_detail_cache(doc_entry, branch_id):
    return f"sales_order_detail_{doc_entry}_{branch_id}"

PAGE_CACHE_TTL = 3600
SALES_ORDER_CACHE_TTL = 4800

def _has_unassigned_sales_order_view_permission(permission_token: str) -> bool:
    decoded = decode_token(permission_token)
    if not decoded:
        return False
    try:
        signed = decoded.get("signed_permission_tree")
        if not signed:
            return False
        permission_list = json.loads(base64.b64decode(signed).decode("utf-8"))
        check_true_permissions([{"module_code": "UNASSIGNED_SO", "method": "create"}], permission_list)
        return True
    except Exception:
        return False

def _has_unassigned_sales_order_create_permission(permission_token: str) -> bool:
    decoded = decode_token(permission_token)
    if not decoded:
        return False
    try:
        signed = decoded.get("signed_permission_tree")
        if not signed:
            return False
        permission_list = json.loads(base64.b64decode(signed).decode("utf-8"))
        check_true_permissions([{"module_code": "UNASSIGNED_SO", "method": "create"}], permission_list)
        return True
    except Exception:
        return False

@app.route("/api/sales_order/get_all", methods=["GET"])
@verify_required
def api_get_all_sales_orders():
    try:

        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        search = request.args.get("search", "", type=str)
        data = {"page": page, "per_page": per_page, "search": search}
        
        key = _sales_order_page_cache(page, per_page, g.branch_id)
        cached = cache_service.get(key)
        if cached and not search:
            return jsonify(cached), 200

        # permission_token = get_requests_permission(request)
        # show_unassigned = bool(permission_token and _has_unassigned_sales_order_view_permission(permission_token))

        result = get_all_sales_orders(
            data,
            # show_unassigned=show_unassigned,
            branch_id=g.branch_id,
        )

        response_dict = {
            "data": {"items": result["items"]},
            "pagination": {"total": result["total"], "page": result["page"], "pages": result["pages"]},
            "success": True,
        }

        if page <= 3 and per_page == 10 and g.branch_id and not search:
            cache_service.set(key, response_dict, ttl=PAGE_CACHE_TTL)
        return jsonify(response_dict), 200
    except Exception:
        raise


@app.route("/api/sales_order/<int:doc_entry>/assign_branch", methods=["POST"])
@verify_required_center_only
def api_assign_branch_to_sales_order(doc_entry):
    try:
        data = request.get_json()
        branch_id = data.get("branch_id")
        if branch_id is None:
            return jsonify({"message": "branch_id is required"}), 400
        sales_order = assign_branch_to_sales_order(doc_entry, branch_id)
        for p in range(1, 4):
            cache_service.delete(_sales_order_page_cache(p, 10, branch_id))
        cache_service.delete(_sales_order_detail_cache(doc_entry, branch_id))
        return jsonify({"data": SalesOrderSchema().dump(sales_order), "success": True}), 200
    except Exception:
        raise

@app.route("/api/sales_order/<int:doc_entry>/pms_assign_branch", methods=["POST"])
@verify_required_center
@decode_and_verify_permission_jwt(authorizes=[{"module_code": "UNASSIGNED_SO", "method": "edit"}])
def api_pms_assign_branch_to_sales_order(doc_entry):
    try:
        raise DisabledAction("ขณะนี้ระบบปิดการใช้งานการกำหนดสาขาผ่านระบบ PMS อยู่ กรุณาจัดการจากระบบ Center")
        data = request.get_json()
        branch_id = data.get("branch_id")
        if branch_id is None:
            return jsonify({"message": "branch_id is required"}), 400
        sales_order = assign_branch_to_sales_order(doc_entry, branch_id)
        return jsonify({"data": SalesOrderSchema().dump(sales_order), "success": True}), 200
    except Exception:
        raise

@app.route("/api/search_sales_order", methods=["GET"])
@verify_required
def api_search_sales_order():
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        search = request.args.get("search", "", type=str)
        data = {"page": page, "per_page": per_page, "search": search}

        # permission_token = get_requests_permission(request)
        # show_unassigned = bool(permission_token and _has_unassigned_sales_order_view_permission(permission_token))

        result = search_sales_order(
            data,
            # show_unassigned=show_unassigned,
            branch_id=g.branch_id,
        )
        return jsonify({
            "data": {"items": SalesOrderSearchSchema(many=True).dump(result["items"])},
            "pagination": {"total": result["total"], "page": result["page"], "pages": result["pages"]},
            "success": True,
        }), 200
    except Exception:
        raise


@app.route("/api/sales_order/get_by_doc_entry/<int:doc_entry>", methods=["GET"])
@verify_required
def api_get_by_doc_entry(doc_entry):
    try:
        key = _sales_order_detail_cache(doc_entry, g.branch_id)
        cached = cache_service.get(key)
        if cached:
            return jsonify(cached), 200

        # permission_token = get_requests_permission(request)
        # show_unassigned = bool(permission_token and _has_unassigned_sales_order_view_permission(permission_token))

        sales_order, items, materials, branch = get_sales_order_detail(
            doc_entry,
            # show_unassigned=show_unassigned,
            branch_id=g.branch_id,
        )
        so_schema = SalesOrderSchema()
        item_schema = SalesItemSchema(many=True)
        mat_schema = MaterialListSchema(many=True)
        sales_order_data = so_schema.dump(sales_order)
        sales_items_data = item_schema.dump(items)
        material_list_data = mat_schema.dump(materials)

        data = sales_order_data
        data["items"] = sales_items_data
        data["material_list"] = material_list_data
        data["branch_code"] = branch.branch_code if branch else None
        data["branch_name"] = branch.branch_name if branch else None

        response_dict = {"data": data, "success": True}

        cutoff = datetime.utcnow() - timedelta(days=7)
        created = sales_order.created_date
        if created and (created.replace(tzinfo=None) >= cutoff):
            cache_service.set(key, response_dict, ttl=SALES_ORDER_CACHE_TTL)

        return jsonify(response_dict), 200
    except Exception:
        raise


@app.route("/api/sales_order/<int:doc_entry>/sales_items", methods=["GET"])
@verify_required
def api_get_sales_items_from_sales_order(doc_entry):
    try:
        items = get_sales_items_from_sales_order(doc_entry)
        return jsonify({"data": SalesItemSchema(many=True).dump(items), "success": True}), 200
    except Exception:
        raise


@app.route("/api/sales_order/get_test_quick", methods=["POST"])
@verify_required
def api_get_sales_order_test_quick():
    try:
        get_test_sales_order()
        return jsonify({"success": True}), 200
    except Exception:
        raise


@app.route("/api/sales_order/create_routine", methods=["POST"])
@verify_required_center
def api_create_sales_order_routine():
    try:
        data = request.get_json()
        sales_orders = data.get("items", [])
        create_sales_order_routine(sales_orders)
        return jsonify({"success": True}), 200
    except Exception:
        raise
