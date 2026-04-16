import os
import shutil
from dataclasses import dataclass
from urllib.parse import urlparse

_PPSTRUCTURE_ENGINE_CACHE = {}


class FigureExtractionError(RuntimeError):
    pass


@dataclass
class ExtractedFigure:
    page: int
    image_url: str
    source_xref: int | None
    bbox_norm: dict
    bbox_pdf: dict
    width_px: int
    height_px: int
    region_type: str
    region_label: str


def _safe_join_under(root: str, relative: str) -> str | None:
    root_abs = os.path.abspath(root)
    candidate = os.path.abspath(os.path.join(root_abs, relative.replace("/", os.sep)))
    if candidate == root_abs or candidate.startswith(root_abs + os.sep):
        return candidate
    return None


def _rect_norm(rect, page_w: float, page_h: float) -> dict:
    x = max(0.0, min(1.0, float(rect.x0) / page_w))
    y = max(0.0, min(1.0, float(rect.y0) / page_h))
    w = max(0.0, min(1.0, float(rect.width) / page_w))
    h = max(0.0, min(1.0, float(rect.height) / page_h))
    return {
        "x": round(x, 6),
        "y": round(y, 6),
        "w": round(w, 6),
        "h": round(h, 6),
    }


def _rect_pdf(rect) -> dict:
    return {
        "x0": round(float(rect.x0), 2),
        "y0": round(float(rect.y0), 2),
        "x1": round(float(rect.x1), 2),
        "y1": round(float(rect.y1), 2),
    }


def _overlap_ratio(rect_a, rect_b) -> float:
    left = max(float(rect_a.x0), float(rect_b.x0))
    top = max(float(rect_a.y0), float(rect_b.y0))
    right = min(float(rect_a.x1), float(rect_b.x1))
    bottom = min(float(rect_a.y1), float(rect_b.y1))
    w = max(0.0, right - left)
    h = max(0.0, bottom - top)
    inter = w * h
    if inter <= 0:
        return 0.0
    area_a = max(1.0, float(rect_a.width) * float(rect_a.height))
    area_b = max(1.0, float(rect_b.width) * float(rect_b.height))
    return inter / min(area_a, area_b)


def _extract_table_rects_with_fitz(page) -> list[dict]:
    import fitz

    try:
        if not hasattr(page, "find_tables"):
            return []
        table_finder = page.find_tables()
        tables = getattr(table_finder, "tables", []) or []
    except Exception:
        return []

    rects: list[dict] = []
    for table in tables:
        bbox = getattr(table, "bbox", None)
        if not bbox:
            continue
        try:
            rect = fitz.Rect(bbox)
            rows = int(getattr(table, "row_count", 0) or 0)
            cols = int(getattr(table, "col_count", 0) or 0)
            rects.append({"rect": rect, "detector": "fitz", "rows": rows, "cols": cols})
        except Exception:
            continue
    return rects


def _extract_table_rects_with_pdfplumber(
    pdf_path: str, page_index: int, allow_text_strategy: bool = False
) -> list[dict]:
    try:
        import pdfplumber
        import fitz
    except ModuleNotFoundError:
        return []
    except Exception:
        return []

    settings_candidates = [
        ("pdfplumber_lines", {"vertical_strategy": "lines", "horizontal_strategy": "lines"}),
        ("pdfplumber_lines_strict", {"vertical_strategy": "lines_strict", "horizontal_strategy": "lines_strict"}),
        (
            "pdfplumber_lines_tuned",
            {"vertical_strategy": "lines", "horizontal_strategy": "lines", "snap_tolerance": 3, "join_tolerance": 3},
        ),
    ]
    if allow_text_strategy:
        settings_candidates.extend(
            [
                ("pdfplumber_text_v", {"vertical_strategy": "text", "horizontal_strategy": "lines"}),
                ("pdfplumber_text_h", {"vertical_strategy": "lines", "horizontal_strategy": "text"}),
                (
                    "pdfplumber_text",
                    {
                        "vertical_strategy": "text",
                        "horizontal_strategy": "text",
                        "snap_tolerance": 3,
                        "join_tolerance": 3,
                        "intersection_tolerance": 5,
                    },
                ),
            ]
        )

    rects: list[dict] = []
    try:
        with pdfplumber.open(pdf_path) as doc:
            if page_index < 0 or page_index >= len(doc.pages):
                return []
            page = doc.pages[page_index]
            for pair in settings_candidates:
                if not isinstance(pair, tuple) or len(pair) != 2:
                    continue
                detector, settings = pair
                try:
                    tables = page.find_tables(table_settings=settings) or []
                except Exception:
                    continue
                for table in tables:
                    bbox = getattr(table, "bbox", None)
                    if not bbox:
                        continue
                    x0, top, x1, bottom = bbox
                    try:
                        data = table.extract() or []
                    except Exception:
                        data = []
                    rows = len(data)
                    cols = max((len(r) for r in data), default=0)
                    rects.append(
                        {
                            "rect": fitz.Rect(float(x0), float(top), float(x1), float(bottom)),
                            "detector": detector,
                            "rows": rows,
                            "cols": cols,
                        }
                    )
    except Exception:
        return []
    return rects


