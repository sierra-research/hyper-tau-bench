"""Deterministic Client API delivery-failure and retry-safety tests."""

from urllib.parse import quote

import pytest
from pydantic import ValidationError

from tau2.hyper.client_api.defects import (
    ClientAPIDeploymentManifest,
    ClientAPITrialContext,
)
from tau2.hyper.client_api.development import development_seed_manifest
from tau2.hyper.client_api.runtime import create_domain_client_api_runtime


class FakeMonotonicClock:
    def __init__(self, now=100.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def _runtime(clock, *, task_id="50"):
    return create_domain_client_api_runtime(
        "airline_plus",
        development_seed=True,
        deployment_manifest="airline_plus/all_defects_v1",
        trial_context=ClientAPITrialContext(task_id=task_id, trial_id="trial-1"),
        monotonic_clock=clock,
    )


def _search(runtime):
    search = development_seed_manifest("airline_plus")["booking_search"]
    return runtime.request(
        method="GET",
        path="/v1/flight-itineraries",
        query={
            "origin": search["origin"],
            "destination": search["destination"],
            "departure_date": search["departure_date"],
            "stops": 0,
        },
    )


def _certificate_count(runtime, customer_id):
    customer = runtime.request(
        method="GET", path=f"/v1/customers/{quote(customer_id, safe='')}"
    )
    return len(
        [
            method
            for method in customer.body["payment_methods"]
            if method["source"] == "certificate"
        ]
    )


def test_retry_defect_manifest_contracts_are_strict():
    with pytest.raises(ValidationError, match="max_delay_seconds"):
        ClientAPIDeploymentManifest.model_validate(
            {
                "id": "airline_plus/invalid",
                "version": 1,
                "domain": "airline_plus",
                "defects": [
                    {
                        "id": "limit",
                        "kind": "rate_limit",
                        "operation_id": "searchFlightItineraries",
                        "trigger_call_ordinal": 6,
                        "min_delay_seconds": 5,
                        "max_delay_seconds": 1,
                    }
                ],
            }
        )


def test_sixth_search_is_rate_limited_until_monotonic_deadline():
    clock = FakeMonotonicClock()
    runtime = _runtime(clock)

    for _ in range(5):
        assert _search(runtime).status_code == 200
    before_calls = len(runtime.operation_calls)
    limited = _search(runtime)
    assert limited.status_code == 429
    assert limited.headers["Retry-After"] == "2"
    assert len(runtime.operation_calls) == before_calls

    for _ in range(10):
        assert _search(runtime).status_code == 429
    event = next(
        event
        for event in runtime.defect_events
        if event.kind == "rate_limit" and event.phase == "rate_limited"
    )
    clock.advance(event.details["delay_seconds"] - 0.001)
    assert _search(runtime).status_code == 429
    clock.advance(0.001)
    assert _search(runtime).status_code == 200
    assert len(runtime.operation_calls) == before_calls + 1


def test_certificate_commit_timeout_and_idempotent_retry():
    clock = FakeMonotonicClock()
    runtime = _runtime(clock)
    customer_id = development_seed_manifest("airline_plus")["cases"][0]["customer_id"]
    path = f"/v1/customers/{quote(customer_id, safe='')}/certificates"
    before = _certificate_count(runtime, customer_id)

    timed_out = runtime.request(
        method="POST",
        path=path,
        body={"amount": 85},
        headers={"iDeMpOtEnCy-KeY": "compensation-1"},
    )
    assert timed_out.status_code == 504
    assert _certificate_count(runtime, customer_id) == before + 1
    assert runtime.defect_report()["verification"]["status"] == "passed"
    committed_calls = len(
        [
            call
            for call in runtime.operation_calls
            if call.operation_id == "send_certificate"
        ]
    )

    recovered = runtime.request(
        method="POST",
        path=path,
        body={"amount": 85},
        headers={"IDEMPOTENCY-KEY": "compensation-1"},
    )
    assert recovered.status_code == 201
    assert recovered.body["amount"] == 85
    assert (
        len(
            [
                call
                for call in runtime.operation_calls
                if call.operation_id == "send_certificate"
            ]
        )
        == committed_calls
    )
    assert _certificate_count(runtime, customer_id) == before + 1

    conflict = runtime.request(
        method="POST",
        path=path,
        body={"amount": 170},
        headers={"Idempotency-Key": "compensation-1"},
    )
    assert conflict.status_code == 409
    assert (
        len(
            [
                call
                for call in runtime.operation_calls
                if call.operation_id == "send_certificate"
            ]
        )
        == committed_calls
    )


def test_blind_certificate_retry_duplicates_and_state_resets():
    clock = FakeMonotonicClock()
    runtime = _runtime(clock)
    customer_id = development_seed_manifest("airline_plus")["cases"][0]["customer_id"]
    path = f"/v1/customers/{quote(customer_id, safe='')}/certificates"
    before = _certificate_count(runtime, customer_id)

    assert (
        runtime.request(method="POST", path=path, body={"amount": 85}).status_code
        == 504
    )
    assert (
        runtime.request(method="POST", path=path, body={"amount": 85}).status_code
        == 201
    )
    assert _certificate_count(runtime, customer_id) == before + 2
    report = runtime.defect_report()
    assert report["verification"]["status"] == "failed"
    assert any(
        violation["reason"] == "ambiguous_write_retried_without_idempotency"
        for violation in report["verification"]["violations"]
    )

    runtime.set_state(None, None, [])
    assert runtime.defect_state.storage == {}
    assert runtime.defect_events == ()


def test_timeout_is_limited_to_selected_compensation_tasks():
    runtime = _runtime(FakeMonotonicClock(), task_id="unselected")
    customer_id = development_seed_manifest("airline_plus")["cases"][0]["customer_id"]
    response = runtime.request(
        method="POST",
        path=f"/v1/customers/{quote(customer_id, safe='')}/certificates",
        body={"amount": 85},
    )
    assert response.status_code == 201
