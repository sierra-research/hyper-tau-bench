"""Tests for versioned Hyper-tau Client API defect deployments."""

import hashlib
import json
from urllib.parse import quote

import pytest
from pydantic import ValidationError

from tau2.hyper.client_api.defects import (
    ClientAPIDeploymentManifest,
    ClientAPITrialContext,
    DefectEvent,
    compile_defect_profile,
    load_defect_profile,
)
from tau2.hyper.client_api.runtime import (
    build_openapi_contract,
    create_domain_client_api_runtime,
)
from tau2.hyper.data_model import HyperMetadata
from tau2.hyper.sandbox.kit import build_kit
from tau2.hyper.task_loader import load_hyper_tau_task


class FakeMonotonicClock:
    def __init__(self, now=100.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def _write_manifest(root, relative_path, *, domain="retail_plus"):
    path = root / f"{relative_path}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "id": relative_path,
                "version": 1,
                "domain": domain,
                "defects": [
                    {
                        "id": "status_case_v1",
                        "kind": "response_value_map",
                        "operation_id": "getOrder",
                        "activation": {
                            "task_ids": ["task-selected"],
                            "call_ordinals": [2],
                        },
                        "path": ["status"],
                        "mapping": {"pending": "PENDING"},
                    }
                ],
            }
        )
    )
    return path


def test_manifest_loader_compiles_stable_profile_and_rejects_wrong_domain(tmp_path):
    _write_manifest(tmp_path, "retail_plus/status_case_v1")

    first = load_defect_profile(
        "retail_plus/status_case_v1",
        expected_domain="retail_plus",
        root=tmp_path,
    )
    first_hash = first.manifest_sha256

    # Formatting is not part of deployment identity.
    manifest_path = tmp_path / "retail_plus/status_case_v1.json"
    manifest_path.write_text(
        json.dumps(json.loads(manifest_path.read_text()), indent=4) + "\n"
    )
    second = load_defect_profile(
        "retail_plus/status_case_v1",
        expected_domain="retail_plus",
        root=tmp_path,
    )

    assert first.manifest_id == "retail_plus/status_case_v1"
    assert first.manifest_sha256 == second.manifest_sha256 == first_hash
    assert first.domain == "retail_plus"
    assert first.defects[0].operation_id == "getOrder"

    with pytest.raises(ValueError, match="targets domain"):
        load_defect_profile(
            "retail_plus/status_case_v1",
            expected_domain="airline_plus",
            root=tmp_path,
        )


def test_manifest_loader_rejects_path_escape_and_invalid_config(tmp_path):
    with pytest.raises(ValueError, match="manifest reference"):
        load_defect_profile("../private", root=tmp_path)

    path = tmp_path / "retail_plus/invalid.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "id": "retail_plus/invalid",
                "version": 1,
                "domain": "retail_plus",
                "defects": [
                    {
                        "id": "bad",
                        "kind": "response_value_map",
                        "operation_id": "getOrder",
                        "path": [],
                        "mapping": {},
                    }
                ],
            }
        )
    )

    with pytest.raises(ValidationError):
        load_defect_profile("retail_plus/invalid", root=tmp_path)


def test_profile_activation_uses_private_task_and_trial_call_ordinal(tmp_path):
    _write_manifest(tmp_path, "retail_plus/status_case_v1")
    profile = load_defect_profile(
        "retail_plus/status_case_v1",
        expected_domain="retail_plus",
        root=tmp_path,
    )

    runtime = create_domain_client_api_runtime(
        "retail_plus",
        defect_profile=profile,
        trial_context=ClientAPITrialContext(
            task_id="task-selected",
            trial_id="trial-1",
        ),
    )

    assert runtime.context.model_dump() == {
        "conversation_id": runtime.context.conversation_id
    }
    assert runtime.trial_context.task_id == "task-selected"
    assert runtime.defect_state.next_call_ordinal("getOrder") == 1
    assert (
        profile.matching_defects(
            kind="response_value_map",
            operation_id="getOrder",
            trial_context=runtime.trial_context,
            call_ordinal=1,
        )
        == ()
    )
    assert runtime.defect_state.next_call_ordinal("getOrder") == 2
    assert [
        defect.id
        for defect in profile.matching_defects(
            kind="response_value_map",
            operation_id="getOrder",
            trial_context=runtime.trial_context,
            call_ordinal=2,
        )
    ] == ["status_case_v1"]

    runtime.record_defect_event(
        DefectEvent(
            defect_id="status_case_v1",
            kind="response_value_map",
            operation_id="getOrder",
            phase="activated",
            call_ordinal=2,
        )
    )
    assert runtime.defect_events[0].defect_id == "status_case_v1"

    runtime.set_state(None, None, [])
    assert runtime.defect_state.call_counts == {}
    assert runtime.defect_events == ()
    assert runtime.trial_context.task_id == "task-selected"


