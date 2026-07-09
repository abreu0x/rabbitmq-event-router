"""rabbitmq-event-router — roteia eventos RabbitMQ para webhooks por regras."""

from rabbitmq_event_router.rules import Event, RoutingRule, match_rules

__all__ = ["Event", "RoutingRule", "match_rules"]
__version__ = "0.1.0"
