from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
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
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        search = request.args.get("search", "", type=str)
        data = {"page": page, "per_page": per_page, "search": search}
        result = get_machine_type_list(data)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/machine_type/all", methods=["GET"])
@verify_required
def api_get_all_machine_types():
    """Return all active machine types (for dropdowns)."""
    try:
        result = get_all_machine_types()
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/machine_type/<int:machine_type_id>", methods=["GET"])
@verify_required
def api_get_machine_type_by_id(machine_type_id):
    try:
        result = get_machine_type_by_id(machine_type_id)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/machine_type/create", methods=["POST"])
@verify_required
def api_create_machine_type():
    try:
        data = request.get_json() or {}
        result = create_machine_type(data)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/machine_type/<int:machine_type_id>", methods=["PUT"])
@verify_required
def api_update_machine_type(machine_type_id):
    try:
        data = request.get_json() or {}
        result = update_machine_type(machine_type_id, data)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500