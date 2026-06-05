from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.ma_sqlalchemy import ComponentTemplateSchema
from app.services.component_template_service import (
    get_all_templates,
    get_template_by_id,
    create_template,
    update_template,
    delete_template,
)
from app.services import cache_service
from app.services.storage_service import get_presigned_url, PRESIGNED_CACHE_TTL


def _cache_key(template_id: int) -> str:
    return f"component_template:{template_id}"


def _resolve_presigned_urls(template_dict: dict) -> dict:
    """Replace MinIO object keys in image_select options with presigned URLs."""
    for sec in template_dict.get("sections") or []:
        if sec.get("type") == "image_select":
            for opt in sec.get("options") or []:
                if opt.get("imageUrl"):
                    opt["imageUrl"] = get_presigned_url(opt["imageUrl"].lstrip("/"))
    return template_dict


@app.route("/api/component_templates", methods=["GET"])
@verify_required
def api_get_component_templates():
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        search = request.args.get("search", "", type=str)
        data = {"page": page, "per_page": per_page, "search": search}
        result = get_all_templates(data)
        return jsonify({
            "data": {"items": ComponentTemplateSchema(many=True).dump(result["items"])},
            "pagination": {"total": result["total"], "page": result["page"], "pages": result["pages"]},
            "success": True,
        }), 200
    except Exception:
        raise


@app.route("/api/component_templates/<int:template_id>", methods=["GET"])
@verify_required
def api_get_component_template_by_id(template_id):
    try:
        key = _cache_key(template_id)
        cached = cache_service.get(key)
        if cached:
            return jsonify({"data": cached, "success": True}), 200

        result = get_template_by_id(template_id)
        dumped = ComponentTemplateSchema().dump(result)
        resolved = _resolve_presigned_urls(dumped)
        cache_service.set(key, resolved, ttl=PRESIGNED_CACHE_TTL)
        return jsonify({"data": resolved, "success": True}), 200
    except Exception:
        raise


@app.route("/api/component_templates", methods=["POST"])
@verify_required
def api_create_component_template():
    try:
        data = request.get_json()
        result = create_template(data)
        return jsonify({"data": ComponentTemplateSchema().dump(result), "success": True}), 201
    except Exception:
        raise


@app.route("/api/component_templates/<int:template_id>", methods=["PUT"])
@verify_required
def api_update_component_template(template_id):
    try:
        data = request.get_json()
        result = update_template(template_id, data)
        cache_service.delete(_cache_key(template_id))
        return jsonify({"data": ComponentTemplateSchema().dump(result), "success": True}), 200
    except Exception:
        raise


@app.route("/api/component_templates/<int:template_id>", methods=["DELETE"])
@verify_required
def api_delete_component_template(template_id):
    try:
        result = delete_template(template_id)
        cache_service.delete(_cache_key(template_id))
        return jsonify({"data": ComponentTemplateSchema().dump(result), "success": True}), 200
    except Exception:
        raise
