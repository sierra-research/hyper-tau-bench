"""Construction-task Client opt-in: hand-authored instructions count.

Stonewall control arms enable the Client with a hand-authored
``client_instructions`` prompt (and no ``client_sections``) over a variant
whose client_knowledge facts are deliberately unreachable. The kit gate
must warn instead of raise for them, and the orchestrator must treat the
hand-authored prompt as a construction opt-in.
"""

from types import SimpleNamespace

import pytest

from tau2.hyper.sandbox.kit import _require_client_held_facts_reachable
from tau2.hyper.sandbox.orchestrator import SandboxOrchestrator


def _task(**overrides):
    base = dict(
        client_enabled=True,
        client_sections=None,
        client_instructions="",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _orchestrator_for(task) -> SandboxOrchestrator:
    orchestrator = SandboxOrchestrator.__new__(SandboxOrchestrator)
    orchestrator.task = task
    return orchestrator


class TestRequireClientHeldFactsReachable:
    def test_no_held_facts_passes(self):
        _require_client_held_facts_reachable("v", set(), None, False)

    def test_declared_sections_pass(self):
        _require_client_held_facts_reachable(
            "v", {"manage_delivered_order"}, ["manage_delivered_order"], False
        )

    def test_undeclared_sections_raise_without_custom_client(self):
        with pytest.raises(ValueError, match="unlearnable"):
            _require_client_held_facts_reachable(
                "v", {"manage_delivered_order"}, [], False
            )

    def test_undeclared_sections_warn_with_custom_client(self):
        _require_client_held_facts_reachable("v", {"manage_delivered_order"}, [], True)

    def test_partially_declared_sections_still_raise(self):
        with pytest.raises(ValueError, match="service_foundations"):
            _require_client_held_facts_reachable(
                "v",
                {"manage_delivered_order", "service_foundations"},
                ["manage_delivered_order"],
                False,
            )


class TestConstructionClientEnabled:
    def test_client_sections_opt_in(self):
        task = _task(client_sections=["manage_delivered_order"])
        assert _orchestrator_for(task)._client_enabled() is True

    def test_hand_authored_instructions_opt_in(self):
        task = _task(client_instructions="You are the operations lead...")
        assert _orchestrator_for(task)._client_enabled() is True

    def test_no_opt_in_skips_client(self):
        assert _orchestrator_for(_task())._client_enabled() is False

    def test_whitespace_instructions_are_not_an_opt_in(self):
        task = _task(client_instructions="   \n")
        assert _orchestrator_for(task)._client_enabled() is False

    def test_client_disabled_wins_over_instructions(self):
        task = _task(client_enabled=False, client_instructions="persona")
        assert _orchestrator_for(task)._client_enabled() is False
