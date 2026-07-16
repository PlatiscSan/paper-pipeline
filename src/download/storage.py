"""Portable and collision-resistant PDF storage paths."""

import hashlib
import re
import unicodedata
from pathlib import Path

from paper_pipeline.db.models import Paper


def safe_filename(value: str, max_length: int = 100) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")
    value = re.sub(r"\s+", "-", value)
    if value.upper() in {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }:
        value = f"_{value}"
    return value[:max_length].rstrip(" .-") or "untitled"


def destination(root: Path, paper: Paper) -> Path:
    stable = paper.doi or paper.pmcid or paper.pmid or paper.arxiv_id or str(paper.id)
    digest = hashlib.sha256(stable.encode()).hexdigest()[:12]
    return (
        root
        / safe_filename(paper.source or "other", 30)
        / str(paper.year or "unknown")
        / (f"{safe_filename(paper.title)}__{digest}.pdf")
    )


def is_pdf(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(5) == b"%PDF-"
    except OSError:
        return False
