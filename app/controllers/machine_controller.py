from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.services.machine_service import (
    get_machine_list,
    get_machine_by_id,
    create_machine,
    update_machine,
    delete_machine,
)

@app.route("/api/get_machine_list", methods=["GET"])
@verify_required
def api_get_machine_list():
    try:
        page = request.args.get("page", type=int)
        per_page = request.args.get("per_page", type=int)
        search = request.args.get("search", "", type=str)
        keyword = request.args.get("keyword", "", type=str)
        query = request.args.get("query", "", type=str)
        status = request.args.get("status", "", type=str)
        is_active = request.args.get("is_active", None, type=str)

        if page is None or per_page is None:
            return jsonify({"error": "page and per_page are required"}), 400

        data = {
            "page": page,
            "per_page": per_page,
            "search": search,
            "keyword": keyword,
            "query": query,
            "status": status,
            "is_active": is_active,
        }
        result = get_machine_list(data)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/get_machine_id/<int:machine_id>", methods=["GET"])
@verify_required
def api_get_machine_by_id(machine_id):
    try:
        result = get_machine_by_id(machine_id)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/create_machine", methods=["POST"])
@verify_required
def api_create_machine():
    try:
        data = request.get_json() or {}
        result = create_machine(data)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/update_machine/<int:machine_id>", methods=["PUT"])
@verify_required
def api_update_machine(machine_id):
    try:
        data = request.get_json() or {}
        result = update_machine(machine_id, data)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/delete_machine/<int:machine_id>", methods=["DELETE"])
@verify_required
def api_delete_machine(machine_id):
    try:
        result = delete_machine(machine_id)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500