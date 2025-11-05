# authz.py
from functools import wraps
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt

def role_required(*roles: str):
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def inner(*args, **kwargs):
            claims = get_jwt() or {}
            role = claims.get("role")
            if role not in roles:
                return jsonify({"error": "forbidden", "required": roles, "got": role}), 403
            return fn(*args, **kwargs)
        return inner
    return wrapper