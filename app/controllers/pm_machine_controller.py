from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.services.pm_machine_service import get_all_pm_machines, create_pm_machine

@app.route("/api/get_pm_machine", methods=["GET"])
@verify_required
def api_get_pm_machine():
    try:
        search = request.args.get("search", "", type=str)
        page = request.args.get("page", type=int)
        per_page = request.args.get("per_page", type=int)
        data = {
            "search": search , 
            "page": page,
            "per_page": per_page
            }
        result = get_all_pm_machines(data)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/create_pm_machine", methods=["POST"])
@verify_required
def api_create_pm_machine():
    try:
        data = request.get_json()
        result = create_pm_machine(data)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500