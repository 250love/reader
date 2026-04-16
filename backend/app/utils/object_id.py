from datetime import datetime

from bson import ObjectId


def parse_object_id(value: str) -> ObjectId | None:
    if not value:
        return None
    if not ObjectId.is_valid(value):
        return None
    return ObjectId(value)


def mongo_doc_to_json(doc: dict) -> dict:
    if not doc:
        return doc

    output = {}
    for key, value in doc.items():
        if key == "_id":
            output["id"] = str(value)
            continue
        output[key] = _to_jsonable(value)
    return output


def _to_jsonable(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    return value
