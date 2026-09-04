"""Tests for construction-runtime contract version selection."""

from tau2.hyper.runtime_contract import (
    CONSTRUCTION_RUNTIME_CONTRACT_VERSION,
    DEFAULT_CONSTRUCTION_RUNTIME_IMAGE,
    runtime_contract_version_for_image,
)


def test_default_construction_image_is_versioned():
    assert DEFAULT_CONSTRUCTION_RUNTIME_IMAGE.endswith(
        f":contract-v{CONSTRUCTION_RUNTIME_CONTRACT_VERSION}"
    )
    assert not DEFAULT_CONSTRUCTION_RUNTIME_IMAGE.endswith(":latest")


def test_pinned_legacy_image_keeps_its_runtime_contract_version():
    assert (
        runtime_contract_version_for_image("tau2-construction-runtime:contract-v2") == 2
    )
    assert (
        runtime_contract_version_for_image("registry.example/runtime@sha256:abc")
        == CONSTRUCTION_RUNTIME_CONTRACT_VERSION
    )
