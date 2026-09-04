from tau2.data_model.message import AssistantMessage, UserMessage
from tau2.data_model.simulation import SimulationRun, TerminationReason
from tau2.data_model.tasks import (
    EvaluationCriteria,
    NLAssertion,
    ResponseAssertion,
    RewardType,
    Task,
    UserScenario,
)
from tau2.environment.environment import Environment
from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation
from tau2.evaluator.evaluator_response_assertions import ResponseAssertionsEvaluator
from tau2.hyper.response_phrasing import (
    apply_response_phrasing_rule_pack_to_task,
    load_response_phrasing_rule_pack,
    render_response_phrasing_rules_markdown,
)
from tau2.run import get_tasks

PREMATURE_OUTCOME_NL_ASSERTION = (
    "The assistant avoided premature outcome language: it did not state or "
    "imply that a fix resolved the issue, an action was completed, or a "
    "requested change should or will work before the conversation contained a "
    "successful tool result or explicit customer confirmation verifying that "
    "outcome. It is acceptable to explain eligibility, ask for confirmation, "
    "or describe what will happen if the customer confirms, as long as the "
    "assistant does not present the outcome as already achieved or as expected "
    "to work before verification. If no fix/action outcome is discussed, this "
    "assertion is satisfied."
)

IDENTIFIER_MINIMIZATION_NL_ASSERTION = (
    "The assistant handled sensitive identifiers appropriately: it did not "
    "expose internal payment, account, database, or tool identifiers when a "
    "customer-facing label was available. Customer-facing identifiers such as "
    "reservation IDs, order IDs, item IDs, flight numbers, and phone numbers "
    "may be used when useful for authentication, lookup, disambiguation, "
    "comparing options, or explicit confirmation of a customer-requested "
    "action. Once an entity is clearly established and no exact confirmation "
    "or disambiguation is needed, the assistant should prefer natural labels "
    "or partial identifiers. If no identifiers are discussed, this assertion "
    "is satisfied."
)

REPEATED_OPENINGS_NL_ASSERTION = NLAssertion(
    id="avoid_repeated_openings",
    judge="response_openings",
    assertion=(
        "The assistant did not begin multiple customer-facing responses with "
        "the same opening phrase template."
    ),
)

BANKING_REPEATED_OPENINGS_NL_ASSERTION = NLAssertion(
    id="avoid_repeated_openings",
    judge="response_openings",
    assertion=(
        "The assistant did not begin multiple customer-facing responses with "
        "the same reusable opening phrase template. Only flag repeated "
        "openings when the initial phrase or sentence frame itself repeats "
        "without a policy need. Do not flag repetition that comes from "
        "required identity-verification factors, including repeated "
        "email-address-plus-date-of-birth prompts, exact transfer wording, "
        "recurring fee or third-party disclaimer language, account-activity "
        "explanation labels, linked-account qualification terms, or stable "
        "completion wording after a verified action when the surrounding "
        "response is otherwise specific to the case."
    ),
)

TELECOM_REPEATED_OPENINGS_NL_ASSERTION = NLAssertion(
    id="avoid_repeated_openings",
    judge="response_openings",
    assertion=(
        "The assistant did not begin multiple customer-facing responses with the "
        "same exact opening phrase or a trivially reworded variant of the same "
        "first clause. Only flag repeated openings when the initial phrase or "
        "sentence frame itself repeats; do not flag responses merely because "
        "independent training cases ask for the same required diagnostic step or "
        "reuse policy-required procedure words, entity labels, or setting names."
    ),
)

NO_GENERIC_SERVICE_INVITATIONS_NL_ASSERTION = (
    "The assistant did not invite the customer to ask for additional help, "
    "request anything else, or reach out later for more assistance. This "
    "includes generic service-closing invitations such as 'Is there anything "
    "else I can help you with?', 'Let me know if you need anything else', "
    "'feel free to reach out', or similar. Initial greetings that ask how the "
    "assistant can help, procedural questions needed to complete the current "
    "request, confirmations before taking an action, and concrete transfer or "
    "handoff statements do not violate this rule."
)

NO_SUPPORT_DEFLECTION_NL_ASSERTION = (
    "The assistant did not tell the customer to contact, call, reach out to, "
    "or speak with customer support, customer service, the company/store/"
    "airline/provider, or another support team/channel outside the current "
    "conversation. The assistant may offer or initiate a transfer, escalation, "
    "handoff, connection to a human agent or specialist, or contact/escalate "
    "on the customer's behalf from within the current conversation. If the "
    "assistant handles the request directly, asks procedural questions, or "
    "offers an in-conversation transfer/handoff/escalation, this assertion is "
    "satisfied."
)

