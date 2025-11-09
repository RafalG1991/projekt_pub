# reports_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from extensions import mysql
from authz import role_required     # <--- DODANE
from Reports import Report

reports_bp = Blueprint("reports", __name__, url_prefix="/report")

@reports_bp.get("/inventory")
@jwt_required()
@role_required("admin")             # <--- TYLKO ADMIN
def inventory():
    res = Report.inventory_report(mysql)
    return jsonify({"inventory": res})

@reports_bp.get("/orders")
@jwt_required()
@role_required("admin")             # <--- TYLKO ADMIN
def orders_report():
    res = Report.orders_report(mysql)
    return jsonify({"orders": res})

@reports_bp.post("/add")
@jwt_required()
@role_required("admin")             # <--- TYLKO ADMIN
def add_ingr():
    req = request.get_json() or {}
    ing_id = req.get("id")
    qty = req.get("quantity")
    if ing_id is None or qty is None:
        return jsonify({"status": "error", "error": "invalid payload"}), 400
    ok = Report.add_ingredient(mysql, qty, ing_id)
    return jsonify({"status": "ok" if ok else "error"})

@reports_bp.get("/recheck")
@jwt_required()
@role_required("admin")
def recheck_all():
    res = Report.checkAllStocks(mysql)
    return {"notified": res}