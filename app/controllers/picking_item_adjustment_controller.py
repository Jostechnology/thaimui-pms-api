from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.ma_sqlalchemy import PickingItemAdjustmentSchema
from app.services import picking_item_adjustment_service


@app.route("/api/picking_request_item/<int:picking_request_item_id>/adjustment", methods=["POST"])
@verify_required
def api_create_picking_item_adjustment(picking_request_item_id):
    data = request.get_json()
    result = picking_item_adjustment_service.create_adjustment(picking_request_item_id, data)
    return jsonify({"data": PickingItemAdjustmentSchema().dump(result), "success": True}), 201


@app.route("/api/picking_request_item/<int:picking_request_item_id>/adjustment", methods=["GET"])
@verify_required
def api_get_picking_item_adjustments(picking_request_item_id):
    data = {
        "page": request.args.get("page", 1, type=int),
        "per_page": request.args.get("per_page", 10, type=int),
    }
    result = picking_item_adjustment_service.get_list(picking_request_item_id, data)
    return jsonify({
        "data": {"items": PickingItemAdjustmentSchema(many=True).dump(result["items"])},
        "pagination": {"total": result["total"], "page": result["page"], "pages": result["pages"]},
        "success": True,
    }), 200


@app.route("/api/picking_request/<int:picking_request_id>/adjustment", methods=["GET"])
@verify_required
def api_get_adjustments_by_picking_request(picking_request_id):
    data = {
        "page": request.args.get("page", 1, type=int),
        "per_page": request.args.get("per_page", 10, type=int),
    }
    result = picking_item_adjustment_service.get_list_by_picking_request(picking_request_id, data)
    return jsonify({
        "data": {"items": PickingItemAdjustmentSchema(many=True).dump(result["items"])},
        "pagination": {"total": result["total"], "page": result["page"], "pages": result["pages"]},
        "success": True,
    }), 200
