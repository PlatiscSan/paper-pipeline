"""Transport/domain models independent of persistence."""

from dataclasses import dataclass, field
from enum import StrEnum


class DownloadStatus(StrEnum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    SKIPPED = "skipped"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class ExtractionStatus(StrEnum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass(slots=True)
class PaperRecord:
    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    abstract: str = ""
    source: str = ""
    source_record_id: str = ""
    url: str = ""
    doi: str = ""
    pmid: str = ""
    pmcid: str = ""
    arxiv_id: str = ""
    pdf_url: str = ""
    keywords: list[str] = field(default_factory=list)
