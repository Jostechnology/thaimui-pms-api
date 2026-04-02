from app.api_auth import verify_required
from app.app import app, db
from flask import request, jsonify
from app.services.item_component_service import (
    get_item_component_detail,
    get_item_component_with_sections,
    save_component_section_data,
    batch_save_component_section_data,
)
from app.services.document_generator_service import generate_component_detail


@app.route("/api/get_item_component_detail/<int:item_component_id>", methods=["GET"])
@verify_required
def api_get_item_component_detail(item_component_id):
    try:
        result = get_item_component_detail(item_component_id)
        return jsonify({"data": result, "success": True}), 200
    except Exception:
        raise


@app.route("/api/item_component/<int:item_component_id>/sections", methods=["GET"])
@verify_required
def api_get_item_component_sections(item_component_id):
    try:
        result = get_item_component_with_sections(item_component_id)
        return jsonify({"data": result, "success": True}), 200
    except Exception:
        raise


@app.route("/api/item_component/sections/batch", methods=["POST"])
@verify_required
def api_batch_save_item_component_sections():
    try:
        data = request.get_json()
        data = data.get("data")
        result = batch_save_component_section_data(data)
        return jsonify({"data": result, "success": True}), 200
    except Exception:
        raise


@app.route("/api/item_component/<int:item_component_id>/sections", methods=["POST"])
@verify_required
def api_save_item_component_sections(item_component_id):
    try:
        data = request.get_json()
        result = save_component_section_data(item_component_id, data)
        return jsonify({"data": result, "success": True}), 200
    except Exception:
        raise


@app.route("/api/item_component/<int:item_component_id>/resend_document", methods=["POST"])
@verify_required
def api_resend_component_document(item_component_id):
    try:
        generate_component_detail(item_component_id)
        db.session.commit()
        return jsonify({"success": True, "message": "Document generation request sent"}), 200
    except Exception:
        raise
