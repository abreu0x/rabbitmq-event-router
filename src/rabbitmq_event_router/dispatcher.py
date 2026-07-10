"""Dispatch de webhooks via httpx com retry + backoff exponencial.

A política de backoff é pura (testável isolada); o `dispatch` recebe o cliente
httpx e a função de sleep por injeção — assim os testes usam `respx` (mock) e
sleep no-op, sem rede nem espera real. `make_on_route` adapta o `dispatch`
(sinaliza falha por retorno) ao contrato do consumer (sinaliza por exceção).
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable

import httpx

from rabbitmq_event_router.logging_config import get_logger
from rabbitmq_event_router.rules import Event

logger = get_logger(__name__)


class DispatchFailedError(RuntimeError):
    """`dispatch` esgotou as retentativas sem uma resposta 2xx."""


def backoff_delays(
    retries: int,
    *,
    base: float = 0.5,
    factor: float = 2.0,
    max_delay: float = 30.0,
    jitter: float = 0.0,
) -> list[float]:
    """Delays (s) entre as `retries` retentativas: `base * factor**i`, capado em `max_delay`.

    `jitter` (0..1) espalha cada delay em ±jitter para evitar retentativas
    sincronizadas (thundering herd) quando muitas mensagens falham contra o
    mesmo destino. `jitter=0` (default) é determinístico.
    """
    if retries < 0:
        raise ValueError("retries deve ser >= 0")
    delays = [min(base * (factor**i), max_delay) for i in range(retries)]
    if jitter:
        # RNG não-cripto: só espalha o instante de retry, sem valor de segurança.
        delays = [d * (1.0 + random.uniform(-jitter, jitter)) for d in delays]  # nosec B311
    return delays


def dispatch(
    event: Event,
    webhook_url: str,
    *,
    client: httpx.Client,
    retries: int = 3,
    base: float = 0.5,
    jitter: float = 0.1,
    sleep: Callable[[float], None] = time.sleep,
) -> bool:
    """POST do evento no webhook, com retry + backoff. `True` se resposta 2xx.

    Faz `retries + 1` tentativas. Erros de transporte (`httpx.HTTPError`) e
    respostas não-2xx disparam retentativa até esgotar; cada falha é logada
    (structlog), então uma entrega problemática nunca fica invisível.
    """
    delays = backoff_delays(retries, base=base, jitter=jitter)
    for attempt in range(retries + 1):
        try:
            response = client.post(webhook_url, json=event.model_dump())
            if response.is_success:
                return True
            logger.warning(
                "webhook_non_2xx", url=webhook_url, attempt=attempt, status=response.status_code
            )
        except httpx.HTTPError as exc:
            logger.warning(
                "webhook_transport_error", url=webhook_url, attempt=attempt, error=str(exc)
            )
        if attempt < len(delays):
            sleep(delays[attempt])
    logger.warning("webhook_giving_up", url=webhook_url, attempts=retries + 1)
    return False


def make_on_route(
    client: httpx.Client,
    *,
    retries: int = 3,
    base: float = 0.5,
    jitter: float = 0.1,
    sleep: Callable[[float], None] = time.sleep,
) -> Callable[[str, Event], None]:
    """Adapta `dispatch` (retorna bool) ao contrato `on_route` do consumer.

    O `consume` só manda pra DLQ em **exceção**; `dispatch` sinaliza falha por
    retorno `False`. Sem essa ponte, ligar os dois direto engoliria entregas
    falhas (ack silencioso, evento perdido). Aqui, falha esgotada vira
    `DispatchFailedError`, então a mensagem é nack'd pra DLQ como esperado.
    """

    def on_route(webhook_url: str, event: Event) -> None:
        ok = dispatch(
            event,
            webhook_url,
            client=client,
            retries=retries,
            base=base,
            jitter=jitter,
            sleep=sleep,
        )
        if not ok:
            raise DispatchFailedError(f"webhook {webhook_url} falhou após {retries + 1} tentativas")

    return on_route
