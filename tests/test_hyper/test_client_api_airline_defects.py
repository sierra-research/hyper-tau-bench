"""End-to-end calibration tests for the Airline+ aggregate defect bundle."""

import hashlib
from copy import deepcopy

import pytest
from pydantic import ValidationError

from tau2.domains.airline_plus.environment import get_tasks
from tau2.hyper.client_api.capabilities import (
    CapabilityDeploymentSession,
    EnableCapabilityAction,
    OfferCapabilityAction,
)
from tau2.hyper.client_api.defects import (
    ClientAPIDeploymentManifest,
    ClientAPITrialContext,
    load_defect_profile,
)
from tau2.hyper.client_api.runtime import (
    build_openapi_contract,
    create_domain_client_api_runtime,
)


class FakeMonotonicClock:
    def __init__(self, now=100.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def _task(task_id):
    return next(task for task in get_tasks() if task.id == task_id)


def _action(task_id, name, ordinal=0):
    actions = [
        action
        for action in _task(task_id).evaluation_criteria.actions
        if action.name == name
    ]
    return actions[ordinal]


def _booking_body(arguments):
    return {
        "customer_id": arguments["user_id"],
        "trip": {
            "origin": arguments["origin"],
            "destination": arguments["destination"],
            "trip_type": arguments["flight_type"],
            "cabin": arguments["cabin"],
            "segments": arguments["flights"],
        },
        "passengers": arguments["passengers"],
        "payment_methods": arguments["payment_methods"],
        "baggage": {
            "total_bags": arguments["total_baggages"],
            "paid_bags": arguments["nonfree_baggages"],
        },
        "insurance": arguments["insurance"],
    }


def _runtime(task_id, clock=None, snapshot=None):
    profile = load_defect_profile(
        "airline_plus/all_defects_v1", expected_domain="airline_plus"
    )
    return create_domain_client_api_runtime(
        "airline_plus",
        defect_profile=profile,
        trial_context=ClientAPITrialContext(task_id=task_id, trial_id="trial-1"),
        monotonic_clock=clock or FakeMonotonicClock(),
        deployment_snapshot=snapshot,
    )


def _developer_context_for(profile, defect_id):
    for index in range(100):
        label = f"developer-booking-{index}"
        context = ClientAPITrialContext(
            task_id=label,
            execution_mode="developer_test",
            developer_test_scenario_id=hashlib.sha256(label.encode()).hexdigest(),
        )
        if defect_id in profile.developer_test_active_defect_ids(context):
            return context
    raise AssertionError(f"No sampled scenario selected {defect_id}")


def _complete(runtime, accepted, clock):
    location = accepted.headers["Location"]
    assert runtime.request(method="GET", path=location).body["status"] == "pending"
    delay = next(
        event.details["delay_seconds"]
        for event in reversed(runtime.defect_events)
        if event.phase == "accepted"
    )
    clock.advance(delay)
    return runtime.request(method="GET", path=location)


def test_a1_booking_completes_asynchronously_exactly_once():
    clock = FakeMonotonicClock()
    runtime = _runtime("8", clock)
    action = _action("8", "book_reservation")
    before = runtime.snapshot()

    accepted = runtime.request(
        method="POST",
        path="/v1/reservations",
        body=_booking_body(action.arguments),
    )

    assert accepted.status_code == 202
    assert runtime.snapshot() == before
    assert runtime.operation_calls == ()
    completed = _complete(runtime, accepted, clock)
    assert completed.status_code == 200
    assert completed.body["status"] == "succeeded"
    assert completed.body["result"]["reservation_id"]
    assert [call.operation_id for call in runtime.operation_calls] == [
        "book_reservation"
    ]
    repeated = runtime.request(method="GET", path=accepted.headers["Location"])
    assert repeated.body == completed.body
    assert len(runtime.operation_calls) == 1


def test_developer_booking_scenarios_expose_exactly_one_conflicting_response():
    profile = load_defect_profile(
        "airline_plus/all_defects_v1", expected_domain="airline_plus"
    )
    action = _action("8", "book_reservation")

    async_runtime = create_domain_client_api_runtime(
        "airline_plus",
        defect_profile=profile,
        trial_context=_developer_context_for(profile, "reservation_booking_async_v1"),
        monotonic_clock=FakeMonotonicClock(),
    )
    timeout_runtime = create_domain_client_api_runtime(
        "airline_plus",
        defect_profile=profile,
        trial_context=_developer_context_for(
            profile, "reservation_booking_post_commit_timeout_v1"
        ),
        monotonic_clock=FakeMonotonicClock(),
    )

    async_response = async_runtime.request(
        method="POST",
        path="/v1/reservations",
        body=_booking_body(action.arguments),
    )
    timeout_response = timeout_runtime.request(
        method="POST",
        path="/v1/reservations",
        body=_booking_body(action.arguments),
        headers={"Idempotency-Key": "developer-booking"},
    )

    assert async_response.status_code == 202
    assert timeout_response.status_code == 504
    assert not any(
        event.kind == "post_commit_timeout" for event in async_runtime.defect_events
    )
    assert not any(
        event.kind == "async_completion" for event in timeout_runtime.defect_events
    )


def test_x4_itinerary_replacement_is_async_and_old_trip_remains_authoritative():
    clock = FakeMonotonicClock()
    runtime = _runtime("7", clock)
    action = _action("7", "update_reservation_flights")
    reservation_id = action.arguments["reservation_id"]
    path = f"/v1/reservations/{reservation_id}"
    before = deepcopy(runtime.request(method="GET", path=path).body["trip"])

    accepted = runtime.request(
        method="PUT",
        path=f"{path}/itinerary",
        body={
            "cabin": action.arguments["cabin"],
            "segments": action.arguments["flights"],
            "payment_method_id": action.arguments["payment_id"],
        },
    )

    assert accepted.status_code == 202
    assert runtime.request(method="GET", path=path).body["trip"] == before
    completed = _complete(runtime, accepted, clock)
    assert completed.body["status"] == "succeeded"
    assert completed.body["result"]["trip"] != before
    assert runtime.request(method="GET", path=path).body["trip"] != before
    assert [call.operation_id for call in runtime.operation_calls].count(
        "update_reservation_flights"
    ) == 1


def test_a3_cancellation_is_missing_until_client_offer_is_accepted():
    profile = load_defect_profile(
        "airline_plus/all_defects_v1", expected_domain="airline_plus"
    )
    session = CapabilityDeploymentSession(profile)
    initial = session.freeze()
    runtime = _runtime("7", snapshot=initial)
    initial_contract = build_openapi_contract(
        runtime.environment,
        defect_profile=profile,
    )
    path = "/v1/reservations/JJAOMK/cancellations"

    assert (
        "/v1/reservations/{reservation_id}/cancellations"
        not in initial_contract["paths"]
    )
    assert runtime.request(method="POST", path=path).status_code == 404
    session.offer(
        OfferCapabilityAction(capability_id="airline_reservation_cancellation_v1")
    )
    assert session.freeze().enabled_capability_ids == ()
    session.enable_offered(
        EnableCapabilityAction(capability_id="airline_reservation_cancellation_v1")
    )
    enabled = _runtime("7", snapshot=session.freeze())
    enabled_contract = build_openapi_contract(
        enabled.environment,
        defect_profile=profile,
    )
    assert (
        "/v1/reservations/{reservation_id}/cancellations"
        not in enabled_contract["paths"]
    )
    assert enabled.request(method="POST", path=path).status_code == 200


def test_x5_booking_timeout_recovers_same_server_id_with_idempotency_key():
    runtime = _runtime("23")
    action = _action("23", "book_reservation")
    customer_path = f"/v1/customers/{action.arguments['user_id']}"
    before_ids = runtime.request(method="GET", path=customer_path).body[
        "reservation_ids"
    ]
    request = {
        "method": "POST",
        "path": "/v1/reservations",
        "body": _booking_body(action.arguments),
        "headers": {"Idempotency-Key": "booking-23-1"},
    }

    timed_out = runtime.request(**request)
    after_ids = runtime.request(method="GET", path=customer_path).body[
        "reservation_ids"
    ]
    recovered = runtime.request(**request)

    assert timed_out.status_code == 504
    assert len(after_ids) == len(before_ids) + 1
    assert recovered.status_code == 201
    assert recovered.body["reservation_id"] == next(
        reservation_id
        for reservation_id in after_ids
        if reservation_id not in before_ids
    )
    assert [call.operation_id for call in runtime.operation_calls].count(
        "book_reservation"
    ) == 1
    assert runtime.defect_report()["verification"]["status"] == "passed"


def test_a6_customer_reservations_use_undocumented_cursor_pages():
    runtime = _runtime("4")
    path = "/v1/customers/helena_oliveira_9276"
    first = runtime.request(method="GET", path=path)
    second = runtime.request(
        method="GET", path=path, query={"cursor": first.body["next_cursor"]}
    )
    contract = build_openapi_contract(
        runtime.environment, defect_profile=runtime.defect_profile
    )
    operation = contract["paths"]["/v1/customers/{customer_id}"]["get"]

    assert len(first.body["reservation_ids"]) == 3
    assert len(second.body["reservation_ids"]) == 2
    assert "next_cursor" not in second.body
    assert set(first.body["reservation_ids"] + second.body["reservation_ids"]) == {
        "GMMG59",
        "JT2IOU",
        "GNPNOI",
        "S5LQFI",
        "ZI4VIJ",
    }
    assert not any(
        parameter["name"] == "cursor" for parameter in operation["parameters"]
    )


def test_booking_async_and_post_commit_timeout_cohorts_are_disjoint():
    profile = load_defect_profile(
        "airline_plus/all_defects_v1", expected_domain="airline_plus"
    )
    booking_async = next(
        defect
        for defect in profile.defects
        if defect.kind == "async_completion"
        and defect.operation_id == "createReservation"
    )
    booking_timeout = next(
        defect
        for defect in profile.defects
        if defect.kind == "post_commit_timeout"
        and defect.operation_id == "createReservation"
    )
    assert set(booking_async.activation.task_ids).isdisjoint(
        booking_timeout.activation.task_ids
    )
    assert set(booking_async.activation.task_ids) | set(
        booking_timeout.activation.task_ids
    ) == {
        "8",
        "14",
        "20",
        "23",
        "24",
        "25",
        "29",
        "35",
        "53",
        "56",
        "58",
        "65",
    }


def test_manifest_rejects_overlapping_async_and_post_commit_timeout_cohorts():
    with pytest.raises(ValidationError, match="overlapping async and post-commit"):
        ClientAPIDeploymentManifest.model_validate(
            {
                "id": "airline_plus/invalid_overlap",
                "version": 1,
                "domain": "airline_plus",
                "defects": [
                    {
                        "id": "async",
                        "kind": "async_completion",
                        "operation_id": "createReservation",
                        "activation": {"task_ids": ["23"]},
                        "status_path": "/v1/workflows/{workflow_id}",
                    },
                    {
                        "id": "timeout",
                        "kind": "post_commit_timeout",
                        "operation_id": "createReservation",
                        "activation": {
                            "task_ids": ["23"],
                            "call_ordinals": [1],
                        },
                    },
                ],
            }
        )


def test_airline_defect_impact_matrix_matches_all_67_tasks():
    tasks = get_tasks()

    def impact(tool_name):
        affected = [
            task
            for task in tasks
            if any(
                action.name == tool_name for action in task.evaluation_criteria.actions
            )
        ]
        calls = sum(
            action.name == tool_name
            for task in tasks
            for action in task.evaluation_criteria.actions
        )
        return len(affected), calls

    assert len(tasks) == 67
    assert impact("book_reservation") == (12, 14)
    assert impact("cancel_reservation") == (12, 16)
    assert impact("update_reservation_flights") == (14, 21)
    assert impact("get_user_details") == (14, 14)
    assert impact("send_certificate") == (3, 3)
    search_names = {"search_direct_flight", "search_onestop_flight"}
    search_tasks = {
        task.id
        for task in tasks
        if any(
            action.name in search_names for action in task.evaluation_criteria.actions
        )
    }
    search_calls = sum(
        action.name in search_names
        for task in tasks
        for action in task.evaluation_criteria.actions
    )
    assert (len(search_tasks), search_calls) == (8, 20)