def _dedupe_rects(candidates: list[dict], overlap_threshold: float = 0.9) -> list[dict]:
    picked: list[dict] = []
    for item in candidates:
        rect = item.get("rect")
        if rect is None:
            continue
        if any(_overlap_ratio(rect, existed["rect"]) >= overlap_threshold for existed in picked):
            continue
        picked.append(item)
    return picked


def _rect_overlap_ratio_to_union(rect_a, rect_b) -> float:
    left = max(float(rect_a.x0), float(rect_b.x0))
    top = max(float(rect_a.y0), float(rect_b.y0))
    right = min(float(rect_a.x1), float(rect_b.x1))
    bottom = min(float(rect_a.y1), float(rect_b.y1))
    inter_w = max(0.0, right - left)
    inter_h = max(0.0, bottom - top)
    inter = inter_w * inter_h
    if inter <= 0:
        return 0.0
    area_a = max(1.0, float(rect_a.width) * float(rect_a.height))
    area_b = max(1.0, float(rect_b.width) * float(rect_b.height))
    union = max(1.0, area_a + area_b - inter)
    return inter / union


def _rects_close_or_overlap(rect_a, rect_b, gap_points: float = 8.0) -> bool:
    try:
        import fitz
    except Exception:
        return False
    expanded = fitz.Rect(rect_a)
    expanded.x0 -= gap_points
    expanded.y0 -= gap_points
    expanded.x1 += gap_points
    expanded.y1 += gap_points
    return expanded.intersects(rect_b)


def _merge_embedded_image_rects(items: list[dict], gap_points: float = 8.0) -> list[dict]:
    try:
        import fitz
    except Exception:
        return items
    if not items:
        return []

    merged: list[dict] = []
    for item in items:
        rect = fitz.Rect(item["rect"])
        xrefs = set(item.get("xrefs") or [])

        attached_idx = []
        for idx, existing in enumerate(merged):
            if _rects_close_or_overlap(rect, existing["rect"], gap_points=gap_points):
                attached_idx.append(idx)

        if not attached_idx:
            merged.append({"rect": rect, "xrefs": xrefs})
            continue

        union_rect = fitz.Rect(rect)
        union_xrefs = set(xrefs)
        for idx in sorted(attached_idx, reverse=True):
            union_rect |= merged[idx]["rect"]
            union_xrefs |= set(merged[idx].get("xrefs") or [])
            merged.pop(idx)
        merged.append({"rect": union_rect, "xrefs": union_xrefs})

    # second pass to resolve chain-merges
    changed = True
    while changed:
        changed = False
        output = []
        while merged:
            current = merged.pop()
            current_rect = fitz.Rect(current["rect"])
            current_xrefs = set(current.get("xrefs") or [])
            keep = []
            for other in merged:
                if _rects_close_or_overlap(current_rect, other["rect"], gap_points=gap_points):
                    current_rect |= other["rect"]
                    current_xrefs |= set(other.get("xrefs") or [])
                    changed = True
                else:
                    keep.append(other)
            merged = keep
            output.append({"rect": current_rect, "xrefs": current_xrefs})
        merged = output
    return merged


