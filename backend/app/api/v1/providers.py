from datetime import datetime, UTC

from flask import Blueprint, g, request

from app.core.auth import auth_required
from app.db.mongo import get_db
from app.utils.object_id import mongo_doc_to_json, parse_object_id

providers_bp = Blueprint("providers", __name__)


def _mask_secret(secret: str) -> str:
    if not secret:
        return ""
    if len(secret) <= 8:
        return "*" * len(secret)
    return f"{secret[:4]}{'*' * (len(secret) - 8)}{secret[-4:]}"


@providers_bp.get("")
@auth_required
def list_providers():
    db = get_db()
    rows = list(db.llm_providers.find({"user_id": g.current_user["_id"]}).sort("created_at", -1))
    items = []
    for row in rows:
        item = mongo_doc_to_json(row)
        item["api_key"] = _mask_secret(item.get("api_key", ""))
        items.append(item)
    return {"items": items}


@providers_bp.post("")
@auth_required
def create_provider():
    payload = request.get_json(silent=True) or {}

    name = (payload.get("name") or "").strip()
    model = (payload.get("model") or "").strip()
    base_url = (payload.get("base_url") or "").strip()
    api_key = (payload.get("api_key") or "").strip()

    if not all([name, model, base_url, api_key]):
        return {"error": "name/model/base_url/api_key are required"}, 400

    now = datetime.now(UTC)
    doc = {
        "user_id": g.current_user["_id"],
        "name": name,
        "model": model,
        "base_url": base_url,
        "api_key": api_key,
        "is_default": bool(payload.get("is_default", False)),
        "created_at": now,
        "updated_at": now,
    }

    db = get_db()
    if doc["is_default"]:
        db.llm_providers.update_many(
            {"user_id": g.current_user["_id"]},
            {"$set": {"is_default": False}},
        )

    inserted = db.llm_providers.insert_one(doc)
    created = db.llm_providers.find_one({"_id": inserted.inserted_id})
    result = mongo_doc_to_json(created)
    result["api_key"] = _mask_secret(result.get("api_key", ""))
    return result, 201


@providers_bp.patch("/<provider_id>")
@auth_required
def update_provider(provider_id: str):
    provider_oid = parse_object_id(provider_id)
    if not provider_oid:
        return {"error": "provider_id is invalid"}, 400

    payload = request.get_json(silent=True) or {}
    allowed_fields = {"name", "model", "base_url", "api_key", "is_default"}
    updates = {k: v for k, v in payload.items() if k in allowed_fields}

    if not updates:
        return {"error": "no valid fields to update"}, 400

    updates["updated_at"] = datetime.now(UTC)
    db = get_db()
    if updates.get("is_default"):
        db.llm_providers.update_many(
            {
                "_id": {"$ne": provider_oid},
                "user_id": g.current_user["_id"],
            },
            {"$set": {"is_default": False}},
        )

    result = db.llm_providers.update_one(
        {"_id": provider_oid, "user_id": g.current_user["_id"]},
        {"$set": updates},
    )
    if result.matched_count == 0:
        return {"error": "provider not found"}, 404

    updated = db.llm_providers.find_one({"_id": provider_oid, "user_id": g.current_user["_id"]})
    item = mongo_doc_to_json(updated)
    item["api_key"] = _mask_secret(item.get("api_key", ""))
    return item


@providers_bp.delete("/<provider_id>")
@auth_required
def delete_provider(provider_id: str):
    provider_oid = parse_object_id(provider_id)
    if not provider_oid:
        return {"error": "provider_id is invalid"}, 400

    db = get_db()
    result = db.llm_providers.delete_one({"_id": provider_oid, "user_id": g.current_user["_id"]})
    if result.deleted_count == 0:
        return {"error": "provider not found"}, 404
    return {"ok": True}
