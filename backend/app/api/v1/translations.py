from flask import Blueprint, current_app, g, request

from app.core.auth import auth_required
from app.db.mongo import get_db
from app.services.translation_provider import translate_text

translations_bp = Blueprint("translations", __name__)


@translations_bp.post("/preview")
@auth_required
def preview_translation():
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    target_lang = payload.get("target_lang") or current_app.config["DEFAULT_TARGET_LANG"]
    provider_id = payload.get("provider_id")

    if not text:
        return {"error": "text is required"}, 400

    translated = translate_text(
        db=get_db(),
        user_id=g.current_user["_id"],
        text=text,
        target_lang=target_lang,
        provider_id=provider_id,
    )
    return {
        "source_text": text,
        "target_lang": target_lang,
        "translated_text": translated,
    }
