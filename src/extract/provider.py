"""Provider abstraction."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(slots=True)
class AIResult:
    data: dict[str, Any]
    response_id: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


class AIProvider(Protocol):
    async def extract_text(
        self, text: str, schema: dict[str, Any], merge: bool = False
    ) -> AIResult: ...
    async def extract_file(self, path: Path, schema: dict[str, Any]) -> AIResult: ...
