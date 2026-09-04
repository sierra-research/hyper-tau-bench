"""End-to-end calibration tests for the Telecom aggregate defect bundle."""

import hashlib
import json

from tau2.data_model.message import ToolCall
from tau2.domains.telecom.environment import get_tasks
from tau2.hyper.client_api.capabilities import (
    CapabilityDeploymentSession,
    EnableCapabilityAction,
    OfferCapabilityAction,
)
from tau2.hyper.client_api.defects import ClientAPITrialContext, load_defect_profile
from tau2.hyper.client_api.development import development_seed_manifest
from tau2.hyper.client_api.runtime import (
    build_openapi_contract,
    create_domain_client_api_runtime,
)

PAYMENT_TASK_ID = (
    "[service_issue]airplane_mode_on|overdue_bill_suspension[PERSONA:None]"
)
CONTRACT_TASK_IDS = {
    "[service_issue]contract_end_suspension|unseat_sim_card[PERSONA:Hard]",
    "[service_issue]contract_end_suspension|lock_sim_card_pin[PERSONA:Hard]",
    "[service_issue]break_apn_settings|contract_end_suspension|lock_sim_card_pin[PERSONA:Hard]",
    "[service_issue]airplane_mode_on|contract_end_suspension|lock_sim_card_pin|unseat_sim_card[PERSONA:Hard]",
    "[service_issue]airplane_mode_on|break_apn_settings|contract_end_suspension|unseat_sim_card[PERSONA:Easy]",
    "[service_issue]airplane_mode_on|break_apn_settings|contract_end_suspension|lock_sim_card_pin[PERSONA:None]",
    "[service_issue]break_apn_settings|contract_end_suspension|lock_sim_card_pin|unseat_sim_card[PERSONA:Hard]",
    "[service_issue]airplane_mode_on|break_apn_settings|contract_end_suspension|lock_sim_card_pin|unseat_sim_card[PERSONA:Easy]",
    "[service_issue]contract_end_suspension|lock_sim_card_pin[PERSONA:Hard][LEVER:transfer_notice_exact_text]",
}