CUSTOMER_VISIBLE_FAILURE_NL_ASSERTION = (
    "When the assistant describes a failed, blocked, or unexpected internal "
    "action/tool/system/backend operation, it explains the customer-visible "
    "outcome in plain language and gives a concrete next step without quoting "
    "raw error strings or exposing internal tool/API/backend/system mechanics. "
    "Violations include phrases such as 'the system returned an error', quoted "
    "backend errors, wrong API/tool explanations, or statements that a "
    "tool/API/system response was inconsistent. If the assistant does not "
    "describe a failed, blocked, or unexpected internal operation, this "
    "assertion is satisfied."
)

NO_INTERNAL_TOOL_MENTIONS_NL_ASSERTION = (
    "The assistant did not mention internal tools, tool calls, tool results, "
    "tool availability, or internal tooling/source limitations in "
    "customer-facing text. Violations include saying the assistant has or "
    "lacks a tool, referring to available/provided/order tools or "
    "policy/tools, naming a cancellation/return/exchange/modify/order tool, "
    "or explaining what a tool can or cannot do. Do not count customer-visible "
    "product language such as power tools, garden tool sets, hand tools, bike "
    "repair tools, measuring tools, hair styling tools, tool-free assembly, "
    "or saying no tools are required for a product."
)

NO_LONG_MENU_DUMPS_NL_ASSERTION = (
    "The assistant avoided broad next-step menu dumps when the customer needed "
    "focused guidance. If the customer was confused, frustrated, blocked by a "
    "limitation or policy, or affected by an error or failed action, mark a "
    "violation when the assistant responds by making the customer choose among "
    "a menu of several next paths, or combines multiple unrelated decisions, "
    "checks, or actions in one turn, instead of identifying the best next step. "
    "This includes three-or-more alternative paths, 'your options are' lists "
    "after a refusal or limitation, or a long turn that mixes status summaries, "
    "policy limits, possible actions, payment or refund choices, and "
    "confirmation requests. Do not mark concise one- or two-option choices, "
    "authentication alternatives, required details for one already-selected "
    "action, option comparisons the customer explicitly requested, or "
    "step-by-step instructions for one customer-visible action as violations. "
    "If no blocked, confused, or error context occurs, this assertion is "
    "satisfied."
)

MATCH_WARMTH_TO_OUTCOME_NL_ASSERTION = (
    "The assistant matched warmth to the outcome. Mark a violation when an "
    "assistant response begins with a celebratory outcome opener or global "
    "upbeat framing such as 'Great news', 'Good news', 'Perfect', 'Awesome', "
    "'Excellent news', 'Fantastic', 'Wonderful', or a standalone 'Great' or "
    "'Excellent', and the same response delivers a meaningful denial, failed "
    "action, unavailable option, ineligible request, unsupported action, or "
    "unresolved limitation for the customer. This applies when the cheerful "
    "wording frames the overall turn before the assistant says the requested "
    "action cannot be done, does not qualify, is not available, failed, or "
    "still needs unresolved troubleshooting. Do not mark neutral "
    "acknowledgements such as 'Great question' or 'Great, thanks', technical "
    "quality labels such as 'Excellent' speed or signal, or cheerful language "
    "that only reports a verified successful resolution. Do not mark a routine "
    "procedural warning or equivalent supported path if it does not block or "
    "constrain the customer's request. If no denial, failure, unavailable "
    "option, ineligible request, unsupported action, or unresolved limitation "
    "occurs in the assistant response, this assertion is satisfied."
)


def test_forbidden_word_response_assertion_fails_assistant_message():
    assertion = ResponseAssertion(
        id="never_say_unfortunately",
        type="forbidden_word",
        value="unfortunately",
    )
    messages = [
        UserMessage(role="user", content="Can you help me?"),
        AssistantMessage(role="assistant", content="Unfortunately, I cannot do that."),
    ]

    checks = ResponseAssertionsEvaluator.evaluate_response_assertions(
        messages,
        [assertion],
    )

    assert len(checks) == 1
    assert not checks[0].met
    assert "Unfortunately" in checks[0].justification


def test_forbidden_word_response_assertion_ignores_user_message():
    assertion = ResponseAssertion(
        id="never_say_unfortunately",
        type="forbidden_word",
        value="unfortunately",
    )
    messages = [
        UserMessage(role="user", content="Unfortunately, my flight changed."),
        AssistantMessage(role="assistant", content="I can help you with that."),
    ]

    checks = ResponseAssertionsEvaluator.evaluate_response_assertions(
        messages,
        [assertion],
    )

    assert checks[0].met


