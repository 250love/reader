from flask import Blueprint

from app.api.v1.agent import agent_bp
from app.api.v1.auth import auth_bp
from app.api.v1.folders import folders_bp
from app.api.v1.health import health_bp
from app.api.v1.papers import papers_bp
from app.api.v1.providers import providers_bp
from app.api.v1.translations import translations_bp

v1_bp = Blueprint("v1", __name__)
v1_bp.register_blueprint(health_bp)
v1_bp.register_blueprint(auth_bp, url_prefix="/auth")
v1_bp.register_blueprint(folders_bp, url_prefix="/folders")
v1_bp.register_blueprint(papers_bp, url_prefix="/papers")
v1_bp.register_blueprint(providers_bp, url_prefix="/providers")
v1_bp.register_blueprint(translations_bp, url_prefix="/translations")
v1_bp.register_blueprint(agent_bp, url_prefix="/agent")
