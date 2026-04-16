import hashlib
from datetime import datetime, UTC

import requests
from bson import ObjectId

from app.utils.object_id import parse_object_id


def _pick_provider(db, user_id: ObjectId, provider_id: str | None) -> dict | None:
    if provider_id:
        provider_oid = parse_object_id(provider_id)
        if provider_oid:
            return db.llm_providers.find_one({"_id": provider_oid, "user_id": user_id})
        return None

    default_provider = db.llm_providers.find_one({"user_id": user_id, "is_default": True})
    if default_provider:
        return default_provider
    return db.llm_providers.find_one({"user_id": user_id})


def _make_hash(text: str, target_lang: str, provider_id: ObjectId | None, user_id: ObjectId) -> str:
    raw = f"{str(user_id)}::{text}::{target_lang}::{str(provider_id) if provider_id else 'stub'}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _build_completion_url(base_url: str) -> str:
    clean = base_url.rstrip("/")
    if clean.endswith("/chat/completions"):
        return clean
    if clean.endswith("/v1"):
        return f"{clean}/chat/completions"
    return f"{clean}/v1/chat/completions"


def _call_llm_translate(provider: dict, text: str, target_lang: str) -> str:
    url = _build_completion_url(provider["base_url"])
    headers = {
        "Authorization": f"Bearer {provider['api_key']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": provider["model"],
        "temperature": 0.2,
        "messages": [
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
    }

    response = requests.post(url, headers=headers, json=payload, timeout=40)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def translate_text(db, user_id: ObjectId, text: str, target_lang: str, provider_id: str | None = None) -> str:
    provider = _pick_provider(db, user_id, provider_id)
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
