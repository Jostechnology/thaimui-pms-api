from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.services.employee_service import delete_employee, get_all_employees, create_employee, update_employee

@app.route("/api/get_employee_list", methods=["GET"])
@verify_required
def api_get_employee_list():
    try:
        search = request.args.get("search", "", type=str)
        data = {"search": search}
        
        result = get_all_employees(data)
        return jsonify({"data": result, "success": True}), 200  
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/create_employee", methods=["POST"])
@verify_required
def api_create_employee():
    try:
        data = request.get_json()
        result = create_employee(data)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/update_employee", methods=["PUT"])
@verify_required
def api_update_employee():
    try:
        data = request.get_json()
        result = update_employee(data)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/delete_employee", methods=["DELETE"])
@verify_required
def api_delete_employee():
    try:
        data = request.get_json()
        employee_ids = data.get("employee_ids", [])
        result = delete_employee(employee_ids)
        return jsonify({"data": result, "success": True}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500