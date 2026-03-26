from app.api_auth import verify_required
from app.app import app
from app.exception import AppException
from flask import request, jsonify
from app.services.item_component_service import (
    get_item_component_detail,
    get_item_component_with_sections,
    save_component_section_data,
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


@app.route("/api/item_component/<int:item_component_id>/sections", methods=["GET"])
@verify_required
def api_get_item_component_sections(item_component_id):
    try:
        result = get_item_component_with_sections(item_component_id)
        return jsonify({"data": result, "success": True}), 200
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/item_component/<int:item_component_id>/sections", methods=["POST"])
@verify_required
def api_save_item_component_sections(item_component_id):
    try:
        data = request.get_json()
        result = save_component_section_data(item_component_id, data)
        return jsonify({"data": result, "success": True}), 200
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500
