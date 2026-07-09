"""Configuração de logging estruturado (structlog → JSON)."""

from __future__ import annotations

import structlog


def configure_logging() -> None:
    """Configura structlog para emitir JSON com timestamp ISO e nível."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Retorna um logger structlog vinculado ao `name`."""
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger
