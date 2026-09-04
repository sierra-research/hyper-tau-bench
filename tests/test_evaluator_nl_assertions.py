import json

import pytest

from tau2.data_model.message import AssistantMessage, ToolCall, UserMessage
from tau2.data_model.simulation import NLAssertionCheck
from tau2.data_model.tasks import EvaluationCriteria, NLAssertion
from tau2.evaluator import evaluator_nl_assertions as nl_module
from tau2.evaluator.evaluator_nl_assertions import NLAssertionsEvaluator


def test_evaluation_criteria_accepts_legacy_and_structured_nl_assertions():
    criteria = EvaluationCriteria(
        nl_assertions=[
            "The assistant greeted the user.",
            {
                "id": "custom_style",
                "judge": "custom_judge",
                "assertion": "The assistant followed the custom style rule.",
            },
        ]
    )

    assert criteria.nl_assertions is not None
    assert criteria.nl_assertions[0] == "The assistant greeted the user."
    assert criteria.nl_assertions[1] == NLAssertion(
        id="custom_style",
        judge="custom_judge",
        assertion="The assistant followed the custom style rule.",
    )


def test_nl_assertion_router_preserves_order_and_routes_custom_judges(monkeypatch):
    generic_calls = []

    def fake_generate(**kwargs):
        messages = kwargs["messages"]
        generic_calls.append(messages)
        return AssistantMessage(
            role="assistant",
            content=json.dumps(
                {
                    "results": [
                        {
                            "expectedOutcome": "The generic assertion passed.",
                            "reasoning": "generic judge ran",
                            "metExpectation": True,
                        }
                    ]
                }
            ),
        )

    def fake_custom_judge(trajectory, assertion):
        return NLAssertionCheck(
            id=assertion.id,
            judge=assertion.judge,
            nl_assertion=assertion.assertion,
            met=True,
            justification=f"custom judge saw {len(trajectory)} message(s)",
        )

    monkeypatch.setattr(nl_module, "generate", fake_generate)
    monkeypatch.setitem(
        NLAssertionsEvaluator.CUSTOM_JUDGES,
        "custom_openings",
        fake_custom_judge,
    )

    checks = NLAssertionsEvaluator.evaluate_nl_assertions(
        [UserMessage(role="user", content="Hello")],
        [
            NLAssertion(
                id="opening_rule",
                judge="custom_openings",
                assertion="The custom assertion passed.",
            ),
            "The generic assertion passed.",
        ],
    )

    assert [check.nl_assertion for check in checks] == [
        "The custom assertion passed.",
        "The generic assertion passed.",
    ]
    assert [check.judge for check in checks] == ["custom_openings", "generic"]
    assert [check.id for check in checks] == ["opening_rule", None]
    assert len(generic_calls) == 1
    assert "The generic assertion passed." in generic_calls[0][1].content
    assert "The custom assertion passed." not in generic_calls[0][1].content


def test_unknown_custom_nl_assertion_judge_raises():
    with pytest.raises(ValueError, match="Unknown NL assertion judge: missing_judge"):
        NLAssertionsEvaluator.evaluate_nl_assertions(
            [UserMessage(role="user", content="Hello")],
            [
                NLAssertion(
                    judge="missing_judge",
                    assertion="This should be routed to a missing judge.",
                )
            ],
        )


def test_response_openings_custom_judge_formats_only_assistant_openings(monkeypatch):
    calls = []

    def fake_generate(**kwargs):
        calls.append(kwargs)
        return AssistantMessage(
            role="assistant",
            content=json.dumps(
                {
                    "metExpectation": False,
                    "repeatedOpenings": [
                        {
                            "template": "I found ...",
                            "responseNumbers": [1, 2],
                            "evidence": [
                                "I found the first order.",
                                "I found the second order.",
                            ],
                        }
                    ],
                    "reasoning": "The openings repeat an I found frame.",
                }
            ),
        )

    monkeypatch.setattr(nl_module, "generate", fake_generate)

    checks = NLAssertionsEvaluator.evaluate_nl_assertions(
        [
            UserMessage(role="user", content="Can you check my orders?"),
            AssistantMessage(
                role="assistant",
                content="I found the first order. It is pending.",
            ),
            AssistantMessage(
                role="assistant",
                content=None,
                tool_calls=[
                    ToolCall(
                        name="get_order_details",
                        arguments={"order_id": "#W123"},
                    )
                ],
            ),
            AssistantMessage(
                role="assistant",
                content="I found the second order. It has shipped.",
            ),
        ],
        [
            NLAssertion(
                id="avoid_repeated_openings",
                judge="response_openings",
                assertion=(
                    "The assistant did not begin multiple customer-facing "
                    "responses with the same opening phrase template."
                ),
            )
        ],
    )

    assert len(checks) == 1
    assert checks[0].id == "avoid_repeated_openings"
    assert checks[0].judge == "response_openings"
    assert checks[0].met is False
    assert "I found frame" in checks[0].justification
    assert len(calls) == 1
    assert calls[0]["call_name"] == "nl_assertions_response_openings_eval"
    user_prompt = calls[0]["messages"][1].content
    assert "1. I found the first order." in user_prompt
    assert "2. I found the second order." in user_prompt
    assert "Can you check my orders?" not in user_prompt
    assert "get_order_details" not in user_prompt
