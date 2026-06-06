from __future__ import annotations

from bson import ObjectId

from app.services.figure_extractor import resolve_local_pdf_path
from app.services.llm_client import call_chat_completion, pick_provider
from app.utils.object_id import parse_object_id


ACADEMIC_TASKS = {
    "paper_summary": {
        "label": "论文速读",
        "mode": "single",
        "description": "快速总结论文研究问题、方法、实验和结论",
    },
    "method_breakdown": {
        "label": "方法拆解",
        "mode": "single",
        "description": "拆解论文输入、输出、模块、流程和汇报讲法",
    },
    "innovation_limits": {
        "label": "创新点与不足",
        "mode": "single",
        "description": "分析论文创新点、不足和后续拓展方向",
    },
    "presentation_outline": {
        "label": "汇报提纲",
        "mode": "single",
        "description": "生成课程汇报提纲、讲稿要点和老师追问",
    },
    "paper_compare": {
        "label": "多篇对比",
        "mode": "multi",
        "description": "对比 2-3 篇论文的问题、方法、实验和优缺点",
    },
    "custom_qa": {
        "label": "自定义提问",
        "mode": "single_or_multi",
        "description": "基于选中论文或通用学术场景回答自定义问题",
    },
}

DEFAULT_CONTEXT_OPTIONS = {
    "include_metadata": True,
    "include_pdf_excerpt": True,
    "include_annotations": True,
    "include_figures": True,
}

SUGGESTED_QUESTIONS = {
    "paper_summary": [
        "这篇论文的方法有什么不足？",
        "这篇论文适合如何复现？",
        "这篇论文可以怎么汇报？",
    ],
    "method_breakdown": [
        "这个方法的输入和输出分别是什么？",
        "方法框架图应该怎么画？",
        "哪些模块最适合重点讲解？",
    ],
    "innovation_limits": [
        "这些创新点和已有方法相比优势在哪里？",
        "哪些不足适合作为后续工作？",
        "如果复现这篇论文，风险点是什么？",
    ],
    "presentation_outline": [
        "第一页应该如何开场？",
        "老师最可能追问哪些实验细节？",
        "如何用一句话总结这篇论文？",
    ],
    "paper_compare": [
        "这几篇论文最核心的差异是什么？",
        "哪篇论文的方法更适合课程汇报？",
        "它们有哪些共同的研究趋势？",
    ],
    "custom_qa": [
        "请继续解释关键方法细节。",
        "请给出适合汇报的回答版本。",
        "请指出当前上下文中无法确定的信息。",
    ],
}


class AcademicAgentError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def list_academic_tasks() -> list[dict]:
    return [
        {"key": key, **value}
        for key, value in ACADEMIC_TASKS.items()
    ]


def extract_pdf_excerpt(
    pdf_path: str,
    max_front_pages: int = 3,
    max_back_pages: int = 2,
    max_chars: int = 12000,
) -> tuple[str, list[int]]:
    try:
        import fitz
    except ModuleNotFoundError as exc:
        raise AcademicAgentError("PyMuPDF is not installed. Please install backend dependencies.", 500) from exc

    doc = fitz.open(pdf_path)
    try:
        page_count = doc.page_count
        if page_count <= 0:
            return "", []

        front = list(range(min(max_front_pages, page_count)))
        back_start = max(0, page_count - max_back_pages)
        page_indexes = []
        for index in [*front, *range(back_start, page_count)]:
            if index not in page_indexes:
                page_indexes.append(index)

        parts = []
        used_pages = []
        remaining = max_chars
        for index in page_indexes:
            if remaining <= 0:
                break
            text = (doc[index].get_text("text") or "").strip()
            if not text:
                continue
            chunk = f"[Page {index + 1}]\n{text}"
            if len(chunk) > remaining:
                chunk = chunk[:remaining]
            parts.append(chunk)
            used_pages.append(index + 1)
            remaining -= len(chunk)

        return "\n\n".join(parts), used_pages
    finally:
        doc.close()


