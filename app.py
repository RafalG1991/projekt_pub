# app.py
import os
from flask import Flask
from dotenv import load_dotenv

from extensions import init_extensions, socketio
from auth_routes import auth_bp
from orders_routes import orders_bp
from lounges_routes import lounge_bp
from reports_routes import reports_bp


load_dotenv()

def create_app():
    app = Flask(__name__)
    init_extensions(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(lounge_bp)
    app.register_blueprint(reports_bp)

    @app.get("/health")
    def health():
        return {"ok": True}

    return app

app = create_app()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)