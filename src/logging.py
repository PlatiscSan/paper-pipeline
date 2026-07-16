"""Safe console/file logging configuration."""

import json
import logging
from pathlib import Path


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "time": self.formatTime(record),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            },
            ensure_ascii=False,
        )


def configure(
    verbose: bool = False,
    quiet: bool = False,
    log_file: Path | None = None,
    json_logs: bool = False,
) -> None:
    level = logging.WARNING if quiet else logging.DEBUG if verbose else logging.INFO
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    formatter: logging.Formatter = (
        JsonFormatter() if json_logs else logging.Formatter("%(levelname)s %(message)s")
    )
    for handler in handlers:
        handler.setFormatter(formatter)
    logging.basicConfig(level=level, handlers=handlers, force=True)