def _stringify(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value if str(item).strip())
    return str(value)


def _append_section(parts: list[str], title: str, body: str) -> None:
    clean = str(body or "").strip()
    if clean:
        parts.append(f"## {title}\n{clean}")


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}\n...[truncated]"


def _build_metadata_section(paper: dict) -> str:
    metadata = paper.get("citationMetadata") or {}
    lines = [
        f"Title: {_stringify(paper.get('title')) or 'Untitled'}",
        f"Authors: {_stringify(paper.get('authors')) or 'Unknown'}",
        f"Conference/Source: {_stringify(paper.get('conference')) or 'Unknown'}",
        f"Year: {_stringify(paper.get('year')) or 'Unknown'}",
        f"Tags: {_stringify(paper.get('tags')) or 'None'}",
        f"Status: {_stringify(paper.get('status')) or 'Unknown'}",
    ]
    if metadata:
        lines.extend(
            [
                "",
                "Citation Metadata:",
                f"- title: {_stringify(metadata.get('title'))}",
                f"- authors: {_stringify(metadata.get('authors'))}",
                f"- year: {_stringify(metadata.get('year'))}",
                f"- venue: {_stringify(metadata.get('venue'))}",
                f"- doi: {_stringify(metadata.get('doi'))}",
                f"- arxiv: {_stringify(metadata.get('arxivId') or metadata.get('arxiv'))}",
                f"- source: {_stringify(metadata.get('source'))}",
            ]
        )
    return "\n".join(lines)


def _build_annotations_section(db, user_id: ObjectId, paper_id: ObjectId) -> tuple[str, int]:
    rows = list(
        db.paper_annotations.find({"paper_id": paper_id, "user_id": user_id})
        .sort([("created_at", -1), ("_id", -1)])
        .limit(10)
    )
    lines = []
    for row in rows:
        text = _stringify(row.get("text"))
        note = _stringify(row.get("note"))
        page = row.get("page") or "?"
        line = f"- Page {page}: {text}"
        if note:
            line += f"\n  Note: {note}"
        lines.append(line)
    return "\n".join(lines), len(rows)


def _build_figures_section(db, user_id: ObjectId, paper_id: ObjectId) -> tuple[str, int]:
    rows = list(
        db.paper_figures.find({"paper_id": paper_id, "user_id": user_id})
        .sort([("page", 1), ("_id", 1)])
        .limit(10)
    )
    lines = []
    for row in rows:
        page = row.get("page") or "?"
        region_type = _stringify(row.get("region_type")) or "region"
        region_label = _stringify(row.get("region_label")) or "unlabeled"
        note = _stringify(row.get("note"))
        tags = _stringify(row.get("tags"))
        line = f"- Page {page}: {region_type} / {region_label}"
        if tags:
            line += f", tags: {tags}"
        if note:
            line += f"\n  Note: {note}"
        lines.append(line)
    return "\n".join(lines), len(rows)


def build_paper_context(
    db,
    user_id: ObjectId,
    paper: dict,
    upload_root: str,
    context_options: dict,
    max_chars: int = 14000,
) -> tuple[str, dict]:
    options = {**DEFAULT_CONTEXT_OPTIONS, **(context_options or {})}
    paper_id = paper["_id"]
    parts = [f"# Paper: {_stringify(paper.get('title')) or str(paper_id)}"]

    if options.get("include_metadata", True):
        _append_section(parts, "Metadata", _build_metadata_section(paper))

    pdf_pages: list[int] = []
    pdf_excerpt = ""
    if options.get("include_pdf_excerpt", True):
        pdf_path = resolve_local_pdf_path(paper.get("file_url", ""), upload_root)
        if pdf_path:
            try:
                pdf_excerpt, pdf_pages = extract_pdf_excerpt(pdf_path)
            except Exception:
                pdf_excerpt = ""
                pdf_pages = []
        _append_section(parts, "PDF Excerpt", pdf_excerpt)

    used_annotations = 0
    if options.get("include_annotations", True):
        annotations, used_annotations = _build_annotations_section(db, user_id, paper_id)
        _append_section(parts, "User Annotations", annotations)

    used_figures = 0
    if options.get("include_figures", True):
        figures, used_figures = _build_figures_section(db, user_id, paper_id)
        _append_section(parts, "Figure Notes", figures)

    context = _truncate("\n\n".join(parts), max_chars)
    source = {
        "paper_id": str(paper_id),
        "title": _stringify(paper.get("title")) or "Untitled",
        "pages": pdf_pages,
        "used_annotations": used_annotations,
        "used_figures": used_figures,
        "has_pdf_excerpt": bool(pdf_excerpt),
    }
    return context, source


