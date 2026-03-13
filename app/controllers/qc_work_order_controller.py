import traceback
from app.api_auth import verify_required
from app.app import app
from app.exception import AppException
from flask import request, jsonify
from app.ma_sqlalchemy import QCWorkOrderSchema, QCWorkOrderSchemaDetail, search_qc_work_order_schema
from app.services.qc_work_order_service import (
    get_all_qc_work_orders,
    get_qc_work_order_by_id,
    create_qc_work_order,
    search_qc_work_orders,
    update_qc_work_order,
    delete_qc_work_order,
)



@app.route("/api/get_qc_work_order_list", methods=["GET"])
@verify_required
def api_get_qc_work_order_list():
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        search = request.args.get("search", "", type=str)
        data = {"page": page, "per_page": per_page, "search": search}
        result = get_all_qc_work_orders(data)
        return jsonify({
            "data": {"items": QCWorkOrderSchema(many=True).dump(result["items"])},
            "pagination": {"total": result["total"], "page": result["page"], "pages": result["pages"]},
            "success": True,
        }), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/qc_work_order/<int:qc_work_order_id>", methods=["GET"])
@verify_required
def api_get_qc_work_order_by_id(qc_work_order_id):
    try:
        result = get_qc_work_order_by_id(qc_work_order_id)
        return jsonify({"data": QCWorkOrderSchemaDetail().dump(result), "success": True}), 200
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/qc_work_order/create", methods=["POST"])
@verify_required
def api_create_qc_work_order():
    try:
        data = request.get_json()
        result = create_qc_work_order(data)
        return jsonify({"data": QCWorkOrderSchema().dump(result), "success": True}), 201
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/qc_work_order/update/<int:qc_work_order_id>", methods=["PUT"])
@verify_required
def api_update_qc_work_order(qc_work_order_id):
    try:
        data = request.get_json() or {}
        result = update_qc_work_order(qc_work_order_id, data)
        return jsonify({"data": QCWorkOrderSchema().dump(result), "success": True}), 200
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/qc_work_order/delete/<int:qc_work_order_id>", methods=["DELETE"])
@verify_required
def api_delete_qc_work_order(qc_work_order_id):
    try:
        result = delete_qc_work_order(qc_work_order_id)
        return jsonify({"data": result, "success": True}), 200
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/search_qc_work_order", methods=["GET"])
@verify_required
def api_search_qc_work_order():
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        search = request.args.get("search", "", type=str)
        data = {"page": page, "per_page": per_page, "search": search}

        result = search_qc_work_orders(data)
        return jsonify({
            "data": {"items": search_qc_work_order_schema(many=True).dump(result["items"])},
            "pagination": {"total": result["total"], "page": result["page"], "pages": result["pages"]},
            "success": True,
        }), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500