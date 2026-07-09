"""rabbitmq-event-router — roteia eventos RabbitMQ para webhooks por regras."""

from rabbitmq_event_router.consumer import consume, parse_message, publish, route_message
from rabbitmq_event_router.rules import Event, RoutingRule, match_rules

__all__ = [
    "Event",
    "RoutingRule",
    "consume",
    "match_rules",
    "parse_message",
    "publish",
    "route_message",
]
__version__ = "0.1.0"
