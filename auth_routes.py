# auth_routes.py
from datetime import datetime
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
from extensions import mysql

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.post("/register")
def register():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    name = (data.get("name") or "").strip()
    password = data.get("password") or ""
    role = (data.get("role") or "employee").strip()

    if not email or not name or not password:
        return jsonify({"error": "missing fields"}), 400
    if len(password) < 6:
        return jsonify({"error": "weak password"}), 400

    cur = mysql.connection.cursor()
    cur.execute("SELECT user_id FROM users WHERE email=%s", (email,))
    if cur.fetchone():
        cur.close()
        return jsonify({"error": "email taken"}), 409

    cur.execute(
        "INSERT INTO users(email, name, role, password_hash) VALUES (%s,%s,%s,%s)",
        (email, name, role, generate_password_hash(password))
    )
    mysql.connection.commit()
    cur.close()
    return jsonify({"ok": True}), 201

@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    cur = mysql.connection.cursor()
    cur.execute("SELECT user_id, email, name, role, password_hash FROM users WHERE email=%s", (email,))
    u = cur.fetchone()
    cur.close()
    if not u or not check_password_hash(u["password_hash"], password):
        return jsonify({"error": "invalid credentials"}), 401

    user_claims = {"email": u["email"], "role": u["role"], "name": u["name"]}
    access = create_access_token(identity=str(u["user_id"]), additional_claims=user_claims)
    refresh = create_refresh_token(identity=str(u["user_id"]), additional_claims=user_claims)
    user = {"id": u["user_id"], **user_claims}
    return jsonify({"access_token": access, "refresh_token": refresh, "user": user})

@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    claims = get_jwt()                      # <— pełne claims
    user_claims = {"email": claims.get("email"), "role": claims.get("role"), "name": claims.get("name")}
    access = create_access_token(identity=get_jwt_identity(), additional_claims=user_claims)
    return jsonify({"access_token": access})

@auth_bp.post("/logout")
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    exp_ts = get_jwt().get("exp")
    exp = datetime.fromtimestamp(exp_ts) if exp_ts else None

    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO jwt_blocklist(jti, expires_at) VALUES (%s,%s)", (jti, exp))
    mysql.connection.commit()
    cur.close()
    return jsonify({"ok": True})

@auth_bp.get("/me")
@jwt_required()
def me():
    # identity to teraz string user_id, a szczegóły trzymamy w claims
    sub = get_jwt_identity()
    claims = get_jwt()
    return jsonify({
        "user": {
            "id": int(sub),
            "email": claims.get("email"),
            "role": claims.get("role"),
            "name": claims.get("name"),
        }
    })
