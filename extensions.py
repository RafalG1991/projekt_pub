# extensions.py
import os
from datetime import timedelta, datetime
from flask import Flask
from flask_cors import CORS
from flask_mysqldb import MySQL
from flask_jwt_extended import JWTManager
from flask import jsonify
from flask_mail import Mail


mysql = MySQL()
jwt = JWTManager()
mail = Mail()

def init_extensions(app: Flask):
    # --- CORS ---
    allowed = [
        # Vite
        "http://localhost:5173", "http://127.0.0.1:5173",
        # CRA
        "http://localhost:3000", "http://127.0.0.1:3000",
    ]
    # dodatkowo: pozwól ustawiać przez env (wiele, po przecinku)
    extra = os.getenv("FRONT_ORIGIN", "")
    if extra:
        allowed.extend([o.strip() for o in extra.split(",") if o.strip()])

    CORS(
        app,
        resources={r"/*": {"origins": allowed}},
        supports_credentials=False,  # True tylko jeśli używasz cookies (httpOnly)
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        max_age=86400,
    )
    app.config["CORS_HEADERS"] = "Content-Type"

    # MySQL (flask-mysqldb)
    app.config['MYSQL_HOST'] = os.getenv("HOST", "localhost")
    app.config['MYSQL_USER'] = os.getenv("USER", "root")
    app.config['MYSQL_PASSWORD'] = os.getenv("PASSWORD", "")
    app.config['MYSQL_DB'] = os.getenv("DB", "pub_db3")
    app.config['MYSQL_CURSORCLASS'] = "DictCursor"
    mysql.init_app(app)

    # JWT
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret")
    app.config["JWT_TOKEN_LOCATION"] = ["headers"]
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=int(os.getenv("JWT_ACCESS_MIN", "15")))
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "7")))
    jwt.init_app(app)

    @jwt.unauthorized_loader
    def _unauth(reason):
        return jsonify({"msg": "missing/invalid auth header", "detail": reason}), 401

    @jwt.invalid_token_loader
    def _invalid(reason):
        return jsonify({"msg": "invalid token", "detail": reason}), 422

    @jwt.expired_token_loader
    def _expired(h, p):
        return jsonify({"msg": "token expired"}), 401

    @jwt.revoked_token_loader
    def _revoked(h, p):
        return jsonify({"msg": "token revoked"}), 401

    # Blacklista JWT -> tabela jwt_blocklist (jti)
    @jwt.token_in_blocklist_loader
    def is_revoked(jwt_header, jwt_payload):
        jti = jwt_payload.get("jti")
        cur = mysql.connection.cursor()
        cur.execute("SELECT 1 FROM jwt_blocklist WHERE jti=%s LIMIT 1", (jti,))
        row = cur.fetchone()
        cur.close()
        return bool(row)
    
    # --- MAIL ---
    app.config["MAIL_SERVER"]   = os.getenv("MAIL_SERVER", "localhost")
    app.config["MAIL_PORT"]     = int(os.getenv("MAIL_PORT", "25"))
    app.config["MAIL_USE_TLS"]  = os.getenv("MAIL_USE_TLS", "false").lower() == "true"
    app.config["MAIL_USE_SSL"]  = os.getenv("MAIL_USE_SSL", "false").lower() == "true"
    app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
    app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
    app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_SENDER", "no-reply@localhost")

    mail.init_app(app)
