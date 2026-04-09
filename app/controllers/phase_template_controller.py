from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.ma_sqlalchemy import PhaseTemplateSchema
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
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    search = request.args.get("search", "", type=str)
    result = get_phase_template_list({"page": page, "per_page": per_page, "search": search})
    return jsonify({
        "data": {
            "items": PhaseTemplateSchema(many=True).dump(result.items),
            "total": result.total,
            "page": result.page,
            "pages": result.pages,
        },
        "success": True,
    }), 200


@app.route("/api/phase_template/all", methods=["GET"])
@verify_required
def api_get_all_phase_templates():
    result = get_all_phase_templates()
    return jsonify({"data": PhaseTemplateSchema(many=True).dump(result), "success": True}), 200


@app.route("/api/phase_template/<int:phase_template_id>", methods=["GET"])
@verify_required
def api_get_phase_template_by_id(phase_template_id):
    result = get_phase_template_by_id(phase_template_id)
    return jsonify({"data": PhaseTemplateSchema().dump(result), "success": True}), 200


@app.route("/api/phase_template/create", methods=["POST"])
@verify_required
def api_create_phase_template():
    data = request.get_json() or {}
    result = create_phase_template(data)
    return jsonify({"data": PhaseTemplateSchema().dump(result), "success": True}), 201


@app.route("/api/phase_template/<int:phase_template_id>", methods=["PUT"])
@verify_required
def api_update_phase_template(phase_template_id):
    data = request.get_json() or {}
    result = update_phase_template(phase_template_id, data)
    return jsonify({"data": PhaseTemplateSchema().dump(result), "success": True}), 200


@app.route("/api/phase_template/<int:phase_template_id>", methods=["DELETE"])
@verify_required
def api_delete_phase_template(phase_template_id):
    result = delete_phase_template(phase_template_id)
    return jsonify({"data": PhaseTemplateSchema().dump(result), "success": True}), 200