def test_non_selected_task_does_not_activate_profile(tmp_path):
    _write_manifest(tmp_path, "retail_plus/status_case_v1")
    profile = load_defect_profile(
        "retail_plus/status_case_v1",
        expected_domain="retail_plus",
        root=tmp_path,
    )
    runtime = create_domain_client_api_runtime(
        "retail_plus",
        defect_profile=profile,
        trial_context=ClientAPITrialContext(task_id="task-control"),
    )

    assert (
        profile.matching_defects(
            kind="response_value_map",
            operation_id="getOrder",
            trial_context=runtime.trial_context,
            call_ordinal=2,
        )
        == ()
    )
    assert runtime.deployment_metadata() == {
        "manifest_id": "retail_plus/status_case_v1",
        "manifest_sha256": profile.manifest_sha256,
        "manifest_version": 1,
    }


def _developer_context(label: str) -> ClientAPITrialContext:
    return ClientAPITrialContext(
        task_id=f"developer-authored-{label}",
        execution_mode="developer_test",
        developer_test_scenario_id=hashlib.sha256(label.encode()).hexdigest(),
    )


def _developer_exposure_profile():
    payload = {
        "id": "retail_plus/developer-exposure-v1",
        "version": 1,
        "domain": "retail_plus",
        "defects": [
            {
                "id": "always_on",
                "kind": "response_field_rename",
                "operation_id": "getOrder",
                "source_field": "status",
                "target_field": "orderStatus",
            },
            {
                "id": "never_local",
                "kind": "response_value_map",
                "operation_id": "getOrder",
                "activation": {
                    "task_ids": ["hidden-a"],
                    "developer_test": {"exposure_rate": 0, "seed": 1},
                },
                "path": ["status"],
                "mapping": {"pending": "PENDING"},
            },
            {
                "id": "always_local",
                "kind": "response_date_to_datetime",
                "operation_id": "getOrder",
                "activation": {
                    "task_ids": ["hidden-b"],
                    "developer_test": {"exposure_rate": 1, "seed": 2},
                },
                "path": ["created_at"],
            },
            {
                "id": "exclusive_a",
                "kind": "response_amount_sign",
                "operation_id": "getOrder",
                "activation": {
                    "task_ids": ["hidden-c"],
                    "developer_test": {
                        "exposure_rate": 0.5,
                        "seed": 3,
                        "mutually_exclusive_group": "response_cohort",
                    },
                },
                "collection_path": ["payments"],
                "discriminator_field": "kind",
                "discriminator_value": "refund",
                "amount_field": "amount",
                "sign": "negative",
            },
            {
                "id": "exclusive_b",
                "kind": "response_amount_sign",
                "operation_id": "getOrder",
                "activation": {
                    "task_ids": ["hidden-d"],
                    "developer_test": {
                        "exposure_rate": 0.5,
                        "seed": 3,
                        "mutually_exclusive_group": "response_cohort",
                    },
                },
                "collection_path": ["payments"],
                "discriminator_field": "kind",
                "discriminator_value": "refund",
                "amount_field": "amount",
                "sign": "positive",
            },
        ],
    }
    return compile_defect_profile(ClientAPIDeploymentManifest.model_validate(payload))


def test_developer_test_exposure_is_stable_and_honors_rate_boundaries():
    profile = _developer_exposure_profile()
    context = _developer_context("stable")

    first = profile.developer_test_active_defect_ids(context)
    second = profile.developer_test_active_defect_ids(context)

    assert first == second
    assert "never_local" not in first
    assert "always_local" in first
    assert len(first & {"exclusive_a", "exclusive_b"}) == 1


def test_developer_test_exclusive_group_selects_at_most_one_member():
    profile = _developer_exposure_profile()
    observed = set()

    for index in range(100):
        active = profile.developer_test_active_defect_ids(
            _developer_context(f"scenario-{index}")
        )
        selected = active & {"exclusive_a", "exclusive_b"}
        assert len(selected) == 1
        observed.update(selected)

    assert observed == {"exclusive_a", "exclusive_b"}


