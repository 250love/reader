import hashlib
import hmac
import random
import re
import secrets
from datetime import UTC, datetime, timedelta

from flask import Blueprint, current_app, g, request
from werkzeug.security import check_password_hash, generate_password_hash

from app.core.auth import auth_required, create_access_token
from app.db.mongo import get_db
from app.services.email_service import send_email_verification_code
from app.utils.object_id import mongo_doc_to_json

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,32}$")
LOWER_RE = re.compile(r"[a-z]")
UPPER_RE = re.compile(r"[A-Z]")
DIGIT_RE = re.compile(r"\d")
SPECIAL_RE = re.compile(r"[^A-Za-z0-9]")


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _to_utc_aware(value: datetime | None) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _public_user(user: dict) -> dict:
    result = mongo_doc_to_json(user)
    result.pop("password_hash", None)
    return result


def _evaluate_password_strength(password: str) -> tuple[int, str]:
    score = 0
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    if LOWER_RE.search(password):
        score += 1
    if UPPER_RE.search(password):
        score += 1
    if DIGIT_RE.search(password):
        score += 1
    if SPECIAL_RE.search(password):
        score += 1

    if score <= 2:
        label = "weak"
    elif score <= 4:
        label = "medium"
    else:
        label = "strong"
    return score, label


def _generate_recommended_password(email: str, display_name: str) -> str:
    secret_key = current_app.config["SECRET_KEY"].encode("utf-8")
    nonce = secrets.token_hex(16)
    seed = f"{email}|{display_name}|{nonce}|{datetime.now(UTC).isoformat()}".encode("utf-8")
    digest = hmac.new(secret_key, seed, hashlib.sha256).digest()

    lowers = "abcdefghijkmnopqrstuvwxyz"
    uppers = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    digits = "23456789"
    specials = "!@#$%^&*()-_=+"
    all_chars = f"{lowers}{uppers}{digits}{specials}"

    chars = [all_chars[b % len(all_chars)] for b in digest[:16]]
    chars[0] = lowers[digest[16] % len(lowers)]
    chars[1] = uppers[digest[17] % len(uppers)]
    chars[2] = digits[digest[18] % len(digits)]
    chars[3] = specials[digest[19] % len(specials)]

    for i in range(len(chars) - 1, 0, -1):
        j = digest[(i + 7) % len(digest)] % (i + 1)
        chars[i], chars[j] = chars[j], chars[i]

    return "".join(chars)


@auth_bp.post("/recommend-password")
def recommend_password():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    display_name = (payload.get("display_name") or "").strip()

    if email and not EMAIL_RE.match(email):
        return {"error": "invalid email"}, 400

    password = _generate_recommended_password(email, display_name)
    score, label = _evaluate_password_strength(password)

    return {
        "recommended_password": password,
        "strength": {
            "score": score,
            "label": label,
            "max_score": 6,
        },
    }


@auth_bp.post("/send-code")
def send_code():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    purpose = (payload.get("purpose") or "register").strip().lower()

    if purpose != "register":
        return {"error": "only register purpose is supported"}, 400
    if not EMAIL_RE.match(email):
        return {"error": "invalid email"}, 400

    db = get_db()
    if db.users.find_one({"email": email}):
        return {"error": "email already registered"}, 409

    now = datetime.now(UTC)
    cooldown_limit = now - timedelta(seconds=current_app.config["EMAIL_CODE_COOLDOWN_SECONDS"])
    latest = db.email_codes.find_one(
        {"email": email, "purpose": purpose},
        sort=[("created_at", -1)],
    )

    latest_created_at = _to_utc_aware(latest.get("created_at")) if latest else None
    if latest_created_at and latest_created_at > cooldown_limit:
        return {"error": "code sent too frequently, please wait"}, 429

    code = f"{random.randint(0, 999999):06d}"
    expires_at = now + timedelta(minutes=current_app.config["EMAIL_CODE_EXPIRE_MINUTES"])

    db.email_codes.insert_one(
        {
            "email": email,
            "purpose": purpose,
            "code_hash": _hash_code(code),
            "created_at": now,
            "expires_at": expires_at,
            "consumed_at": None,
        }
    )

    sent = False
    try:
        sent = send_email_verification_code(email, code)
    except Exception:
        sent = False

    if sent:
        return {"ok": True, "message": "verification code has been sent"}

    if current_app.config["ALLOW_DEBUG_EMAIL_CODE"]:
        return {
            "ok": True,
            "message": "smtp not configured, returning debug code",
            "debug_code": code,
        }
    return {"error": "failed to send email code"}, 500


