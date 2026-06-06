from datetime import UTC, datetime

from flask import Flask
from pymongo import ASCENDING
from pymongo import DESCENDING
from pymongo import MongoClient
from werkzeug.security import generate_password_hash

_mongo_client: MongoClient | None = None
_mongo_db = None


def init_mongo(app: Flask) -> None:
    global _mongo_client, _mongo_db

    _mongo_client = MongoClient(app.config["MONGO_URI"], tz_aware=True)
    _mongo_db = _mongo_client[app.config["MONGO_DB_NAME"]]
    _create_indexes()
    _ensure_demo_account(app)


def get_db():
    if _mongo_db is None:
        raise RuntimeError("MongoDB is not initialized.")
    return _mongo_db


def _create_indexes() -> None:
    if _mongo_db is None:
        return

    _mongo_db.users.create_index([("email", ASCENDING)], unique=True, name="uniq_user_email")
    _mongo_db.users.create_index([("username", ASCENDING)], unique=True, sparse=True, name="uniq_user_username")
    _mongo_db.email_codes.create_index([("email", ASCENDING), ("purpose", ASCENDING)], name="email_purpose_idx")
    _mongo_db.email_codes.create_index([("expires_at", ASCENDING)], name="email_code_expire_idx")
    _mongo_db.papers.create_index([("user_id", ASCENDING), ("created_at", ASCENDING)], name="papers_user_created_idx")
    _mongo_db.papers.create_index(
        [("user_id", ASCENDING), ("last_opened_at", ASCENDING)],
        name="papers_user_last_opened_idx",
    )
    _mongo_db.paper_annotations.create_index(
        [("user_id", ASCENDING), ("paper_id", ASCENDING), ("created_at", ASCENDING)],
        name="paper_annotations_user_paper_created_idx",
    )
    _mongo_db.paper_annotations.create_index(
        [("paper_id", ASCENDING), ("user_id", ASCENDING)],
        name="paper_annotations_paper_user_idx",
    )
    _mongo_db.ai_runs.create_index(
        [("user_id", ASCENDING), ("created_at", DESCENDING)],
        name="ai_runs_user_created_idx",
    )


def _ensure_demo_account(app: Flask) -> None:
    if _mongo_db is None:
        return
    if not app.config.get("DEMO_ACCOUNT_ENABLED", True):
        return

    username = app.config.get("DEMO_ACCOUNT_USERNAME", "111").strip()
    password = app.config.get("DEMO_ACCOUNT_PASSWORD", "111")
    email = app.config.get("DEMO_ACCOUNT_EMAIL", "111@example.local").strip().lower()
    if not username or not password or not email:
        return

    users = _mongo_db.users
    existing = users.find_one({"$or": [{"username": username}, {"email": email}]})
    now = datetime.now(UTC)
    doc = {
        "username": username,
        "email": email,
        "display_name": username,
        "password_hash": generate_password_hash(password),
        "updated_at": now,
    }

    if existing:
        users.update_one(
            {"_id": existing["_id"]},
            {"$set": doc},
        )
        return

    doc["created_at"] = now
    users.insert_one(doc)
