from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.ma_sqlalchemy import SalesItemSchema, SalesItemDetailSchema
from app.services.sales_item_service import get_all_sales_items, create_sales_item, get_sales_item_detail


@app.route("/api/get_sales_item_list", methods=["GET"])
@verify_required
def api_get_sales_item_list():
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        search = request.args.get("search", "", type=str)
        data = {"page": page, "per_page": per_page, "search": search}

        result = get_all_sales_items(data)
        return jsonify({
            "data": {"items": SalesItemSchema(many=True).dump(result["items"])},
            "pagination": {"total": result["total"], "page": result["page"], "pages": result["pages"]},
            "success": True,
        }), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/sales_item/<int:sales_item_id>", methods=["GET"])
@verify_required
def api_get_sales_item_detail(sales_item_id):
    try:
        result = get_sales_item_detail(sales_item_id)
        return jsonify({"data": SalesItemDetailSchema().dump(result), "success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/create_sales_item", methods=["POST"])
@verify_required
def api_create_sales_item():
    try:
        data = request.get_json()
        result = create_sales_item(data)
        return jsonify({"data": SalesItemSchema().dump(result), "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500
