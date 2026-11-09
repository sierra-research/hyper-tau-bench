"""A score-only run keeps what the Client enabled during the build."""

from tau2.hyper.client_api.capabilities import (
    CapabilityDeploymentSession,
    EnableCapabilityAction,
    empty_deployment_snapshot,
)
from tau2.hyper.client_api.defects import load_defect_profile
from tau2.hyper.sandbox.orchestrator import (
    DEPLOYMENT_SNAPSHOT_FILE,
    load_deployment_snapshot,
    write_deployment_snapshot,
)


def test_score_only_loads_the_snapshot_the_build_left(tmp_path):
    """The build writes its sealed snapshot beside the kit; a re-score reads it back.

    A kit with no such file (built before it existed) still scores against the
    empty snapshot, as before.
    """
    assert load_deployment_snapshot(tmp_path) == empty_deployment_snapshot()

    profile = load_defect_profile(
        "retail_plus/all_defects_v1", expected_domain="retail_plus"
    )
    session = CapabilityDeploymentSession(profile)
    session.apply(EnableCapabilityAction(capability_id="retail_partial_return_v1"))
    sealed = session.seal()

    path = write_deployment_snapshot(tmp_path, sealed)

    assert path == tmp_path / DEPLOYMENT_SNAPSHOT_FILE
    assert not path.is_relative_to(tmp_path / "workspace")
    loaded = load_deployment_snapshot(tmp_path)
    assert loaded == sealed
    assert loaded.enables("retail_partial_return_v1")
    assert loaded != empty_deployment_snapshot()
