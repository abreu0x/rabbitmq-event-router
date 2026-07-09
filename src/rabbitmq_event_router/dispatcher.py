"""Dispatch de webhooks via httpx com retry + backoff exponencial.

A política de backoff é pura (testável isolada); o `dispatch` recebe o cliente
httpx e a função de sleep por injeção — assim os testes usam `respx` (mock) e
sleep no-op, sem rede nem espera real.
"""

from __future__ import annotations

import time
from collections.abc import Callable

import httpx

from rabbitmq_event_router.rules import Event


def backoff_delays(
    retries: int,
    *,
    base: float = 0.5,
    factor: float = 2.0,
    max_delay: float = 30.0,
) -> list[float]:
    """Delays (s) entre as `retries` retentativas: `base * factor**i`, capado em `max_delay`."""
    if retries < 0:
        raise ValueError("retries deve ser >= 0")
    return [min(base * (factor**i), max_delay) for i in range(retries)]


def dispatch(
    event: Event,
    webhook_url: str,
    *,
    client: httpx.Client,
    retries: int = 3,
    base: float = 0.5,
    sleep: Callable[[float], None] = time.sleep,
) -> bool:
    """POST do evento no webhook, com retry + backoff. `True` se resposta 2xx.

    Faz `retries + 1` tentativas. Erros de transporte (`httpx.HTTPError`) e
    respostas não-2xx disparam retentativa até esgotar.
    """
    delays = backoff_delays(retries, base=base)
    for attempt in range(retries + 1):
        try:
            response = client.post(webhook_url, json=event.model_dump())
            if response.is_success:
                return True
        except httpx.HTTPError:
            pass
        if attempt < len(delays):
            sleep(delays[attempt])
    return False