def test_all_evaluation_includes_response_assertion_reward_basis():
    task = Task(
        id="response_assertion_reward",
        user_scenario=UserScenario(instructions="Ask for help."),
        evaluation_criteria=EvaluationCriteria(
            response_assertions=[
                ResponseAssertion(
                    id="never_say_unfortunately",
                    type="forbidden_word",
                    value="unfortunately",
                )
            ],
            reward_basis=[RewardType.RESPONSE_ASSERTION],
        ),
    )
    simulation = SimulationRun(
        id="response_assertion_reward",
        task_id=task.id,
        start_time="2026-01-01T00:00:00Z",
        end_time="2026-01-01T00:00:01Z",
        duration=1.0,
        termination_reason=TerminationReason.USER_STOP,
        messages=[AssistantMessage(role="assistant", content="I can help with that.")],
    )

    reward_info = evaluate_simulation(
        simulation=simulation,
        task=task,
        evaluation_type=EvaluationType.ALL,
        solo_mode=False,
        domain="test",
        environment_constructor=lambda **_: Environment(
            domain_name="test",
            policy="",
        ),
    )

    assert reward_info.reward == 1.0
    assert reward_info.reward_breakdown == {RewardType.RESPONSE_ASSERTION: 1.0}


def test_regex_forbidden_word_response_assertion_matches_precise_pattern():
    assertion = ResponseAssertion(
        id="no_first_person_cant",
        type="forbidden_word",
        value=r"\bI\s+(?:cannot|can\u2019t|can't|can not)\b",
        match="regex_case_insensitive",
    )
    messages = [
        AssistantMessage(
            role="assistant",
            content="The order can't be cancelled, but I can help with a return.",
        ),
        AssistantMessage(
            role="assistant",
            content="I can't issue a replacement shipment through this channel.",
        ),
    ]

    checks = ResponseAssertionsEvaluator.evaluate_response_assertions(
        messages,
        [assertion],
    )

    assert len(checks) == 1
    assert not checks[0].met
    assert "replacement shipment" in checks[0].justification


def test_retail_internal_tool_rule_uses_semantic_nl_assertion():
    pack = load_response_phrasing_rule_pack(
        "tau2/hyper/response_phrasing/retail_response_phrasing.yaml"
    )
    assert pack is not None

    assert all(
        assertion.id != "no_internal_tool_mentions"
        for assertion in pack.response_assertions
    )
    assert NO_INTERNAL_TOOL_MENTIONS_NL_ASSERTION in pack.nl_assertions


def test_max_occurrences_response_assertion_counts_across_assistant_messages():
    assertion = ResponseAssertion(
        id="max_one_apology_per_conversation",
        type="max_occurrences",
        value=r"\b(?:sorry|apolog(?:ize|ise|ized|ised|izing|ising|y|ies)|regret)\b",
        match="regex_case_insensitive",
        max_count=1,
    )
    messages = [
        UserMessage(role="user", content="Sorry, I need help."),
        AssistantMessage(role="assistant", content="I am sorry about the disruption."),
        AssistantMessage(
            role="assistant", content="I apologize, but I cannot do that."
        ),
    ]

    checks = ResponseAssertionsEvaluator.evaluate_response_assertions(
        messages,
        [assertion],
    )

    assert len(checks) == 1
    assert not checks[0].met
    assert "Found 2 matches" in checks[0].justification


def test_max_occurrences_response_assertion_allows_one_match():
    assertion = ResponseAssertion(
        id="max_one_apology_per_conversation",
        type="max_occurrences",
        value=r"\b(?:sorry|apolog(?:ize|ise|ized|ised|izing|ising|y|ies)|regret)\b",
        match="regex_case_insensitive",
        max_count=1,
    )
    messages = [
        AssistantMessage(role="assistant", content="I am sorry about the disruption."),
        AssistantMessage(role="assistant", content="The reservation is basic economy."),
    ]

    checks = ResponseAssertionsEvaluator.evaluate_response_assertions(
        messages,
        [assertion],
    )

    assert checks[0].met


def test_no_repeated_opening_phrase_normalizes_identifiers():
    assertion = ResponseAssertion(
        id="avoid_repeated_openings",
        type="no_repeated_opening_phrase",
        value="3",
        match="normalized_first_tokens",
    )
    messages = [
        AssistantMessage(
            role="assistant",
            content="Order #W1234567 is pending and can still be updated.",
        ),
        AssistantMessage(
            role="assistant",
            content="Order #W7654321 is delivered and can be returned.",
        ),
    ]

    checks = ResponseAssertionsEvaluator.evaluate_response_assertions(
        messages,
        [assertion],
    )

    assert not checks[0].met
    assert "order id is" in checks[0].justification


def test_no_repeated_opening_phrase_allows_shared_first_word():
    assertion = ResponseAssertion(
        id="avoid_repeated_openings",
        type="no_repeated_opening_phrase",
        value="3",
        match="normalized_first_tokens",
    )
    messages = [
        AssistantMessage(
            role="assistant",
            content="Please check whether mobile data is turned on.",
        ),
        AssistantMessage(
            role="assistant",
            content="Please turn airplane mode off, then tell me once it is off.",
        ),
    ]

    checks = ResponseAssertionsEvaluator.evaluate_response_assertions(
        messages,
        [assertion],
    )

    assert checks[0].met


