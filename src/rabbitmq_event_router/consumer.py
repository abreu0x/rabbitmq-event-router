"""Consumer/publisher pika — transporte RabbitMQ em volta do matcher puro.

A decisão de roteamento (`route_message`) é pura e testável sem broker; o loop
`consume` só adiciona ack manual + prefetch + parada determinística (útil em
teste). A publicação existe pra fechar o ciclo no integration test.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence

import pika

from rabbitmq_event_router.rules import Event, RoutingRule, match_rules


def parse_message(body: bytes) -> Event:
    """Decodifica o corpo JSON da mensagem em `Event`."""
    return Event.model_validate(json.loads(body))


def route_message(body: bytes, rules: Sequence[RoutingRule]) -> list[str]:
    """Parseia + casa regras, retornando as `webhook_url` destino (ordenadas)."""
    event = parse_message(body)
    return [rule.webhook_url for rule in match_rules(event, list(rules))]


def publish(url: str, queue: str, event: Event) -> None:  # pragma: no cover
    """Publica um `Event` (JSON, persistente) na `queue` default exchange.

    I/O de broker — exercitado pelo integration test (testcontainers), não por
    cobertura de linha do job de unit.
    """
    conn = pika.BlockingConnection(pika.URLParameters(url))
    try:
        channel = conn.channel()
        channel.queue_declare(queue=queue, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=queue,
            body=event.model_dump_json().encode(),
            properties=pika.BasicProperties(delivery_mode=2),
        )
    finally:
        conn.close()


def consume(
    url: str,
    queue: str,
    rules: Sequence[RoutingRule],
    on_route: Callable[[str, Event], None],
    *,
    prefetch: int = 10,
    max_messages: int | None = None,
    inactivity_timeout: float = 5.0,
) -> int:  # pragma: no cover
    """Consome de `queue`, roteia por `rules`, chama `on_route(webhook_url, event)`.

    Ack manual por mensagem. Para após `max_messages` ou ao ficar
    `inactivity_timeout` segundos sem mensagem. Retorna o total processado.
    I/O de broker — exercitado pelo integration test (testcontainers).
    """
    conn = pika.BlockingConnection(pika.URLParameters(url))
    try:
        channel = conn.channel()
        channel.queue_declare(queue=queue, durable=True)
        channel.basic_qos(prefetch_count=prefetch)
        processed = 0
        for method, _props, body in channel.consume(queue, inactivity_timeout=inactivity_timeout):
            if method is None:  # inactivity timeout: nada mais na fila
                break
            event = parse_message(body)
            for rule in match_rules(event, list(rules)):
                on_route(rule.webhook_url, event)
            channel.basic_ack(method.delivery_tag)
            processed += 1
            if max_messages is not None and processed >= max_messages:
                break
        channel.cancel()
        return processed
    finally:
        conn.close()
