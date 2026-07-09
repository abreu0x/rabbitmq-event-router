"""Modelo de regras de roteamento e o matcher puro.

A lógica de roteamento vive separada do transporte (pika/RabbitMQ) e do
dispatch (httpx/webhook) — assim é testável sem broker nem rede, e é onde
entram property tests (hypothesis) nas próximas etapas.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RoutingRule(BaseModel):
    """Se `event_type` casar, o evento é roteado para `webhook_url`."""

    event_type: str = Field(min_length=1)
    webhook_url: str = Field(min_length=1)
    priority: int = 0
    enabled: bool = True


class Event(BaseModel):
    """Evento recebido da exchange RabbitMQ."""

    event_type: str = Field(min_length=1)
    payload: dict[str, object] = Field(default_factory=dict)


def match_rules(event: Event, rules: list[RoutingRule]) -> list[RoutingRule]:
    """Regras habilitadas cujo `event_type` casa com o evento.

    Ordena por `priority` decrescente (empate mantém ordem de inserção, já que
    `sorted` é estável) — determinístico, requisito pros property tests futuros.
    """
    matched = [r for r in rules if r.enabled and r.event_type == event.event_type]
    return sorted(matched, key=lambda r: r.priority, reverse=True)
