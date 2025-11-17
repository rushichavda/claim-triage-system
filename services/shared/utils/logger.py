"""
Structured logging utilities using structlog.
Provides JSON logging for production observability.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor


def add_severity(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Add severity level for Google Cloud Logging compatibility.
    """
    if method_name == "warn":
        method_name = "warning"

    event_dict["severity"] = method_name.upper()
    return event_dict


def censor_phi_fields(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Censor potential PHI fields in log events.
    """
    phi_keywords = [
        "ssn",
        "social_security",
        "password",
        "secret",
        "token",
        "api_key",
        "dob",
        "date_of_birth",
    ]

    for key in list(event_dict.keys()):
        key_lower = key.lower()
        if any(keyword in key_lower for keyword in phi_keywords):
            event_dict[key] = "[REDACTED]"

    return event_dict


def setup_logging(log_level: str = "INFO", json_logs: bool = True) -> None:
    """
    Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Whether to output JSON format (for production)
    """
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_severity,
        censor_phi_fields,  # Censor PHI before logging
    ]

    if json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)