def test_no_repeated_opening_phrase_catches_repeated_confirmation_frame():
    assertion = ResponseAssertion(
        id="avoid_repeated_openings",
        type="no_repeated_opening_phrase",
        value="3",
        match="normalized_first_tokens",
    )
    messages = [
        AssistantMessage(
            role="assistant",
            content="Please confirm you want to cancel order #W1234567.",
        ),
        AssistantMessage(
            role="assistant",
            content="Please confirm you want to cancel order #W7654321.",
        ),
    ]

    checks = ResponseAssertionsEvaluator.evaluate_response_assertions(
        messages,
        [assertion],
    )

    assert not checks[0].met
    assert "please confirm you" in checks[0].justification


def test_response_phrasing_rule_packs_include_domain_safety_metadata():
    paths = [
        "tau2/hyper/response_phrasing/airline_response_phrasing.yaml",
        "tau2/hyper/response_phrasing/banking_response_phrasing.yaml",
        "tau2/hyper/response_phrasing/retail_response_phrasing.yaml",
        "tau2/hyper/response_phrasing/telecom_response_phrasing.yaml",
    ]

    rules_by_id = {}
    for path in paths:
        pack = load_response_phrasing_rule_pack(path)
        assert pack is not None
        for rule in pack.rules:
            assert set(rule.domain_safety) == {
                "airline",
                "retail",
                "telecom",
                "banking_knowledge",
            }
            assert rule.domain_safety["banking_knowledge"].reasoning
            rules_by_id[rule.id] = rule

    assert rules_by_id["never_say_unfortunately"].domain_safety["retail"].safe
    assert (
        not rules_by_id["no_generic_service_invitations"].domain_safety["retail"].safe
    )
    assert "one-shot" in (
        rules_by_id["no_generic_service_invitations"].domain_safety["retail"].reason
    )
    assert not rules_by_id["one_visible_action"].domain_safety["telecom"].safe
    assert "operational shorthand" in (
        rules_by_id["one_visible_action"].domain_safety["telecom"].safe_if
    )
    assert not rules_by_id["no_first_person_inability"].domain_safety["airline"].safe
    assert (
        not rules_by_id["no_internal_tool_mentions"]
        .domain_safety["banking_knowledge"]
        .safe
    )
    assert "customer-discoverable tools" in (
        rules_by_id["no_internal_tool_mentions"]
        .domain_safety["banking_knowledge"]
        .safe_if
    )
    assert not rules_by_id["no_policy_jargon"].domain_safety["banking_knowledge"].safe
    assert (
        rules_by_id["never_say_unfortunately"].domain_safety["banking_knowledge"].safe
    )


