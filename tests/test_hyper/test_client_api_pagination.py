"""Deterministic Client API pagination and incomplete-result tests."""

from pydantic import ValidationError

from tau2.hyper.client_api.defects import ClientAPIDeploymentManifest
from tau2.hyper.client_api.development import development_seed_manifest
from tau2.hyper.client_api.runtime import (
    build_openapi_contract,
    create_domain_client_api_runtime,
)


def _runtime():
    return create_domain_client_api_runtime(
        "airline_plus",
        development_seed=True,
        deployment_manifest="airline_plus/all_defects_v1",
    )


def _query(**extra):
    search = development_seed_manifest("airline_plus")["booking_search"]
    return {
        "origin": search["origin"],
        "destination": search["destination"],
        "departure_date": search["departure_date"],
        "stops": 0,
        **extra,
    }


def _economy_price(itinerary):
    return sum(
        next(
            offer["price"]
            for offer in segment["cabin_offers"]
            if offer["cabin"] == "economy"
        )
        for segment in itinerary["segments"]
    )


def test_pagination_manifest_rejects_invalid_page_size():
    try:
        ClientAPIDeploymentManifest.model_validate(
            {
                "id": "airline_plus/invalid",
                "version": 1,
                "domain": "airline_plus",
                "defects": [
                    {
                        "id": "pagination",
                        "kind": "pagination",
                        "operation_id": "searchFlightItineraries",
                        "collection_path": ["itineraries"],
                        "page_size": 0,
                    }
                ],
            }
        )
    except ValidationError as error:
        assert "page_size" in str(error)
    else:
        raise AssertionError("zero page size should be rejected")


def test_flight_search_best_itinerary_is_on_later_page():
    runtime = _runtime()
    first = runtime.request(method="GET", path="/v1/flight-itineraries", query=_query())

    assert first.status_code == 200
    assert len(first.body["itineraries"]) == 2
    cursor = first.body["next_cursor"]
    assert cursor.startswith("cur_")

    second = runtime.request(
        method="GET",
        path="/v1/flight-itineraries",
        query=_query(cursor=cursor),
    )
    assert second.status_code == 200
    assert len(second.body["itineraries"]) == 1
    assert "next_cursor" not in second.body

    all_results = first.body["itineraries"] + second.body["itineraries"]
    assert min(all_results, key=_economy_price) in second.body["itineraries"]


def test_cursor_is_deterministic_query_bound_and_trial_local():
    first_runtime = _runtime()
    second_runtime = _runtime()
    first = first_runtime.request(
        method="GET", path="/v1/flight-itineraries", query=_query()
    )
    repeated = second_runtime.request(
        method="GET", path="/v1/flight-itineraries", query=_query()
    )
    assert first.body["next_cursor"] == repeated.body["next_cursor"]

    mismatched = first_runtime.request(
        method="GET",
        path="/v1/flight-itineraries",
        query={
            **_query(cursor=first.body["next_cursor"]),
            "departure_date": "2099-01-01",
        },
    )
    assert mismatched.status_code == 400

    before_calls = len(second_runtime.operation_calls)
    foreign = second_runtime.request(
        method="GET",
        path="/v1/flight-itineraries",
        query=_query(cursor="cur_unknown"),
    )
    assert foreign.status_code == 400
    assert len(second_runtime.operation_calls) == before_calls

    first_runtime.set_state(None, None, [])
    assert first_runtime.defect_state.storage == {}


def test_invalid_cursor_does_not_consume_rate_limit_ordinal():
    runtime = _runtime()
    for _ in range(5):
        assert (
            runtime.request(
                method="GET", path="/v1/flight-itineraries", query=_query()
            ).status_code
            == 200
        )

    invalid = runtime.request(
        method="GET",
        path="/v1/flight-itineraries",
        query=_query(cursor="cur_unknown"),
    )
    assert invalid.status_code == 400
    assert runtime.defect_state.call_counts["searchFlightItineraries"] == 5

    limited = runtime.request(
        method="GET", path="/v1/flight-itineraries", query=_query()
    )
    assert limited.status_code == 429


def test_pagination_remains_absent_from_published_openapi():
    runtime = _runtime()
    operation = build_openapi_contract(
        runtime.environment, defect_profile=runtime.defect_profile
    )["paths"]["/v1/flight-itineraries"]["get"]
    assert operation["x-api-pagination"] == "none"
    assert not any(
        parameter["name"] == "cursor" for parameter in operation["parameters"]
    )
