from datetime import datetime, UTC

from flask import Blueprint, g, request

from app.core.auth import auth_required
from app.db.mongo import get_db
from app.utils.object_id import mongo_doc_to_json, parse_object_id

folders_bp = Blueprint("folders", __name__)


@folders_bp.get("")
@auth_required
def list_folders():
    db = get_db()
    rows = list(db.folders.find({"user_id": g.current_user["_id"]}).sort("created_at", -1))
    return {"items": [mongo_doc_to_json(row) for row in rows]}


@folders_bp.post("")
@auth_required
def create_folder():
    payload = request.get_json(silent=True) or {}

    name = (payload.get("name") or "").strip()
    parent_id = payload.get("parent_id")

    if not name:
        return {"error": "name is required"}, 400

    parent_oid = parse_object_id(parent_id) if parent_id else None
    if parent_id and not parent_oid:
        return {"error": "parent_id is invalid"}, 400

    now = datetime.now(UTC)
    doc = {
        "user_id": g.current_user["_id"],
        "name": name,
        "parent_id": parent_oid,
        "created_at": now,
        "updated_at": now,
    }

    db = get_db()
    inserted = db.folders.insert_one(doc)
    created = db.folders.find_one({"_id": inserted.inserted_id})
    return mongo_doc_to_json(created), 201


@folders_bp.delete("/<folder_id>")
@auth_required
def delete_folder(folder_id: str):
    folder_oid = parse_object_id(folder_id)
    if not folder_oid:
        return {"error": "folder_id is invalid"}, 400

    db = get_db()
    result = db.folders.delete_one({"_id": folder_oid, "user_id": g.current_user["_id"]})
    if result.deleted_count == 0:
        return {"error": "folder not found"}, 404

    db.papers.update_many(
        {"user_id": g.current_user["_id"], "folder_id": folder_oid},
        {"$set": {"folder_id": None, "updated_at": datetime.now(UTC)}},
    )
    db.folders.update_many(
        {"user_id": g.current_user["_id"], "parent_id": folder_oid},
        {"$set": {"parent_id": None, "updated_at": datetime.now(UTC)}},
    )
    return {"ok": True}


@folders_bp.patch("/<folder_id>")
@auth_required
def rename_folder(folder_id: str):
    folder_oid = parse_object_id(folder_id)
    if not folder_oid:
        return {"error": "folder_id is invalid"}, 400

    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    if not name:
        return {"error": "name is required"}, 400

    db = get_db()
    result = db.folders.update_one(
        {"_id": folder_oid, "user_id": g.current_user["_id"]},
        {"$set": {"name": name, "updated_at": datetime.now(UTC)}},
    )
    if result.matched_count == 0:
        return {"error": "folder not found"}, 404

    updated = db.folders.find_one({"_id": folder_oid, "user_id": g.current_user["_id"]})
    return mongo_doc_to_json(updated)
