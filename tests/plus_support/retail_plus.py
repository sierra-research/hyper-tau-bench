"""Pinned derivation expectations for the retail_plus corpora.

Companion to :mod:`tests.plus_support.airline_plus`. retail_plus (domain data
and hyper-sops fact tree) was originally derived from canonical retail by a
generator and two porters that are no longer part of the benchmark, so the
expectations they contributed are pinned here: the retired refund-window
spellings as literals, and the canonical identifier universe rebuilt from the
committed canonical corpus (``data/tau2/domains/retail``), whose ids are
exactly the domains of the generator's remap tables.

Item ids are deliberately absent from the forbidden set: the port deranges
them, reusing the canonical id strings with different meanings, so their
correctness is proven by the option-combination binding gates instead.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
CANONICAL_DIR = DATA_DIR / "tau2" / "domains" / "retail"
PLUS_DIR = DATA_DIR / "tau2" / "domains" / "retail_plus"

OUTPUT_FILES = ("policy.md", "db.json", "tasks.json", "split_tasks.json")

# Retired canonical refund window (the plus window is 3 to 6 business days),
# in every spelling the 2026-08 audit observed: exact, worded, hyphenated,
# and en-dash forms.
RETIRED_WINDOW_PHRASES = ("5 to 7 business days", "5-7 business days")
RETIRED_WINDOW_PATTERNS = (
    r"(?i)\b(?:5|five)[ \t]*(?:-|–|—|to)[ \t]*(?:-|–|—)?[ \t]*(?:7|seven)"
    r"[ \t-]*(?:business|calendar)?[ \t-]*days?\b",
    r"(?i)\bfive[- ]to[- ]seven\b",
    r"(?<![\d.-])5\s?[–—-]\s?7(?![\d-])",
)


def _email_forms(email: str, first: str, last: str) -> tuple[str, ...]:
    """The textual spellings a canonical email appears in across the corpus.

    Task text quotes user emails in three shapes (dotted, undotted, and
    surname-only), all of which the port had to rewrite.
    """
    match = re.fullmatch(r"([a-z]+)\.([a-z]+)(\d+)@(.+)", email)
    if not match:
        return (email,)
    digits, domain = match.group(3), match.group(4)
    lower_first, lower_last = first.lower(), last.lower()
    return (
        f"{lower_first}.{lower_last}{digits}@{domain}",
        f"{lower_first}{lower_last}{digits}@{domain}",
        f"{lower_last}{digits}@{domain}",
    )


def canonical_identifier_tokens() -> dict[str, set[str]]:
    """Canonical retail tokens that must not appear in retail_plus."""
    db = json.loads((CANONICAL_DIR / "db.json").read_text())
    emails: set[str] = set()
    for user in db["users"].values():
        emails.update(
            _email_forms(
                user["email"],
                user["name"]["first_name"],
                user["name"]["last_name"],
            )
        )
    return {
        "user_id": set(db["users"]),
        "order_id": set(db["orders"]),
        "payment_id": {
            payment_id
            for user in db["users"].values()
            for payment_id in user["payment_methods"]
        },
        "tracking_id": {
            tracking
            for order in db["orders"].values()
            for fulfillment in order["fulfillments"]
            for tracking in fulfillment["tracking_id"]
        },
        "product_id": set(db["products"]),
        "email": emails,
    }


def canonical_zips() -> set[str]:
    db = json.loads((CANONICAL_DIR / "db.json").read_text())
    return {user["address"]["zip"] for user in db["users"].values()} | {
        order["address"]["zip"] for order in db["orders"].values()
    }


def collect_committed_leakage() -> list[str]:
    """Every canonical token or retired window spelling in committed retail_plus.

    Price movement, the item-id derangement, and affine-recovery resistance
    are asserted separately against the committed db; this scan owns the
    identifier and phrase families.
    """
    blob = "\n".join((PLUS_DIR / name).read_text() for name in OUTPUT_FILES)
    tokens = canonical_identifier_tokens()

    leaked = []
    for label, values in tokens.items():
        leaked.extend(f"{label}:{value}" for value in sorted(values) if value in blob)

    # Bare / hash-stripped canonical order spellings. The order ids are stored
    # in their '#W1234567' display form, so 'W1234567' and a bare '1234567'
    # escaped both the port's rewrite and an exact-token scan. The guards keep
    # the digit form from matching inside longer ids (item / tracking) or
    # '_'-joined payment ids.
    for order_id in sorted(tokens["order_id"]):
        digits = order_id.lstrip("#").lstrip("W")
        for pattern, label in (
            (rf"(?<![#\w])W{digits}(?!\d)", "bare_order"),
            (rf"(?<![#\d_W]){digits}(?!\d)", "bare_order_digits"),
        ):
            if re.search(pattern, blob):
                leaked.append(f"{label}:{order_id}")

    for phrase in RETIRED_WINDOW_PHRASES:
        if phrase in blob:
            leaked.append(f"policy phrase: {phrase!r}")
    for pattern in RETIRED_WINDOW_PATTERNS:
        if re.search(pattern, blob):
            leaked.append(f"window spelling: {pattern!r}")
    return leaked


# ---------------------------------------------------------------------------
# Hyper-sops expectations (data/tau2/hyper/sops/retail_plus)
# ---------------------------------------------------------------------------

HYPER_ROOT = DATA_DIR / "tau2" / "hyper"
SOPS_ROOT = HYPER_ROOT / "sops" / "retail_plus"
DOMAIN_NEW = "retail_plus"
RESPONSE_PACK_RULES_PATH = (
    "tau2/hyper/response_phrasing/retail_plus_response_phrasing.yaml"
)

LEGACY_SECTION_IDS = (
    "cancelling_pending_order",
    "changing_pending_order",
    "exchanging_delivered_order",
    "returning_delivered_order",
    "transferring_to_person",
    "updating_default_shipping_address",
    "what_you_can_do",
    "who_you_can_help",
    "wrong_entitlement",
)

HIERARCHY_SECTION_IDS = (
    "customer_identity",
    "manage_customer_profile",
    "manage_delivered_order",
    "manage_pending_order",
    "service_foundations",
)

# Canonical values that must not survive anywhere in the schema/SOP layer. The
# path pattern requires the trailing slash so sops/retail_plus/ never matches.
SCHEMA_FORBIDDEN_PATTERNS = (
    r"5 to 7 business days",
    r"5-7 business days",
    r"(?i)\bfive[- ]to[- ]seven\b",
    r"(?<![\d.-])5\s?[–—-]\s?7(?![\d-])",
    r"(?i)\bseven[- ]day\b",
    r"tau2/hyper/sops/retail/",
)

# The artifact tree additionally bans the canonical escalation window
# (7 to 10) and both windows' single-bound echoes ("a seven-day promise"
# restated the canonical ceiling without any range spelling). It does not
# touch the Slack capture's deliberate "seven to ten calendar days".
ARTIFACT_FORBIDDEN_PHRASES = (
    r"5[- ]to[- ]7",
    r"(?<![\d-])5\s?[–-]\s?7(?![\d-])",
    r"7[- ]to[- ]10",
    r"(?<![\d.-])7\s?[–-]\s?10(?![\d-])",
    r"five to seven business days",
    r"seven to ten business days",
    r"five-to-seven",
    r"seven-to-ten",
    r"(?i)\bseven[- ]day\b",
    r"(?i)\bten[- ]day\b",
    r"tau2/hyper/sops/retail/",
)

# ---------------------------------------------------------------------------
# In-tree authoring pipeline (paths relative to SOPS_ROOT)
# ---------------------------------------------------------------------------

def artifact_forbidden_identifier_patterns() -> list[str]:
    """Canonical identifiers that must be absent from the ported artifact tree.

    Order ids are additionally banned in their hash-stripped URL form (the
    site map's ``/account/orders/W...`` routes); the canonical and plus id
    namespaces are disjoint, so banning every bare canonical form is safe.
    """
    tokens = canonical_identifier_tokens()

    def guard(token: str) -> str:
        return rf"(?<![0-9A-Za-z_]){re.escape(token)}(?![0-9A-Za-z_])"

    patterns: list[str] = []
    for label in ("user_id", "order_id", "product_id", "tracking_id", "payment_id"):
        patterns.extend(guard(token) for token in sorted(tokens[label]))
    patterns.extend(
        guard(token.removeprefix("#")) for token in sorted(tokens["order_id"])
    )
    patterns.extend(re.escape(email) for email in sorted(tokens["email"]))
    # The '#' exclusion keeps HTML character entities (&#10003; is a
    # checkmark) from matching five-digit zips.
    patterns.extend(
        rf"(?<![#\d]){re.escape(zip_code)}(?!\d)"
        for zip_code in sorted(canonical_zips())
    )
    return patterns


def load_spec() -> dict[str, Any]:
    return yaml.safe_load((PLUS_DIR / "delta_spec.yaml").read_text())
