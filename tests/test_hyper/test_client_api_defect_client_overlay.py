"""Tests for host-only Client knowledge about deployed API defects."""

import pytest
from pydantic import ValidationError

from tau2.hyper.client import ClientContext
from tau2.hyper.client_api.defects import (
    ClientAPIDeploymentManifest,
    compile_defect_profile,
    load_defect_profile,
)
from tau2.hyper.client_sim.api_defect_overlay import (
    render_api_defect_client_overlay,
)
from tau2.hyper.sandbox.orchestrator import SandboxOrchestrator
from tau2.hyper.task_loader import load_hyper_tau_task


def _manifest_payload():
    return {
        "id": "retail_plus/client-aware-v1",
        "version": 1,
        "domain": "retail_plus",
        "defects": [
            {
                "id": "refund_sign",
                "kind": "response_amount_sign",
                "operation_id": "getOrder",
                "activation": {
                    "task_ids": ["hidden-refund-task"],
                    "developer_test": {"exposure_rate": 0.5, "seed": 44},
                },
                "collection_path": ["payments"],
                "discriminator_field": "transaction_type",
                "discriminator_value": "refund",
                "amount_field": "amount",
                "sign": "negative",
            }
        ],
        "client": {
            "published_api_version": "2026-07",
            "deployed_api_version": "2026-08",
            "defects": [
                {
                    "defect_id": "refund_sign",
                    "actual_behavior": (
                        "getOrder returns refund payment amounts as negative values."
                    ),
                    "disclosure_conditions": [
                        (
                            "The Developer reports getOrder and observes a refund "
                            "payment with a negative amount."
                        )
                    ],
                    "expected_remediation": (
                        "Accept the deployed negative refund representation."
                    ),
                    "client_can_deploy_fix": False,
                }
            ],
        },
    }


def test_client_facts_compile_immutably_and_reference_deployed_defects():
    manifest = ClientAPIDeploymentManifest.model_validate(_manifest_payload())
    profile = compile_defect_profile(manifest)

    assert profile.client is manifest.client
    assert profile.client.published_api_version == "2026-07"
    assert profile.client.deployed_api_version == "2026-08"
    assert profile.client.defects[0].client_can_deploy_fix is False

    payload = _manifest_payload()
    payload["client"]["defects"][0]["defect_id"] = "not_deployed"
    with pytest.raises(ValidationError, match="not_deployed"):
        ClientAPIDeploymentManifest.model_validate(payload)


def test_client_facts_reject_duplicate_references_and_identical_versions():
    payload = _manifest_payload()
    payload["client"]["defects"].append(payload["client"]["defects"][0])
    with pytest.raises(ValidationError, match="unique"):
        ClientAPIDeploymentManifest.model_validate(payload)

    payload = _manifest_payload()
    payload["client"]["deployed_api_version"] = "2026-07"
    with pytest.raises(ValidationError, match="must differ"):
        ClientAPIDeploymentManifest.model_validate(payload)


def test_api_defect_overlay_is_separate_evidence_gated_and_nonspecific():
    profile = compile_defect_profile(
        ClientAPIDeploymentManifest.model_validate(_manifest_payload())
    )

    overlay = render_api_defect_client_overlay(profile)

    assert "API deployment facts" in overlay
    assert "getOrder returns refund payment amounts as negative" in overlay
    assert "2026-07" in overlay and "2026-08" in overlay
    assert "Do not volunteer" in overlay
    assert "Developer-test scope: cohort-specific" in overlay
    assert "may be inactive" in overlay
    assert "Do not enumerate other possible cohort behaviors" in overlay
    assert "Can you be more specific about what you're seeing?" in overlay
    vague_rule = overlay.split("VAGUE REPORT RESPONSE", 1)[1].split("\n", 2)[1]
    assert "endpoint" not in vague_rule.lower()
    assert "status" not in vague_rule.lower()
    assert "body" not in vague_rule.lower()
    assert "policy-knowledge" not in overlay


def test_capability_only_overlay_uses_semantic_offer_and_acceptance_rules():
    manifest = ClientAPIDeploymentManifest.model_validate(
        {
            "id": "retail_plus/capability-only-v1",
            "version": 1,
            "domain": "retail_plus",
            "capabilities": [
                {
                    "id": "retail_partial_return_v1",
                    "operation_id": "createOrderReturn",
                    "missing_functionality": (
                        "Return selected products from a delivered purchase."
                    ),
                }
            ],
        }
    )

    overlay = render_api_defect_client_overlay(compile_defect_profile(manifest))

    assert "Return selected products from a delivered purchase" in overlay
    assert "Judge functional meaning, not keywords" in overlay
    assert "action `offer`" in overlay
    assert "Never enable it in the offer turn" in overlay
    assert "action `respond`" in overlay
    assert "request_term_groups" not in overlay


@pytest.mark.parametrize(
    "task_id",
    [
        "003_airline_plus_construction_core_evidence_hard_all_defects_performance_easy",
        "007_retail_plus_construction_core_evidence_seeded_all_defects_performance_easy",
        "015_telecom_construction_core_evidence_hard_all_defects_performance_medium",
    ],
)
def test_all_defects_tasks_enable_client_from_deployment_facts(task_id):
    task = load_hyper_tau_task(task_id)
    orchestrator = SandboxOrchestrator(task, builder=object())

    assert task.client_sections is None
    assert not task.client_instructions
    assert orchestrator._client_enabled()
    prompt = orchestrator._resolve_client_instructions()
    assert "API deployment facts" in prompt
    assert "respond_about_deployable_capability" in prompt
    assert "deployment mismatch in your opening message" in prompt


class _FakeClient:
    def generate_response(self, message, state):
        return f"answer to {message}", {"previous": state}


def test_client_context_records_ordered_discussions_with_deployment_attribution():
    context = ClientContext(
        client=_FakeClient(),
        client_state={"turn": 0},
        deployment_manifest_id="retail_plus/all_defects_v1",
        deployment_manifest_sha256="a" * 64,
    )

    assert context.talk("first") == "answer to first"
    assert context.talk("second") == "answer to second"

    assert context.turns_used == 2
    assert context.result_metadata() == {
        "turns_used": 2,
        "deployment": {
            "manifest_id": "retail_plus/all_defects_v1",
            "manifest_sha256": "a" * 64,
        },
        "discussions": [
            {
                "turn": 1,
                "developer_message": "first",
                "client_response": "answer to first",
            },
            {
                "turn": 2,
                "developer_message": "second",
                "client_response": "answer to second",
            },
        ],
    }


def test_all_defects_manifest_facts_never_enter_candidate_kit(tmp_path):
    from tau2.hyper.sandbox.kit import build_kit

    task = load_hyper_tau_task(
        "007_retail_plus_construction_core_evidence_seeded_all_defects_performance_easy"
    )
    profile = load_defect_profile(
        task.client_api_deployment_manifest,
        expected_domain=task.source_domain,
    )

    build_kit(task, tmp_path)
    corpus = "\n".join(
        path.read_text(errors="replace")
        for path in tmp_path.rglob("*")
        if path.is_file()
    )

    assert profile.manifest_id not in corpus
    assert profile.manifest_sha256 not in corpus
    for fact in profile.client.defects:
        assert fact.actual_behavior not in corpus
