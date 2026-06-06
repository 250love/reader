import requests
from bson import ObjectId

from app.utils.object_id import parse_object_id


def pick_provider(db, user_id: ObjectId, provider_id: str | None = None) -> dict | None:
    """Pick a user-owned LLM provider by explicit id, default flag, then first row."""
    if provider_id:
        provider_oid = parse_object_id(provider_id)
        if not provider_oid:
            return None
        return db.llm_providers.find_one({"_id": provider_oid, "user_id": user_id})

    default_provider = db.llm_providers.find_one({"user_id": user_id, "is_default": True})
    if default_provider:
        return default_provider
    return db.llm_providers.find_one({"user_id": user_id})


def build_completion_url(base_url: str) -> str:
    clean = str(base_url or "").rstrip("/")
    if clean.endswith("/chat/completions"):
        return clean
    if clean.endswith("/v1"):
        return f"{clean}/chat/completions"
    return f"{clean}/v1/chat/completions"


def call_chat_completion(
    provider: dict,
    messages: list[dict],
    temperature: float = 0.2,
    timeout: int = 60,
) -> str:
    url = build_completion_url(provider["base_url"])
    headers = {
        "Authorization": f"Bearer {provider['api_key']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": provider["model"],
        "temperature": temperature,
        "messages": messages,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()
