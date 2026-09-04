"""Data model helpers for the banking_knowledge domain.

This domain's persistent records live behind the Client REST API
(``client_api/openapi.yaml``); there is no on-disk database file shipped
with this kit for the agent to load directly. ``self.client_api.request(...)``
already returns parsed JSON (via ``response.body``), so ``workspace/tools.py``
works directly with those dictionaries rather than through a separate ORM-style
model layer here.

This module is kept as a placeholder integration point in case future
workspace code wants shared typed helpers for REST payloads. It intentionally
contains no domain-specific field definitions, since inventing resource shapes
that are not documented in ``client_api/openapi.yaml`` would risk diverging
from the authoritative contract.
"""

from typing import Any, Dict


def as_dict(payload: Any) -> Dict[str, Any]:
    """Normalize a Client API response body to a plain dict.

    Client API responses are already JSON-compatible dicts. This helper
    exists so call sites have a single, explicit place to route payloads
    through if that ever needs to change, without scattering isinstance
    checks across tools.py.
    """
    if isinstance(payload, dict):
        return payload
    if payload is None:
        return {}
    raise TypeError(f"Expected a JSON object from the Client API, got {type(payload)!r}")
