"""Aplica a migration Alembic num SQLite temporário e valida o schema."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def _config(db_url: str) -> Config:
    cfg = Config()
    migrations = Path(__file__).resolve().parents[2] / "migrations"
    cfg.set_main_option("script_location", str(migrations))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def test_upgrade_creates_routing_rules(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    command.upgrade(_config(db_url), "head")

    inspector = inspect(create_engine(db_url))
    assert "routing_rules" in inspector.get_table_names()
    columns = {col["name"] for col in inspector.get_columns("routing_rules")}
    assert {"id", "event_type", "webhook_url", "priority", "enabled"} <= columns


def test_downgrade_removes_table(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    cfg = _config(db_url)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")

    inspector = inspect(create_engine(db_url))
    assert "routing_rules" not in inspector.get_table_names()
