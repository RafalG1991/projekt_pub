# lounge_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from extensions import mysql
from Lounge import Lounge

lounge_bp = Blueprint("lounge", __name__, url_prefix="/lounge")

@lounge_bp.get("/tables")
@jwt_required(optional=True)
def tables():
    data = Lounge.getTables(mysql)  
    return jsonify({"tables": data})

@lounge_bp.get("/tables/available")
@jwt_required(optional=True)
def available():
    guests = int(request.args.get("guests", 1))
    data = Lounge.getAvailableTables(mysql, guests)  
    return jsonify({"tables": data})

@lounge_bp.get('/areas')
@jwt_required()
def get_lounges():
    lounges = Lounge.getLounges(mysql)
    return jsonify({"lounges": [
        {"lounge_id": r["lounge_id"], "name": r["name"]} for r in lounges
    ]}), 200

@lounge_bp.get('/tables/by-area/<int:loungeId>')
@jwt_required()
def get_tables_by_area(loungeId):
    check = Lounge.getLoungeById(mysql, loungeId)
    if check is None:
        return jsonify({"error": f"Lounge {loungeId} not found"}), 404

    rows = Lounge.getTablesByLounge(mysql, loungeId)
    return jsonify({"tables": [
        {
            "table_id": r["table_id"],
            "table_number": r["table_number"],
            "capacity": r["capacity"],
            "table_status": r["table_status"],
            "lounge_id": r["lounge_id"],
            "lounge_name": r["lounge_name"],
        } for r in rows
    ]}), 200