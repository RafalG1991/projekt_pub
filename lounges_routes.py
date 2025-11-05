# lounge_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from extensions import mysql
from Lounge import Lounge

lounge_bp = Blueprint("lounge", __name__, url_prefix="/lounge")

@lounge_bp.get("/tables")
@jwt_required()
def tables():
    data = Lounge.getTables(mysql)  # <-- nazwa 1:1
    return jsonify({"tables": data})

@lounge_bp.get("/tables/available")
@jwt_required()
def available():
    guests = int(request.args.get("guests", 1))
    data = Lounge.getAvailableTables(mysql, guests)  # <-- nazwa 1:1
    return jsonify({"tables": data})
