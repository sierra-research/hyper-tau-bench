"""Tests for external transformation packs and shared artifact pooling."""

from tau2.hyper.sandbox.kit import _pool_uploaded_material_names
from tau2.hyper.transformations.base import KitFile


def test_uploaded_material_pool_deduplicates_identical_shared_artifacts():
    shared = KitFile(
        relative_path="uploaded_materials/workspace.json",
        content=b'{"shared": true}',
        artifact_kind="slack_mcp_dump",
    )
    duplicate = KitFile(
        relative_path=shared.relative_path,
        content=shared.content,
        artifact_kind=shared.artifact_kind,
    )

    pooled = _pool_uploaded_material_names([shared, duplicate])

    assert len(pooled) == 1
    assert pooled[0].relative_path == "uploaded_materials/workspace_export.json"


def test_client_carriers_pooled_ordinal_names_do_not_collide():
    """Two sections' unrelated refdocs share a per-section ordinal name;
    neither is a shared carrier, so both client versions ship (pooling
    renames them apart) and no base file is shadow-dropped."""
    from tau2.hyper.sandbox.kit import _substitute_client_carriers

    section_a_doc = KitFile(
        relative_path="uploaded_materials/reference_document_01.pdf",
        content=b"section A schedule",
        artifact_kind="reference_document_pack",
        client_substitute=True,
    )
    section_b_doc = KitFile(
        relative_path="uploaded_materials/reference_document_01.pdf",
        content=b"section B fee sheet",
        artifact_kind="reference_document_pack",
        client_substitute=True,
    )
    section_c_base = KitFile(
        relative_path="uploaded_materials/reference_document_01.pdf",
        content=b"section C base doc",
        artifact_kind="reference_document_pack",
    )

    rows: list[dict[str, str]] = []
    kept = _substitute_client_carriers(
        [section_a_doc, section_b_doc, section_c_base], rows
    )

    assert kept == [section_a_doc, section_b_doc, section_c_base]
    assert rows == []


def test_client_carrier_shadows_base_copy_at_stable_path():
    """A name-stable shared carrier (slack export outside the pooled
    namespace) still drops the base copy and keeps the client version."""
    from tau2.hyper.sandbox.kit import _substitute_client_carriers

    client_export = KitFile(
        relative_path="slack_workspace/workspace_export.json",
        content=b'{"fork": "client"}',
        artifact_kind="slack_mcp_dump",
        client_substitute=True,
    )
    base_export = KitFile(
        relative_path="slack_workspace/workspace_export.json",
        content=b'{"fork": "base"}',
        artifact_kind="slack_mcp_dump",
    )

    rows: list[dict[str, str]] = []
    kept = _substitute_client_carriers([base_export, client_export], rows)

    assert kept == [client_export]
    assert [row["kit_path"] for row in rows] == [
        "slack_workspace/workspace_export.json"
    ]


def test_client_carrier_conflict_at_stable_path_still_raises():
    """Two disagreeing client versions of one name-stable carrier remain
    an authoring error."""
    import pytest

    from tau2.hyper.sandbox.kit import _substitute_client_carriers

    first = KitFile(
        relative_path="slack_workspace/workspace_export.json",
        content=b'{"fork": "client-a"}',
        artifact_kind="slack_mcp_dump",
        client_substitute=True,
    )
    second = KitFile(
        relative_path="slack_workspace/workspace_export.json",
        content=b'{"fork": "client-b"}',
        artifact_kind="slack_mcp_dump",
        client_substitute=True,
    )

    with pytest.raises(ValueError, match="Conflicting client-substituted"):
        _substitute_client_carriers([first, second], [])


def test_client_carrier_preserved_filename_in_pool_is_stable_identity():
    """preserve_filename files keep their names through pooling, so path
    identity (and shadowing) applies even under uploaded_materials/."""
    from tau2.hyper.sandbox.kit import _substitute_client_carriers

    client_screen = KitFile(
        relative_path="uploaded_materials/device_screen_checklist.png",
        content=b"client png",
        artifact_kind="device_ui_screenshot",
        preserve_filename=True,
        client_substitute=True,
    )
    base_screen = KitFile(
        relative_path="uploaded_materials/device_screen_checklist.png",
        content=b"base png",
        artifact_kind="device_ui_screenshot",
        preserve_filename=True,
    )

    rows: list[dict[str, str]] = []
    kept = _substitute_client_carriers([base_screen, client_screen], rows)

    assert kept == [client_screen]