def test_developer_test_sampling_preserves_always_on_and_final_task_activation():
    profile = _developer_exposure_profile()
    developer_context = _developer_context("baseline")

    assert [
        defect.id
        for defect in profile.matching_defects(
            kind="response_field_rename",
            operation_id="getOrder",
            trial_context=developer_context,
            call_ordinal=1,
        )
    ] == ["always_on"]
    assert (
        profile.matching_defects(
            kind="response_value_map",
            operation_id="getOrder",
            trial_context=developer_context,
            call_ordinal=1,
        )
        == ()
    )

    final_selected = ClientAPITrialContext(task_id="hidden-a")
    assert [
        defect.id
        for defect in profile.matching_defects(
            kind="response_value_map",
            operation_id="getOrder",
            trial_context=final_selected,
            call_ordinal=1,
        )
    ] == ["never_local"]
    final_control = ClientAPITrialContext(task_id="developer-authored-baseline")
    assert (
        profile.matching_defects(
            kind="response_value_map",
            operation_id="getOrder",
            trial_context=final_control,
            call_ordinal=1,
        )
        == ()
    )


def test_hyper_task_manifest_reference_is_host_configuration_for_rest_only():
    metadata = HyperMetadata(
        source_domain="retail_plus",
        task_description="Build a test agent",
        test_task_ids=[],
        client_api_mode="rest",
        client_api_deployment_manifest="retail_plus/status_case_v1",
    )

    assert metadata.client_api_deployment_manifest == "retail_plus/status_case_v1"

    with pytest.raises(ValidationError, match="requires client_api_mode='rest'"):
        HyperMetadata(
            source_domain="retail_plus",
            task_description="Build a test agent",
            test_task_ids=[],
            client_api_deployment_manifest="retail_plus/status_case_v1",
        )


def test_runtime_rejects_manifest_operation_missing_from_domain(tmp_path):
    path = _write_manifest(tmp_path, "retail_plus/status_case_v1")
    data = json.loads(path.read_text())
    data["defects"][0]["operation_id"] = "notARealOperation"
    path.write_text(json.dumps(data))
    profile = load_defect_profile(
        "retail_plus/status_case_v1",
        expected_domain="retail_plus",
        root=tmp_path,
    )

    with pytest.raises(ValueError, match="unknown operation IDs"):
        create_domain_client_api_runtime(
            "retail_plus",
            defect_profile=profile,
        )


def test_deployment_identity_and_selectors_never_enter_developer_kit(
    tmp_path, monkeypatch
):
    manifest_id = "airline_plus/private_deployment_v1"
    profile = compile_defect_profile(
        ClientAPIDeploymentManifest.model_validate(
            {
                "id": manifest_id,
                "version": 1,
                "domain": "airline_plus",
                "defects": [
                    {
                        "id": "private_selector",
                        "kind": "response_value_map",
                        "operation_id": "getReservation",
                        "activation": {"task_ids": ["hidden-task-17"]},
                        "path": ["insurance"],
                        "mapping": {"yes": True},
                    }
                ],
            }
        )
    )
    task = load_hyper_tau_task(
        "003_airline_plus_construction_core_evidence_hard_all_defects_performance_easy"
    )
    task = task.model_copy(
        update={
            "hyper": task.hyper.model_copy(
                update={"client_api_deployment_manifest": manifest_id}
            )
        }
    )
    monkeypatch.setattr(
        "tau2.hyper.sandbox.kit.load_defect_profile",
        lambda *args, **kwargs: profile,
    )

    kit_path = build_kit(task, tmp_path / "kit")
    developer_manifest = json.loads(
        (kit_path / "framework" / "deployment_manifest.json").read_text()
    )
    visible_text = "\n".join(
        path.read_text(errors="ignore")
        for path in kit_path.rglob("*")
        if path.is_file()
    )

    assert not (kit_path / "kit_config.json").exists()
    assert not any(
        token in key
        for key in developer_manifest
        for token in ("deployment", "defect", "profile")
    )
    assert manifest_id not in visible_text
    assert profile.manifest_sha256 not in visible_text
    assert "hidden-task-17" not in visible_text


def test_a2_get_reservation_exposes_boolean_insurance_against_string_schema():
    runtime = create_domain_client_api_runtime(
        "airline_plus",
        development_seed=True,
        deployment_manifest="airline_plus/all_defects_v1",
    )
    before = runtime.snapshot()

    response = runtime.request(
        method="GET",
        path="/v1/reservations/DV9R03",
    )
    contract = build_openapi_contract(
        runtime.environment,
        defect_profile=runtime.defect_profile,
    )
    advertised_insurance = contract["paths"]["/v1/reservations/{reservation_id}"][
        "get"
    ]["responses"]["200"]["content"]["application/json"]["schema"]["properties"][
        "insurance"
    ]

    assert response.status_code == 200
    assert response.body["insurance"] is True
    assert advertised_insurance["enum"] == ["yes", "no"]
    assert advertised_insurance["type"] == "string"
    assert runtime.snapshot() == before
    assert [event.phase for event in runtime.defect_events] == ["response_transformed"]


