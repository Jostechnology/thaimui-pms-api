from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.services.phase_template_service import (
    get_phase_template_list,
    get_all_phase_templates,
    get_phase_template_by_id,
    create_phase_template,
    update_phase_template,
    delete_phase_template,
)


@app.route("/api/phase_template/list", methods=["GET"])
@verify_required
def api_get_phase_template_list():
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        search = request.args.get("search", "", type=str)
        data = {"page": page, "per_page": per_page, "search": search}
        result = get_phase_template_list(data)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/phase_template/all", methods=["GET"])
@verify_required
def api_get_all_phase_templates():
    """Return all active templates (for dropdowns)."""
    try:
        result = get_all_phase_templates()
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/phase_template/<int:phase_template_id>", methods=["GET"])
@verify_required
def api_get_phase_template_by_id(phase_template_id):
    try:
        result = get_phase_template_by_id(phase_template_id)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/phase_template/create", methods=["POST"])
@verify_required
def api_create_phase_template():
    try:
        data = request.get_json() or {}
        result = create_phase_template(data)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/phase_template/<int:phase_template_id>", methods=["PUT"])
@verify_required
def api_update_phase_template(phase_template_id):
    try:
        data = request.get_json() or {}
        result = update_phase_template(phase_template_id, data)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/phase_template/<int:phase_template_id>", methods=["DELETE"])
@verify_required
def api_delete_phase_template(phase_template_id):
    try:
        result = delete_phase_template(phase_template_id)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500