class FakeMonotonicClock:
    def __init__(self, now=100.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def _profile():
    return load_defect_profile("telecom/all_defects_v1", expected_domain="telecom")


def _runtime(
    task_id=PAYMENT_TASK_ID,
    *,
    clock=None,
    development_seed=True,
    enable_payment=True,
    trial_context=None,
):
    profile = _profile()
    session = CapabilityDeploymentSession(profile)
    if enable_payment:
        session.offer(
            OfferCapabilityAction(capability_id="telecom_bill_payment_request_v1")
        )
        session.enable_offered(
            EnableCapabilityAction(capability_id="telecom_bill_payment_request_v1")
        )
    return create_domain_client_api_runtime(
        "telecom",
        development_seed=development_seed,
        defect_profile=profile,
        deployment_snapshot=session.freeze(),
        trial_context=trial_context
        or ClientAPITrialContext(task_id=task_id, trial_id="trial-1"),
        monotonic_clock=clock or FakeMonotonicClock(),
    )


def _developer_context_for(profile, defect_id):
    for index in range(100):
        label = f"developer-telecom-{index}"
        context = ClientAPITrialContext(
            task_id=label,
            execution_mode="developer_test",
            developer_test_scenario_id=hashlib.sha256(label.encode()).hexdigest(),
        )
        if defect_id in profile.developer_test_active_defect_ids(context):
            return context
    raise AssertionError(f"No sampled scenario selected {defect_id}")


def _developer_context_without(profile, defect_id):
    for index in range(100):
        label = f"developer-control-{index}"
        context = ClientAPITrialContext(
            task_id=label,
            execution_mode="developer_test",
            developer_test_scenario_id=hashlib.sha256(label.encode()).hexdigest(),
        )
        if defect_id not in profile.developer_test_active_defect_ids(context):
            return context
    raise AssertionError(f"Every sampled scenario selected {defect_id}")


def _telecom_case():
    return development_seed_manifest("telecom")["cases"][0]


def _request_and_pay(runtime):
    case = _telecom_case()
    runtime.environment.user_tools.db.surroundings.phone_number = case["phone_number"]
    runtime.sync_environment()
    response = runtime.request(
        method="POST",
        path=(
            f"/v1/customers/{case['customer_id']}/bills/"
            f"{case['overdue_bill_id']}/payment-requests"
        ),
    )
    assert response.status_code == 200
    runtime.environment.make_tool_call("make_payment", requestor="user")
    runtime.sync_environment()
    return case


def _event(runtime, defect_id, phase):
    return next(
        event
        for event in reversed(runtime.defect_events)
        if event.defect_id == defect_id and event.phase == phase
    )


def test_t1_line_resumption_completes_async_after_paid_projection_converges():
    clock = FakeMonotonicClock()
    runtime = _runtime(clock=clock)
    case = _request_and_pay(runtime)
    projection = _event(runtime, "paid_bill_projection_lag_v1", "propagation_started")
    clock.advance(projection.details["delay_seconds"])
    paid = runtime.request(method="GET", path=f"/v1/bills/{case['overdue_bill_id']}")
    assert paid.body["status"] == "Paid"

    line_path = f"/v1/lines/{case['suspended_line_id']}"
    resumption_path = (
        f"/v1/customers/{case['customer_id']}/lines/"
        f"{case['suspended_line_id']}/resumptions"
    )
    accepted = runtime.request(method="POST", path=resumption_path)
    assert accepted.status_code == 202
    assert runtime.request(method="GET", path=line_path).body["status"] == "Suspended"

    workflow = _event(runtime, "line_resumption_async_v1", "accepted")
    clock.advance(workflow.details["delay_seconds"])
    completed = runtime.request(method="GET", path=accepted.headers["Location"])
    assert completed.body["status"] == "succeeded"
    assert completed.body["result"]["status"] == "Active"
    assert runtime.request(method="GET", path=line_path).body["status"] == "Active"
    assert [call.operation_id for call in runtime.operation_calls].count(
        "resume_line"
    ) == 1
    assert runtime.defect_report()["verification"]["status"] == "passed"


def test_t2_overdue_status_remains_raw_uppercase_schema_drift():
    runtime = _runtime()
    case = _telecom_case()
    response = runtime.request(
        method="GET", path=f"/v1/bills/{case['overdue_bill_id']}"
    )
    contract = build_openapi_contract(
        runtime.environment,
        defect_profile=runtime.defect_profile,
    )
    advertised = contract["paths"]["/v1/bills/{bill_id}"]["get"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"]["properties"]["status"]

    assert response.body["status"] == "OVERDUE"
    assert "Overdue" in advertised["enum"]
    assert "OVERDUE" not in advertised["enum"]


def test_t3_payment_request_is_missing_until_client_offer_is_accepted():
    profile = _profile()
    session = CapabilityDeploymentSession(profile)
    runtime = _runtime(enable_payment=False)
    contract = build_openapi_contract(
        runtime.environment,
        defect_profile=profile,
    )
    path = "/v1/customers/C9001/bills/B9003/payment-requests"

    assert (
        "/v1/customers/{customer_id}/bills/{bill_id}/payment-requests"
        not in contract["paths"]
    )
    assert runtime.request(method="POST", path=path).status_code == 404
    session.offer(
        OfferCapabilityAction(capability_id="telecom_bill_payment_request_v1")
    )
    assert session.freeze().enabled_capability_ids == ()
    session.enable_offered(
        EnableCapabilityAction(capability_id="telecom_bill_payment_request_v1")
    )
    assert session.freeze().enabled_capability_ids == (
        "telecom_bill_payment_request_v1",
    )


def test_x8_host_verification_rejects_resume_without_payment_or_converged_read():
    no_payment = _runtime()
    case = _telecom_case()
    path = (
        f"/v1/customers/{case['customer_id']}/lines/"
        f"{case['suspended_line_id']}/resumptions"
    )
    assert no_payment.request(method="POST", path=path).status_code == 202
    report = no_payment.defect_report()["verification"]
    assert report["status"] == "failed"
    assert report["violations"][0]["reason"] == "projection_trigger_not_observed"

    not_converged = _runtime()
    _request_and_pay(not_converged)
    assert not_converged.request(method="POST", path=path).status_code == 202
    report = not_converged.defect_report()["verification"]
    assert report["status"] == "failed"
    assert report["violations"][0]["resource_id"] == case["overdue_bill_id"]


def test_developer_scenario_sampling_controls_projection_lag_end_to_end():
    profile = _profile()
    active_context = _developer_context_for(profile, "paid_bill_projection_lag_v1")
    inactive_context = _developer_context_without(
        profile, "paid_bill_projection_lag_v1"
    )

    active = _runtime(trial_context=active_context)
    active_case = _request_and_pay(active)
    active_read = active.request(
        method="GET", path=f"/v1/bills/{active_case['overdue_bill_id']}"
    )
    assert active_read.body["status"] == "Awaiting Payment"
    assert _event(active, "paid_bill_projection_lag_v1", "propagation_started")

    inactive = _runtime(trial_context=inactive_context)
    inactive_case = _request_and_pay(inactive)
    inactive_read = inactive.request(
        method="GET", path=f"/v1/bills/{inactive_case['overdue_bill_id']}"
    )
    assert inactive_read.body["status"] == "Paid"
    assert not any(
        event.defect_id == "paid_bill_projection_lag_v1"
        for event in inactive.defect_events
    )


def test_x8_trusted_semantic_replay_preserves_converged_read_observation():
    clock = FakeMonotonicClock()
    live = _runtime(clock=clock)
    case = _request_and_pay(live)
    projection = _event(live, "paid_bill_projection_lag_v1", "propagation_started")
    clock.advance(projection.details["delay_seconds"])
    live.request(method="GET", path=f"/v1/bills/{case['overdue_bill_id']}")
    resumption_path = (
        f"/v1/customers/{case['customer_id']}/lines/"
        f"{case['suspended_line_id']}/resumptions"
    )
    accepted = live.request(method="POST", path=resumption_path)
    workflow = _event(live, "line_resumption_async_v1", "accepted")
    clock.advance(workflow.details["delay_seconds"])
    live.request(method="GET", path=accepted.headers["Location"])
    calls = live.operation_calls
    assert [call.operation_id for call in calls] == [
        "send_payment_request",
        "get_details_by_id",
        "__client_api_projection_observed__",
        "resume_line",
    ]

    replay = _runtime()
    replay.environment.user_tools.db.surroundings.phone_number = case["phone_number"]
    replay.sync_environment()
    replay.replay_operation(
        ToolCall(
            id="semantic-0",
            name=calls[0].operation_id,
            arguments=calls[0].arguments,
            requestor="assistant",
        )
    )
    replay.environment.make_tool_call("make_payment", requestor="user")
    replay.sync_environment()
    for index, call in enumerate(calls[1:], start=1):
        replay.replay_operation(
            ToolCall(
                id=f"semantic-{index}",
                name=call.operation_id,
                arguments=call.arguments,
                requestor="assistant",
            )
        )

    assert replay.defect_report()["verification"]["status"] == "passed"
    assert (
        replay.request(
            method="GET", path=f"/v1/lines/{case['suspended_line_id']}"
        ).body["status"]
        == "Active"
    )


def test_x9_contract_end_date_is_utc_datetime_only_for_nine_task_cohort():
    tasks_by_id = {task.id: task for task in get_tasks()}
    for task_id in sorted(CONTRACT_TASK_IDS):
        runtime = _runtime(task_id, development_seed=False)
        initial = tasks_by_id[task_id].initial_state
        runtime.set_state(
            initial.initialization_data,
            initial.initialization_actions,
            initial.message_history or [],
        )
        before = runtime.snapshot()
        response = runtime.request(method="GET", path="/v1/lines/L1002")
        contract = build_openapi_contract(
            runtime.environment,
            defect_profile=runtime.defect_profile,
        )
        advertised = contract["paths"]["/v1/lines/{line_id}"]["get"]["responses"][
            "200"
        ]["content"]["application/json"]["schema"]["properties"]["contract_end_date"]

        assert response.status_code == 200
        assert response.body["contract_end_date"].endswith("T00:00:00Z")
        assert '"format": "date"' in json.dumps(advertised, sort_keys=True, indent=2)
        assert "date-time" not in json.dumps(advertised)
        assert runtime.snapshot() == before


def test_telecom_defect_impact_matrix_matches_all_119_tasks():
    tasks = get_tasks()
    payment_ids = {
        task.id
        for task in tasks
        if any(
            action.name == "send_payment_request"
            for action in task.evaluation_criteria.actions
        )
    }
    resumption_ids = {
        task.id
        for task in tasks
        if any(
            action.name == "resume_line" for action in task.evaluation_criteria.actions
        )
    }
    profile = _profile()
    date_defect = next(
        defect
        for defect in profile.defects
        if defect.id == "line_contract_end_datetime_v1"
    )

    assert len(tasks) == 119
    assert payment_ids == resumption_ids
    assert len(payment_ids) == 7
    assert set(date_defect.activation.task_ids) == CONTRACT_TASK_IDS
    assert len(CONTRACT_TASK_IDS) == 9
