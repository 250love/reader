import hashlib
from datetime import datetime, UTC

from bson import ObjectId

from app.services.llm_client import call_chat_completion, pick_provider


def _make_hash(text: str, target_lang: str, provider_id: ObjectId | None, user_id: ObjectId) -> str:
    raw = f"{str(user_id)}::{text}::{target_lang}::{str(provider_id) if provider_id else 'stub'}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _call_llm_translate(provider: dict, text: str, target_lang: str) -> str:
    return call_chat_completion(
        provider,
        [
            {
                "role": "system",
                "content": (
                    "You are an academic translator. Keep terminology accurate and output only translated text."
                ),
            },
            {
                "role": "user",
                "content": f"Translate the following to {target_lang}:\n\n{text}",
            },
        ],
        temperature=0.2,
        timeout=40,
    )


def translate_text(db, user_id: ObjectId, text: str, target_lang: str, provider_id: str | None = None) -> str:
    provider = pick_provider(db, user_id, provider_id)
    real_provider_id = provider["_id"] if provider else None
    cache_key = _make_hash(text, target_lang, real_provider_id, user_id)

    cached = db.translations.find_one({"cache_key": cache_key, "user_id": user_id})
    if cached:
        return cached["translated_text"]

    if provider:
        try:
            translated = _call_llm_translate(provider, text, target_lang)
        except Exception:
            translated = f"[Translation API Error Fallback]\n{text}"
    else:
        translated = f"[Stub Translation -> {target_lang}]\n{text}"

    db.translations.insert_one(
        {
            "cache_key": cache_key,
            "user_id": user_id,
            "provider_id": real_provider_id,
            "source_text": text,
            "target_lang": target_lang,
            "translated_text": translated,
            "created_at": datetime.now(UTC),
        }
    )
    return translated
