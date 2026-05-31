import re
from datetime import UTC, datetime


CITATION_FORMATS = {"gbt7714", "apa", "ieee"}
CITATION_METADATA_FIELDS = {
    "title",
    "authors",
    "year",
    "venue",
    "volume",
    "issue",
    "pages",
    "doi",
    "arxivId",
    "url",
    "citationText",
    "source",
}


def empty_citation_metadata(source: str = "") -> dict:
    return {
        "title": "",
        "authors": [],
        "year": "",
        "venue": "",
        "volume": "",
        "issue": "",
        "pages": "",
        "doi": "",
        "arxivId": "",
        "url": "",
        "citationText": "",
        "source": source,
    }


def normalize_citation_metadata(value) -> dict:
    data = empty_citation_metadata()
    if not isinstance(value, dict):
        return data

    for field in CITATION_METADATA_FIELDS:
        if field not in value:
            continue
        if field == "authors":
            data[field] = _normalize_authors(value.get(field))
        else:
            data[field] = str(value.get(field) or "").strip()
    return data


def extract_citation_metadata_from_pdf(pdf_path: str) -> dict:
    metadata = empty_citation_metadata("pdf-auto")
    warnings = []

    try:
        import fitz
    except ModuleNotFoundError:
        warnings.append("PyMuPDF is not installed.")
        metadata["warnings"] = warnings
        return metadata

    text = ""
    doc_meta = {}
    try:
        with fitz.open(pdf_path) as doc:
            doc_meta = doc.metadata or {}
            for page_index in range(min(3, doc.page_count)):
                text += "\n" + (doc[page_index].get_text("text") or "")
    except Exception as exc:
        warnings.append(f"PDF text extraction failed: {exc}")
        metadata["warnings"] = warnings
        return metadata

    normalized_text = _normalize_space(text)
    lines = _clean_lines(text)

    metadata["title"] = _pick_title(lines, doc_meta)
    metadata["doi"] = _pick_doi(normalized_text)
    metadata["arxivId"] = _pick_arxiv_id(normalized_text)
    metadata["authors"] = _pick_authors(lines, normalized_text, doc_meta, metadata["title"])
    metadata["year"] = _pick_year(normalized_text, doc_meta, metadata["arxivId"])
    metadata["url"] = _pick_url(normalized_text, metadata["doi"], metadata["arxivId"])
    metadata["citationText"] = _pick_raw_citation(lines, normalized_text)

    venue, volume, issue, pages = _pick_publication_parts(normalized_text)
    metadata["venue"] = venue
    metadata["volume"] = volume
    metadata["issue"] = issue
    metadata["pages"] = pages

    if metadata["arxivId"] and not metadata["venue"]:
        metadata["venue"] = f"arXiv:{metadata['arxivId']}"

    metadata["extractedAt"] = datetime.now(UTC).isoformat()
    if warnings:
        metadata["warnings"] = warnings
    return metadata


