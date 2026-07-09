# rabbitmq-event-router

> **Daemon Python** que roteia eventos RabbitMQ para webhooks com regras em banco.

[![CI](https://github.com/abreu0x/rabbitmq-event-router/actions/workflows/ci.yml/badge.svg)](https://github.com/abreu0x/rabbitmq-event-router/actions)
[![Release](https://img.shields.io/github/v/release/abreu0x/rabbitmq-event-router?include_prereleases&style=flat-square)](https://github.com/abreu0x/rabbitmq-event-router/releases)
[![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)

> **Status `v0.1.0`:** funcional ponta a ponta — consumo pika (ack + prefetch + DLX),
> matcher de regras (DB via SQLAlchemy/Alembic), dispatch httpx com retry/backoff, admin
> FastAPI e Docker Compose. Coberto por unit + property (hypothesis) + integration
> (testcontainers), tudo em CI. Contract (schemathesis), chaos e mutation são o próximo passo.

## 🚀 Demo em 30s

```bash
uv sync --all-extras
uv run pytest          # ruff + mypy + testes
```

```python
from rabbitmq_event_router import Event, RoutingRule, match_rules

rules = [
    RoutingRule(event_type="motion", webhook_url="https://hook/alarme", priority=10),
    RoutingRule(event_type="motion", webhook_url="https://hook/log", priority=1),
]
match_rules(Event(event_type="motion"), rules)
# → regras habilitadas que casam, ordenadas por prioridade
```

## 🏗️ Architecture

```mermaid
flowchart LR
    RMQ[(RabbitMQ)] -- pika --> C[consumer]
    C --> R[rules matcher<br/>puro, testado]
    R --> D[dispatcher httpx]
    D -- webhook --> W[atuadores]
    DB[(SQLAlchemy + Alembic)] -. regras .-> R
```

Camadas separadas de propósito: o **matcher de regras** é puro (sem broker, sem rede),
o que o torna testável em unidade + property tests (hypothesis) sem infra.

## 🧪 Testes & CI

| Camada | Ferramenta | Status |
|--------|-----------|--------|
| Estilo & tipos | `ruff` + `mypy --strict` | ✅ em CI |
| Unit + cobertura | `pytest` (≥ 80%) | ✅ 98% |
| Admin API | FastAPI + `TestClient` (CRUD, input `strict`) | ✅ |
| Dispatcher | httpx + retry/backoff, testado com `respx` | ✅ sem rede |
| Persistência | SQLAlchemy 2.0 + Alembic (SQLite in-mem) | ✅ load + migração testadas |
| Property-based | `hypothesis` no matcher | ✅ 3 invariantes |
| Integration | `testcontainers` (RabbitMQ efêmero) | ✅ route + **DLX poison→DLQ** |
| Contract | `schemathesis` no OpenAPI | _planejado (já rendeu 404-docs + strict)_ |
| Chaos | `toxiproxy` · mutation `mutmut` nightly | _planejado_ |

## 🗺️ Roadmap

- [x] Modelo de regras + matcher puro, testado (ruff/mypy/cov)
- [x] Consumer/publisher pika (ack manual + prefetch) + integration testcontainers
- [x] Persistência SQLAlchemy 2.0 + Alembic (migração testada) · property tests (hypothesis)
- [x] Admin FastAPI (CRUD, input `strict`) + structlog + Docker Compose (broker+DB+service)
- [x] Dispatcher httpx (retry + backoff exponencial) + DLX (poison → DLQ) + Systemd unit · **tag `v0.1.0`**
- [ ] schemathesis (contract) · chaos (toxiproxy) · mutmut nightly

## 🛠️ Stack

Python 3.12 · Pydantic 2 · pika · SQLAlchemy 2.0 · Alembic · FastAPI · httpx · structlog · pytest · ruff · mypy

## 📄 Licença

MIT — ver [LICENSE](LICENSE).
