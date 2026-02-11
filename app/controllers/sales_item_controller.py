from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.services.sales_item_service import get_all_sales_items, create_sales_item


@app.route("/api/get_sales_item_list", methods=["GET"])
@verify_required
def api_get_sales_item_list():
    try:
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 10, type=int)
        search = request.args.get("search", "", type=str)
        data = {"page": page, "limit": limit, "search": search}

        result = get_all_sales_items(data)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/create_sales_item", methods=["POST"])
@verify_required
def api_create_sales_item():
    try:
        data = request.get_json()
        result = create_sales_item(data)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500
