import traceback
from app.api_auth import verify_required
from app.app import app
from app.exception import AppException
from flask import request, jsonify
from app.ma_sqlalchemy import MaterialListSchema, SalesItemSchema, SalesOrderSchema, SalesOrderSearchSchema
from app.services.sales_order_service import get_test_sales_order, search_sales_order, get_sales_order_detail, get_all_sales_orders, get_sales_items_from_sales_order


@app.route("/api/sales_order/get_all", methods=["GET"])
@verify_required
def api_get_all_sales_orders():
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        search = request.args.get("search", "", type=str)
        data = {"page": page, "per_page": per_page, "search": search}

        result = get_all_sales_orders(data)
        return jsonify({
            "data": {"items": result["items"]},
            "pagination": {"total": result["total"], "page": result["page"], "pages": result["pages"]},
            "success": True,
        }), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/search_sales_order", methods=["GET"])
@verify_required
def api_search_sales_order():
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        search = request.args.get("search", "", type=str)
        data = {"page": page, "per_page": per_page, "search": search}

        result = search_sales_order(data)
        return jsonify({
            "data": {"items": SalesOrderSearchSchema(many=True).dump(result["items"])},
            "pagination": {"total": result["total"], "page": result["page"], "pages": result["pages"]},
            "success": True,
        }), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/sales_order/get_by_doc_entry/<int:doc_entry>", methods=["GET"])
@verify_required
def api_get_by_doc_entry(doc_entry):
    try:

        sales_order, items, materials = get_sales_order_detail(doc_entry)
        so_schema = SalesOrderSchema()
        item_schema = SalesItemSchema(many=True)
        mat_schema = MaterialListSchema(many=True)
        sales_order_data = so_schema.dump(sales_order)
        sales_items_data = item_schema.dump(items)
        material_list_data = mat_schema.dump(materials)

        data = sales_order_data
        data["items"] = sales_items_data
        data["material_list"] = material_list_data
        return jsonify({"data": data, "success": True}), 200
    except AppException as e:
        return jsonify({"error" : e.message}), e.status_code
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/sales_order/<int:doc_entry>/sales_items", methods=["GET"])
@verify_required
def api_get_sales_items_from_sales_order(doc_entry):
    try:
        items = get_sales_items_from_sales_order(doc_entry)
        return jsonify({"data": SalesItemSchema(many=True).dump(items), "success": True}), 200
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500



@app.route("/api/sales_order/get_test_quick", methods=["POST"])
@verify_required
def api_get_sales_order_test_quick():
    try:
        get_test_sales_order()
        return jsonify({"success": True}), 200
    except AppException as e:
        return jsonify({"error" : e.message}), e.status_code
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

