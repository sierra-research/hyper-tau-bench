"""Deterministic asynchronous-completion defect tests for Retail+."""

import json
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
from tau2.hyper.client_api.runtime import (
    build_openapi_contract,
    create_domain_client_api_runtime,
)
from tau2.hyper.sandbox.sealed_runner import (
    SealedCandidateEnvironment,
    SealedRunnerConfig,
)


class FakeMonotonicClock:
    def __init__(self, now=100.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def _runtime(
    clock,
    *,
    task_id="task-async",
    trial_id="trial-1",
    defect_profile=None,
):
    profile = defect_profile or load_defect_profile(
        "retail_plus/all_defects_v1", expected_domain="retail_plus"
    )
    session = CapabilityDeploymentSession(profile)
    if profile.capabilities:
        session.apply(EnableCapabilityAction(capability_id="retail_partial_return_v1"))
    return create_domain_client_api_runtime(
        "retail_plus",
        development_seed=True,
        trial_context=ClientAPITrialContext(
            task_id=task_id,
            trial_id=trial_id,
        ),
        monotonic_clock=clock,
        defect_profile=profile,
        deployment_snapshot=session.freeze(),
    )


def _return_request(runtime):
    cases = {
        case["id"]: case for case in development_seed_manifest("retail_plus")["cases"]
    }
    delivered = cases["delivered_order"]
    order_id = delivered["order_id"]
    path = f"/v1/orders/{quote(order_id, safe='')}"
    order = runtime.request(method="GET", path=path).body
    item_id = order["items"][0]["item_id"]
    runtime.set_state(None, None, [])
    return {
        "method": "POST",
        "path": f"{path}/returns",
        "body": {
            "item_ids": [item_id],
            "refund_payment_method_id": delivered["payment_method_ids"]["credit_card"],
        },
        "order_path": path,
    }


def _accept(runtime, request):
    return runtime.request(
        method=request["method"],
        path=request["path"],
        body=request["body"],
    )


def _async_defect(runtime):
    return next(
        defect
        for defect in runtime.defect_profile.defects
        if defect.kind == "async_completion"
    )


def test_published_openapi_stays_synchronous_and_omits_workflow_resource():
    clock = FakeMonotonicClock()
    runtime = _runtime(clock)
    contract = build_openapi_contract(
        runtime.environment,
        defect_profile=runtime.defect_profile,
    )
    session = CapabilityDeploymentSession(runtime.defect_profile)
    session.apply(EnableCapabilityAction(capability_id="retail_partial_return_v1"))
    return_operation = json.loads(
        session.render_enabled_contract("retail_partial_return_v1")
    )

    assert "200" in return_operation["responses"]
    assert "202" not in return_operation["responses"]
    assert "/v1/orders/{order_id}/returns" not in contract["paths"]
    assert "/v1/return-workflows/{workflow_id}" not in contract["paths"]
    defect = _async_defect(runtime)
    assert defect.min_delay_seconds > 0
    assert defect.max_delay_seconds >= defect.min_delay_seconds
    assert not hasattr(defect, "polls_to_complete")


def test_async_manifest_rejects_inverted_delay_range():
    with pytest.raises(ValidationError, match="max_delay_seconds"):
        ClientAPIDeploymentManifest.model_validate(
            {
                "id": "retail_plus/invalid_async",
                "version": 1,
                "domain": "retail_plus",
                "defects": [
                    {
                        "id": "invalid_async",
                        "kind": "async_completion",
                        "operation_id": "createOrderReturn",
                        "status_path": "/v1/workflows/{workflow_id}",
                        "min_delay_seconds": 2,
                        "max_delay_seconds": 1,
                    }
                ],
            }
        )


def test_async_return_uses_elapsed_time_and_completes_exactly_once():
    clock = FakeMonotonicClock()
    runtime = _runtime(clock)
    request = _return_request(runtime)
    before = runtime.snapshot()

    accepted = _accept(runtime, request)

    assert accepted.status_code == 202
    assert accepted.body["status"] == "pending"
    assert accepted.body["workflow_id"].startswith("wf_")
    assert accepted.headers["Location"].endswith(accepted.body["workflow_id"])
    assert int(accepted.headers["Retry-After"]) >= 1
    assert runtime.snapshot() == before
    assert runtime.operation_calls == ()
    assert runtime.defect_events[-1].phase == "accepted"

    location = accepted.headers["Location"]
    for _ in range(20):
        pending = runtime.request(method="GET", path=location)
        assert pending.status_code == 200
        assert pending.body == {
            "workflow_id": accepted.body["workflow_id"],
            "status": "pending",
        }
    assert runtime.snapshot() == before
    assert runtime.operation_calls == ()

    delay = runtime.defect_events[-1].details["delay_seconds"]
    clock.advance(delay - 0.001)
    assert runtime.request(method="GET", path=location).body["status"] == "pending"
    clock.advance(0.001)

    completed = runtime.request(method="GET", path=location)
    after = runtime.snapshot()

    assert completed.status_code == 200
    assert completed.body["status"] == "succeeded"
    assert completed.body["result"]["status"] == "return requested"
    assert after != before
    assert [call.operation_id for call in runtime.operation_calls] == [
        "return_delivered_order_items"
    ]
    assert runtime.defect_events[-1].phase == "completed"

    repeated = runtime.request(method="GET", path=location)
    assert repeated.body == completed.body
    assert runtime.snapshot() == after
    assert [call.operation_id for call in runtime.operation_calls] == [
        "return_delivered_order_items"
    ]

    pending = next(
        case
        for case in development_seed_manifest("retail_plus")["cases"]
        if case["id"] == "pending_order"
    )
    pending_path = f"/v1/orders/{quote(pending['order_id'], safe='')}"
    cancellation = runtime.request(
        method="POST",
        path=f"{pending_path}/cancellations",
        body={"reason": "ordered by mistake"},
    )
    assert cancellation.status_code == 200
    projection = next(
        defect
        for defect in runtime.defect_profile.defects
        if defect.kind == "projection_lag"
    )
    clock.advance(projection.max_delay_seconds)
    observed = runtime.request(method="GET", path=pending_path)
    refund = next(
        payment
        for payment in observed.body["payments"]
        if payment["transaction_type"] == "refund"
    )
    assert refund["amount"] < 0


def test_async_workflow_status_errors_are_public_and_stable():
    runtime = _runtime(FakeMonotonicClock())

    missing = runtime.request(
        method="GET",
        path="/v1/return-workflows/wf_does_not_exist",
    )
    wrong_method = runtime.request(
        method="POST",
        path="/v1/return-workflows/wf_does_not_exist",
    )

    assert missing.status_code == 404
    assert missing.body["error"]["code"] == "workflow_not_found"
    assert wrong_method.status_code == 405
    assert wrong_method.headers["allow"] == "GET"


def test_terminal_failure_is_cached_after_one_completion_attempt(monkeypatch):
    clock = FakeMonotonicClock()
    runtime = _runtime(clock)
    accepted = _accept(runtime, _return_request(runtime))
    defect = _async_defect(runtime)
    attempts = 0
    original = runtime.environment.make_tool_call

    def reject_return(tool_name, /, **kwargs):
        nonlocal attempts
        if tool_name == "return_delivered_order_items":
            attempts += 1
            raise RuntimeError("simulated downstream rejection")
        return original(tool_name, **kwargs)

    monkeypatch.setattr(runtime.environment, "make_tool_call", reject_return)
    clock.advance(defect.max_delay_seconds)

    failed = runtime.request(method="GET", path=accepted.headers["Location"])
    repeated = runtime.request(method="GET", path=accepted.headers["Location"])

    assert failed.body["status"] == "failed"
    assert repeated.body == failed.body
    assert attempts == 1
    assert runtime.operation_calls == ()
    assert runtime.defect_events[-1].phase == "failed"


def test_post_commit_response_failure_does_not_report_mutation_failed(monkeypatch):
    from tau2.hyper.client_api import catalog as catalog_module

    clock = FakeMonotonicClock()
    runtime = _runtime(clock)
    request = _return_request(runtime)
    before = runtime.snapshot()
    accepted = _accept(runtime, request)

    def reject_response(*_args, **_kwargs):
        raise RuntimeError("secret response adapter detail")

    monkeypatch.setattr(
        catalog_module,
        "adapt_operation_response",
        reject_response,
    )
    clock.advance(_async_defect(runtime).max_delay_seconds)

    completed = runtime.request(method="GET", path=accepted.headers["Location"])
    after = runtime.snapshot()
    repeated = runtime.request(method="GET", path=accepted.headers["Location"])

    assert completed.status_code == 200
    assert completed.body == {
        "workflow_id": accepted.body["workflow_id"],
        "status": "succeeded",
        "result": None,
        "warning": {
            "code": "invalid_response_body",
            "message": "The completed operation could not normalize its response",
        },
    }
    assert "secret response adapter detail" not in str(completed.body)
    assert repeated.body == completed.body
    assert after != before
    assert runtime.snapshot() == after
    assert [call.operation_id for call in runtime.operation_calls] == [
        "return_delivered_order_items"
    ]
    assert runtime.defect_events[-1].phase == "completed"
    assert runtime.defect_events[-1].details["response_available"] is False


def test_workflow_identity_and_delay_are_seeded_and_reproducible():
    first = _runtime(FakeMonotonicClock(), task_id="same", trial_id="same")
    second = _runtime(FakeMonotonicClock(), task_id="same", trial_id="same")
    different = _runtime(FakeMonotonicClock(), task_id="same", trial_id="different")

    first_request = _return_request(first)
    first_accept = _accept(first, first_request)
    second_accept = _accept(second, _return_request(second))
    different_accept = _accept(different, _return_request(different))

    assert first_accept.body["workflow_id"] == second_accept.body["workflow_id"]
    assert (
        first.defect_events[-1].details["delay_seconds"]
        == second.defect_events[-1].details["delay_seconds"]
    )
    assert first_accept.body["workflow_id"] != different_accept.body["workflow_id"]
    assert (
        first.defect_events[-1].details["delay_seconds"]
        != different.defect_events[-1].details["delay_seconds"]
    )

    second_workflow = _accept(first, first_request)
    assert second_workflow.body["workflow_id"] != first_accept.body["workflow_id"]
    assert (
        first.defect_events[-1].details["delay_seconds"]
        != first.defect_events[-2].details["delay_seconds"]
    )

    changed_defects = tuple(
        defect.model_copy(update={"seed": defect.seed + 1})
        if defect.kind == "async_completion"
        else defect
        for defect in second.defect_profile.defects
    )
    changed_seed_profile = second.defect_profile.model_copy(
        update={"defects": changed_defects}
    )
    changed_seed = _runtime(
        FakeMonotonicClock(),
        task_id="same",
        trial_id="same",
        defect_profile=changed_seed_profile,
    )
    changed_seed_accept = _accept(changed_seed, _return_request(changed_seed))
    assert changed_seed_accept.body["workflow_id"] != second_accept.body["workflow_id"]
    assert (
        changed_seed.defect_events[-1].details["delay_seconds"]
        != second.defect_events[-1].details["delay_seconds"]
    )


def test_async_workflows_are_discarded_on_trial_reset():
    clock = FakeMonotonicClock()
    runtime = _runtime(clock)
    accepted = _accept(runtime, _return_request(runtime))
    location = accepted.headers["Location"]

    runtime.set_state(None, None, [])

    missing = runtime.request(method="GET", path=location)
    assert missing.status_code == 404
    assert runtime.defect_state.storage == {}
    assert runtime.defect_events == ()


class _StatusRunner:
    def __init__(self, runtime, location):
        self.runtime = runtime
        self.location = location
        self.calls = []

    def request(self, method, payload=None):
        self.calls.append((method, payload or {}))
        if method == "tool_call":
            return self.runtime.request(method="GET", path=self.location).body
        if method == "snapshot":
            return self.runtime.snapshot()
        return {"ok": True}


def test_terminal_status_wrapper_attaches_canonical_semantic_mutation(tmp_path):
    clock = FakeMonotonicClock()
    runtime = _runtime(clock)
    accepted = _accept(runtime, _return_request(runtime))
    clock.advance(_async_defect(runtime).max_delay_seconds)
    runner = _StatusRunner(runtime, accepted.headers["Location"])
    metadata = {
        "domain": "retail_plus",
        "policy": "",
        "tools": {
            "get_return_workflow": {
                "schema": {
                    "type": "function",
                    "function": {
                        "name": "get_return_workflow",
                        "description": "Read a return workflow.",
                        "parameters": {"type": "object", "properties": {}},
                    },
                },
                "return_schema": {"type": "object"},
                "info": {"tool_type": "read"},
                "mutates_state": False,
            }
        },
    }
    environment = SealedCandidateEnvironment(
        SealedRunnerConfig(
            kit_path=tmp_path,
            image="tau2-construction-runtime:contract-v7",
            domain="retail_plus",
            client_api_mode="rest",
        ),
        metadata=metadata,
        runner=runner,
        client_api_runtime=runtime,
    )

    response = environment.get_response(
        ToolCall(
            id="outer-status",
            name="get_return_workflow",
            arguments={},
            requestor="assistant",
        )
    )

    assert [call.name for call in response.semantic_tool_calls] == [
        "return_delivered_order_items"
    ]
    assert response.semantic_tool_calls[0].id == "outer-status:client-api:0"

    repeated = environment.get_response(
        ToolCall(
            id="outer-status-repeat",
            name="get_return_workflow",
            arguments={},
            requestor="assistant",
        )
    )
    assert repeated.semantic_tool_calls == []


def test_semantic_replay_completes_matching_pending_workflow_before_deadline():
    live_clock = FakeMonotonicClock()
    live = _runtime(live_clock, task_id="replay", trial_id="same")
    live_request = _return_request(live)
    live_accept = _accept(live, live_request)
    live_clock.advance(_async_defect(live).max_delay_seconds)
    live_terminal = live.request(
        method="GET",
        path=live_accept.headers["Location"],
    )
    canonical = live.operation_calls[0]

    replay = _runtime(
        FakeMonotonicClock(),
        task_id="replay",
        trial_id="same",
    )
    replay_request = _return_request(replay)
    replay_accept = _accept(replay, replay_request)

    replay.replay_operation(
        ToolCall(
            id="outer-status:client-api:0",
            name=canonical.operation_id,
            arguments=canonical.arguments,
            requestor="assistant",
        )
    )
    replay_terminal = replay.request(
        method="GET",
        path=replay_accept.headers["Location"],
    )

    assert replay_terminal.body == live_terminal.body
    assert replay.snapshot() == live.snapshot()
    assert replay.operation_calls == (canonical,)
