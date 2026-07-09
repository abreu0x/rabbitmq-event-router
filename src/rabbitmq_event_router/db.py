"""Persistência das regras de roteamento (SQLAlchemy 2.0).

As regras vivem em banco (não hardcoded) — assim dá pra mudar roteamento sem
redeploy. `load_rules` converte ORM → o modelo Pydantic puro usado pelo matcher,
mantendo a lógica de roteamento desacoplada do banco.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from rabbitmq_event_router.rules import RoutingRule


class Base(DeclarativeBase):
    """Base declarativa do projeto."""


class RoutingRuleORM(Base):
    """Regra de roteamento persistida."""

    __tablename__ = "routing_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    webhook_url: Mapped[str] = mapped_column(String(2048))
    priority: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    def to_pydantic(self) -> RoutingRule:
        """Converte a linha do banco no modelo puro usado pelo matcher."""
        return RoutingRule(
            event_type=self.event_type,
            webhook_url=self.webhook_url,
            priority=self.priority,
            enabled=self.enabled,
        )


def load_rules(session: Session) -> list[RoutingRule]:
    """Carrega as regras habilitadas do banco como `RoutingRule`."""
    stmt = select(RoutingRuleORM).where(RoutingRuleORM.enabled.is_(True))
    return [row.to_pydantic() for row in session.scalars(stmt)]
