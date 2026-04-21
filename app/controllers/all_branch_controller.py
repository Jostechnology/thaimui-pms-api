from app.api_auth import verify_required_all_branch, decode_and_verify_permission_jwt
from app.app import app
from flask import request, jsonify, g
from app.services.sales_order_service import get_all_sales_orders


@app.route("/api/all_branch/sales_order/get_all", methods=["GET"])
@verify_required_all_branch
@decode_and_verify_permission_jwt(authorizes=[{"module_code": "ALL_BRANCH", "method": "view"}])
def api_all_branch_get_all_sales_orders():
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        search = request.args.get("search", "", type=str)
        start_date = request.args.get("start_date", None, type=str)
        end_date = request.args.get("end_date", None, type=str)
        data = {"page": page, "per_page": per_page, "search": search, "start_date": start_date, "end_date": end_date}

        result = get_all_sales_orders(
            data,
            branch_id=None,
        )
        return jsonify({
            "data": {"items": result["items"]},
            "pagination": {"total": result["total"], "page": result["page"], "pages": result["pages"]},
            "success": True,
        }), 200
    except Exception:
        raise
