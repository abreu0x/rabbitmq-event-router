"""Smoke test do entrypoint ASGI (não toca no banco)."""

from __future__ import annotations

from rabbitmq_event_router.asgi import app


def test_asgi_app_exposes_rules_api() -> None:
    assert app.title == "rabbitmq-event-router admin"
    assert "/rules" in app.openapi()["paths"]
