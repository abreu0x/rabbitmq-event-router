"""Testes da persistência com SQLite in-memory (sem Docker)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from rabbitmq_event_router.db import Base, RoutingRuleORM, load_rules


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as sess:
        yield sess


def test_load_rules_filters_disabled_and_converts(session: Session) -> None:
    session.add_all(
        [
            RoutingRuleORM(event_type="motion", webhook_url="https://a", priority=5, enabled=True),
            RoutingRuleORM(event_type="motion", webhook_url="https://b", enabled=False),
            RoutingRuleORM(event_type="tamper", webhook_url="https://c"),
        ]
    )
    session.commit()

    rules = load_rules(session)

    assert {r.webhook_url for r in rules} == {"https://a", "https://c"}
    motion = next(r for r in rules if r.event_type == "motion")
    assert motion.priority == 5
    assert motion.enabled is True


def test_load_rules_empty(session: Session) -> None:
    assert load_rules(session) == []


def test_orm_defaults(session: Session) -> None:
    session.add(RoutingRuleORM(event_type="e", webhook_url="https://u"))
    session.commit()
    rule = load_rules(session)[0]
    assert rule.priority == 0
    assert rule.enabled is True
