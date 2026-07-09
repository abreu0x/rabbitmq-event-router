"""Testa que o logging estruturado emite JSON com os campos esperados."""

from __future__ import annotations

import json

import pytest

from rabbitmq_event_router.logging_config import configure_logging, get_logger


def test_logger_emits_json(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging()
    log = get_logger("test")
    log.info("evento_roteado", webhook="https://a", event_type="motion")

    line = capsys.readouterr().out.strip().splitlines()[-1]
    data = json.loads(line)
    assert data["event"] == "evento_roteado"
    assert data["webhook"] == "https://a"
    assert data["level"] == "info"
    assert "timestamp" in data
