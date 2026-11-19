"""Structured logging configuration for application.

Implements structured logging according to AGENTS.md §11 using Python standard library
logging to maintain strict compliance with dependency restrictions (AGENTS.md §7).
"""

from datetime import datetime, timezone
import json
import logging
import sys

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """Formats log records as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record into a JSON string."""
        log_entry: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Include custom details dictionary if passed in extra={'details': ...}
        if hasattr(record, "details") and isinstance(record.details, dict):
            log_entry["details"] = record.details

        return json.dumps(log_entry)


def setup_logging(
    log_level: str | None = None,
    use_json: bool = False,
) -> None:
    """Configure structured logging for the application.

    Args:
        log_level: Desired log level string (DEBUG, INFO, WARN, ERROR). Defaults to settings.log_level.
        use_json: If True, formats output as JSON lines; otherwise standard human-readable format.
    """
    level_name = log_level or settings.log_level
    numeric_level = getattr(logging, level_name.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing stream handlers to avoid duplicate output
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler):
            root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    if use_json:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root_logger.addHandler(handler)
