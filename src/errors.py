"""Structured pipeline errors."""

from enum import StrEnum


class ErrorCode(StrEnum):
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    REMOTE_FORBIDDEN = "REMOTE_FORBIDDEN"
    REMOTE_NOT_FOUND = "REMOTE_NOT_FOUND"
    NO_OPEN_ACCESS_PDF = "NO_OPEN_ACCESS_PDF"
    INVALID_PDF = "INVALID_PDF"
    HTML_INSTEAD_OF_PDF = "HTML_INSTEAD_OF_PDF"
    PDF_TEXT_EMPTY = "PDF_TEXT_EMPTY"
    AI_UNSUPPORTED_FEATURE = "AI_UNSUPPORTED_FEATURE"
    AI_INVALID_JSON = "AI_INVALID_JSON"
    AI_SCHEMA_MISMATCH = "AI_SCHEMA_MISMATCH"
    AI_TIMEOUT = "AI_TIMEOUT"
    CONFIG_INVALID = "CONFIG_INVALID"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    DATABASE_ERROR = "DATABASE_ERROR"


class PipelineError(Exception):
    """An expected error with a stable machine-readable code."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
