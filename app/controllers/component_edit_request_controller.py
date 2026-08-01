from app.api_auth import decode_and_verify_permission_jwt, verify_required
from app.app import app
from flask import request, jsonify
from app.ma_sqlalchemy import ComponentEditRequestListSchema, ComponentEditRequestSchema
from app.services import component_edit_request_service


@app.route("/api/component_edit_request/list", methods=["GET"])
@verify_required
@decode_and_verify_permission_jwt(authorizes=[{"module_code": "COMPONENT_EDIT", "method": "view"}])
def api_get_component_edit_request_list():
    data = {
        "page": request.args.get("page", 1, type=int),
        "per_page": request.args.get("per_page", 10, type=int),
        "search": request.args.get("search", "", type=str),
        "status": request.args.get("status", "", type=str),
        "work_order_id": request.args.get("work_order_id", None, type=int),
    }
    result = component_edit_request_service.get_all_edit_requests(data)
    return jsonify({
        "data": {"items": ComponentEditRequestListSchema(many=True).dump(result["items"])},
        "pagination": {"total": result["total"], "page": result["page"], "pages": result["pages"]},
        "success": True,
    }), 200


@app.route("/api/component_edit_request/<int:edit_request_id>", methods=["GET"])
@verify_required
@decode_and_verify_permission_jwt(authorizes=[{"module_code": "COMPONENT_EDIT", "method": "view"}])
def api_get_component_edit_request(edit_request_id):
    result = component_edit_request_service.get_edit_request_detail(edit_request_id)
    return jsonify({"data": ComponentEditRequestListSchema().dump(result), "success": True}), 200


@app.route("/api/item_component/<int:item_component_id>/edit_request", methods=["GET"])
@verify_required
def api_get_component_edit_requests_for_component(item_component_id):
    result = component_edit_request_service.get_requests_for_component(item_component_id)
    return jsonify({"data": ComponentEditRequestSchema(many=True).dump(result), "success": True}), 200


@app.route("/api/item_component/<int:item_component_id>/edit_request", methods=["POST"])
@verify_required
@decode_and_verify_permission_jwt(authorizes=[{"module_code": "COMPONENT_EDIT", "method": "create"}])
def api_create_component_edit_request(item_component_id):
    data = request.get_json() or {}
    result = component_edit_request_service.create_edit_request(item_component_id, data)
    return jsonify({"data": ComponentEditRequestSchema().dump(result), "success": True}), 201


@app.route("/api/component_edit_request/<int:edit_request_id>/approve", methods=["POST"])
@verify_required
@decode_and_verify_permission_jwt(authorizes=[{"module_code": "COMPONENT_EDIT", "method": "edit"}])
def api_approve_component_edit_request(edit_request_id):
    data = request.get_json() or {}
    result = component_edit_request_service.approve_edit_request(edit_request_id, data)
    return jsonify({"data": ComponentEditRequestSchema().dump(result), "success": True}), 200


@app.route("/api/component_edit_request/<int:edit_request_id>/reject", methods=["POST"])
@verify_required
@decode_and_verify_permission_jwt(authorizes=[{"module_code": "COMPONENT_EDIT", "method": "edit"}])
def api_reject_component_edit_request(edit_request_id):
    data = request.get_json() or {}
    result = component_edit_request_service.reject_edit_request(edit_request_id, data)
    return jsonify({"data": ComponentEditRequestSchema().dump(result), "success": True}), 200


@app.route("/api/component_edit_request/<int:edit_request_id>/cancel", methods=["POST"])
@verify_required
def api_cancel_component_edit_request(edit_request_id):
    result = component_edit_request_service.cancel_edit_request(edit_request_id)
    return jsonify({"data": ComponentEditRequestSchema().dump(result), "success": True}), 200
