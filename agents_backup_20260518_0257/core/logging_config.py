#!/usr/bin/env python3
"""
📝 STRUCTURED LOGGING — structlog + JSON output
Every log line is machine-readable, correlated, and searchable.
"""
import sys
import logging
import structlog
from structlog.processors import TimeStamper, JSONRenderer, StackInfoRenderer
from structlog.stdlib import LoggerFactory, add_log_level, filter_by_level
from pythonjsonlogger import jsonlogger

from core.config import settings

# ───────────────────────────────────────────────
# Configuration
# ───────────────────────────────────────────────

LOG_LEVEL = getattr(logging, settings.observability.log_level.upper(), logging.INFO)
JSON_LOGS = settings.observability.json_logs

# ───────────────────────────────────────────────
# Standard Library Logging Setup
# ───────────────────────────────────────────────

def configure_logging():
    """Configure both stdlib logging and structlog."""
    
    # 1. Standard library logging
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(LOG_LEVEL)
    
    if JSON_LOGS:
        # JSON formatter for production
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={"levelname": "level", "asctime": "timestamp"},
        )
    else:
        # Human-readable for development
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler
    if settings.observability.log_file:
        import os
        os.makedirs(os.path.dirname(settings.observability.log_file), exist_ok=True)
        file_handler = logging.FileHandler(settings.observability.log_file)
        file_handler.setLevel(LOG_LEVEL)
        if JSON_LOGS:
            file_handler.setFormatter(jsonlogger.JsonFormatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s"
            ))
        else:
            file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # 2. structlog configuration
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.ExtraAdder(),
    ]
    
    if JSON_LOGS:
        shared_processors.append(structlog.processors.JSONRenderer())
    else:
        shared_processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Suppress noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("aioredis").setLevel(logging.WARNING)


def get_logger(name: str):
    """Get a structured logger."""
    return structlog.get_logger(name)


class LogContext:
    """
    Context manager for adding correlation IDs and metadata to all logs.
    Usage:
        with LogContext(correlation_id="abc123", agent="scanner"):
            logger.info("Scan complete")
    """
    def __init__(self, **context):
        self.context = context
        self.token = None
    
    def __enter__(self):
        from structlog.contextvars import bind_contextvars
        bind_contextvars(**self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        from structlog.contextvars import unbind_contextvars
        unbind_contextvars(*self.context.keys())

# Auto-configure on import
configure_logging()
