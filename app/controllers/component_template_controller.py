from app.api_auth import verify_required
from app.app import app
from app.exception import AppException
from flask import request, jsonify
from app.ma_sqlalchemy import ComponentTemplateSchema
from app.services.component_template_service import (
    get_all_templates,
    get_template_by_id,
    create_template,
    update_template,
    delete_template,
)


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
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/component_templates/<int:template_id>", methods=["GET"])
@verify_required
def api_get_component_template_by_id(template_id):
    try:
        result = get_template_by_id(template_id)
        return jsonify({"data": ComponentTemplateSchema().dump(result), "success": True}), 200
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/component_templates", methods=["POST"])
@verify_required
def api_create_component_template():
    try:
        data = request.get_json()
        result = create_template(data)
        return jsonify({"data": ComponentTemplateSchema().dump(result), "success": True}), 201
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/component_templates/<int:template_id>", methods=["PUT"])
@verify_required
def api_update_component_template(template_id):
    try:
        data = request.get_json()
        result = update_template(template_id, data)
        return jsonify({"data": ComponentTemplateSchema().dump(result), "success": True}), 200
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/component_templates/<int:template_id>", methods=["DELETE"])
@verify_required
def api_delete_component_template(template_id):
    try:
        result = delete_template(template_id)
        return jsonify({"data": ComponentTemplateSchema().dump(result), "success": True}), 200
    except AppException as e:
        return jsonify({"error": e.message}), e.status_code
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500
