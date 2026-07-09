"""Testes da API admin com TestClient + SQLite in-memory (sem Docker)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from rabbitmq_event_router.api import create_app
from rabbitmq_event_router.db import Base


@pytest.fixture
def client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def session_factory() -> Session:
        return Session(engine)

    with TestClient(create_app(session_factory)) as test_client:
        yield test_client


def test_create_and_fetch_rule(client: TestClient) -> None:
    resp = client.post(
        "/rules",
        json={"event_type": "motion", "webhook_url": "https://a", "priority": 5},
    )
    assert resp.status_code == 201
    rule_id = resp.json()["id"]

    fetched = client.get(f"/rules/{rule_id}")
    assert fetched.status_code == 200
    assert fetched.json()["event_type"] == "motion"
    assert fetched.json()["priority"] == 5


def test_list_rules(client: TestClient) -> None:
    client.post("/rules", json={"event_type": "a", "webhook_url": "https://a"})
    client.post("/rules", json={"event_type": "b", "webhook_url": "https://b"})
    resp = client.get("/rules")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_missing_returns_404(client: TestClient) -> None:
    assert client.get("/rules/999").status_code == 404


def test_delete_rule(client: TestClient) -> None:
    rule_id = client.post("/rules", json={"event_type": "x", "webhook_url": "https://x"}).json()[
        "id"
    ]
    assert client.delete(f"/rules/{rule_id}").status_code == 204
    assert client.get(f"/rules/{rule_id}").status_code == 404


def test_create_invalid_payload_returns_422(client: TestClient) -> None:
    assert client.post("/rules", json={"event_type": ""}).status_code == 422
