# auth_routes.py
from datetime import datetime
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
from extensions import mysql
from mailer import send_email
from tokens import generate_activation_token, expiry
import os

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.post("/register")
def register():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")  # zakładam że masz hashowanie gdzieś (bcrypt)
    name = (data.get("name") or "").strip()
    role = "employee"  # lub wg formularza, ale zwykle pracę zaczyna się od 'employee'

    if not email or not password:
        return jsonify({"ok": False, "error": "invalid_payload"}), 400

    cur = mysql.connection.cursor()
    # sprawdź duplikat
    cur.execute("SELECT user_id FROM users WHERE email=%s", (email,))
    if cur.fetchone():
        cur.close()
        return jsonify({"ok": False, "error": "email_in_use"}), 409

    # TODO: zahashuj hasło (bcrypt/werkzeug.security)
    from werkzeug.security import generate_password_hash
    password_hash = generate_password_hash(password)

    token = generate_activation_token()
    exp = expiry(24)

    cur.execute("""
        INSERT INTO users (email, password_hash, name, role, is_active, activation_token, activation_expires)
        VALUES (%s, %s, %s, %s, 0, %s, %s)
    """, (email, password_hash, name, role, token, exp))
    mysql.connection.commit()
    cur.close()

    # Wyślij mail
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    activation_link_front = f"{frontend_url}/activate?token={token}"
    activation_link_back = f"http://127.0.0.1:5000/auth/activate/{token}"

    subject = "Aktywacja konta w Pub Manager"
    body = (
        f"Cześć {name or email},\n\n"
        f"Dziękujemy za rejestrację. Aktywuj swoje konto klikając w link (ważny 24h):\n\n"
        f"{activation_link_front}\n\n"
        f"(Alternatywnie: {activation_link_back})\n\n"
        f"Pozdrawiamy,\nZespół Pub Manager"
    )
    send_email(subject, [email], body)

    return jsonify({"ok": True, "message": "activation_sent"}), 201

# GET /auth/activate/<token> – backendowa aktywacja (link z maila może iść tu)
@auth_bp.get("/activate/<token>")
def activate_with_path(token: str):
    return _activate_common(token)


# GET /auth/activate – aktywacja przez ?token=...
@auth_bp.get("/activate")
def activate_with_query():
    token = request.args.get("token", "")
    return _activate_common(token)


def _activate_common(token: str):
    if not token:
        return jsonify({"ok": False, "error": "missing_token"}), 400
    cur = mysql.connection.cursor()
    cur.execute("""
      SELECT user_id, activation_expires
      FROM users
      WHERE activation_token=%s AND is_active=0
    """, (token,))
    row = cur.fetchone()
    if not row:
        cur.close()
        return jsonify({"ok": False, "error": "invalid_or_used"}), 400

    # DictCursor/tuple
    user_id = row["user_id"] if isinstance(row, dict) else row[0]
    expires = row["activation_expires"] if isinstance(row, dict) else row[1]
    if isinstance(expires, str):
        # jeśli driver zwróci string
        try:
            expires = datetime.fromisoformat(expires)
        except Exception:
            pass

    if expires and datetime.utcnow() > expires:
        cur.close()
        return jsonify({"ok": False, "error": "token_expired"}), 400

    # aktywuj i wyczyść token
    cur.execute("""
      UPDATE users
      SET is_active=1, activation_token=NULL, activation_expires=NULL
      WHERE user_id=%s
    """, (user_id,))
    mysql.connection.commit()
    cur.close()
    return jsonify({"ok": True, "message": "activated"})


# POST /auth/resend-activation – ponowne wysłanie linku
@auth_bp.post("/resend-activation")
def resend_activation():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"ok": False, "error": "invalid_payload"}), 400

    cur = mysql.connection.cursor()
    cur.execute("""
      SELECT user_id, name, is_active
      FROM users WHERE email=%s
    """, (email,))
    row = cur.fetchone()
    if not row:
        cur.close()
        # nie ujawniamy czy user istnieje
        return jsonify({"ok": True, "message": "activation_sent"}), 200

    is_active = (row["is_active"] if isinstance(row, dict) else row[2]) == 1
    if is_active:
        cur.close()
        return jsonify({"ok": True, "message": "already_active"}), 200

    user_id = row["user_id"] if isinstance(row, dict) else row[0]
    name = row["name"] if isinstance(row, dict) else (row[1] if len(row) > 1 else "")

    token = generate_activation_token()
    exp = expiry(24)
    cur.execute("""
      UPDATE users SET activation_token=%s, activation_expires=%s WHERE user_id=%s
    """, (token, exp, user_id))
    mysql.connection.commit()
    cur.close()

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    activation_link_front = f"{frontend_url}/activate?token={token}"
    activation_link_back = f"http://127.0.0.1:5000/auth/activate/{token}"

    subject = "Aktywacja konta – ponowne wysłanie"
    body = (
        f"Cześć {name or email},\n\n"
        f"Oto nowy link aktywacyjny (ważny 24h):\n\n"
        f"{activation_link_front}\n\n"
        f"(Alternatywnie: {activation_link_back})\n\n"
        f"Pozdrawiamy,\nZespół Pub Manager"
    )
    send_email(subject, [email], body)
    return jsonify({"ok": True, "message": "activation_sent"})

@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify({"ok": False, "error": "invalid_credentials"}), 401

    cur = mysql.connection.cursor()
    cur.execute("""
      SELECT user_id, email, name, role, password_hash AS password, is_active
      FROM users WHERE email=%s
    """, (email,))
    u = cur.fetchone()
    cur.close()

    if not u:
        return jsonify({"ok": False, "error": "invalid_credentials"}), 401

    from werkzeug.security import check_password_hash
    pwd_hash = u["password"] if isinstance(u, dict) else u[4]
    active = (u["is_active"] if isinstance(u, dict) else u[5]) == 1
    if not check_password_hash(pwd_hash, password):
        return jsonify({"ok": False, "error": "invalid_credentials"}), 401
    if not active:
        return jsonify({"ok": False, "error": "account_inactive"}), 403

    # (reszta – generowanie JWT – jak wcześniej po Waszych poprawkach)
    user_claims = {
        "email": u["email"] if isinstance(u, dict) else u[1],
        "role":  u["role"]  if isinstance(u, dict) else u[3],
        "name":  u["name"]  if isinstance(u, dict) else u[2],
    }
    user_id = str(u["user_id"] if isinstance(u, dict) else u[0])
    access = create_access_token(identity=user_id, additional_claims=user_claims)
    refresh = create_refresh_token(identity=user_id, additional_claims=user_claims)
    return jsonify({
        "access_token": access,
        "refresh_token": refresh,
        "user": {"id": int(user_id), **user_claims}
    })

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