def test_airline_response_phrasing_rule_pack_renders_and_applies():
    pack = load_response_phrasing_rule_pack(
        "tau2/hyper/response_phrasing/airline_response_phrasing.yaml"
    )
    assert pack is not None
    assert render_response_phrasing_rules_markdown(pack) == (
        '- Never use the word "unfortunately" in responses to the customer.\n'
        "- Do not apologize more than once per conversation.\n"
        "- Do not tell the customer that an issue is resolved, a change is "
        "complete, or a requested action should or will work until the "
        "relevant tool result or customer confirmation has verified that "
        "outcome. Before verification, frame it as the next thing to check or "
        "as what will be attempted after confirmation.\n"
        "- Use the least specific customer identifier that still lets the "
        "customer understand, disambiguate, compare options, or confirm the "
        "action. Customer-facing identifiers such as reservation IDs, order "
        "IDs, item IDs, flight numbers, and phone numbers are allowed when "
        "useful for lookup, disambiguation, option comparison, or explicit "
        "action confirmation. Otherwise, prefer natural labels or partial "
        "identifiers, and do not expose internal payment, account, database, "
        "or tool identifiers when a customer-facing label is available.\n"
        "- Do not begin multiple customer-facing responses with the same "
        "opening phrase. Repeating an opening phrase is allowed only if "
        "another instruction explicitly requires that exact wording.\n"
        "- Do not invite the customer to ask for additional help, request "
        "anything else, or reach out later for more assistance.\n"
        "- Do not tell the customer to contact, call, reach out to, or speak "
        "with customer support or another support channel. Handle the request "
        "directly when possible, or offer an in-conversation transfer, "
        "escalation, or handoff when needed.\n"
        "- When an action fails or behaves unexpectedly, explain the "
        "customer-visible outcome in plain language and give one concrete next "
        "step. Do not quote raw error strings or mention internal tools, APIs, "
        "backend systems, or system mechanics.\n"
        "- When the customer is confused, frustrated, blocked by a limitation "
        "or policy, or affected by an error or failed action, do not present a "
        "large menu of next-step options. Recommend the best next action and "
        "ask for one confirmation or one needed piece of information.\n"
        "- Do not use celebratory or overly positive openings such as "
        '"Great news", "Good news", "Perfect", "Awesome", "Excellent news", '
        "or similar when the same response contains a denial, failure, "
        "unavailable option, ineligible request, unsupported action, or "
        "unresolved limitation. Match the warmth of the response to the "
        "outcome.\n"
        "- Do not use markdown formatting, numbered lists, bullet lists, bold "
        "text, or inline code formatting in customer-facing responses.\n"
        "- Do not frame limitations as first-person inability using phrases "
        'like "I can\'t", "I cannot", "I can not", "I\'m unable to", or '
        '"I\'m not able to". Say the booking, fare, or request is not eligible '
        "instead.\n"
        "- Do not mention internal tools, provided policy/source material, "
        "policy/tool availability, booking systems, or source limitations in "
        "customer-facing responses. Explain customer-visible booking facts "
        "directly.\n"
    )

    task = get_tasks("airline", task_ids=["0"])[0]
    updated_task = apply_response_phrasing_rule_pack_to_task(task, pack)

    assert updated_task.evaluation_criteria is not None
    assert (
        RewardType.RESPONSE_ASSERTION in updated_task.evaluation_criteria.reward_basis
    )
    assert RewardType.NL_ASSERTION in updated_task.evaluation_criteria.reward_basis
    assert updated_task.evaluation_criteria.response_assertions is not None
    assert [
        assertion.id
        for assertion in updated_task.evaluation_criteria.response_assertions
    ] == [
        "never_say_unfortunately",
        "no_markdown_formatting",
        "no_first_person_inability",
        "no_internal_tool_or_source_language",
    ]
    assert updated_task.evaluation_criteria.nl_assertions is not None
    assert "Agent should refuse to proceed with the cancellation." in (
        updated_task.evaluation_criteria.nl_assertions
    )
    assert "The assistant did not apologize more than once." in (
        updated_task.evaluation_criteria.nl_assertions
    )
    assert PREMATURE_OUTCOME_NL_ASSERTION in (
        updated_task.evaluation_criteria.nl_assertions
    )
    assert IDENTIFIER_MINIMIZATION_NL_ASSERTION in (
        updated_task.evaluation_criteria.nl_assertions
    )
    assert REPEATED_OPENINGS_NL_ASSERTION in (
        updated_task.evaluation_criteria.nl_assertions
    )
    assert NO_GENERIC_SERVICE_INVITATIONS_NL_ASSERTION in (
        updated_task.evaluation_criteria.nl_assertions
    )
    assert NO_SUPPORT_DEFLECTION_NL_ASSERTION in (
        updated_task.evaluation_criteria.nl_assertions
    )
    assert CUSTOMER_VISIBLE_FAILURE_NL_ASSERTION in (
        updated_task.evaluation_criteria.nl_assertions
    )
    assert NO_LONG_MENU_DUMPS_NL_ASSERTION in (
        updated_task.evaluation_criteria.nl_assertions
    )
    assert MATCH_WARMTH_TO_OUTCOME_NL_ASSERTION in (
        updated_task.evaluation_criteria.nl_assertions
    )


def test_airline_response_phrasing_rule_pack_catches_observed_phrases():
    pack = load_response_phrasing_rule_pack(
        "tau2/hyper/response_phrasing/airline_response_phrasing.yaml"
    )
    assert pack is not None

    messages = [
        AssistantMessage(
            role="assistant",
            content=(
                "I can't make that change under the airline policy available "
                "to me.\n- Cabin: basic economy"
            ),
        )
    ]

    checks = ResponseAssertionsEvaluator.evaluate_response_assertions(
        messages,
        pack.response_assertions,
    )

    failed_ids = {check.response_assertion.id for check in checks if not check.met}
    assert failed_ids == {
        "no_markdown_formatting",
        "no_first_person_inability",
        "no_internal_tool_or_source_language",
    }


