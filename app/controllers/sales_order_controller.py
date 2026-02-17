import traceback
from app.api_auth import verify_required
from app.app import app
from app.exception import AppException
from flask import request, jsonify
from app.ma_sqlalchemy import SalesOrderSchema
from app.services.sales_order_service import search_sales_order, get_sales_order_detail


@app.route("/api/search_sales_order", methods=["GET"])
@verify_required
def api_search_sales_order():
    try:
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 10, type=int)
        search = request.args.get("search", "", type=str)
        data = {"page": page, "limit": limit, "search": search}

        result = search_sales_order(data)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/sales_order/get_by_doc_entry/<int:doc_entry>", methods=["GET"])
@verify_required
def api_get_by_doc_entry(doc_entry):
    try:

        result = get_sales_order_detail(doc_entry)
        schema = SalesOrderSchema()
        data = schema.dump(result)
        return jsonify({"data": data, "success": True}), 200
    except AppException as e:
        return jsonify({"error" : e.message}), e.status_code
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
