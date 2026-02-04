from app.app import app, db
from flask import request, jsonify
from app.services import user_service

@app.route("/api/get_all_roles", methods=["GET", "POST"])
def api_get_all_roles():
    try:
        data = request.get_json(silent=True) or {}
        username = data.get("username")
        role_id = data.get("role_id")
        
        # Handle "undefined" string from frontend
        if role_id == "undefined":
            role_id = None
            
        result, status = user_service.get_all_roles(username, role_id)
        
        return jsonify({
            "data": result,
            "success": True,
            "message": "ดึงรายการบทบาททั้งหมดสำเร็จ"
        }), status
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "เกิดข้อผิดพลาดในการดึงข้อมูล",
            "error": str(e)
        }), 500