"""Versioned contract shared by Hyper-tau hosts and construction runtimes."""

import re

# contract-v6 added local Client API mock dispatch (local-only; task pins
# stayed on contract-v5). contract-v7: kits no longer carry kit_config.json;
# the host injects runtime wiring (domain, client_api_mode) via the sealed
# 'configure' request instead, so maintained pins jump from v5 to v7.
CONSTRUCTION_RUNTIME_CONTRACT_VERSION = 7

DEFAULT_CONSTRUCTION_RUNTIME_IMAGE = (
    f"tau2-construction-runtime:contract-v{CONSTRUCTION_RUNTIME_CONTRACT_VERSION}"
)


def runtime_contract_version_for_image(image: str) -> int:
    """Return the contract version pinned in an image tag, or the default.

    Every maintained bundle is explicitly pinned to ``contract-v7``.
    Digest and commit-tag images have no parseable contract number, so they use
    the current host contract just as they did before versioned task pinning.
    """
    match = re.search(r":contract-v(\d+)$", image)
    if match is not None:
        return int(match.group(1))
    return CONSTRUCTION_RUNTIME_CONTRACT_VERSION
