"""Testes do dispatcher com respx (mock httpx) — sem rede, sem espera real."""

from __future__ import annotations

import httpx
import pytest
import respx
from structlog.testing import capture_logs

from rabbitmq_event_router.dispatcher import (
    DispatchFailedError,
    backoff_delays,
    dispatch,
    make_on_route,
)
from rabbitmq_event_router.rules import Event

EVENT = Event(event_type="motion")


def _no_sleep(_delay: float) -> None:
    """Sleep no-op para os testes não esperarem o backoff real."""


def test_backoff_delays_exponential() -> None:
    assert backoff_delays(3, base=1.0, factor=2.0) == [1.0, 2.0, 4.0]


def test_backoff_delays_capped() -> None:
    assert backoff_delays(4, base=10.0, factor=10.0, max_delay=30.0) == [10.0, 30.0, 30.0, 30.0]


def test_backoff_delays_zero() -> None:
    assert backoff_delays(0) == []


def test_backoff_delays_jitter_within_bounds() -> None:
    plain = backoff_delays(5, base=1.0, factor=2.0, max_delay=100.0)
    jittered = backoff_delays(5, base=1.0, factor=2.0, max_delay=100.0, jitter=0.2)
    assert len(jittered) == len(plain)
    for d, j in zip(plain, jittered, strict=True):
        assert d * 0.8 <= j <= d * 1.2


def test_backoff_delays_negative_rejected() -> None:
    with pytest.raises(ValueError, match="retries"):
        backoff_delays(-1)


@respx.mock
def test_dispatch_success_no_retry() -> None:
    route = respx.post("https://hook").mock(return_value=httpx.Response(200))
    with httpx.Client() as client:
        assert dispatch(EVENT, "https://hook", client=client, sleep=_no_sleep) is True
    assert route.call_count == 1


@respx.mock
def test_dispatch_retries_then_gives_up() -> None:
    route = respx.post("https://hook").mock(return_value=httpx.Response(500))
    with httpx.Client() as client:
        ok = dispatch(EVENT, "https://hook", client=client, retries=2, sleep=_no_sleep)
    assert ok is False
    assert route.call_count == 3  # tentativa inicial + 2 retries


@respx.mock
def test_dispatch_recovers_on_retry() -> None:
    route = respx.post("https://hook").mock(side_effect=[httpx.Response(503), httpx.Response(200)])
    with httpx.Client() as client:
        assert dispatch(EVENT, "https://hook", client=client, retries=3, sleep=_no_sleep) is True
    assert route.call_count == 2


@respx.mock
def test_dispatch_handles_transport_error() -> None:
    route = respx.post("https://hook").mock(side_effect=httpx.ConnectError("boom"))
    with httpx.Client() as client:
        ok = dispatch(EVENT, "https://hook", client=client, retries=1, sleep=_no_sleep)
    assert ok is False
    assert route.call_count == 2


@respx.mock
def test_dispatch_logs_each_failure_and_giving_up() -> None:
    respx.post("https://hook").mock(return_value=httpx.Response(500))
    with capture_logs() as logs, httpx.Client() as client:
        dispatch(EVENT, "https://hook", client=client, retries=1, jitter=0.0, sleep=_no_sleep)
    events = [e["event"] for e in logs]
    assert "webhook_non_2xx" in events
    assert "webhook_giving_up" in events


@respx.mock
def test_make_on_route_raises_on_exhausted_retries() -> None:
    # A ponte transforma o retorno False do dispatch em exceção → consumer manda à DLQ.
    respx.post("https://hook").mock(return_value=httpx.Response(500))
    with httpx.Client() as client:
        on_route = make_on_route(client, retries=0, jitter=0.0, sleep=_no_sleep)
        with pytest.raises(DispatchFailedError, match="falhou"):
            on_route("https://hook", EVENT)


@respx.mock
def test_make_on_route_silent_on_success() -> None:
    respx.post("https://hook").mock(return_value=httpx.Response(200))
    with httpx.Client() as client:
        on_route = make_on_route(client, jitter=0.0, sleep=_no_sleep)
        assert on_route("https://hook", EVENT) is None