def test_retail_response_phrasing_rule_pack_renders_and_applies():
    pack = load_response_phrasing_rule_pack(
        "tau2/hyper/response_phrasing/retail_response_phrasing.yaml"
    )
    assert pack is not None
    assert render_response_phrasing_rules_markdown(pack) == (
        '- Never use the word "unfortunately" in responses to the customer.\n'
        "- Do not apologize more than once per conversation.\n"
        "- Do not tell the customer that an issue is resolved, a change is "
        "complete, or a requested action should or will work until the "
        "relevant tool result or customer confirmation has verified that "
        "outcome. Before verification, frame it as the next thing to check or "
        "as what will be attempted after confirmation.\n"
        "- Use the least specific customer identifier that still lets the "
        "customer understand, disambiguate, compare options, or confirm the "
        "action. Customer-facing identifiers such as reservation IDs, order "
        "IDs, item IDs, flight numbers, and phone numbers are allowed when "
        "useful for lookup, disambiguation, option comparison, or explicit "
        "action confirmation. Otherwise, prefer natural labels or partial "
        "identifiers, and do not expose internal payment, account, database, "
        "or tool identifiers when a customer-facing label is available.\n"
        "- Do not begin multiple customer-facing responses with the same "
        "opening phrase. Repeating an opening phrase is allowed only if "
        "another instruction explicitly requires that exact wording.\n"
        "- Do not invite the customer to ask for additional help, request "
        "anything else, or reach out later for more assistance.\n"
        "- Do not tell the customer to contact, call, reach out to, or speak "
        "with customer support or another support channel. Handle the request "
        "directly when possible, or offer an in-conversation transfer, "
        "escalation, or handoff when needed.\n"
        "- When an action fails or behaves unexpectedly, explain the "
        "customer-visible outcome in plain language and give one concrete next "
        "step. Do not quote raw error strings or mention internal tools, APIs, "
        "backend systems, or system mechanics.\n"
        "- When the customer is confused, frustrated, blocked by a limitation "
        "or policy, or affected by an error or failed action, do not present a "
        "large menu of next-step options. Recommend the best next action and "
        "ask for one confirmation or one needed piece of information.\n"
        "- Do not use celebratory or overly positive openings such as "
        '"Great news", "Good news", "Perfect", "Awesome", "Excellent news", '
        "or similar when the same response contains a denial, failure, "
        "unavailable option, ineligible request, unsupported action, or "
        "unresolved limitation. Match the warmth of the response to the "
        "outcome.\n"
        '- Do not use first-person inability phrases like "I can\'t", "I cannot", '
        'or "I can not" in responses to the customer.\n'
        "- Do not mention internal tools or tooling in responses to the customer.\n"
        '- Do not use the words "policy" or "policies" in responses to the '
        "customer.\n"
    )

    task = get_tasks("retail", task_ids=["0"])[0]
    updated_task = apply_response_phrasing_rule_pack_to_task(task, pack)

    assert updated_task.evaluation_criteria is not None
    assert (
        RewardType.RESPONSE_ASSERTION in updated_task.evaluation_criteria.reward_basis
    )
    assert RewardType.NL_ASSERTION in updated_task.evaluation_criteria.reward_basis
    assert updated_task.evaluation_criteria.response_assertions is not None
    assert len(updated_task.evaluation_criteria.response_assertions) == 3
    assert updated_task.evaluation_criteria.response_assertions[0].id == (
        "never_say_unfortunately"
    )
    assert [
        assertion.id
        for assertion in updated_task.evaluation_criteria.response_assertions
    ] == [
        "never_say_unfortunately",
        "no_first_person_cant",
        "no_policy_jargon",
    ]
    assert updated_task.evaluation_criteria.nl_assertions is not None
    assert "The assistant did not apologize more than once." in (
        updated_task.evaluation_criteria.nl_assertions
    )
    assert PREMATURE_OUTCOME_NL_ASSERTION in (
        updated_task.evaluation_criteria.nl_assertions
    )
    assert IDENTIFIER_MINIMIZATION_NL_ASSERTION in (
        updated_task.evaluation_criteria.nl_assertions
    )
    assert REPEATED_OPENINGS_NL_ASSERTION in (
        updated_task.evaluation_criteria.nl_assertions
    )
    assert NO_GENERIC_SERVICE_INVITATIONS_NL_ASSERTION in (
        updated_task.evaluation_criteria.nl_assertions
    )
    assert NO_SUPPORT_DEFLECTION_NL_ASSERTION in (
        updated_task.evaluation_criteria.nl_assertions
    )
    assert CUSTOMER_VISIBLE_FAILURE_NL_ASSERTION in (
        updated_task.evaluation_criteria.nl_assertions
    )
    assert NO_INTERNAL_TOOL_MENTIONS_NL_ASSERTION in (
        updated_task.evaluation_criteria.nl_assertions
    )
    assert NO_LONG_MENU_DUMPS_NL_ASSERTION in (
        updated_task.evaluation_criteria.nl_assertions
    )
    assert MATCH_WARMTH_TO_OUTCOME_NL_ASSERTION in (
        updated_task.evaluation_criteria.nl_assertions
    )


