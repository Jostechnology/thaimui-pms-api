from app.api_auth import verify_required
from app.app import app
from flask import request, jsonify
from app.ma_sqlalchemy import HolidaySchema
from app.services import holiday_service


@app.route("/api/get_holiday_list", methods=["GET"])
@verify_required
def api_get_holiday_list():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 31, type=int)
    search = request.args.get("search", "", type=str)
    year = request.args.get("year", type=int)
    result = holiday_service.get_all_holidays({"page": page, "per_page": per_page, "search": search, "year": year})
    return jsonify({
        "data": {"items": HolidaySchema(many=True).dump(result["items"])},
        "pagination": {"total": result["total"], "page": result["page"], "pages": result["pages"]},
        "success": True,
    }), 200


@app.route("/api/get_holiday/<int:holiday_id>", methods=["GET"])
@verify_required
def api_get_holiday_by_id(holiday_id):
    h = holiday_service.get_holiday_by_id(holiday_id)
    return jsonify({"data": HolidaySchema().dump(h), "success": True}), 200


@app.route("/api/create_holiday", methods=["POST"])
@verify_required
def api_create_holiday():
    data = request.get_json() or {}
    h = holiday_service.create_holiday(data)
    return jsonify({"data": HolidaySchema().dump(h), "success": True}), 200


@app.route("/api/update_holiday/<int:holiday_id>", methods=["PUT"])
@verify_required
def api_update_holiday(holiday_id):
    data = request.get_json() or {}
    h = holiday_service.update_holiday(holiday_id, data)
    return jsonify({"data": HolidaySchema().dump(h), "success": True}), 200


@app.route("/api/delete_holiday/<int:holiday_id>", methods=["DELETE"])
@verify_required
def api_delete_holiday(holiday_id):
    result = holiday_service.delete_holiday(holiday_id)
    return jsonify({"data": result, "success": True}), 200


@app.route("/api/sync_holidays", methods=["POST"])
@verify_required
def api_sync_holidays():
    data = request.get_json() or {}
    year = data.get("year") or request.args.get("year", type=int)
    result = holiday_service.sync_holidays_from_api(year)
    return jsonify({"data": result, "success": True}), 200
