import os
import shutil
import uuid
from datetime import datetime, UTC
from urllib.parse import urlparse

from flask import Blueprint, current_app, g, request
from pymongo import DESCENDING
from werkzeug.utils import secure_filename

from app.core.auth import auth_required
from app.db.mongo import get_db
from app.services.figure_extractor import (
    FigureExtractionError,
    clear_paper_figure_dir,
    extract_visual_regions,
    resolve_local_pdf_path,
)
from app.services.translation_provider import translate_text
from app.utils.object_id import mongo_doc_to_json, parse_object_id

papers_bp = Blueprint("papers", __name__)
ALLOWED_PDF_EXTENSIONS = {".pdf"}
HIGHLIGHT_COLORS = {"yellow", "pink", "green", "blue", "purple"}


def _remove_uploaded_file_if_local(file_url: str, user_id: str) -> None:
    if not file_url:
        return

    parsed = urlparse(file_url)
    path = parsed.path if parsed.scheme else file_url
    if not path.startswith("/uploads/"):
        return

    relative = path[len("/uploads/"):].lstrip("/")
    if not relative:
        return

    first, _, rest = relative.partition("/")
    if not first or not rest:
        return
    if first != user_id:
        return

    upload_root = os.path.abspath(current_app.config["UPLOAD_DIR"])
    candidate = os.path.abspath(os.path.join(upload_root, relative.replace("/", os.sep)))
    if not (candidate == upload_root or candidate.startswith(upload_root + os.sep)):
        return

    if os.path.isfile(candidate):
        os.remove(candidate)


def _extract_upload_relative_path(file_url: str) -> str | None:
    if not file_url:
        return None
    parsed = urlparse(file_url)
    path = parsed.path if parsed.scheme else file_url
    if not path.startswith("/uploads/"):
        return None
    relative = path[len("/uploads/"):].lstrip("/")
    return relative or None


def _normalize_owned_upload_url(file_url: str, user_id: str) -> tuple[str | None, str | None]:
    if not file_url:
        return "", None

    relative = _extract_upload_relative_path(file_url)
    if not relative:
        return None, "file_url must be a local uploaded file path (/uploads/...)"

    first, _, rest = relative.partition("/")
    if not first or not rest:
        return None, "file_url is invalid"
    if first != user_id:
        return None, "file_url does not belong to current user"

    upload_root = os.path.abspath(current_app.config["UPLOAD_DIR"])
    candidate = os.path.abspath(os.path.join(upload_root, relative.replace("/", os.sep)))
    if not (candidate == upload_root or candidate.startswith(upload_root + os.sep)):
        return None, "file_url is invalid"
    if not os.path.isfile(candidate):
        return None, "uploaded file not found"

    normalized_relative = relative.replace("\\", "/")
    return f"/uploads/{normalized_relative}", None