def test_telecom_response_phrasing_rule_pack_renders_and_applies():
    pack = load_response_phrasing_rule_pack(
        "tau2/hyper/response_phrasing/telecom_response_phrasing.yaml"
    )
    assert pack is not None
    assert render_response_phrasing_rules_markdown(pack) == (
        "- When giving the customer phone troubleshooting instructions, ask for "
        "only one customer-visible phone action or settings check per assistant "
        "response. It is fine to ask them to report the result of that one "
        "action.\n"
        "- Do not expose raw diagnostic command names, function names, "
        "snake_case identifiers, or code formatting in customer-facing "
        "responses. Describe the customer-visible phone action in plain "
        "language instead.\n"
        "- Do not use markdown formatting, numbered lists, bullet lists, bold "
        "text, or inline code formatting in customer-facing responses.\n"
        "- Do not tell the customer that an issue is resolved, a change is "
        "complete, or a requested action should or will work until the "
        "relevant tool result or customer confirmation has verified that "
        "outcome. Before verification, frame it as the next thing to check or "
        "as what will be attempted after confirmation.\n"
        "- Use the least specific customer identifier that still lets the "
        "customer understand, disambiguate, compare options, or confirm the "
        "action. Customer-facing identifiers such as reservation IDs, order "
        "IDs, item IDs, flight numbers, and phone numbers are allowed when "
        "useful for lookup, disambiguation, option comparison, or explicit "
        "action confirmation. Otherwise, prefer natural labels or partial "
        "identifiers, and do not expose internal payment, account, database, "
        "or tool identifiers when a customer-facing label is available.\n"
        "- Do not begin multiple customer-facing responses with the same "
        "opening phrase. Repeating an opening phrase is allowed only if "
        "another instruction explicitly requires that exact wording.\n"
        "- Do not invite the customer to ask for additional help, request "
        "anything else, or reach out later for more assistance.\n"
        "- Do not tell the customer to contact, call, reach out to, or speak "
        "with customer support or another support channel. Handle the request "
        "directly when possible, or offer an in-conversation transfer, "
        "escalation, or handoff when needed.\n"
        "- When an action fails or behaves unexpectedly, explain the "
        "customer-visible outcome in plain language and give one concrete next "
        "step. Do not quote raw error strings or mention internal tools, APIs, "
        "backend systems, or system mechanics.\n"
        "- When the customer is confused, frustrated, blocked by a limitation "
        "or policy, or affected by an error or failed action, do not present a "
        "large menu of next-step options. Recommend the best next action and "
        "ask for one confirmation or one needed piece of information.\n"
        "- Do not use celebratory or overly positive openings such as "
        '"Great news", "Good news", "Perfect", "Awesome", "Excellent news", '
        "or similar when the same response contains a denial, failure, "
        "unavailable option, ineligible request, unsupported action, or "
        "unresolved limitation. Match the warmth of the response to the "
        "outcome.\n"
        "- Do not apologize more than once per conversation.\n"
        '- Do not explain limitations by saying "as an AI," "as a virtual '
        'assistant," "my primary function," or "my main function." State the '
        "limitation directly.\n"
        "- When the customer expresses frustration, anxiety, confusion, or "
        "worry, acknowledge it briefly and then move directly to a concrete "
        "next step. Do not stack multiple sympathy or apology sentences before "
        "the next step.\n"
    )

    task = get_tasks(
        "telecom",
        task_ids=["[mobile_data_issue]data_mode_off[PERSONA:None]"],
    )[0]
    updated_task = apply_response_phrasing_rule_pack_to_task(task, pack)

    assert updated_task.evaluation_criteria is not None
    assert (
        RewardType.RESPONSE_ASSERTION in updated_task.evaluation_criteria.reward_basis
    )
    assert RewardType.NL_ASSERTION in updated_task.evaluation_criteria.reward_basis
    assert updated_task.evaluation_criteria.response_assertions is not None
    assert [
        assertion.id
        for assertion in updated_task.evaluation_criteria.response_assertions
    ] == [
        "no_tool_or_code_language",
        "no_markdown_formatting",
        "apologize_at_most_once",
        "no_ai_self_limitation",
    ]
    assert updated_task.evaluation_criteria.nl_assertions is not None
    assert len(updated_task.evaluation_criteria.nl_assertions) >= 5
    assert any(
        "only one customer-visible phone action" in assertion
        for assertion in updated_task.evaluation_criteria.nl_assertions
    )
    assert PREMATURE_OUTCOME_NL_ASSERTION in (
        updated_task.evaluation_criteria.nl_assertions
    )
    assert IDENTIFIER_MINIMIZATION_NL_ASSERTION in (
        updated_task.evaluation_criteria.nl_assertions
    )
    assert TELECOM_REPEATED_OPENINGS_NL_ASSERTION in (
        updated_task.evaluation_criteria.nl_assertions
    )
    assert NO_GENERIC_SERVICE_INVITATIONS_NL_ASSERTION in (
        updated_task.evaluation_criteria.nl_assertions
    )
    assert NO_SUPPORT_DEFLECTION_NL_ASSERTION in (
        updated_task.evaluation_criteria.nl_assertions
    )
    assert CUSTOMER_VISIBLE_FAILURE_NL_ASSERTION in (
        updated_task.evaluation_criteria.nl_assertions
    )
    assert NO_LONG_MENU_DUMPS_NL_ASSERTION in (
        updated_task.evaluation_criteria.nl_assertions
    )
    assert MATCH_WARMTH_TO_OUTCOME_NL_ASSERTION in (
        updated_task.evaluation_criteria.nl_assertions
    )
    assert any(
        "expresses frustration, anxiety, confusion, or worry" in assertion
        for assertion in updated_task.evaluation_criteria.nl_assertions
    )


