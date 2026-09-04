"""Baggage-ledger gate for airline_plus (Phase A of the 2026-08 audit fixes).

The standalone cutover carried ``total_baggages``/``nonfree_baggages`` over
from canonical airline verbatim, but the plus allowance matrix changed
(delta_spec ``baggage_allowance``), so 138 reservations kept a
``nonfree_baggages`` that only the CANONICAL matrix explains (137
regular/economy, allowance 1 -> 0; 1 silver/economy, 2 -> 1). This gate pins
the repaired invariant: for every reservation,

    nonfree_baggages == max(0, total_baggages - allowance(membership, cabin) * pax)

under the plus matrix, except the four reservations that are
allowance-inconsistent in canonical airline itself and are deliberately kept
at parity (their payment histories still satisfy the component invariant in
test_standalone_invariants.py, which uses the stored nonfree count).
"""

import json
from pathlib import Path

import pytest
import yaml

from tau2.utils.utils import DATA_DIR

PLUS_DIR = Path(DATA_DIR) / "tau2" / "domains" / "airline_plus"

CABINS = ("basic_economy", "economy", "business")

# Plus reservations whose nonfree_baggages is allowance-inconsistent in
# canonical airline too; kept verbatim for parity with canonical world data.
CANONICAL_PARITY_EXCEPTIONS = {
    "3T9GXF",  # canonical ZTC69Q (silver/business, stored nonfree 1)
    "8LEYAO",  # canonical Z76ICV (regular/business, stored nonfree 1)
    "R4711P",  # canonical ZSZOKG (regular/basic_economy, stored nonfree 0)
    "TL1EAK",  # canonical Z9OE94 (silver/economy, stored nonfree 1)
}


@pytest.fixture(scope="module")
def spec():
    return yaml.safe_load((PLUS_DIR / "delta_spec.yaml").read_text())


@pytest.fixture(scope="module")
def plus_db():
    return json.loads((PLUS_DIR / "db.json").read_text())


def test_nonfree_baggages_match_plus_allowance(plus_db, spec):
    """Every reservation's stored nonfree count derives from the plus matrix;
    the pinned exception set must match the violations exactly, so a repaired
    (or newly broken) exception cannot rot in the pin list silently."""
    matrix = {
        m: spec["baggage_allowance"][m]["new"] for m in spec["baggage_allowance"]
    }
    violations = set()
    for rid, res in plus_db["reservations"].items():
        membership = plus_db["users"][res["user_id"]]["membership"]
        allowance = matrix[membership][CABINS.index(res["cabin"])]
        expected = max(0, res["total_baggages"] - allowance * len(res["passengers"]))
        if res["nonfree_baggages"] != expected:
            violations.add(rid)
    unexpected = violations - CANONICAL_PARITY_EXCEPTIONS
    repaired = CANONICAL_PARITY_EXCEPTIONS - violations
    assert not unexpected, f"allowance-inconsistent outside pin list: {sorted(unexpected)}"
    assert not repaired, f"pinned exceptions no longer inconsistent: {sorted(repaired)}"