def _merge_visual_candidates(items: list[dict], gap_points: float = 10.0, iou_threshold: float = 0.08) -> list[dict]:
    try:
        import fitz
    except Exception:
        return items
    if not items:
        return []

    merged: list[dict] = []
    for item in items:
        rect = fitz.Rect(item["rect"])
        xrefs = set(item.get("xrefs") or [])
        kinds = set(item.get("kinds") or [])

        attached_idx = []
        for idx, existing in enumerate(merged):
            should_merge = _rects_close_or_overlap(rect, existing["rect"], gap_points=gap_points)
            if not should_merge:
                should_merge = _rect_overlap_ratio_to_union(rect, existing["rect"]) >= iou_threshold
            if should_merge:
                attached_idx.append(idx)

        if not attached_idx:
            merged.append({"rect": rect, "xrefs": xrefs, "kinds": kinds})
            continue

        union_rect = fitz.Rect(rect)
        union_xrefs = set(xrefs)
        union_kinds = set(kinds)
        for idx in sorted(attached_idx, reverse=True):
            union_rect |= merged[idx]["rect"]
            union_xrefs |= set(merged[idx].get("xrefs") or [])
            union_kinds |= set(merged[idx].get("kinds") or [])
            merged.pop(idx)
        merged.append({"rect": union_rect, "xrefs": union_xrefs, "kinds": union_kinds})

    changed = True
    while changed:
        changed = False
        output = []
        while merged:
            current = merged.pop()
            current_rect = fitz.Rect(current["rect"])
            current_xrefs = set(current.get("xrefs") or [])
            current_kinds = set(current.get("kinds") or [])
            keep = []
            for other in merged:
                should_merge = _rects_close_or_overlap(current_rect, other["rect"], gap_points=gap_points)
                if not should_merge:
                    should_merge = _rect_overlap_ratio_to_union(current_rect, other["rect"]) >= iou_threshold
                if should_merge:
                    current_rect |= other["rect"]
                    current_xrefs |= set(other.get("xrefs") or [])
                    current_kinds |= set(other.get("kinds") or [])
                    changed = True
                else:
                    keep.append(other)
            merged = keep
            output.append({"rect": current_rect, "xrefs": current_xrefs, "kinds": current_kinds})
        merged = output

    return merged


