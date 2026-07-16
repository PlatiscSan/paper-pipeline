"""Identifier normalization, canonicalization, and merging."""

import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from paper_pipeline.models import PaperRecord

TRACKING = {"fbclid", "gclid", "mc_cid", "mc_eid"}


def normalize_doi(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value)
    return value.rstrip(".,;:)]}")


def normalize_pmid(value: str) -> str:
    match = re.search(r"\b(\d{1,12})\b", value)
    return match.group(1) if match else ""


def normalize_pmcid(value: str) -> str:
    match = re.search(r"\bPMC\s*(\d+)\b", value, re.I)
    return f"PMC{match.group(1)}" if match else ""


def normalize_arxiv_id(value: str) -> str:
    value = re.sub(r"^(?:arxiv:|https?://arxiv\.org/(?:abs|pdf)/)", "", value.strip(), flags=re.I)
    value = re.sub(r"\.pdf$", "", value, flags=re.I)
    match = re.match(r"(?:[a-z-]+/\d{7}|\d{4}\.\d{4,5})(?:v\d+)?", value, re.I)
    return match.group(0).lower() if match else ""


def normalize_url(value: str) -> str:
    if not value.strip():
        return ""
    parts = urlsplit(value.strip())
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in TRACKING
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def normalize_title(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split()).casefold()


def canonical_key(paper: PaperRecord) -> str:
    candidates = (
        ("doi", normalize_doi(paper.doi)),
        ("pmcid", normalize_pmcid(paper.pmcid)),
        ("pmid", normalize_pmid(paper.pmid)),
        ("arxiv", normalize_arxiv_id(paper.arxiv_id)),
        ("url", normalize_url(paper.url)),
        ("title", normalize_title(paper.title)),
    )
    for prefix, value in candidates:
        if value:
            return f"{prefix}:{value}"
    raise ValueError("Paper requires at least one identifier, URL, or title")


def merge_records(old: PaperRecord, new: PaperRecord) -> PaperRecord:
    """Merge metadata without resetting processing state."""
    result = PaperRecord(**{name: getattr(old, name) for name in old.__dataclass_fields__})
    for name in (
        "doi",
        "pmid",
        "pmcid",
        "arxiv_id",
        "pdf_url",
        "url",
        "source",
        "source_record_id",
    ):
        if not getattr(result, name) and getattr(new, name):
            setattr(result, name, getattr(new, name))
    if len(new.abstract) > len(result.abstract):
        result.abstract = new.abstract
    if not result.title or (result.title.endswith("...") and len(new.title) > len(result.title)):
        result.title = new.title
    result.year = result.year or new.year
    result.authors = list(dict.fromkeys([*result.authors, *new.authors]))
    result.keywords = list(dict.fromkeys([*result.keywords, *new.keywords]))
    return result
