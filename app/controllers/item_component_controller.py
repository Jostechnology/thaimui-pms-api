from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.ma_sqlalchemy import (
    ItemComponentSchema,
    ItemComponentVersionSchema,
    ItemComponentVersionListSchema,
)
from app.services.item_component_service import (
    get_item_component_detail,
    get_item_component_with_sections,
    get_item_component_version,
    get_item_component_versions,
    resend_component_document,
    save_component,
    save_component_section_data,
    batch_save_component_section_data,
    update_component_material_usage,
)


@app.route("/api/get_item_component_detail/<int:item_component_id>", methods=["GET"])
@verify_required
def api_get_item_component_detail(item_component_id):
    try:
        result = get_item_component_detail(item_component_id)
        return jsonify({"data": ItemComponentSchema().dump(result), "success": True}), 200
    except Exception:
        raise


@app.route("/api/item_component/<int:item_component_id>/sections", methods=["GET"])
@verify_required
def api_get_item_component_sections(item_component_id):
    try:
        result = get_item_component_with_sections(item_component_id)
        return jsonify({"data": ItemComponentSchema().dump(result), "success": True}), 200
    except Exception:
        raise


@app.route("/api/item_component/sections/batch", methods=["POST"])
@verify_required
def api_batch_save_item_component_sections():
    try:
        data = request.get_json()
        data = data.get("data")
        result = batch_save_component_section_data(data)
        notices = [n for n in (getattr(r, "test_section_notice", None) for r in result) if n]
        return jsonify({
            "data": ItemComponentSchema(many=True).dump(result),
            "test_section_notices": notices,
            "success": True,
        }), 200
    except Exception:
        raise


@app.route("/api/item_component/<int:item_component_id>/sections", methods=["POST"])
@verify_required
def api_save_item_component_sections(item_component_id):
    try:
        data = request.get_json()
        result = save_component_section_data(item_component_id, data)
        return jsonify({
            "data": ItemComponentSchema().dump(result),
            "test_section_notice": getattr(result, "test_section_notice", None),
            "success": True,
        }), 200
    except Exception:
        raise


@app.route("/api/item_component/<int:item_component_id>/material_usage", methods=["PATCH"])
@verify_required
def api_update_item_component_material_usage(item_component_id):
    try:
        data = request.get_json()
        result = update_component_material_usage(item_component_id, data)
        return jsonify({"data": ItemComponentSchema().dump(result), "success": True}), 200
    except Exception:
        raise


@app.route("/api/item_component/<int:item_component_id>/save", methods=["POST"])
@verify_required
def api_save_item_component(item_component_id):
    try:
        data = request.get_json()
        result = save_component(item_component_id, data)
        return jsonify({
            "data": ItemComponentSchema().dump(result),
            "test_section_notice": getattr(result, "test_section_notice", None),
            "success": True,
        }), 200
    except Exception:
        raise


@app.route("/api/item_component/<int:item_component_id>/versions", methods=["GET"])
@verify_required
def api_get_item_component_versions(item_component_id):
    try:
        result = get_item_component_versions(item_component_id)
        return jsonify({
            "data": ItemComponentVersionListSchema(many=True).dump(result),
            "success": True,
        }), 200
    except Exception:
        raise


@app.route("/api/item_component/<int:item_component_id>/versions/<int:version_no>", methods=["GET"])
@verify_required
def api_get_item_component_version(item_component_id, version_no):
    try:
        result = get_item_component_version(item_component_id, version_no)
        return jsonify({"data": ItemComponentVersionSchema().dump(result), "success": True}), 200
    except Exception:
        raise


@app.route("/api/item_component/<int:item_component_id>/resend_document", methods=["POST"])
@verify_required
def api_resend_component_document(item_component_id):
    try:
        result = resend_component_document(item_component_id)
        return jsonify({
            "data": ItemComponentVersionListSchema().dump(result),
            "success": True,
            "message": "Document generation request sent",
        }), 200
    except Exception:
        raise
