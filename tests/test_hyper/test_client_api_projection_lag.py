"""Monotonic-time Client API projection-lag defect tests."""

from urllib.parse import quote

import pytest
from pydantic import ValidationError

from tau2.data_model.message import ToolCall
from tau2.hyper.client_api.capabilities import (
    CapabilityDeploymentSession,
    EnableCapabilityAction,
)
from tau2.hyper.client_api.defects import (
    ClientAPIDeploymentManifest,
    ClientAPITrialContext,
    load_defect_profile,
)
from tau2.hyper.client_api.development import development_seed_manifest
from tau2.hyper.client_api.runtime import create_domain_client_api_runtime
from tau2.hyper.data_model import EvaluationResult


class FakeMonotonicClock:
    def __init__(self, now=100.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def _runtime(domain, clock, *, task_id="projection-task", trial_id="trial-1"):
    profile = load_defect_profile(f"{domain}/all_defects_v1", expected_domain=domain)
    session = CapabilityDeploymentSession(profile)
    if domain == "retail_plus":
        session.apply(EnableCapabilityAction(capability_id="retail_partial_return_v1"))
    elif domain == "telecom":
        session.apply(
            EnableCapabilityAction(capability_id="telecom_bill_payment_request_v1")
        )
        if task_id == "projection-task":
            task_id = (
                "[service_issue]airplane_mode_on|overdue_bill_suspension[PERSONA:None]"
            )
    return create_domain_client_api_runtime(
        domain,
        development_seed=True,
        defect_profile=profile,
        deployment_snapshot=session.freeze(),
        trial_context=ClientAPITrialContext(task_id=task_id, trial_id=trial_id),
        monotonic_clock=clock,
    )


def _projection_defect(runtime):
    return next(
        defect
        for defect in runtime.defect_profile.defects
        if defect.kind == "projection_lag"
    )


def _latest_started_event(runtime):
    return next(
        event
        for event in reversed(runtime.defect_events)
        if event.kind == "projection_lag" and event.phase == "propagation_started"
    )


def _retail_pending_case():
    return next(
        case
        for case in development_seed_manifest("retail_plus")["cases"]
        if case["id"] == "pending_order"
    )


def _telecom_case():
    return development_seed_manifest("telecom")["cases"][0]


def _pay_telecom_bill(runtime):
    case = _telecom_case()
    # The Client API development seed owns business resources only; bind the
    # simulated user's surroundings as a real task initializer would.
    runtime.environment.user_tools.db.surroundings.phone_number = case["phone_number"]
    runtime.sync_environment()
    customer_id = quote(case["customer_id"], safe="")
    bill_id = quote(case["overdue_bill_id"], safe="")
    payment = runtime.request(
        method="POST",
        path=f"/v1/customers/{customer_id}/bills/{bill_id}/payment-requests",
    )
    assert payment.status_code == 200
    assert payment.body["status"] == "awaiting_payment"
    runtime.environment.make_tool_call("make_payment", requestor="user")
    runtime.sync_environment()
    return case


def test_projection_manifest_documents_and_enforces_clean_surface_requirements():
    with pytest.raises(ValidationError, match="projected_fields"):
        ClientAPIDeploymentManifest.model_validate(
            {
                "id": "telecom/invalid_projection",
                "version": 1,
                "domain": "telecom",
                "defects": [
                    {
                        "id": "invalid_projection",
                        "kind": "projection_lag",
                        "operation_id": "getBill",
                        "trigger_operation_ids": ["createBillPaymentRequest"],
                        "capture_timing": "after_trigger",
                        "start_condition": "projection_change",
                        "resource_id_argument": "bill_id",
                        "read_surfaces": [
                            {
                                "operation_id": "getBill",
                                "resource_id_field": "bill_id",
                            },
                            {
                                "operation_id": "listCustomerBills",
                                "resource_id_field": "bill_id",
                                "collection_path": ["bills"],
                            },
                        ],
                    }
                ],
            }
        )


def test_retail_order_projection_is_complete_time_based_and_authoritative():
    clock = FakeMonotonicClock()
    runtime = _runtime("retail_plus", clock)
    case = _retail_pending_case()
    order_path = f"/v1/orders/{quote(case['order_id'], safe='')}"
    before = runtime.request(method="GET", path=order_path).body

    receipt = runtime.request(
        method="POST",
        path=f"{order_path}/cancellations",
        body={"reason": "ordered by mistake"},
    )
    canonical = runtime.snapshot()["orders"][case["order_id"]]

    assert receipt.status_code == 200
    assert receipt.body["status"] == "cancelled"
    assert canonical["status"] == "cancelled"
    started = _latest_started_event(runtime)
    assert 1.5 <= started.details["delay_seconds"] <= 5.0

    for _ in range(20):
        assert runtime.request(method="GET", path=order_path).body == before
    clock.advance(started.details["delay_seconds"] - 0.001)
    assert runtime.request(method="GET", path=order_path).body == before
    clock.advance(0.001)

    converged = runtime.request(method="GET", path=order_path)
    refund = next(
        payment
        for payment in converged.body["payments"]
        if payment["transaction_type"] == "refund"
    )
    assert converged.body["orderStatus"] == "cancelled"
    assert "status" not in converged.body
    assert refund["amount"] < 0  # Existing response-sign defect runs afterward.
    assert runtime.snapshot()["orders"][case["order_id"]] == canonical
    assert [event.phase for event in runtime.defect_events[-3:]] == [
        "converged",
        "response_transformed",
        "response_transformed",
    ]


def test_projection_delay_is_seeded_reproducible_and_trial_local():
    first = _runtime(
        "retail_plus", FakeMonotonicClock(), task_id="same", trial_id="same"
    )
    second = _runtime(
        "retail_plus", FakeMonotonicClock(), task_id="same", trial_id="same"
    )
    different = _runtime(
        "retail_plus", FakeMonotonicClock(), task_id="same", trial_id="different"
    )

    for runtime in (first, second, different):
        case = _retail_pending_case()
        path = f"/v1/orders/{quote(case['order_id'], safe='')}/cancellations"
        runtime.request(
            method="POST",
            path=path,
            body={"reason": "ordered by mistake"},
        )

    first_delay = _latest_started_event(first).details["delay_seconds"]
    assert first_delay == _latest_started_event(second).details["delay_seconds"]
    assert first_delay != _latest_started_event(different).details["delay_seconds"]

    first.set_state(None, None, [])
    assert first.defect_state.storage == {}
    assert first.defect_events == ()


def test_semantic_replay_arms_the_same_retail_projection():
    clock = FakeMonotonicClock()
    live = _runtime("retail_plus", clock, task_id="replay", trial_id="same")
    case = _retail_pending_case()
    order_path = f"/v1/orders/{quote(case['order_id'], safe='')}"
    before = live.request(method="GET", path=order_path).body
    live.request(
        method="POST",
        path=f"{order_path}/cancellations",
        body={"reason": "ordered by mistake"},
    )
    canonical = live.operation_calls[-1]

    replay = _runtime(
        "retail_plus", FakeMonotonicClock(), task_id="replay", trial_id="same"
    )
    replay.replay_operation(
        ToolCall(
            id="outer:client-api:0",
            name=canonical.operation_id,
            arguments=canonical.arguments,
            requestor="assistant",
        )
    )

    assert replay.snapshot() == live.snapshot()
    assert replay.request(method="GET", path=order_path).body == before
    assert (
        _latest_started_event(replay).details["delay_seconds"]
        == _latest_started_event(live).details["delay_seconds"]
    )


def test_async_return_arms_projection_only_when_terminal_mutation_commits():
    clock = FakeMonotonicClock()
    runtime = _runtime("retail_plus", clock)
    case = next(
        case
        for case in development_seed_manifest("retail_plus")["cases"]
        if case["id"] == "delivered_order"
    )
    order_path = f"/v1/orders/{quote(case['order_id'], safe='')}"
    before = runtime.request(method="GET", path=order_path).body
    item_id = before["items"][0]["item_id"]

    accepted = runtime.request(
        method="POST",
        path=f"{order_path}/returns",
        body={
            "item_ids": [item_id],
            "refund_payment_method_id": case["payment_method_ids"]["credit_card"],
        },
    )
    assert accepted.status_code == 202
    assert not any(event.kind == "projection_lag" for event in runtime.defect_events)

    async_defect = next(
        defect
        for defect in runtime.defect_profile.defects
        if defect.kind == "async_completion"
    )
    clock.advance(async_defect.max_delay_seconds)
    terminal = runtime.request(method="GET", path=accepted.headers["Location"])

    assert terminal.body["status"] == "succeeded"
    assert _latest_started_event(runtime).details["resource_id"] == case["order_id"]
    assert runtime.request(method="GET", path=order_path).body == before


def test_telecom_bill_detail_and_collection_share_time_based_staleness():
    clock = FakeMonotonicClock()
    runtime = _runtime("telecom", clock)
    case = _pay_telecom_bill(runtime)
    bill_path = f"/v1/bills/{quote(case['overdue_bill_id'], safe='')}"
    collection_path = f"/v1/customers/{quote(case['customer_id'], safe='')}/bills"

    canonical_bill = next(
        bill
        for bill in runtime.snapshot()["bills"]
        if bill["bill_id"] == case["overdue_bill_id"]
    )
    assert canonical_bill["status"] == "Paid"
    started = _latest_started_event(runtime)
    assert 1.5 <= started.details["delay_seconds"] <= 5.0

    for _ in range(10):
        assert runtime.request(method="GET", path=bill_path).body["status"] == (
            "Awaiting Payment"
        )
        listed = runtime.request(method="GET", path=collection_path).body["bills"]
        assert (
            next(bill for bill in listed if bill["bill_id"] == case["overdue_bill_id"])[
                "status"
            ]
            == "Awaiting Payment"
        )

    clock.advance(started.details["delay_seconds"])
    assert runtime.request(method="GET", path=bill_path).body["status"] == "Paid"
    listed = runtime.request(method="GET", path=collection_path).body["bills"]
    assert (
        next(bill for bill in listed if bill["bill_id"] == case["overdue_bill_id"])[
            "status"
        ]
        == "Paid"
    )


def test_telecom_verification_report_requires_converged_read_before_resumption():
    clock = FakeMonotonicClock()
    unsafe = _runtime("telecom", clock)
    case = _pay_telecom_bill(unsafe)
    line_path = (
        f"/v1/customers/{quote(case['customer_id'], safe='')}/lines/"
        f"{quote(case['suspended_line_id'], safe='')}"
    )

    unsafe.request(method="POST", path=f"{line_path}/resumptions")
    assert unsafe.defect_report()["verification"]["status"] == "failed"

    safe_clock = FakeMonotonicClock()
    safe = _runtime("telecom", safe_clock)
    case = _pay_telecom_bill(safe)
    started = _latest_started_event(safe)
    safe_clock.advance(started.details["delay_seconds"])
    safe.request(
        method="GET",
        path=f"/v1/bills/{quote(case['overdue_bill_id'], safe='')}",
    )
    safe.request(method="POST", path=f"{line_path}/resumptions")

    assert safe.defect_report()["verification"]["status"] == "passed"


def test_failed_projection_verification_is_folded_into_host_scoring():
    from tau2.hyper._inner import _apply_client_api_defect_report

    result = EvaluationResult(task_id="telecom-task", reward=1.0)
    report = {
        "verification": {
            "status": "failed",
            "violations": [{"defect_id": "paid_bill_projection_lag_v1"}],
        },
        "events": [],
    }

    _apply_client_api_defect_report(result, report)

    assert result.reward == 0.0
    assert result.reward_breakdown == {"CLIENT_API_DEFECT": 0.0}
    assert result.client_api_defect_report == report


def test_async_and_projection_defaults_use_the_same_larger_delay_window():
    retail = _runtime("retail_plus", FakeMonotonicClock())
    async_defect = next(
        defect
        for defect in retail.defect_profile.defects
        if defect.kind == "async_completion"
    )
    projection = _projection_defect(retail)

    assert (async_defect.min_delay_seconds, async_defect.max_delay_seconds) == (
        1.5,
        5.0,
    )
    assert (projection.min_delay_seconds, projection.max_delay_seconds) == (1.5, 5.0)
