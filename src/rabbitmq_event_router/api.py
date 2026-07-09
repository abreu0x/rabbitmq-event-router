"""API admin (FastAPI) para CRUD das regras de roteamento.

`create_app` recebe a session factory por injeção — assim os testes usam SQLite
in-memory e produção usa Postgres, sem a app saber a diferença.

Este módulo NÃO usa `from __future__ import annotations`: o FastAPI precisa das
anotações como objetos reais para resolver os `Depends` locais de `create_app`
(como strings, ele as procuraria no namespace global do módulo e falharia).
"""

from collections.abc import Callable, Iterator
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from rabbitmq_event_router.db import RoutingRuleORM


class RuleIn(BaseModel):
    """Payload de criação de regra.

    `strict=True`: a API rejeita tipos errados (ex. `0` para um campo boolean)
    em vez de coagir — contrato honesto com o schema OpenAPI.
    """

    model_config = ConfigDict(strict=True)

    event_type: str = Field(min_length=1, max_length=128)
    webhook_url: str = Field(min_length=1, max_length=2048)
    priority: int = Field(default=0, ge=-1000, le=1000)
    enabled: bool = True


class RuleOut(RuleIn):
    """Regra retornada pela API (inclui id)."""

    model_config = ConfigDict(from_attributes=True, strict=True)

    id: int


def create_app(session_factory: Callable[[], Session]) -> FastAPI:
    """Cria a app FastAPI com CRUD de regras usando `session_factory`."""
    app = FastAPI(title="rabbitmq-event-router admin", version="0.1.0")

    def get_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    SessionDep = Annotated[Session, Depends(get_session)]

    @app.post("/rules", response_model=RuleOut, status_code=status.HTTP_201_CREATED)
    def create_rule(rule: RuleIn, session: SessionDep) -> RoutingRuleORM:
        orm = RoutingRuleORM(**rule.model_dump())
        session.add(orm)
        session.commit()
        session.refresh(orm)
        return orm

    @app.get("/rules", response_model=list[RuleOut])
    def list_rules(session: SessionDep) -> list[RoutingRuleORM]:
        return list(session.scalars(select(RoutingRuleORM)))

    not_found: dict[int | str, dict[str, Any]] = {
        status.HTTP_404_NOT_FOUND: {"description": "Regra não encontrada"}
    }

    @app.get("/rules/{rule_id}", response_model=RuleOut, responses=not_found)
    def get_rule(rule_id: int, session: SessionDep) -> RoutingRuleORM:
        orm = session.get(RoutingRuleORM, rule_id)
        if orm is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        return orm

    @app.delete(
        "/rules/{rule_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        responses=not_found,
    )
    def delete_rule(rule_id: int, session: SessionDep) -> None:
        orm = session.get(RoutingRuleORM, rule_id)
        if orm is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        session.delete(orm)
        session.commit()

    return app