def format_paper_citation(paper: dict, citation_format: str, index: int) -> str:
    metadata = normalize_citation_metadata(paper.get("citationMetadata"))
    title = metadata["title"] or str(paper.get("title") or "Untitled").strip()
    authors = metadata["authors"] or _split_authors(str(paper.get("authors") or ""))
    venue = metadata["venue"] or str(paper.get("conference") or "").strip()
    year = metadata["year"] or _extract_year_from_text(str(paper.get("year") or "") + " " + venue) or "n.d."
    volume = metadata["volume"]
    issue = metadata["issue"]
    pages = metadata["pages"]
    doi = metadata["doi"]
    arxiv_id = metadata["arxivId"]
    url = metadata["url"]

    if citation_format == "gbt7714":
        raw = metadata["citationText"]
        if raw:
            return _ensure_number_prefix(raw, index)
        if arxiv_id:
            citation = f"[{index}] {_format_gbt_authors(authors)}. {title}[EB/OL]. arXiv:{arxiv_id}"
            if year and year != "n.d.":
                citation += f", {year}"
            return _with_period(citation)
        citation = f"[{index}] {_format_gbt_authors(authors)}. {title}[J]"
        tail = _format_gbt_tail(venue, year, volume, issue, pages)
        if tail:
            citation += f". {tail}"
        if doi:
            citation += f". DOI: {doi}"
        return _with_period(citation)

    if citation_format == "ieee":
        if arxiv_id:
            citation = f"[{index}] {_format_ieee_authors(authors)}, \"{title},\" arXiv preprint arXiv:{arxiv_id}"
            if year and year != "n.d.":
                citation += f", {year}"
            return _with_period(citation)
        citation = f"[{index}] {_format_ieee_authors(authors)}, \"{title}\""
        tail = _format_ieee_tail(venue, year, volume, issue, pages)
        if tail:
            citation += f", {tail}"
        if doi:
            citation += f", doi: {doi}"
        return _with_period(citation)

    if arxiv_id:
        arxiv_url = url or f"https://arxiv.org/abs/{_strip_arxiv_version(arxiv_id)}"
        citation = f"[{index}] {_format_apa_authors(authors)} ({year}). {_with_period(title)} arXiv. {arxiv_url}"
        return _with_period(citation)

    citation = f"[{index}] {_format_apa_authors(authors)} ({year}). {_with_period(title)}"
    tail = _format_apa_tail(venue, volume, issue, pages)
    if tail:
        citation += f" {_with_period(tail)}"
    if doi:
        citation += f" https://doi.org/{doi}"
    return _with_period(citation)


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _clean_lines(text: str) -> list[str]:
    lines = []
    for raw in (text or "").splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if line:
            lines.append(line)
    return lines


