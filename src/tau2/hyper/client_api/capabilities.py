"""Host-owned mutable Client capability deployment plane."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from tau2.hyper.client_api.defects import DefectProfile


class EnableCapabilityAction(BaseModel):
    """Typed allowlisted action produced by the Client control plane."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["enable_capability"] = "enable_capability"
    capability_id: str = Field(min_length=1)


class OfferCapabilityAction(BaseModel):
    """Typed allowlisted offer produced by the Client simulator."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["offer_capability"] = "offer_capability"
    capability_id: str = Field(min_length=1)


class DeploymentSnapshot(BaseModel):
    """Immutable capability state injected into every runtime clone."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled_capability_ids: tuple[str, ...] = ()
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    def enables(self, capability_id: str) -> bool:
        """Return whether routing may execute this capability."""

        return capability_id in self.enabled_capability_ids


def empty_deployment_snapshot() -> DeploymentSnapshot:
    """Return the stable initial snapshot used before any Client action."""

    digest = hashlib.sha256(b'{"enabled":[]}').hexdigest()
    return DeploymentSnapshot(sha256=digest)


class CapabilityDeploymentSession:
    """Run-scoped mutable session limited to manifest-authored capabilities."""

    def __init__(
        self,
        profile: DefectProfile,
    ):
        self.profile = profile
        self._capabilities = {
            capability.id: capability for capability in profile.capabilities
        }
        self._offered: set[str] = set()
        self.offers: list[OfferCapabilityAction] = []
        self._enabled: set[str] = set()
        self.actions: list[EnableCapabilityAction] = []
        self._sealed = False

    def offer(self, action: OfferCapabilityAction) -> bool:
        """Record one allowlisted Client offer; return whether state changed."""

        if self._sealed:
            raise RuntimeError("Capability deployment session is sealed")
        if action.capability_id not in self._capabilities:
            raise ValueError(
                f"Capability {action.capability_id!r} is not allowlisted by the deployment"
            )
        if (
            action.capability_id in self._offered
            or action.capability_id in self._enabled
        ):
            return False
        self._offered.add(action.capability_id)
        self.offers.append(action)
        return True

    def enable_offered(self, action: EnableCapabilityAction) -> bool:
        """Enable an allowlisted capability only after the Client offered it."""

        if action.capability_id not in self._offered:
            raise ValueError(
                f"Capability {action.capability_id!r} must be offered before it is enabled"
            )
        return self.apply(action)

    def apply(self, action: EnableCapabilityAction) -> bool:
        """Atomically apply one allowlisted action; return whether state changed."""

        if self._sealed:
            raise RuntimeError("Capability deployment session is sealed")
        if action.capability_id not in self._capabilities:
            raise ValueError(
                f"Capability {action.capability_id!r} is not allowlisted by the deployment"
            )
        if action.capability_id in self._enabled:
            return False
        self._enabled.add(action.capability_id)
        self.actions.append(action)
        return True

    def freeze(self) -> DeploymentSnapshot:
        """Freeze current mutable state for local tests or hidden clones."""

        enabled = tuple(sorted(self._enabled))
        payload = json.dumps(
            {"enabled": enabled},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return DeploymentSnapshot(
            enabled_capability_ids=enabled,
            sha256=hashlib.sha256(payload).hexdigest(),
        )

    def seal(self) -> DeploymentSnapshot:
        """Freeze submission state and reject every later deployment action."""

        snapshot = self.freeze()
        self._sealed = True
        return snapshot

    def render_enabled_contract(self, capability_id: str) -> str:
        """Render the exact newly enabled operation as JSON."""

        if capability_id not in self._enabled:
            raise ValueError(f"Capability {capability_id!r} is not enabled")
        from tau2.hyper.client_api.runtime import (
            build_openapi_contract,
            create_domain_client_api_runtime,
        )

        runtime = create_domain_client_api_runtime(self.profile.domain)
        contract = build_openapi_contract(runtime.environment)
        operation_id = self._capabilities[capability_id].operation_id
        for path, path_item in contract["paths"].items():
            for method, operation in path_item.items():
                if operation.get("operationId") == operation_id:
                    return json.dumps(
                        {"method": method.upper(), "path": path, **operation},
                        indent=2,
                    )
        raise ValueError(
            f"Enabled capability operation {operation_id!r} is unavailable"
        )
