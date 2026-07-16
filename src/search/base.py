"""Common search protocol and helpers."""

from typing import Protocol

from paper_pipeline.models import PaperRecord


class SearchProvider(Protocol):
    name: str

    async def search(
        self, keyword: str, limit: int, years: tuple[int, int] | None
    ) -> list[PaperRecord]: ...


def allocate(total: int, sources: list[str]) -> dict[str, int]:
    """Deterministically distribute a per-keyword total across sources."""
    quotient, remainder = divmod(total, len(sources))
    return {source: quotient + (index < remainder) for index, source in enumerate(sources)}


def parse_years(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    pieces = value.split("-", 1)
    start = int(pieces[0])
    end = int(pieces[-1])
    if start > end or start < 1000 or end > 9999:
        raise ValueError("year must be YYYY or YYYY-YYYY")
    return start, end
