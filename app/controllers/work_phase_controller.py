from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.services.work_phase_service import create_work_phase, delete_work_phase, edit_work_phase, update_phase_status


@app.route("/api/create_work_phase", methods=["POST"])
@verify_required
def api_create_work_phase():
    try:
        data = request.get_json()
        result = create_work_phase(data)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/edit_work_phase/<int:work_phase_id>", methods=["PUT"])
@verify_required
def api_edit_work_phase(work_phase_id):
    try:
        data = request.get_json()
        result = edit_work_phase(work_phase_id, data)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/update_work_phase/<int:work_phase_id>", methods=["PUT"])
@verify_required
def api_update_work_phase(work_phase_id):
    try:
        data = request.get_json()
        result = update_phase_status(work_phase_id, data)
        return jsonify({"data": result, "success": True}), 200
    except ValueError as e:
        return jsonify({"error": str(e), "success": False}), 400
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/delete_work_phase", methods=["DELETE"])
@verify_required
def api_delete_work_phase():
    try:
        data = request.get_json()
        work_phase_ids = data.get("work_phase_ids", [])
        if not work_phase_ids:
            return jsonify({"error": "work_phase_ids is required", "success": False}), 400
        result = delete_work_phase(work_phase_ids)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

