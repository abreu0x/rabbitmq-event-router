"""Property-based tests do matcher (hypothesis)."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from rabbitmq_event_router.rules import Event, RoutingRule, match_rules

rule_strategy = st.builds(
    RoutingRule,
    event_type=st.text(min_size=1, max_size=12),
    webhook_url=st.text(min_size=1, max_size=24),
    priority=st.integers(min_value=-100, max_value=100),
    enabled=st.booleans(),
)


@given(
    event_type=st.text(min_size=1, max_size=12),
    rules=st.lists(rule_strategy, max_size=25),
)
def test_result_only_enabled_and_matching(event_type: str, rules: list[RoutingRule]) -> None:
    result = match_rules(Event(event_type=event_type), rules)
    for rule in result:
        assert rule.enabled
        assert rule.event_type == event_type


@given(
    event_type=st.text(min_size=1, max_size=12),
    rules=st.lists(rule_strategy, max_size=25),
)
def test_result_is_subset_of_input(event_type: str, rules: list[RoutingRule]) -> None:
    result = match_rules(Event(event_type=event_type), rules)
    assert len(result) <= len(rules)
    for rule in result:
        assert rule in rules


@given(
    event_type=st.text(min_size=1, max_size=12),
    rules=st.lists(rule_strategy, max_size=25),
)
def test_result_sorted_by_priority_desc(event_type: str, rules: list[RoutingRule]) -> None:
    result = match_rules(Event(event_type=event_type), rules)
    priorities = [rule.priority for rule in result]
    assert priorities == sorted(priorities, reverse=True)
