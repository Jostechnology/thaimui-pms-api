from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.services.work_phase_service import create_work_phase, update_work_phase , delete_work_phase


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


    
@app.route("/api/delete_work_phase/<int:work_phase_id>", methods=["DELETE"])
@verify_required
def api_delete_work_phase(work_phase_id):
    try:
        result = delete_work_phase(work_phase_id)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@app.route("/api/update_work_phase/<int:work_phase_id>", methods=["PUT"])
@verify_required
def api_update_work_phase(work_phase_id):
    try:
        data = request.get_json()
        result = update_work_phase(work_phase_id, data)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500
