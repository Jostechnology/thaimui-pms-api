from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.services.item_component_service import (
    get_item_component_detail,
    get_component_spec_types,
    get_component_option_types,
    update_item_component_detail,
)


@app.route("/api/get_item_component_detail/<int:item_component_id>", methods=["GET"])
@verify_required
def api_get_item_component_detail(item_component_id):
    try:
        result = get_item_component_detail(item_component_id)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/get_component_spec_types", methods=["GET"])
@verify_required
def api_get_component_spec_types():
    try:
        result = get_component_spec_types()
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/get_component_option_types", methods=["GET"])
@verify_required
def api_get_component_option_types():
    try:
        result = get_component_option_types()
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/update_item_component_detail/<int:item_component_id>", methods=["PUT"])
@verify_required
def api_update_item_component_detail(item_component_id):
    try:
        data = request.get_json()
        result = update_item_component_detail(item_component_id, data)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500
