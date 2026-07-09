"""Testes da lógica de roteamento (sem broker)."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from rabbitmq_event_router.consumer import parse_message, route_message
from rabbitmq_event_router.rules import RoutingRule


def test_parse_message() -> None:
    ev = parse_message(b'{"event_type": "motion", "payload": {"cam": 1}}')
    assert ev.event_type == "motion"
    assert ev.payload == {"cam": 1}


def test_route_message_orders_by_priority() -> None:
    rules = [
        RoutingRule(event_type="motion", webhook_url="https://a", priority=5),
        RoutingRule(event_type="motion", webhook_url="https://b", priority=1),
        RoutingRule(event_type="tamper", webhook_url="https://c"),
    ]
    assert route_message(b'{"event_type": "motion"}', rules) == ["https://a", "https://b"]


def test_route_message_no_match() -> None:
    assert route_message(b'{"event_type": "x"}', []) == []


def test_parse_invalid_json_raises() -> None:
    with pytest.raises(json.JSONDecodeError):
        parse_message(b"not json")


def test_parse_missing_event_type_raises() -> None:
    with pytest.raises(ValidationError):
        parse_message(b'{"payload": {}}')
