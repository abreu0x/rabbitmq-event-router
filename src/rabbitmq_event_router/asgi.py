"""Entrypoint ASGI da API admin (usado por uvicorn / Docker Compose).

Lê `DATABASE_URL` do ambiente (default SQLite local). O schema é gerenciado por
Alembic (`alembic upgrade head`), não criado aqui.
"""

from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from rabbitmq_event_router.api import create_app
from rabbitmq_event_router.logging_config import configure_logging

configure_logging()

_engine: Engine = create_engine(os.environ.get("DATABASE_URL", "sqlite:///./router.db"))


def _session_factory() -> Session:
    return Session(_engine)


app = create_app(_session_factory)
