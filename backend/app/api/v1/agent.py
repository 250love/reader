from flask import Blueprint, current_app, g, request

from app.core.auth import auth_required
from app.db.mongo import get_db
from app.services.academic_agent import (
    AcademicAgentError,
    list_academic_tasks,
    run_academic_task,
)
from app.utils.object_id import mongo_doc_to_json, parse_object_id

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


@agent_bp.get("/runs")
@auth_required
def list_agent_runs():
    db = get_db()
    raw_limit = request.args.get("limit", 100)
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        limit = 100
    limit = max(1, min(limit, 100))

    rows = list(
        db.ai_runs.find({"user_id": g.current_user["_id"]})
        .sort("created_at", -1)
        .limit(limit)
    )
    return {"items": [mongo_doc_to_json(row) for row in rows]}


@agent_bp.get("/runs/<run_id>")
@auth_required
def get_agent_run(run_id):
    run_oid = parse_object_id(run_id)
    if not run_oid:
        return {"error": "run_id is invalid"}, 400

    db = get_db()
    row = db.ai_runs.find_one({"_id": run_oid, "user_id": g.current_user["_id"]})
    if not row:
        return {"error": "run not found"}, 404
    return mongo_doc_to_json(row)


@agent_bp.delete("/runs/<run_id>")
@auth_required
def delete_agent_run(run_id):
    run_oid = parse_object_id(run_id)
    if not run_oid:
        return {"error": "run_id is invalid"}, 400

    db = get_db()
    result = db.ai_runs.delete_one({"_id": run_oid, "user_id": g.current_user["_id"]})
    if result.deleted_count == 0:
        return {"error": "run not found"}, 404
    return {"ok": True}