def _parse_rects(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    rects = []
    for raw in value:
        if not isinstance(raw, dict):
            continue
        try:
            x = float(raw.get("x"))
            y = float(raw.get("y"))
            w = float(raw.get("w"))
            h = float(raw.get("h"))
        except (TypeError, ValueError):
            continue

        if w <= 0 or h <= 0:
            continue
        x = max(0.0, min(1.0, x))
        y = max(0.0, min(1.0, y))
        w = max(0.0, min(1.0 - x, w))
        h = max(0.0, min(1.0 - y, h))
        if w <= 0 or h <= 0:
            continue
        rects.append(
            {
                "x": round(x, 6),
                "y": round(y, 6),
                "w": round(w, 6),
                "h": round(h, 6),
            }
        )
    return rects


def _remove_paper_figure_assets(user_id: str, paper_id: str) -> None:
    upload_root = os.path.abspath(current_app.config["UPLOAD_DIR"])
    figures_root = os.path.abspath(os.path.join(upload_root, user_id, "figures", paper_id))
    if not (
        figures_root == upload_root
        or figures_root.startswith(upload_root + os.sep)
    ):
        return

    if os.path.isdir(figures_root):
        shutil.rmtree(figures_root, ignore_errors=True)


@papers_bp.get("")
@auth_required
def list_papers():
    db = get_db()

    folder_id = request.args.get("folder_id")
    query = (request.args.get("q") or "").strip()
    sort_by = (request.args.get("sort_by") or "last_opened_at").strip()
    sort_order = (request.args.get("sort_order") or "desc").strip().lower()

    allowed_sort_by = {"created_at", "last_opened_at"}
    if sort_by not in allowed_sort_by:
        return {"error": "sort_by must be one of created_at,last_opened_at"}, 400
    if sort_order not in {"asc", "desc"}:
        return {"error": "sort_order must be asc or desc"}, 400

    sort_direction = DESCENDING if sort_order == "desc" else 1

    filters = {}
    if folder_id:
        folder_oid = parse_object_id(folder_id)
        if not folder_oid:
            return {"error": "folder_id is invalid"}, 400
        filters["folder_id"] = folder_oid

    if query:
        filters["$or"] = [
            {"title": {"$regex": query, "$options": "i"}},
            {"authors": {"$regex": query, "$options": "i"}},
            {"conference": {"$regex": query, "$options": "i"}},
        ]

    filters["user_id"] = g.current_user["_id"]
    if sort_by == "created_at":
        sort_spec = [("created_at", sort_direction), ("last_opened_at", sort_direction), ("_id", sort_direction)]
    else:
        sort_spec = [("last_opened_at", sort_direction), ("created_at", sort_direction), ("_id", sort_direction)]

    rows = list(db.papers.find(filters).sort(sort_spec))
    return {"items": [mongo_doc_to_json(row) for row in rows]}


@papers_bp.post("/upload")
@auth_required
def upload_pdf():
    file = request.files.get("file")
    if not file:
        return {"error": "file is required"}, 400

    original_name = secure_filename(file.filename or "")
    if not original_name:
        return {"error": "invalid filename"}, 400

    ext = os.path.splitext(original_name)[1].lower()
    if ext not in ALLOWED_PDF_EXTENSIONS:
        return {"error": "only .pdf files are allowed"}, 400

    user_folder = str(g.current_user["_id"])
    upload_root = current_app.config["UPLOAD_DIR"]
    target_dir = os.path.join(upload_root, user_folder)
    os.makedirs(target_dir, exist_ok=True)

    saved_name = f"{uuid.uuid4().hex}.pdf"
    save_path = os.path.join(target_dir, saved_name)
    file.save(save_path)

    relative_url = f"/uploads/{user_folder}/{saved_name}"
    absolute_url = f"{request.host_url.rstrip('/')}{relative_url}"
    return {
        "ok": True,
        "file_name": original_name,
        "relative_url": relative_url,
        "file_url": absolute_url,
    }


@papers_bp.post("")
@auth_required
def create_paper():
    payload = request.get_json(silent=True) or {}
    db = get_db()

    title = (payload.get("title") or "").strip()
    if not title:
        return {"error": "title is required"}, 400

    folder_id = payload.get("folder_id")
    folder_oid = parse_object_id(folder_id) if folder_id else None
    if folder_id and not folder_oid:
        return {"error": "folder_id is invalid"}, 400
    if folder_oid:
        folder = db.folders.find_one({"_id": folder_oid, "user_id": g.current_user["_id"]})
        if not folder:
            return {"error": "folder not found"}, 404

    user_id = str(g.current_user["_id"])
    normalized_file_url, file_err = _normalize_owned_upload_url(str(payload.get("file_url", "")).strip(), user_id)
    if file_err:
        return {"error": file_err}, 400

    now = datetime.now(UTC)
    doc = {
        "user_id": g.current_user["_id"],
        "title": title,
        "authors": payload.get("authors", ""),
        "conference": payload.get("conference", ""),
        "year": payload.get("year"),
        "file_url": normalized_file_url or "",
        "folder_id": folder_oid,
        "tags": payload.get("tags", []),
        "status": payload.get("status", "todo"),
        "last_opened_at": now,
        "created_at": now,
        "updated_at": now,
    }

    inserted = db.papers.insert_one(doc)
    created = db.papers.find_one({"_id": inserted.inserted_id})
    return mongo_doc_to_json(created), 201


@papers_bp.get("/<paper_id>")
@auth_required
def get_paper(paper_id: str):
    paper_oid = parse_object_id(paper_id)
    if not paper_oid:
        return {"error": "paper_id is invalid"}, 400

    db = get_db()
    paper = db.papers.find_one({"_id": paper_oid, "user_id": g.current_user["_id"]})
    if not paper:
        return {"error": "paper not found"}, 404
    return mongo_doc_to_json(paper)


@papers_bp.get("/<paper_id>/figures")
@auth_required
def list_paper_figures(paper_id: str):
    paper_oid = parse_object_id(paper_id)
    if not paper_oid:
        return {"error": "paper_id is invalid"}, 400

    db = get_db()
    paper = db.papers.find_one({"_id": paper_oid, "user_id": g.current_user["_id"]})
    if not paper:
        return {"error": "paper not found"}, 404

    rows = list(
        db.paper_figures.find(
            {"paper_id": paper_oid, "user_id": g.current_user["_id"]}
        ).sort([("page", 1), ("bbox_norm.y", 1), ("bbox_norm.x", 1), ("_id", 1)])
    )
    return {"items": [mongo_doc_to_json(row) for row in rows]}


@papers_bp.post("/<paper_id>/figures/extract")
@auth_required
def extract_paper_figures(paper_id: str):
    paper_oid = parse_object_id(paper_id)
    if not paper_oid:
        return {"error": "paper_id is invalid"}, 400

    payload = request.get_json(silent=True) or {}
    force_refresh = bool(payload.get("force", True))
    simple_mode = bool(payload.get("simple_mode", True))
    include_tables = bool(payload.get("include_tables", not simple_mode))
    include_boxed_text = bool(payload.get("include_boxed_text", not simple_mode))
    include_embedded_images = bool(payload.get("include_embedded_images", True))
    include_table_text_strategy = bool(payload.get("include_table_text_strategy", False if simple_mode else False))
    include_image_block_candidates = bool(payload.get("include_image_block_candidates", True))
    include_vector_graphics = bool(payload.get("include_vector_graphics", True if simple_mode else False))
    only_captioned_vector_regions = bool(payload.get("only_captioned_vector_regions", True if simple_mode else False))
    try:
        figure_text_coverage_max = float(payload.get("figure_text_coverage_max", 0.72))
    except (TypeError, ValueError):
        figure_text_coverage_max = 0.72
    figure_text_coverage_max = max(0.2, min(0.98, figure_text_coverage_max))
    enable_ocr_layout = bool(
        payload.get("enable_ocr_layout", False if simple_mode else current_app.config.get("OCR_LAYOUT_ENABLED_DEFAULT", False))
    )
    ocr_layout_lang = (payload.get("ocr_layout_lang") or current_app.config.get("OCR_LAYOUT_LANG", "en")).strip() or "en"
    ocr_layout_use_gpu = bool(payload.get("ocr_layout_use_gpu", current_app.config.get("OCR_LAYOUT_USE_GPU", False)))

    db = get_db()
    paper = db.papers.find_one({"_id": paper_oid, "user_id": g.current_user["_id"]})
    if not paper:
        return {"error": "paper not found"}, 404

    if not force_refresh:
        existing = list(
            db.paper_figures.find(
                {"paper_id": paper_oid, "user_id": g.current_user["_id"]}
            ).sort([("page", 1), ("bbox_norm.y", 1), ("bbox_norm.x", 1), ("_id", 1)])
        )
        return {"ok": True, "cached": True, "items": [mongo_doc_to_json(row) for row in existing]}

    upload_root = current_app.config["UPLOAD_DIR"]
    user_id = str(g.current_user["_id"])
    pdf_path = resolve_local_pdf_path(paper.get("file_url", ""), upload_root)
    if not pdf_path:
        return {
            "error": "only local uploaded pdf can be extracted currently; remote file_url is unsupported"
        }, 400

    try:
        clear_paper_figure_dir(upload_root, user_id, paper_id)
        extracted, warnings = extract_visual_regions(
            pdf_path=pdf_path,
            upload_root=upload_root,
            user_id=user_id,
            paper_id=paper_id,
            include_embedded_images=include_embedded_images,
            include_tables=include_tables,
            include_boxed_text=include_boxed_text,
            include_table_text_strategy=include_table_text_strategy,
            enable_ocr_layout=enable_ocr_layout,
            ocr_layout_lang=ocr_layout_lang,
            ocr_layout_use_gpu=ocr_layout_use_gpu,
            merge_embedded_images=True if simple_mode else False,
            embedded_merge_gap_points=10.0,
            min_embedded_area_ratio=0.004,
            include_image_block_candidates=include_image_block_candidates,
            include_vector_graphics=include_vector_graphics,
            figure_text_coverage_max=figure_text_coverage_max,
            only_captioned_vector_regions=only_captioned_vector_regions,
        )
    except FigureExtractionError as exc:
        return {"error": str(exc)}, 400
    except Exception:
        return {"error": "figure extraction failed"}, 500

    db.paper_figures.delete_many({"paper_id": paper_oid, "user_id": g.current_user["_id"]})

    now = datetime.now(UTC)
    docs = []
    for item in extracted:
        docs.append(
            {
                "paper_id": paper_oid,
                "user_id": g.current_user["_id"],
                "page": item.page,
                "image_url": item.image_url,
                "source_xref": item.source_xref,
                "region_type": item.region_type,
                "region_label": item.region_label,
                "bbox_norm": item.bbox_norm,
                "bbox_pdf": item.bbox_pdf,
                "width_px": item.width_px,
                "height_px": item.height_px,
                "note": "",
                "tags": [],
                "created_at": now,
                "updated_at": now,
            }
        )

    if docs:
        db.paper_figures.insert_many(docs)

    rows = list(
        db.paper_figures.find(
            {"paper_id": paper_oid, "user_id": g.current_user["_id"]}
        ).sort([("page", 1), ("bbox_norm.y", 1), ("bbox_norm.x", 1), ("_id", 1)])
    )
    return {
        "ok": True,
        "cached": False,
        "extractor": "image_multisource_merged" if simple_mode else "hybrid_regions_fitz_pdfplumber",
        "count": len(rows),
        "warnings": warnings,
        "items": [mongo_doc_to_json(row) for row in rows],
    }


@papers_bp.patch("/<paper_id>/figures/<figure_id>")
@auth_required
def update_paper_figure(paper_id: str, figure_id: str):
    paper_oid = parse_object_id(paper_id)
    if not paper_oid:
        return {"error": "paper_id is invalid"}, 400
    figure_oid = parse_object_id(figure_id)
    if not figure_oid:
        return {"error": "figure_id is invalid"}, 400

    payload = request.get_json(silent=True) or {}
    updates = {}
    if "note" in payload:
        updates["note"] = str(payload.get("note") or "")
    if "tags" in payload:
        tags = payload.get("tags")
        if not isinstance(tags, list):
            return {"error": "tags must be a list"}, 400
        updates["tags"] = [str(tag).strip() for tag in tags if str(tag).strip()]

    if not updates:
        return {"error": "no valid fields to update"}, 400

    updates["updated_at"] = datetime.now(UTC)
    db = get_db()

    result = db.paper_figures.update_one(
        {
            "_id": figure_oid,
            "paper_id": paper_oid,
            "user_id": g.current_user["_id"],
        },
        {"$set": updates},
    )
    if result.matched_count == 0:
        return {"error": "figure not found"}, 404

    updated = db.paper_figures.find_one({"_id": figure_oid})
    return mongo_doc_to_json(updated)


@papers_bp.patch("/<paper_id>")
@auth_required
def update_paper(paper_id: str):
    paper_oid = parse_object_id(paper_id)
    if not paper_oid:
        return {"error": "paper_id is invalid"}, 400

    db = get_db()
    payload = request.get_json(silent=True) or {}
    allowed_fields = {"title", "authors", "conference", "year", "status", "tags", "file_url"}
    updates = {k: v for k, v in payload.items() if k in allowed_fields}
    if "folder_id" in payload:
        folder_oid = parse_object_id(payload.get("folder_id")) if payload.get("folder_id") else None
        if payload.get("folder_id") and not folder_oid:
            return {"error": "folder_id is invalid"}, 400
        if folder_oid:
            folder = db.folders.find_one({"_id": folder_oid, "user_id": g.current_user["_id"]})
            if not folder:
                return {"error": "folder not found"}, 404
        updates["folder_id"] = folder_oid

    if not updates:
        return {"error": "no valid fields to update"}, 400

    if "file_url" in updates:
        normalized_file_url, file_err = _normalize_owned_upload_url(
            str(updates.get("file_url") or "").strip(),
            str(g.current_user["_id"]),
        )
        if file_err:
            return {"error": file_err}, 400
        updates["file_url"] = normalized_file_url or ""

    updates["updated_at"] = datetime.now(UTC)
    result = db.papers.update_one(
        {"_id": paper_oid, "user_id": g.current_user["_id"]},
        {"$set": updates},
    )
    if result.matched_count == 0:
        return {"error": "paper not found"}, 404

    updated = db.papers.find_one({"_id": paper_oid, "user_id": g.current_user["_id"]})
    return mongo_doc_to_json(updated)


@papers_bp.get("/<paper_id>/annotations")
@auth_required
def list_paper_annotations(paper_id: str):
    paper_oid = parse_object_id(paper_id)
    if not paper_oid:
        return {"error": "paper_id is invalid"}, 400

    db = get_db()
    paper = db.papers.find_one({"_id": paper_oid, "user_id": g.current_user["_id"]})
    if not paper:
        return {"error": "paper not found"}, 404

    rows = list(
        db.paper_annotations.find(
            {"paper_id": paper_oid, "user_id": g.current_user["_id"]}
        ).sort([("created_at", -1), ("_id", -1)])
    )
    return {"items": [mongo_doc_to_json(row) for row in rows]}


@papers_bp.post("/<paper_id>/annotations")
@auth_required
def create_paper_annotation(paper_id: str):
    paper_oid = parse_object_id(paper_id)
    if not paper_oid:
        return {"error": "paper_id is invalid"}, 400

    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text") or "").strip()
    page = payload.get("page")
    color = str(payload.get("color") or "yellow").strip().lower()
    note = str(payload.get("note") or "")
    rects = _parse_rects(payload.get("rects"))

    if not text:
        return {"error": "text is required"}, 400
    if len(text) > 5000:
        return {"error": "text is too long"}, 400
    if not isinstance(page, int) or page <= 0:
        return {"error": "page must be a positive integer"}, 400
    if color not in HIGHLIGHT_COLORS:
        return {"error": "invalid color"}, 400
    if len(note) > 5000:
        return {"error": "note is too long"}, 400
    if not rects:
        return {"error": "rects is required"}, 400

    db = get_db()
    paper = db.papers.find_one({"_id": paper_oid, "user_id": g.current_user["_id"]})
    if not paper:
        return {"error": "paper not found"}, 404

    now = datetime.now(UTC)
    doc = {
        "paper_id": paper_oid,
        "user_id": g.current_user["_id"],
        "page": page,
        "text": text,
        "color": color,
        "note": note,
        "rects": rects,
        "created_at": now,
        "updated_at": now,
    }
    inserted = db.paper_annotations.insert_one(doc)
    created = db.paper_annotations.find_one({"_id": inserted.inserted_id})
    return mongo_doc_to_json(created), 201


@papers_bp.patch("/<paper_id>/annotations/<annotation_id>")
@auth_required
def update_paper_annotation(paper_id: str, annotation_id: str):
    paper_oid = parse_object_id(paper_id)
    if not paper_oid:
        return {"error": "paper_id is invalid"}, 400
    annotation_oid = parse_object_id(annotation_id)
    if not annotation_oid:
        return {"error": "annotation_id is invalid"}, 400

    payload = request.get_json(silent=True) or {}
    updates = {}

    if "color" in payload:
        color = str(payload.get("color") or "").strip().lower()
        if color not in HIGHLIGHT_COLORS:
            return {"error": "invalid color"}, 400
        updates["color"] = color
    if "note" in payload:
        note = str(payload.get("note") or "")
        if len(note) > 5000:
            return {"error": "note is too long"}, 400
        updates["note"] = note
    if "rects" in payload:
        rects = _parse_rects(payload.get("rects"))
        if not rects:
            return {"error": "rects is required"}, 400
        updates["rects"] = rects

    if not updates:
        return {"error": "no valid fields to update"}, 400

    updates["updated_at"] = datetime.now(UTC)
    db = get_db()
    result = db.paper_annotations.update_one(
        {
            "_id": annotation_oid,
            "paper_id": paper_oid,
            "user_id": g.current_user["_id"],
        },
        {"$set": updates},
    )
    if result.matched_count == 0:
        return {"error": "annotation not found"}, 404

    updated = db.paper_annotations.find_one(
        {"_id": annotation_oid, "paper_id": paper_oid, "user_id": g.current_user["_id"]}
    )
    return mongo_doc_to_json(updated)


@papers_bp.delete("/<paper_id>/annotations/<annotation_id>")
@auth_required
def delete_paper_annotation(paper_id: str, annotation_id: str):
    paper_oid = parse_object_id(paper_id)
    if not paper_oid:
        return {"error": "paper_id is invalid"}, 400
    annotation_oid = parse_object_id(annotation_id)
    if not annotation_oid:
        return {"error": "annotation_id is invalid"}, 400

    db = get_db()
    result = db.paper_annotations.delete_one(
        {"_id": annotation_oid, "paper_id": paper_oid, "user_id": g.current_user["_id"]}
    )
    if result.deleted_count == 0:
        return {"error": "annotation not found"}, 404
    return {"ok": True}


@papers_bp.delete("/<paper_id>")
@auth_required
def delete_paper(paper_id: str):
    paper_oid = parse_object_id(paper_id)
    if not paper_oid:
        return {"error": "paper_id is invalid"}, 400

    db = get_db()
    paper = db.papers.find_one({"_id": paper_oid, "user_id": g.current_user["_id"]})
    if not paper:
        return {"error": "paper not found"}, 404

    result = db.papers.delete_one({"_id": paper_oid, "user_id": g.current_user["_id"]})
    if result.deleted_count == 0:
        return {"error": "paper not found"}, 404

    try:
        _remove_uploaded_file_if_local(paper.get("file_url", ""), str(g.current_user["_id"]))
    except Exception:
        pass
    try:
        db.paper_figures.delete_many({"paper_id": paper_oid, "user_id": g.current_user["_id"]})
        _remove_paper_figure_assets(str(g.current_user["_id"]), paper_id)
    except Exception:
        pass
    try:
        db.paper_annotations.delete_many({"paper_id": paper_oid, "user_id": g.current_user["_id"]})
    except Exception:
        pass

    return {"ok": True}


@papers_bp.post("/<paper_id>/ocr/start")
@auth_required
def start_ocr(paper_id: str):
    paper_oid = parse_object_id(paper_id)
    if not paper_oid:
        return {"error": "paper_id is invalid"}, 400

    db = get_db()
    paper = db.papers.find_one({"_id": paper_oid, "user_id": g.current_user["_id"]})
    if not paper:
        return {"error": "paper not found"}, 404

    # Placeholder: later this should enqueue Celery OCR task.
    return {
        "ok": True,
        "paper_id": paper_id,
        "task_status": "queued",
        "message": "OCR task has been queued (stub).",
    }


@papers_bp.post("/<paper_id>/open")
@auth_required
def mark_opened(paper_id: str):
    paper_oid = parse_object_id(paper_id)
    if not paper_oid:
        return {"error": "paper_id is invalid"}, 400

    now = datetime.now(UTC)
    db = get_db()
    result = db.papers.update_one(
        {"_id": paper_oid, "user_id": g.current_user["_id"]},
        {"$set": {"last_opened_at": now, "updated_at": now}},
    )
    if result.matched_count == 0:
        return {"error": "paper not found"}, 404

    paper = db.papers.find_one({"_id": paper_oid, "user_id": g.current_user["_id"]})
    return mongo_doc_to_json(paper)


@papers_bp.post("/<paper_id>/translate-selection")
@auth_required
def translate_selection(paper_id: str):
    paper_oid = parse_object_id(paper_id)
    if not paper_oid:
        return {"error": "paper_id is invalid"}, 400

    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    target_lang = payload.get("target_lang") or current_app.config["DEFAULT_TARGET_LANG"]
    provider_id = payload.get("provider_id")

    if not text:
        return {"error": "text is required"}, 400

    db = get_db()
    paper = db.papers.find_one({"_id": paper_oid, "user_id": g.current_user["_id"]})
    if not paper:
        return {"error": "paper not found"}, 404

    translated = translate_text(
        db=db,
        user_id=g.current_user["_id"],
        text=text,
        target_lang=target_lang,
        provider_id=provider_id,
    )
    return {
        "paper_id": paper_id,
        "source_text": text,
        "target_lang": target_lang,
        "translated_text": translated,
    }
