"""Integration: publica e consome de um RabbitMQ efêmero (testcontainers).

Precisa de Docker. Marcado `integration` — o job de unit não roda isto.
"""

from __future__ import annotations

import pytest
from testcontainers.rabbitmq import RabbitMqContainer

from rabbitmq_event_router.consumer import consume, publish
from rabbitmq_event_router.rules import Event, RoutingRule

pytestmark = pytest.mark.integration


def test_publish_consume_and_route() -> None:
    with RabbitMqContainer("rabbitmq:3.13-management-alpine") as rabbit:
        params = rabbit.get_connection_params()
        url = f"amqp://guest:guest@{params.host}:{params.port}/"
        queue = "events"

        publish(url, queue, Event(event_type="motion", payload={"cam": 1}))
        publish(url, queue, Event(event_type="tamper"))

        rules = [RoutingRule(event_type="motion", webhook_url="https://alarme")]
        routed: list[str] = []

        processed = consume(
            url,
            queue,
            rules,
            lambda webhook, _event: routed.append(webhook),
            max_messages=2,
            inactivity_timeout=15.0,
        )

        assert processed == 2
        assert routed == ["https://alarme"]  # só 'motion' casa
