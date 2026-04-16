from functools import wraps

from bson import ObjectId
from flask import current_app, g, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.db.mongo import get_db


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="paper-reader-auth")


def create_access_token(user_id: str) -> str:
    return _serializer().dumps({"user_id": user_id})


def decode_access_token(token: str) -> dict | None:
    try:
        return _serializer().loads(
            token,
            max_age=current_app.config["ACCESS_TOKEN_EXPIRE_SECONDS"],
        )
    except (BadSignature, SignatureExpired):
        return None


def auth_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return {"error": "authorization header is required"}, 401

        token = auth_header.split(" ", 1)[1].strip()
        payload = decode_access_token(token)
        if not payload:
            return {"error": "invalid or expired token"}, 401

        user_id = payload.get("user_id")
        if not user_id or not ObjectId.is_valid(user_id):
            return {"error": "invalid token payload"}, 401

        db = get_db()
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return {"error": "user not found"}, 401

        g.current_user = user
        return view_func(*args, **kwargs)

    return wrapper

