from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.ma_sqlalchemy import MachineTypeSchema
from app.services.machine_type_service import (
    get_machine_type_list,
    get_all_machine_types,
    get_machine_type_by_id,
    create_machine_type,
    update_machine_type,
    delete_machine_type,
)


@app.route("/api/machine_type/list", methods=["GET"])
@verify_required
def api_get_machine_type_list():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    search = request.args.get("search", "", type=str)
    result = get_machine_type_list({"page": page, "per_page": per_page, "search": search})
    return jsonify({
        "data": {
            "items": MachineTypeSchema(many=True).dump(result.items),
            "total": result.total,
            "page": result.page,
            "pages": result.pages,
        },
        "success": True,
    }), 200


@app.route("/api/machine_type/all", methods=["GET"])
@verify_required
def api_get_all_machine_types():
    result = get_all_machine_types()
    return jsonify({"data": MachineTypeSchema(many=True).dump(result), "success": True}), 200


@app.route("/api/machine_type/<int:machine_type_id>", methods=["GET"])
@verify_required
def api_get_machine_type_by_id(machine_type_id):
    result = get_machine_type_by_id(machine_type_id)
    return jsonify({"data": MachineTypeSchema().dump(result), "success": True}), 200


@app.route("/api/machine_type/create", methods=["POST"])
@verify_required
def api_create_machine_type():
    data = request.get_json() or {}
    result = create_machine_type(data)
    return jsonify({"data": MachineTypeSchema().dump(result), "success": True}), 201


@app.route("/api/machine_type/<int:machine_type_id>", methods=["PUT"])
@verify_required
def api_update_machine_type(machine_type_id):
    data = request.get_json() or {}
    result = update_machine_type(machine_type_id, data)
    return jsonify({"data": MachineTypeSchema().dump(result), "success": True}), 200


@app.route("/api/machine_type/<int:machine_type_id>", methods=["DELETE"])
@verify_required
def api_delete_machine_type(machine_type_id):
    result = delete_machine_type(machine_type_id)
    return jsonify({"data": MachineTypeSchema().dump(result), "success": True}), 200
