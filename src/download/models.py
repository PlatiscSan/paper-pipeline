"""Download value objects."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Candidate:
    url: str
    method: str


@dataclass(slots=True)
class DownloadResult:
    path: str = ""
    url: str = ""
    method: str = ""
    bytes: int = 0
    status: str = "failed"
    error_code: str = ""
    error_message: str = ""
