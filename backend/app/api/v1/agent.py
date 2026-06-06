from flask import Blueprint, current_app, g, request

from app.core.auth import auth_required
from app.db.mongo import get_db
from app.services.academic_agent import (
    AcademicAgentError,
    list_academic_tasks,
    run_academic_task,
)

agent_bp = Blueprint("agent", __name__)


@agent_bp.post("/search")
@auth_required
def agent_search():
    payload = request.get_json(silent=True) or {}
    query = (payload.get("query") or "").strip()

    if not query:
        return {"error": "query is required"}, 400

    # Stub for future web-search / citation agent.
    return {
        "query": query,
        "status": "stub",
        "results": [],
        "message": "Agent search interface is reserved and ready for implementation.",
    }


@agent_bp.get("/tasks")
@auth_required
def list_tasks():
    return {"items": list_academic_tasks()}


@agent_bp.post("/run")
@auth_required
def run_agent_task():
    payload = request.get_json(silent=True) or {}
    db = get_db()

    try:
        return run_academic_task(
            db=db,
            user_id=g.current_user["_id"],
            payload=payload,
            upload_root=current_app.config["UPLOAD_DIR"],
        )
    except AcademicAgentError as exc:
        return {"error": str(exc)}, exc.status_code
    except Exception:
        return {"error": "academic agent run failed"}, 500
