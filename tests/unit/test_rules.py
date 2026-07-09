"""Testes unitários do matcher de regras (sem broker, sem rede)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from rabbitmq_event_router.rules import Event, RoutingRule, match_rules


def test_match_returns_only_enabled_matching() -> None:
    rules = [
        RoutingRule(event_type="motion", webhook_url="https://a"),
        RoutingRule(event_type="motion", webhook_url="https://b", enabled=False),
        RoutingRule(event_type="tamper", webhook_url="https://c"),
    ]
    matched = match_rules(Event(event_type="motion"), rules)
    assert [r.webhook_url for r in matched] == ["https://a"]


def test_match_orders_by_priority_desc() -> None:
    rules = [
        RoutingRule(event_type="e", webhook_url="low", priority=1),
        RoutingRule(event_type="e", webhook_url="high", priority=10),
        RoutingRule(event_type="e", webhook_url="mid", priority=5),
    ]
    matched = match_rules(Event(event_type="e"), rules)
    assert [r.webhook_url for r in matched] == ["high", "mid", "low"]


def test_no_rules_returns_empty() -> None:
    assert match_rules(Event(event_type="x"), []) == []


def test_rule_defaults() -> None:
    rule = RoutingRule(event_type="e", webhook_url="u")
    assert rule.enabled is True
    assert rule.priority == 0


def test_empty_event_type_rejected() -> None:
    with pytest.raises(ValidationError):
        Event(event_type="")