def _extract_image_block_rects_with_fitz(page) -> list[dict]:
    try:
        raw = page.get_text("dict") or {}
    except Exception:
        return []

    blocks = raw.get("blocks") if isinstance(raw, dict) else []
    out = []
    for block in blocks or []:
        if not isinstance(block, dict):
            continue
        if int(block.get("type", 0) or 0) != 1:
            continue
        bbox = block.get("bbox")
        if not bbox or not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            continue
        try:
            import fitz

            rect = fitz.Rect(float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
            out.append({"rect": rect, "xrefs": set(), "kinds": {"image_block"}})
        except Exception:
            continue
    return out


def _extract_vector_visual_rects_with_fitz(page, min_edge_points: float = 24.0) -> list[dict]:
    try:
        import fitz
    except Exception:
        return []

    rects = []
    if hasattr(page, "cluster_drawings"):
        try:
            clusters = page.cluster_drawings() or []
        except Exception:
            clusters = []
        for item in clusters:
            try:
                rect = fitz.Rect(item)
            except Exception:
                continue
            if float(rect.width) < min_edge_points or float(rect.height) < min_edge_points:
                continue
            rects.append({"rect": rect, "xrefs": set(), "kinds": {"vector"}})
        if rects:
            return rects

    try:
        drawings = page.get_drawings() or []
    except Exception:
        drawings = []
    for draw in drawings:
        rect = draw.get("rect")
        if rect is None:
            continue
        try:
            rect = fitz.Rect(rect)
        except Exception:
            continue
        if float(rect.width) < min_edge_points or float(rect.height) < min_edge_points:
            continue
        rects.append({"rect": rect, "xrefs": set(), "kinds": {"vector"}})
    return rects


def _text_coverage_ratio(page, rect) -> float:
    area = max(1.0, float(rect.width) * float(rect.height))
    try:
        blocks = page.get_text("blocks", clip=rect) or []
    except Exception:
        return 0.0

    covered = 0.0
    for block in blocks:
        if not isinstance(block, (list, tuple)) or len(block) < 4:
            continue
        try:
            x0 = max(float(rect.x0), float(block[0]))
            y0 = max(float(rect.y0), float(block[1]))
            x1 = min(float(rect.x1), float(block[2]))
            y1 = min(float(rect.y1), float(block[3]))
            w = max(0.0, x1 - x0)
            h = max(0.0, y1 - y0)
            covered += w * h
        except Exception:
            continue
    return min(1.0, covered / area)


def _has_figure_caption_nearby(page, rect) -> bool:
    import re

    try:
        clip = page.rect.__class__(
            max(0.0, float(rect.x0) - 20.0),
            max(0.0, float(rect.y0) - 90.0),
            min(float(page.rect.x1), float(rect.x1) + 20.0),
            min(float(page.rect.y1), float(rect.y1) + 44.0),
        )
        text = (page.get_text("text", clip=clip) or "").lower()
    except Exception:
        return False
    if not text.strip():
        return False
    return bool(
        re.search(
            r"\b(fig(?:ure)?\.?\s*\d+)\b|(?:^|\s)图\s*\d+",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    )


def _has_table_caption_nearby(page, rect) -> bool:
    import re

    try:
        clip = page.rect.__class__(
            float(rect.x0),
            max(0.0, float(rect.y0) - 72.0),
            float(rect.x1),
            min(float(page.rect.y1), float(rect.y0) + 8.0),
        )
        text = (page.get_text("text", clip=clip) or "").lower()
    except Exception:
        return False
    if not text.strip():
        return False
    return bool(re.search(r"\btable\b|\btab\.\b", text, flags=re.IGNORECASE))


def _get_ppstructure_engine(lang: str = "en", use_gpu: bool = False):
    key = (lang, bool(use_gpu))
    if key in _PPSTRUCTURE_ENGINE_CACHE:
        return _PPSTRUCTURE_ENGINE_CACHE[key]

    from paddleocr import PPStructure

    engine = PPStructure(
        show_log=False,
        layout=True,
        ocr=True,
        table=True,
        lang=lang,
        use_gpu=bool(use_gpu),
    )
    _PPSTRUCTURE_ENGINE_CACHE[key] = engine
    return engine


def _parse_layout_bbox(raw_bbox):
    if not raw_bbox:
        return None

    # Format A: [x0, y0, x1, y1]
    if isinstance(raw_bbox, (list, tuple)) and len(raw_bbox) == 4 and all(
        isinstance(v, (int, float)) for v in raw_bbox
    ):
        x0, y0, x1, y1 = raw_bbox
        return float(x0), float(y0), float(x1), float(y1)

    # Format B: [[x,y], [x,y], ...]
    if isinstance(raw_bbox, (list, tuple)) and len(raw_bbox) >= 2:
        points = []
        for point in raw_bbox:
            if (
                isinstance(point, (list, tuple))
                and len(point) >= 2
                and isinstance(point[0], (int, float))
                and isinstance(point[1], (int, float))
            ):
                points.append((float(point[0]), float(point[1])))
        if points:
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            return min(xs), min(ys), max(xs), max(ys)

    return None


def _extract_layout_regions_with_ppstructure(
    *,
    page,
    engine,
    np_module,
    render_scale: float = 2.0,
) -> tuple[list[dict], str | None]:
    try:
        import fitz
    except Exception:
        return [], "Failed to initialize OCR dependencies."

    pix = page.get_pixmap(matrix=fitz.Matrix(render_scale, render_scale), alpha=False)
    if pix.width <= 4 or pix.height <= 4:
        return [], None

    try:
        rgb = np_module.frombuffer(pix.samples, dtype=np_module.uint8).reshape((pix.height, pix.width, 3))
        bgr = rgb[:, :, ::-1]
        result = engine(bgr) or []
    except Exception as exc:
        return [], f"PP-Structure inference failed: {exc}"

    scale_x = float(page.rect.width) / float(pix.width)
    scale_y = float(page.rect.height) / float(pix.height)

    candidates = []
    for block in result:
        block_type = str(block.get("type") or "").lower()
        if block_type not in {"table", "figure", "chart"}:
            continue
        parsed = _parse_layout_bbox(block.get("bbox"))
        if not parsed:
            continue

        x0, y0, x1, y1 = parsed
        if x1 <= x0 or y1 <= y0:
            continue

        rect = fitz.Rect(
            max(0.0, x0 * scale_x),
            max(0.0, y0 * scale_y),
            max(0.0, x1 * scale_x),
            max(0.0, y1 * scale_y),
        )
        candidates.append(
            {
                "rect": rect,
                "detector": f"ppstructure_{block_type}",
                "rows": 0,
                "cols": 0,
                "kind": block_type,
            }
        )

    return candidates, None


def resolve_local_pdf_path(file_url: str, upload_root: str) -> str | None:
    if not file_url:
        return None

    parsed = urlparse(file_url)
    path = parsed.path if parsed.scheme else file_url
    if not path.startswith("/uploads/"):
        return None

    relative = path[len("/uploads/"):].lstrip("/")
    if not relative:
        return None

    candidate = _safe_join_under(upload_root, relative)
    if not candidate or not os.path.isfile(candidate):
        return None
    return candidate


def clear_paper_figure_dir(upload_root: str, user_id: str, paper_id: str) -> None:
    relative = f"{user_id}/figures/{paper_id}"
    figures_dir = _safe_join_under(upload_root, relative)
    if not figures_dir:
        return
    if os.path.isdir(figures_dir):
        shutil.rmtree(figures_dir, ignore_errors=True)


def extract_visual_regions(
    *,
    pdf_path: str,
    upload_root: str,
    user_id: str,
    paper_id: str,
    render_scale: float = 2.0,
    min_edge_points: float = 24.0,
    include_embedded_images: bool = True,
    include_tables: bool = True,
    include_boxed_text: bool = True,
    include_table_text_strategy: bool = False,
    enable_ocr_layout: bool = False,
    ocr_layout_lang: str = "en",
    ocr_layout_use_gpu: bool = False,
    include_ocr_layout_figures: bool = True,
    min_boxed_text_chars: int = 36,
    max_table_area_ratio: float = 0.5,
    max_table_height_ratio: float = 0.82,
    merge_embedded_images: bool = False,
    embedded_merge_gap_points: float = 8.0,
    min_embedded_area_ratio: float = 0.003,
    include_image_block_candidates: bool = True,
    include_vector_graphics: bool = False,
    figure_text_coverage_max: float = 0.72,
    only_captioned_vector_regions: bool = False,
) -> tuple[list[ExtractedFigure], list[str]]:
    try:
        import fitz
    except ModuleNotFoundError as exc:
        raise FigureExtractionError("PyMuPDF is not installed. Please install dependencies first.") from exc

    relative_dir = f"{user_id}/figures/{paper_id}"
    output_dir = _safe_join_under(upload_root, relative_dir)
    if not output_dir:
        raise FigureExtractionError("Invalid figure output path.")
    os.makedirs(output_dir, exist_ok=True)

    figures: list[ExtractedFigure] = []
    warnings: list[str] = []
    ocr_layout_enabled_for_pages = False
    ocr_engine = None
    np_module = None

    if enable_ocr_layout:
        try:
            import numpy as np_module  # type: ignore[assignment]
        except ModuleNotFoundError:
            warnings.append("OCR layout unavailable: numpy not installed.")
        except Exception:
            warnings.append("OCR layout unavailable: failed to initialize numpy.")

        if np_module is not None:
            try:
                ocr_engine = _get_ppstructure_engine(lang=ocr_layout_lang, use_gpu=ocr_layout_use_gpu)
                ocr_layout_enabled_for_pages = True
            except ModuleNotFoundError:
                warnings.append("OCR layout unavailable: PaddleOCR not installed (pip install paddleocr paddlepaddle).")
            except Exception as exc:
                warnings.append(f"OCR layout unavailable: {exc}")

    def save_region(
        *,
        page,
        page_num: int,
        rect,
        label_prefix: str,
        region_type: str,
        source_xref: int | None = None,
        local_counter: int = 0,
    ):
        matrix = fitz.Matrix(render_scale, render_scale)
        clip = fitz.Rect(rect)
        pix = page.get_pixmap(matrix=matrix, clip=clip, alpha=False)
        if pix.width <= 4 or pix.height <= 4:
            return

        image_name = f"p{page_num:03d}_{label_prefix}_{local_counter:03d}.png"
        image_path = os.path.join(output_dir, image_name)
        pix.save(image_path)

        page_rect = page.rect
        page_w = float(page_rect.width or 1.0)
        page_h = float(page_rect.height or 1.0)
        image_url = f"/uploads/{relative_dir}/{image_name}".replace("\\", "/")

        figures.append(
            ExtractedFigure(
                page=page_num,
                image_url=image_url,
                source_xref=source_xref,
                bbox_norm=_rect_norm(rect, page_w, page_h),
                bbox_pdf=_rect_pdf(rect),
                width_px=pix.width,
                height_px=pix.height,
                region_type=region_type,
                region_label=label_prefix,
            )
        )

    doc = fitz.open(pdf_path)
    try:
        for page_index in range(doc.page_count):
            page = doc[page_index]
            page_num = page_index + 1
            page_rect = page.rect

            selected_rects = []
            per_page_counter = 0

            if include_embedded_images:
                image_entries = page.get_images(full=True)
                seen_xref: set[int] = set()
                embedded_candidates: list[dict] = []
                for row in image_entries:
                    xref = int(row[0])
                    if xref in seen_xref:
                        continue
                    seen_xref.add(xref)

                    rects = page.get_image_rects(xref)
                    for rect in rects:
                        if float(rect.width) < min_edge_points or float(rect.height) < min_edge_points:
                            continue
                        area_ratio = float(rect.width) * float(rect.height) / (
                            float(page_rect.width) * float(page_rect.height)
                        )
                        if area_ratio < min_embedded_area_ratio:
                            continue
                        embedded_candidates.append({"rect": rect, "xrefs": {xref}, "kinds": {"embedded"}})

                if include_image_block_candidates:
                    embedded_candidates.extend(_extract_image_block_rects_with_fitz(page))

                if include_vector_graphics:
                    embedded_candidates.extend(
                        _extract_vector_visual_rects_with_fitz(page, min_edge_points=min_edge_points)
                    )

                if merge_embedded_images or include_image_block_candidates or include_vector_graphics:
                    embedded_candidates = _merge_visual_candidates(
                        embedded_candidates,
                        gap_points=embedded_merge_gap_points,
                        iou_threshold=0.08,
                    )

                for item in embedded_candidates:
                    rect = item["rect"]
                    if any(_overlap_ratio(rect, used) >= 0.92 for used in selected_rects):
                        continue
                    xrefs = item.get("xrefs") or set()
                    kinds = set(item.get("kinds") or set())
                    source_xref = next(iter(xrefs)) if len(xrefs) == 1 else None
                    width_ratio = float(rect.width) / max(1.0, float(page_rect.width))
                    height_ratio = float(rect.height) / max(1.0, float(page_rect.height))
                    if width_ratio > 0.985 and height_ratio > 0.985:
                        continue
                    if width_ratio < 0.03 or height_ratio < 0.03:
                        continue

                    caption_nearby = _has_figure_caption_nearby(page, rect)
                    if "vector" in kinds:
                        if only_captioned_vector_regions and not caption_nearby:
                            continue
                        if width_ratio < 0.12 and height_ratio < 0.12 and not caption_nearby:
                            continue

                    text_coverage = _text_coverage_ratio(page, rect) if ("vector" in kinds or "image_block" in kinds) else 0.0
                    if text_coverage > figure_text_coverage_max and not caption_nearby:
                        continue

                    per_page_counter += 1
                    save_region(
                        page=page,
                        page_num=page_num,
                        rect=rect,
                        label_prefix="image",
                        region_type="embedded_image",
                        source_xref=source_xref,
                        local_counter=per_page_counter,
                    )
                    selected_rects.append(rect)

            if include_tables:
                fitz_table_rects = _extract_table_rects_with_fitz(page)
                plumber_table_rects = _extract_table_rects_with_pdfplumber(
                    pdf_path,
                    page_index,
                    allow_text_strategy=include_table_text_strategy,
                )
                ocr_layout_candidates = []
                if ocr_layout_enabled_for_pages:
                    ocr_layout_candidates, warning = _extract_layout_regions_with_ppstructure(
                        page=page,
                        engine=ocr_engine,
                        np_module=np_module,
                        render_scale=render_scale,
                    )
                    if warning:
                        warnings.append(warning)

                table_candidates = _dedupe_rects(
                    [
                        *fitz_table_rects,
                        *plumber_table_rects,
                        *[item for item in ocr_layout_candidates if item.get("kind") == "table"],
                    ],
                    overlap_threshold=0.86,
                )

                for candidate in table_candidates:
                    rect = candidate["rect"]
                    cols = int(candidate.get("cols", 0) or 0)
                    rows = int(candidate.get("rows", 0) or 0)
                    detector = str(candidate.get("detector") or "")

                    if float(rect.width) < min_edge_points or float(rect.height) < min_edge_points:
                        continue
                    area_ratio = float(rect.width) * float(rect.height) / (float(page_rect.width) * float(page_rect.height))
                    height_ratio = float(rect.height) / float(page_rect.height)
                    width_ratio = float(rect.width) / float(page_rect.width)
                    has_caption = _has_table_caption_nearby(page, rect)

                    if area_ratio > max_table_area_ratio:
                        continue
                    if height_ratio > max_table_height_ratio and width_ratio > 0.52:
                        continue
                    # Guard against long text blocks / references being treated as a "table".
                    if detector.startswith("pdfplumber_text"):
                        if rows < 3 or cols < 3:
                            continue
                        if cols <= 3 and not has_caption:
                            continue
                    if width_ratio > 0.6 and height_ratio > 0.68 and not has_caption:
                        continue
                    if any(_overlap_ratio(rect, used) >= 0.85 for used in selected_rects):
                        continue

                    per_page_counter += 1
                    save_region(
                        page=page,
                        page_num=page_num,
                        rect=rect,
                        label_prefix="table",
                        region_type="table",
                        local_counter=per_page_counter,
                    )
                    selected_rects.append(rect)

                if ocr_layout_enabled_for_pages and include_ocr_layout_figures:
                    ocr_figure_candidates = _dedupe_rects(
                        [item for item in ocr_layout_candidates if item.get("kind") in {"figure", "chart"}],
                        overlap_threshold=0.86,
                    )
                    for candidate in ocr_figure_candidates:
                        rect = candidate["rect"]
                        width_ratio = float(rect.width) / float(page_rect.width)
                        height_ratio = float(rect.height) / float(page_rect.height)
                        if width_ratio < 0.06 or height_ratio < 0.06:
                            continue
                        if width_ratio > 0.95 and height_ratio > 0.95:
                            continue
                        if any(_overlap_ratio(rect, used) >= 0.85 for used in selected_rects):
                            continue

                        per_page_counter += 1
                        save_region(
                            page=page,
                            page_num=page_num,
                            rect=rect,
                            label_prefix="ocr_figure",
                            region_type="ocr_figure",
                            local_counter=per_page_counter,
                        )
                        selected_rects.append(rect)

            if include_boxed_text:
                try:
                    drawings = page.get_drawings()
                except Exception:
                    drawings = []

                for draw in drawings:
                    rect = draw.get("rect")
                    if rect is None:
                        continue
                    rect = fitz.Rect(rect)

                    if float(rect.width) < 120 or float(rect.height) < 48:
                        continue
                    if float(rect.width) > float(page_rect.width) * 0.95 and float(rect.height) > float(page_rect.height) * 0.95:
                        continue
                    if any(_overlap_ratio(rect, used) >= 0.9 for used in selected_rects):
                        continue

                    txt = (page.get_text("text", clip=rect) or "").strip()
                    if len(txt) < min_boxed_text_chars:
                        continue

                    per_page_counter += 1
                    save_region(
                        page=page,
                        page_num=page_num,
                        rect=rect,
                        label_prefix="boxed_text",
                        region_type="boxed_text",
                        local_counter=per_page_counter,
                    )
                    selected_rects.append(rect)
    finally:
        doc.close()

    figures.sort(key=lambda item: (item.page, item.bbox_norm["y"], item.bbox_norm["x"]))
    # Keep warning list short and stable.
    dedup_warnings = []
    seen = set()
    for warning in warnings:
        if warning in seen:
            continue
        seen.add(warning)
        dedup_warnings.append(warning)
    return figures, dedup_warnings