def build_messages(task: str, query: str, papers_context: str, target_lang: str) -> list[dict]:
    language_hint = target_lang or "zh-CN"
    has_paper_context = bool(str(papers_context or "").strip())
    prompts = {
        "paper_summary": (
            "你是一个严谨的学术论文阅读助手。请根据提供的论文上下文，用中文完成论文速读。\n\n"
            "要求：\n"
            "1. 只基于上下文回答，不要编造。\n"
            "2. 信息不足时写“根据当前上下文无法确定”。\n"
            "3. 输出结构如下：\n"
            "   一、研究问题\n"
            "   二、核心方法\n"
            "   三、主要创新点\n"
            "   四、实验设置\n"
            "   五、主要结论\n"
            "   六、局限与不足\n"
            "   七、汇报时的一句话总结\n\n"
            f"论文上下文：\n{papers_context}"
        ),
        "method_breakdown": (
            "你是计算机方向论文讲解助手。请将论文方法拆解为适合课程汇报的形式。\n\n"
            "输出结构：\n"
            "1. 方法总览\n"
            "2. 输入是什么\n"
            "3. 输出是什么\n"
            "4. 中间模块有哪些\n"
            "5. 每个模块的作用\n"
            "6. 训练或推理流程\n"
            "7. 方法框架图可以怎么画\n"
            "8. 答辩时可以怎么讲\n\n"
            f"论文上下文：\n{papers_context}"
        ),
        "innovation_limits": (
            "请分析这篇论文的创新点与不足。\n\n"
            "要求：\n"
            "1. 至少给出 3 个创新点。\n"
            "2. 每个创新点都解释为什么有价值。\n"
            "3. 至少给出 3 个不足。\n"
            "4. 不足要结合方法、实验或应用场景，不要泛泛而谈。\n"
            "5. 最后给出可继续扩展的研究方向。\n"
            "6. 信息不足时要明确说明。\n\n"
            f"论文上下文：\n{papers_context}"
        ),
        "presentation_outline": (
            "请根据论文内容生成一个适合 5-8 分钟课程汇报的提纲。\n\n"
            "要求：\n"
            "1. 按讲解顺序组织。\n"
            "2. 每一部分给出建议讲解时长。\n"
            "3. 给出可以直接口述的讲稿要点。\n"
            "4. 列出老师可能追问的 5 个问题及回答思路。\n"
            "5. 输出要适合计算机专业课程汇报。\n\n"
            f"论文上下文：\n{papers_context}"
        ),
        "paper_compare": (
            "请比较以下多篇论文。\n\n"
            "要求：\n"
            "1. 用 Markdown 表格输出。\n"
            "2. 对比维度包括：研究问题、方法路线、数据集/实验、优点、不足、可借鉴点。\n"
            "3. 表格后总结这几篇论文的共同趋势和差异。\n"
            "4. 不要编造上下文中没有的信息。\n\n"
            f"多篇论文上下文：\n{papers_context}"
        ),
        "custom_qa": (
            "你是一个严谨的学术论文问答助手。请基于用户选中的论文上下文回答问题。\n\n"
            "要求：\n"
            "1. 如果提供了论文上下文，请优先基于上下文回答。\n"
            "2. 如果没有选择论文或上下文不足，请明确说明，并以通用学术助手身份回答。\n"
            "3. 回答要结构清晰，适合学生理解。\n"
            "4. 如果涉及多篇论文，请指出不同论文之间的差异。\n\n"
            f"用户问题：\n{query}\n\n"
            f"论文上下文：\n{papers_context or '未选择论文上下文。'}"
        ),
    }

    system_content = (
        "You are a careful academic assistant. Use only the supplied paper context. "
        f"Answer in {language_hint}. Do not invent unsupported facts."
    )
    if task == "custom_qa" and not has_paper_context:
        system_content = (
            "You are a careful academic assistant. No paper context was selected for this turn, "
            f"so answer as a general academic helper in {language_hint}. Be clear when your answer is not paper-specific."
        )

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": prompts[task]},
    ]


