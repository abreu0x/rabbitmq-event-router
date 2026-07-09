"""Consumer/publisher pika — transporte RabbitMQ em volta do matcher puro.

A decisão de roteamento (`route_message`) é pura e testável sem broker. O loop
`consume` adiciona ack manual + prefetch + parada determinística, e envia a
mensagem para a **DLQ via DLX** quando o processamento falha (nack sem requeue).
`publish` e `consume` declaram a mesma topologia, então os argumentos batem.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence

import pika
from pika.adapters.blocking_connection import BlockingChannel

from rabbitmq_event_router.rules import Event, RoutingRule, match_rules


def parse_message(body: bytes) -> Event:
    """Decodifica o corpo JSON da mensagem em `Event`."""
    return Event.model_validate(json.loads(body))


def route_message(body: bytes, rules: Sequence[RoutingRule]) -> list[str]:
    """Parseia + casa regras, retornando as `webhook_url` destino (ordenadas)."""
    event = parse_message(body)
    return [rule.webhook_url for rule in match_rules(event, list(rules))]


def declare_topology(channel: BlockingChannel, queue: str) -> str:  # pragma: no cover
    """Declara a fila principal com dead-lettering + a DLQ. Retorna o nome da DLQ.

    Idempotente e com argumentos consistentes — chamada por publish e consume.
    """
    dlq = f"{queue}.dlq"
    channel.queue_declare(queue=dlq, durable=True)
    channel.queue_declare(
        queue=queue,
        durable=True,
        arguments={"x-dead-letter-exchange": "", "x-dead-letter-routing-key": dlq},
    )
    return dlq


def publish(url: str, queue: str, event: Event) -> None:  # pragma: no cover
    """Publica um `Event` (JSON, persistente) na `queue`."""
    conn = pika.BlockingConnection(pika.URLParameters(url))
    try:
        channel = conn.channel()
        declare_topology(channel, queue)
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

    Ack manual em sucesso; em exceção durante o processamento, `basic_nack`
    sem requeue — a mensagem vai para a DLQ via DLX. Para após `max_messages`
    ou `inactivity_timeout` sem mensagem. Retorna o total processado com sucesso.
    """
    conn = pika.BlockingConnection(pika.URLParameters(url))
    try:
        channel = conn.channel()
        declare_topology(channel, queue)
        channel.basic_qos(prefetch_count=prefetch)
        processed = 0
        for method, _props, body in channel.consume(queue, inactivity_timeout=inactivity_timeout):
            if method is None:  # inactivity timeout: nada mais na fila
                break
            try:
                event = parse_message(body)
                for rule in match_rules(event, list(rules)):
                    on_route(rule.webhook_url, event)
            except Exception:
                channel.basic_nack(method.delivery_tag, requeue=False)
            else:
                channel.basic_ack(method.delivery_tag)
                processed += 1
            if max_messages is not None and processed >= max_messages:
                break
        channel.cancel()
        return processed
    finally:
        conn.close()
