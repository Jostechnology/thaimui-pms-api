from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.ma_sqlalchemy import ShiftSchema
from app.services import shift_service


@app.route("/api/get_shift_list", methods=["GET"])
@verify_required
def api_get_shift_list():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    search = request.args.get("search", "", type=str)
    result = shift_service.get_all_shifts({"page": page, "per_page": per_page, "search": search})
    return jsonify({
        "data": {"items": ShiftSchema(many=True).dump(result["items"])},
        "pagination": {"total": result["total"], "page": result["page"], "pages": result["pages"]},
        "success": True,
    }), 200


@app.route("/api/get_shift/<int:shift_id>", methods=["GET"])
@verify_required
def api_get_shift_by_id(shift_id):
    shift = shift_service.get_shift_by_id(shift_id)
    return jsonify({"data": ShiftSchema().dump(shift), "success": True}), 200


@app.route("/api/get_default_shift", methods=["GET"])
@verify_required
def api_get_default_shift():
    shift = shift_service.get_default_shift()
    return jsonify({"data": ShiftSchema().dump(shift), "success": True}), 200


@app.route("/api/create_shift", methods=["POST"])
@verify_required
def api_create_shift():
    data = request.get_json() or {}
    shift = shift_service.create_shift(data)
    return jsonify({"data": ShiftSchema().dump(shift), "success": True}), 200


@app.route("/api/update_shift/<int:shift_id>", methods=["PUT"])
@verify_required
def api_update_shift(shift_id):
    data = request.get_json() or {}
    shift = shift_service.update_shift(shift_id, data)
    return jsonify({"data": ShiftSchema().dump(shift), "success": True}), 200


@app.route("/api/delete_shift/<int:shift_id>", methods=["DELETE"])
@verify_required
def api_delete_shift(shift_id):
    result = shift_service.delete_shift(shift_id)
    return jsonify({"data": result, "success": True}), 200