def test_banking_response_phrasing_rule_pack_uses_banking_safe_rules():
    pack = load_response_phrasing_rule_pack(
        "tau2/hyper/response_phrasing/banking_response_phrasing.yaml"
    )
    assert pack is not None
    assert [rule.id for rule in pack.rules] == [
        "one_visible_action",
        "never_say_unfortunately",
        "no_premature_outcome_language",
        "avoid_repeated_openings",
        "no_generic_service_invitations",
        "customer_visible_failure_language",
        "no_long_menu_dumps",
        "match_warmth_to_outcome",
        "no_first_person_cant",
        "apologize_at_most_once",
        "no_ai_self_limitation",
        "restrained_frustration_acknowledgement",
    ]
    assert all(rule.domain_safety["banking_knowledge"].safe for rule in pack.rules)
    assert {
        "identifier_minimization",
        "no_support_deflection",
        "no_markdown_formatting",
        "no_first_person_inability",
        "no_internal_tool_or_source_language",
        "no_internal_tool_mentions",
        "no_policy_jargon",
        "no_tool_or_code_language",
    }.isdisjoint({rule.id for rule in pack.rules})

    rendered_rules = render_response_phrasing_rules_markdown(pack)
    assert "banking self-service, verification, security" in rendered_rules
    assert "exactly two verification factors" in rendered_rules
    assert "Single-step information-bundle exception" in rendered_rules
    assert "Do not tell the customer to contact" not in rendered_rules
    assert "Do not use markdown formatting" not in rendered_rules
    assert "Do not mention internal tools" not in rendered_rules

    assert [assertion.id for assertion in pack.response_assertions] == [
        "never_say_unfortunately",
        "no_first_person_cant",
        "apologize_at_most_once",
        "no_ai_self_limitation",
    ]
    assert len(pack.nl_assertions) == 8
    nl_assertion_strings = [
        assertion for assertion in pack.nl_assertions if isinstance(assertion, str)
    ]
    assert any(
        "banking self-service, verification, security" in assertion
        for assertion in nl_assertion_strings
    )
    assert any(
        "two verification factors" in assertion for assertion in nl_assertion_strings
    )
    assert any(
        (
            "fields, documents, criteria, setup/readiness checklist items, "
            "or counterparty/destination details"
        )
        in assertion
        for assertion in nl_assertion_strings
    )
    assert any(
        "setup/readiness checklist items" in assertion
        for assertion in nl_assertion_strings
    )
    assert PREMATURE_OUTCOME_NL_ASSERTION in pack.nl_assertions
    assert BANKING_REPEATED_OPENINGS_NL_ASSERTION in pack.nl_assertions
    assert NO_GENERIC_SERVICE_INVITATIONS_NL_ASSERTION in pack.nl_assertions
    assert CUSTOMER_VISIBLE_FAILURE_NL_ASSERTION in pack.nl_assertions
    assert NO_LONG_MENU_DUMPS_NL_ASSERTION in pack.nl_assertions
    assert MATCH_WARMTH_TO_OUTCOME_NL_ASSERTION in pack.nl_assertions
    assert any(
        "expresses frustration, anxiety, confusion, or worry" in assertion
        for assertion in nl_assertion_strings
    )


def test_orchestrator_inner_tasks_grade_stage_composed_phrasing():
    # Regression (2026-08-29, release/006 first phrasing-ON construction run):
    # tasks take phrasing through a composition_pipeline stage that narrows the
    # domain rule pack, and _load_inner_tasks read the raw rules path instead of
    # resolving the stage — scored traffic graded against rules the task drops
    # while run_local_test (resolver-based) graded the narrowed selection.
    from tau2.data_model.tasks import RewardType
    from tau2.hyper.response_phrasing import (
        load_selected_response_phrasing_rule_pack_for_task,
    )
    from tau2.hyper.sandbox.orchestrator import SandboxOrchestrator
    from tau2.hyper.task_loader import load_hyper_tau_task

    task = load_hyper_tau_task(
        "006_airline_plus_construction_core_evidence_response_phrasing"
        "_performance_medium"
    )
    full_pack = load_response_phrasing_rule_pack(task.response_phrasing_rules_path)
    selected_pack = load_selected_response_phrasing_rule_pack_for_task(task)
    selected_ids = {rule.id for rule in selected_pack.rules}
    # The stage genuinely narrows the pack, so grading the raw path would
    # apply rules this task deliberately drops.
    assert selected_ids < {rule.id for rule in full_pack.rules}

    orchestrator = SandboxOrchestrator.from_task(task, builder=None)
    inner_tasks = orchestrator._load_inner_tasks(task.test_task_ids[:2])
    assert inner_tasks
    for inner_task in inner_tasks:
        criteria = inner_task.evaluation_criteria
        assert criteria is not None and criteria.response_assertions
        assert [assertion.id for assertion in criteria.response_assertions] == [
            assertion.id for assertion in selected_pack.response_assertions
        ]
        assert RewardType.RESPONSE_ASSERTION in criteria.reward_basis
