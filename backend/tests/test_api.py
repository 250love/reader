import io
import os
import sys
from datetime import UTC, datetime

import pytest
from bson import ObjectId


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

os.environ["SECRET_KEY"] = "pytest-secret"
os.environ["MONGO_URI"] = "mongodb://localhost:27017"
os.environ["MONGO_DB_NAME"] = "paper_reader_pytest"
os.environ["ALLOW_DEBUG_EMAIL_CODE"] = "true"
os.environ["EMAIL_CODE_COOLDOWN_SECONDS"] = "0"
os.environ["SMTP_HOST"] = ""
os.environ["SMTP_USERNAME"] = ""
os.environ["SMTP_PASSWORD"] = ""
os.environ["SMTP_FROM_EMAIL"] = ""
os.environ["DEMO_ACCOUNT_ENABLED"] = "true"
os.environ["DEMO_ACCOUNT_USERNAME"] = "111"
os.environ["DEMO_ACCOUNT_PASSWORD"] = "111"
os.environ["DEMO_ACCOUNT_EMAIL"] = "111@example.local"

from app import create_app
from app.db.mongo import get_db


@pytest.fixture()
def app(tmp_path):
    os.environ["UPLOAD_DIR"] = str(tmp_path / "uploads")
    flask_app = create_app()
    flask_app.config.update(TESTING=True)
    db = get_db()
    db.client.drop_database(flask_app.config["MONGO_DB_NAME"])

    flask_app = create_app()
    flask_app.config.update(TESTING=True)
    yield flask_app

    db = get_db()
    db.client.drop_database(flask_app.config["MONGO_DB_NAME"])


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, password="111"):
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "111", "password": password},
    )
    return response


def auth_headers(client):
    response = login(client)
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.get_json()['token']}"}


def test_health_check_returns_ok(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_register_login_and_me_flow(client):
    email = "pytest_user@example.com"
    password = "StrongPass123!"

    code_response = client.post(
        "/api/v1/auth/send-code",
        json={"email": email, "purpose": "register"},
    )
    assert code_response.status_code == 200
    code = code_response.get_json()["debug_code"]

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "confirm_password": password,
            "code": code,
            "display_name": "Pytest User",
        },
    )
    assert register_response.status_code == 201
    token = register_response.get_json()["token"]

    login_response = client.post(
        "/api/v1/auth/login",
        json={"identifier": email, "password": password},
    )
    assert login_response.status_code == 200

    me_response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert me_response.get_json()["user"]["email"] == email


def test_login_with_demo_account_and_reject_wrong_password(client):
    ok_response = login(client)
    bad_response = login(client, password="wrong-password")

    assert ok_response.status_code == 200
    assert "token" in ok_response.get_json()
    assert bad_response.status_code == 401


def test_protected_endpoint_requires_auth(client):
    response = client.get("/api/v1/papers")

    assert response.status_code == 401
    assert "authorization" in response.get_json()["error"]


def test_upload_rejects_non_pdf_file(client):
    response = client.post(
        "/api/v1/papers/upload",
        data={"file": (io.BytesIO(b"not a pdf"), "note.txt")},
        headers=auth_headers(client),
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "pdf" in response.get_json()["error"].lower()


def test_generate_citations_for_supported_formats(client):
    headers = auth_headers(client)
    user_response = client.get("/api/v1/auth/me", headers=headers)
    user_id = ObjectId(user_response.get_json()["user"]["id"])
    paper_id = ObjectId()

    get_db().papers.insert_one(
        {
            "_id": paper_id,
            "user_id": user_id,
            "title": "A Test Paper for Citation",
            "authors": "Alice Wang, Bob Li",
            "conference": "Journal of Reader Tests",
            "year": "2026",
            "citationMetadata": {
                "title": "A Test Paper for Citation",
                "authors": ["Alice Wang", "Bob Li"],
                "year": "2026",
                "venue": "Journal of Reader Tests",
                "source": "manual",
            },
            "file_url": "",
            "folder_id": None,
            "tags": [],
            "status": "todo",
            "last_opened_at": datetime.now(UTC),
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
    )

    for citation_format in ["gbt7714", "apa", "ieee"]:
        response = client.post(
            "/api/v1/papers/citations",
            json={"paper_ids": [str(paper_id)], "format": citation_format},
            headers=headers,
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["items"][0]["citation"].startswith("[1]")
        assert "[1]" in payload["text"]
