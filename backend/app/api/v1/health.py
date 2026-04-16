from datetime import datetime, UTC

from flask import Blueprint

from app.db.mongo import get_db

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health_check():
    mongo_ok = False
    db_name = None
    try:
        db = get_db()
        db.command("ping")
        mongo_ok = True
        db_name = db.name
    except Exception:
        mongo_ok = False

    return {
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat(),
        "mongo_connected": mongo_ok,
        "mongo_db_name": db_name,
    }
