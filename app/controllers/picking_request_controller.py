from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.ma_sqlalchemy import PickingRequestDetailSchema, PickingRequestSchema
from app.services import picking_request_service


@app.route("/api/picking_request/list", methods=["GET"])
@verify_required
def api_get_picking_request_list():
    data = {
        "page": request.args.get("page", 1, type=int),
        "per_page": request.args.get("per_page", 10, type=int),
        "search": request.args.get("search", "", type=str),
        "status": request.args.get("status", "", type=str),
        "doc_entry": request.args.get("doc_entry", None, type=int),
    }
    result = picking_request_service.get_list(data)
    return jsonify({
        "data": {"items": PickingRequestDetailSchema(many=True).dump(result["items"])},
        "pagination": {"total": result["total"], "page": result["page"], "pages": result["pages"]},
        "success": True,
    }), 200


@app.route("/api/sales_order/<int:doc_entry>/picking_request", methods=["POST"])
@verify_required
def api_create_picking_request_for_sales_order(doc_entry):
    data = request.get_json()
    result = picking_request_service.create_for_sales_order(doc_entry, data)
    return jsonify({"data": PickingRequestDetailSchema().dump(result), "success": True}), 201


@app.route("/api/sales_order/<int:doc_entry>/picking_request", methods=["GET"])
@verify_required
def api_get_picking_requests_for_sales_order(doc_entry):
    result = picking_request_service.get_by_sales_order(doc_entry)
    return jsonify({"data": PickingRequestDetailSchema(many=True).dump(result), "success": True}), 200


@app.route("/api/picking_request/<int:picking_request_id>/status", methods=["PATCH"])
@verify_required
def api_update_picking_request_status(picking_request_id):
    data = request.get_json()
    result = picking_request_service.update_status(picking_request_id, data)
    return jsonify({"data": PickingRequestSchema().dump(result), "success": True}), 200
