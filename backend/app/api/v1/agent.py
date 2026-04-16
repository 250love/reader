from flask import Blueprint, request

from app.core.auth import auth_required

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