@auth_bp.post("/register")
def register():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    confirm_password = payload.get("confirm_password") or ""
    code = (payload.get("code") or "").strip()
    display_name = (payload.get("display_name") or "").strip()
    username = (payload.get("username") or "").strip()

    if not EMAIL_RE.match(email):
        return {"error": "invalid email"}, 400
    score, label = _evaluate_password_strength(password)
    if score < 4:
        return {
            "error": (
                "password is too weak, use at least 8 chars and include "
                "uppercase, lowercase, number, and special character"
            )
        }, 400
    if confirm_password and confirm_password != password:
        return {"error": "password and confirm_password do not match"}, 400
    if len(code) != 6 or not code.isdigit():
        return {"error": "invalid code format"}, 400

    db = get_db()
    if db.users.find_one({"email": email}):
        return {"error": "email already registered"}, 409
    if username:
        if not USERNAME_RE.match(username):
            return {"error": "username must be 3-32 chars (letters/numbers/_)"}, 400
        if db.users.find_one({"username": username}):
            return {"error": "username already exists"}, 409

    now = datetime.now(UTC)
    code_doc = db.email_codes.find_one(
        {
            "email": email,
            "purpose": "register",
            "consumed_at": None,
        },
        sort=[("created_at", -1)],
    )

    if not code_doc:
        return {"error": "verification code not found"}, 400
    expires_at = _to_utc_aware(code_doc.get("expires_at"))
    if not expires_at:
        return {"error": "verification code timestamp is invalid"}, 400
    if expires_at < now:
        return {"error": "verification code expired"}, 400
    if code_doc["code_hash"] != _hash_code(code):
        return {"error": "verification code is incorrect"}, 400

    user_doc = {
        "email": email,
        "username": username or email.split("@")[0],
        "display_name": display_name or email.split("@")[0],
        "password_hash": generate_password_hash(password),
        "created_at": now,
        "updated_at": now,
    }
    inserted = db.users.insert_one(user_doc)
    db.email_codes.update_one(
        {"_id": code_doc["_id"]},
        {"$set": {"consumed_at": now}},
    )

    created_user = db.users.find_one({"_id": inserted.inserted_id})
    token = create_access_token(str(inserted.inserted_id))

    return {
        "token": token,
        "user": _public_user(created_user),
    }, 201


@auth_bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    identifier = (payload.get("identifier") or payload.get("email") or "").strip()
    password = payload.get("password") or ""

    if not identifier:
        return {"error": "email or username is required"}, 400
    if not password:
        return {"error": "password is required"}, 400

    db = get_db()
    identifier_lower = identifier.lower()
    if "@" in identifier:
        user = db.users.find_one({"email": identifier_lower})
    else:
        user = db.users.find_one({"$or": [{"username": identifier}, {"email": identifier_lower}]})
    if not user:
        return {"error": "invalid email or password"}, 401
    if not check_password_hash(user["password_hash"], password):
        return {"error": "invalid email or password"}, 401

    token = create_access_token(str(user["_id"]))
    return {
        "token": token,
        "user": _public_user(user),
    }


@auth_bp.get("/me")
@auth_required
def me():
    return {"user": _public_user(g.current_user)}
