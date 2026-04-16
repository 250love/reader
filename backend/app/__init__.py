import os

from flask import Flask
from flask import send_from_directory
from flask_cors import CORS

from app.api import register_api
from app.core.config import Config
from app.db.mongo import init_mongo


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)

    CORS(
        app,
        origins=app.config["CORS_ORIGINS"],
        supports_credentials=True,
    )

    init_mongo(app)
    register_api(app)

    @app.get("/uploads/<path:filename>")
    def serve_upload(filename: str):
        return send_from_directory(app.config["UPLOAD_DIR"], filename)

    return app