def test_r2_get_order_renames_status_against_published_schema():
    runtime = create_domain_client_api_runtime(
        "retail_plus",
        development_seed=True,
        deployment_manifest="retail_plus/all_defects_v1",
    )
    before = runtime.snapshot()

    response = runtime.request(
        method="GET",
        path=f"/v1/orders/{quote('#W9000001', safe='')}",
    )
    contract = build_openapi_contract(
        runtime.environment,
        defect_profile=runtime.defect_profile,
    )
    advertised_properties = contract["paths"]["/v1/orders/{order_id}"]["get"][
        "responses"
    ]["200"]["content"]["application/json"]["schema"]["properties"]

    assert response.status_code == 200
    assert response.body["orderStatus"] == "pending"
    assert "status" not in response.body
    assert "status" in advertised_properties
    assert "orderStatus" not in advertised_properties
    assert runtime.snapshot() == before
    assert runtime.defect_events[-1].phase == "response_transformed"
    assert runtime.defect_events[-1].details == {
        "object_path": [],
        "source_field": "status",
        "target_field": "orderStatus",
    }


def test_x3_get_order_emits_negative_refund_without_changing_canonical_amount():
    clock = FakeMonotonicClock()
    runtime = create_domain_client_api_runtime(
        "retail_plus",
        development_seed=True,
        deployment_manifest="retail_plus/all_defects_v1",
        monotonic_clock=clock,
    )
    order_id = "#W9000001"
    order_path = f"/v1/orders/{quote(order_id, safe='')}"

    cancellation = runtime.request(
        method="POST",
        path=f"{order_path}/cancellations",
        body={"reason": "ordered by mistake"},
    )
    canonical_refund = next(
        payment
        for payment in runtime.snapshot()["orders"][order_id]["payment_history"]
        if payment["transaction_type"] == "refund"
    )
    projection = next(
        defect
        for defect in runtime.defect_profile.defects
        if defect.kind == "projection_lag"
    )
    clock.advance(projection.max_delay_seconds)
    observed = runtime.request(method="GET", path=order_path)
    observed_refund = next(
        payment
        for payment in observed.body["payments"]
        if payment["transaction_type"] == "refund"
    )

    assert cancellation.status_code == 200
    assert cancellation.body["payments"][-1]["amount"] > 0
    assert canonical_refund["amount"] > 0
    assert observed.status_code == 200
    assert observed_refund["amount"] == -canonical_refund["amount"]
    assert runtime.defect_events[-1].phase == "response_transformed"


def test_t2_get_bill_exposes_uppercase_overdue_against_title_case_schema():
    runtime = create_domain_client_api_runtime(
        "telecom",
        development_seed=True,
        deployment_manifest="telecom/all_defects_v1",
    )
    before = runtime.snapshot()

    response = runtime.request(method="GET", path="/v1/bills/B9003")
    contract = build_openapi_contract(
        runtime.environment,
        defect_profile=runtime.defect_profile,
    )
    advertised_status = contract["paths"]["/v1/bills/{bill_id}"]["get"]["responses"][
        "200"
    ]["content"]["application/json"]["schema"]["properties"]["status"]

    assert response.status_code == 200
    assert response.body["status"] == "OVERDUE"
    assert "Overdue" in advertised_status["enum"]
    assert "OVERDUE" not in advertised_status["enum"]
    assert runtime.snapshot() == before
    assert runtime.defect_events[-1].phase == "response_transformed"


def test_contract_mismatch_manifests_leave_control_runtime_unchanged():
    airline = create_domain_client_api_runtime(
        "airline_plus",
        development_seed=True,
    )
    retail = create_domain_client_api_runtime(
        "retail_plus",
        development_seed=True,
    )
    telecom = create_domain_client_api_runtime(
        "telecom",
        development_seed=True,
    )

    reservation = airline.request(
        method="GET",
        path="/v1/reservations/DV9R03",
    )
    order = retail.request(
        method="GET",
        path=f"/v1/orders/{quote('#W9000001', safe='')}",
    )
    bill = telecom.request(method="GET", path="/v1/bills/B9003")

    assert reservation.body["insurance"] == "yes"
    assert order.status_code == 200
    assert bill.body["status"] == "Overdue"
    assert airline.defect_events == ()
    assert retail.defect_events == ()
    assert telecom.defect_events == ()
