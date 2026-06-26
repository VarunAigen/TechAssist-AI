"""Structured logging configuration for the RAG Knowledge Assistant."""

import logging
import json
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record):
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        for key in ("tenant_id", "user_id", "endpoint", "duration_ms", "ip_address"):
            if hasattr(record, key):
                log_data[key] = getattr(record, key)

        # Add exception info if present
        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class ReadableFormatter(logging.Formatter):
    """Human-readable log formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, "")
        timestamp = datetime.now().strftime("%H:%M:%S")
        level = f"{color}{record.levelname:>8}{self.RESET}"
        name = record.name.split(".")[-1]  # Short logger name
        msg = record.getMessage()

        extras = []
        for key in ("tenant_id", "user_id", "endpoint", "duration_ms"):
            if hasattr(record, key):
                extras.append(f"{key}={getattr(record, key)}")
        extra_str = f" [{', '.join(extras)}]" if extras else ""

        formatted = f"{timestamp} {level} {name}: {msg}{extra_str}"

        if record.exc_info and record.exc_info[0]:
            formatted += "\n" + self.formatException(record.exc_info)

        return formatted


def setup_logging(environment: str = "dev"):
    """Configure logging for the application.
    
    Args:
        environment: "dev" for readable output, "prod" for JSON output.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    if environment == "prod":
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(ReadableFormatter())

    root_logger.addHandler(console_handler)

    # Quieten noisy libraries
    for noisy in ("chromadb", "httpx", "httpcore", "sentence_transformers",
                   "urllib3", "asyncio", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        f"Logging configured (environment={environment})"
    )