def _validate_task(task: str, paper_ids: list, query: str) -> None:
    if task not in ACADEMIC_TASKS:
        raise AcademicAgentError("task is invalid", 400)
    if not isinstance(paper_ids, list):
        raise AcademicAgentError("paper_ids must be a list", 400)

    count = len(paper_ids)
    mode = ACADEMIC_TASKS[task]["mode"]
    if mode == "single" and count != 1:
        raise AcademicAgentError("this task requires exactly 1 paper", 400)
    if mode == "multi" and count not in {2, 3}:
        raise AcademicAgentError("paper_compare requires 2-3 papers", 400)
    if mode == "single_or_multi" and count > 3:
        raise AcademicAgentError("custom_qa can include at most 3 papers", 400)
    if task == "custom_qa" and not query.strip():
        raise AcademicAgentError("query is required for custom_qa", 400)


def _load_user_papers(db, user_id: ObjectId, paper_ids: list) -> list[dict]:
    parsed_ids = []
    seen = set()
    for raw_id in paper_ids:
        paper_oid = parse_object_id(str(raw_id))
        if not paper_oid:
            raise AcademicAgentError("paper_id is invalid", 400)
        if paper_oid in seen:
            continue
        seen.add(paper_oid)
        parsed_ids.append(paper_oid)

    rows = list(db.papers.find({"_id": {"$in": parsed_ids}, "user_id": user_id}))
    by_id = {row["_id"]: row for row in rows}
    missing = [str(paper_oid) for paper_oid in parsed_ids if paper_oid not in by_id]
    if missing:
        raise AcademicAgentError("paper not found", 404)
    return [by_id[paper_oid] for paper_oid in parsed_ids]


def run_academic_task(db, user_id: ObjectId, payload: dict, upload_root: str) -> dict:
    task = str(payload.get("task") or "").strip()
    paper_ids = payload.get("paper_ids") or []
    query = str(payload.get("query") or "").strip()
    provider_id = payload.get("provider_id") or None
    target_lang = str(payload.get("target_lang") or "zh-CN").strip() or "zh-CN"
    context_options = payload.get("context_options") or {}

    _validate_task(task, paper_ids, query)

    provider = pick_provider(db, user_id, provider_id)
    if not provider:
        raise AcademicAgentError("Please configure an LLM provider first.", 400)

    papers = _load_user_papers(db, user_id, paper_ids)
    per_paper_limit = 8000 if task == "paper_compare" else 14000

    contexts = []
    sources = []
    for index, paper in enumerate(papers, start=1):
        context, source = build_paper_context(
            db=db,
            user_id=user_id,
            paper=paper,
            upload_root=upload_root,
            context_options=context_options,
            max_chars=per_paper_limit,
        )
        contexts.append(f"===== Paper {index} =====\n{context}")
        sources.append(source)

    papers_context = "\n\n".join(contexts)
    messages = build_messages(task, query, papers_context, target_lang)
    answer = call_chat_completion(provider, messages, temperature=0.2, timeout=60)

    return {
        "ok": True,
        "task": task,
        "answer": answer,
        "sources": sources,
        "suggested_questions": SUGGESTED_QUESTIONS.get(task, SUGGESTED_QUESTIONS["custom_qa"]),
    }