def _normalize_authors(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return _split_authors(str(value or ""))


def _split_authors(authors: str) -> list[str]:
    raw = str(authors or "").strip()
    if not raw:
        return []
    raw = re.sub(r"\bet\s+al\.?\b", "", raw, flags=re.IGNORECASE)
    normalized = raw
    for old, new in [("；", ";"), ("，", ","), ("、", ","), (" and ", ","), (" & ", ",")]:
        normalized = normalized.replace(old, new)
    parts = normalized.split(";") if ";" in normalized else normalized.split(",")
    return [part.strip(" .;，,") for part in parts if part.strip(" .;，,")]


def _pick_title(lines: list[str], doc_meta: dict) -> str:
    for line in lines[:20]:
        match = re.search(r"^(?:题目|标题)\s*[:：]\s*(.+)$", line)
        if match:
            return match.group(1).strip()

    title_meta = str(doc_meta.get("title") or "").strip()
    if title_meta and len(title_meta) > 6 and not _looks_like_tool_title(title_meta):
        return title_meta

    candidates = [
        line for line in lines[:18]
        if 8 <= len(line) <= 180
        and not re.search(r"^(arXiv|doi|abstract|keywords|摘要|关键词)\b", line, flags=re.IGNORECASE)
        and not re.search(r"^\d+$", line)
        and not re.search(r"copyright|permission|reproduce|journalistic|scholarly works|licensed under|creative commons", line, flags=re.IGNORECASE)
        and not re.search(r"^\[?\d+\]?", line)
    ]
    if not candidates:
        return ""

    for candidate in candidates[:10]:
        if 8 <= len(candidate) <= 90 and not re.search(r"[,.;:]\s", candidate):
            return candidate
    return max(candidates[:6], key=len)


def _looks_like_tool_title(title: str) -> bool:
    return bool(re.search(r"microsoft|word|powerpoint|latex|arxiv", title, flags=re.IGNORECASE))


def _pick_authors(lines: list[str], text: str, doc_meta: dict, title: str) -> list[str]:
    for line in lines[:30]:
        match = re.search(r"^作者\s*[:：]\s*(.+)$", line)
        if match:
            return _split_authors(match.group(1))

    author_meta = str(doc_meta.get("author") or "").strip()
    if author_meta:
        authors = _split_authors(author_meta)
        if authors:
            return authors

    if title:
        title_index = next((idx for idx, line in enumerate(lines[:20]) if line.strip() == title.strip()), -1)
        if title_index >= 0:
            names = []
            for line in lines[title_index + 1: title_index + 28]:
                if re.search(r"^(abstract|摘要|keywords|关键词)\b", line, flags=re.IGNORECASE):
                    break
                if "@" in line or re.search(r"\b(google|university|research|institute|department|laboratory|brain)\b", line, flags=re.IGNORECASE):
                    continue
                cleaned = re.sub(r"[*∗†‡§]+", "", line).strip()
                if re.search(r"\b[A-Z][A-Za-zŁł]+(?:\s+[A-Z]\.)?\s+[A-Z][A-Za-zŁł]+\b", cleaned) and len(cleaned) < 80:
                    names.append(cleaned)
            if names:
                return names

    for idx, line in enumerate(lines[:12]):
        if title and line.strip() == title.strip():
            continue
        if re.search(r"^(abstract|摘要|keywords|关键词)\b", line, flags=re.IGNORECASE):
            break
        if re.search(r"copyright|permission|reproduce|journalistic|scholarly works|licensed under|creative commons", line, flags=re.IGNORECASE):
            continue
        if re.search(r"\b[A-Z][a-z]+(?:\s+[A-Z]\.)?\s+[A-Z][a-z]+\b", line) and len(line) < 180:
            return _split_authors(line)
        if idx > 0 and len(line) < 120 and re.search(r"[,，、;；]", line):
            parts = _split_authors(line)
            if len(parts) >= 2:
                return parts

    return []


def _pick_year(text: str, doc_meta: dict, arxiv_id: str = "") -> str:
    if arxiv_id:
        match = re.match(r"(?P<yy>\d{2})(?P<month>\d{2})\.", arxiv_id)
        if match:
            yy = int(match.group("yy"))
            return str(2000 + yy if yy < 50 else 1900 + yy)

    arxiv_line = re.search(r"arXiv\s*:\s*\d{4}\.\d{4,5}(?:v\d+)?.{0,80}?\b((?:19|20)\d{2})\b", text or "", flags=re.IGNORECASE)
    if arxiv_line:
        return arxiv_line.group(1)

    for value in [doc_meta.get("creationDate"), doc_meta.get("modDate"), text]:
        year = _extract_year_from_text(str(value or ""))
        if year:
            return year
    return ""


def _extract_year_from_text(text: str) -> str:
    match = re.search(r"\b(19|20)\d{2}\b", text or "")
    return match.group(0) if match else ""


def _pick_doi(text: str) -> str:
    match = re.search(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", text or "", flags=re.IGNORECASE)
    return match.group(0).rstrip(".") if match else ""


def _pick_arxiv_id(text: str) -> str:
    match = re.search(r"arXiv\s*:\s*(\d{4}\.\d{4,5}(?:v\d+)?)", text or "", flags=re.IGNORECASE)
    return match.group(1) if match else ""


def _strip_arxiv_version(arxiv_id: str) -> str:
    return re.sub(r"v\d+$", "", arxiv_id or "")


def _pick_url(text: str, doi: str, arxiv_id: str) -> str:
    if doi:
        return f"https://doi.org/{doi}"
    if arxiv_id:
        return f"https://arxiv.org/abs/{_strip_arxiv_version(arxiv_id)}"
    match = re.search(r"https?://[^\s)\]]+", text or "", flags=re.IGNORECASE)
    return match.group(0).rstrip(".") if match else ""


def _pick_raw_citation(lines: list[str], text: str) -> str:
    for idx, line in enumerate(lines):
        match = re.search(r"^(?:引用格式|参考文献格式|建议引用)\s*[:：]\s*(.*)$", line)
        if match:
            tail = match.group(1).strip()
            if tail:
                return tail
            return " ".join(lines[idx + 1: idx + 4]).strip()
    match = re.search(r"(?:引用格式|参考文献格式|建议引用)\s*[:：]\s*(.{20,280})", text or "")
    return match.group(1).strip() if match else ""


def _pick_publication_parts(text: str) -> tuple[str, str, str, str]:
    volume = ""
    issue = ""
    pages = ""
    venue = ""

    match = re.search(
        r"(?P<venue>[\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z\s&.,·-]{2,80})[,，]\s*"
        r"(?P<year>(?:19|20)\d{2})[,，]\s*(?P<volume>\d+)\s*\(\s*(?P<issue>\d+)\s*\)\s*[:：]\s*(?P<pages>[\w\-–—]+)",
        text or "",
    )
    if match:
        return (
            match.group("venue").strip(" ,，."),
            match.group("volume"),
            match.group("issue"),
            match.group("pages"),
        )

    match = re.search(r"\bvol\.?\s*(?P<volume>\d+)", text or "", flags=re.IGNORECASE)
    if match:
        volume = match.group("volume")
    match = re.search(r"\bno\.?\s*(?P<issue>\d+)", text or "", flags=re.IGNORECASE)
    if match:
        issue = match.group("issue")
    match = re.search(r"\bpp\.?\s*(?P<pages>[\w\-–—]+)", text or "", flags=re.IGNORECASE)
    if match:
        pages = match.group("pages")
    return venue, volume, issue, pages


def _ensure_number_prefix(citation: str, index: int) -> str:
    clean = str(citation or "").strip()
    clean = re.sub(r"^\[\d+\]\s*", "", clean)
    return f"[{index}] {clean}"


def _with_period(value: str) -> str:
    clean = str(value or "").strip()
    if not clean:
        return ""
    return clean if clean.endswith((".", "!", "?", "。")) else f"{clean}."


def _format_gbt_authors(authors: list[str]) -> str:
    if not authors:
        return "佚名"
    if len(authors) > 3:
        return f"{', '.join(authors[:3])}, 等"
    return ", ".join(authors)


def _format_apa_authors(authors: list[str]) -> str:
    if not authors:
        return "Unknown author"
    if len(authors) > 3:
        return f"{', '.join(authors[:3])}, et al."
    if len(authors) == 1:
        return authors[0]
    if len(authors) == 2:
        return f"{authors[0]} & {authors[1]}"
    return f"{', '.join(authors[:-1])}, & {authors[-1]}"


def _format_ieee_authors(authors: list[str]) -> str:
    if not authors:
        return "Unknown author"
    names = [_to_initial_name(author) for author in authors[:3]]
    if len(authors) > 3:
        return f"{', '.join(names)}, et al."
    if len(names) == 1:
        return names[0]
    return f"{', '.join(names[:-1])}, and {names[-1]}"


def _to_initial_name(name: str) -> str:
    clean = str(name or "").strip()
    if any("\u4e00" <= char <= "\u9fff" for char in clean):
        return clean
    parts = [part for part in clean.replace(".", " ").split() if part]
    if len(parts) <= 1:
        return clean
    family = parts[-1]
    initials = " ".join(f"{part[0].upper()}." for part in parts[:-1])
    return f"{initials} {family}".strip()


def _format_gbt_tail(venue: str, year: str, volume: str, issue: str, pages: str) -> str:
    parts = []
    if venue:
        parts.append(venue)
    if year and year != "n.d.":
        parts.append(year)
    if volume:
        vol = volume + (f"({issue})" if issue else "")
        parts.append(vol)
    tail = ", ".join(parts)
    if pages:
        tail += f": {pages}" if tail else pages
    return tail


def _format_apa_tail(venue: str, volume: str, issue: str, pages: str) -> str:
    tail = venue
    if volume:
        tail += f", {volume}" if tail else volume
        if issue:
            tail += f"({issue})"
    if pages:
        tail += f", {pages}" if tail else pages
    return tail


def _format_ieee_tail(venue: str, year: str, volume: str, issue: str, pages: str) -> str:
    parts = []
    if venue:
        parts.append(venue)
    if volume:
        parts.append(f"vol. {volume}")
    if issue:
        parts.append(f"no. {issue}")
    if pages:
        parts.append(f"pp. {pages}")
    if year and year != "n.d.":
        parts.append(year)
    return ", ".join(parts)
