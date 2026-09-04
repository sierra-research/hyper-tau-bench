"""Repo-wide gate: every banking corpus world sits on the frozen domain clock.

The banking_knowledge domain freezes "now" at 2025-11-14 03:40:00 EST
(``KNOWLEDGE_FIXED_DATE`` / ``get_current_time``), and construction kits ship
that clock verbatim in the SOP front matter. Corpus worlds authored at a later
"today" put delivered artifacts in the model's future, so this gate pins:

1. the domain clock constants and the SOP front matter to each other,
2. every corpus ``anchor_date`` (and per-corpus ``ANCHOR_DATE`` checker
   constant) to the frozen date,
3. training_records event dates to the frozen date, modulo an explicit
   per-file allowlist of genuinely forward-looking references.

Per-corpus ``check_corpus.py`` remains the source of truth for delivered
artifacts (it enforces dates <= ANCHOR_DATE with its own allowlists); this
gate only guarantees all those anchors agree on which day "today" is.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from tau2.domains.banking_knowledge.utils import KNOWLEDGE_FIXED_DATE
from tau2.utils.utils import DATA_DIR

FROZEN_DATE = date(2025, 11, 14)
FROZEN_CLOCK = "2025-11-14 03:40:00 EST"

SECTIONS_ROOT = DATA_DIR / "tau2/hyper/sops/banking_knowledge/sections"
BANKING_SOP = DATA_DIR / "tau2/hyper/sops/banking_sop.md"

# Forward-looking dates a training record may legitimately mention (promo end
# dates, card expiries, eligibility windows, pinned incident-window ends, and
# the explicitly simulated console clocks of incident-response drills). Keyed
# by path relative to SECTIONS_ROOT; values are exact ISO dates allowed past
# the frozen clock.
TRAINING_RECORD_FUTURE_DATES: dict[str, set[str]] = {
    # November promo window end (KB fact: active 11/01-11/30).
    "business_checking_opening_promotions/training_records/case_003.md": {"2025-11-30"},
    "business_savings_opening_promotions/training_records/case_007.md": {"2025-11-30"},
    "business_savings_opening_promotions/training_records/case_008.md": {"2025-11-30"},
    "business_savings_opening_promotions/training_records/case_009.md": {"2025-11-30"},
    # Bronze promo window end (KB fact: 2025-10-01 through 2026-03-31).
    "business_credit_card_selection_promos/training_records/case_001.md": {
        "2026-03-31"
    },
    # Platinum first-year fee-waiver window end (KB fact: through 2026-02-28).
    "business_credit_card_selection_promos/training_records/case_005.md": {
        "2026-02-28"
    },
    "credit_card_closure_retention_downgrade_payoff/training_records/case_016.md": {
        "2026-02-28"
    },
    # EcoCard promo window end (KB fact: runs through 2025-12-15).
    "personal_credit_card_rewards_and_promos/training_records/case_008.md": {
        "2025-12-15"
    },
    # Backend-incident protocol windows are pinned KB facts (11/13 incident
    # protocol until 11/15 23:59; 11/14 incident window 11/14-11/18), and
    # cases C/E/F/G are incident-response drills with explicitly simulated
    # console clocks issued alongside the dated bulletins.
    "credit_card_declines_and_backend_incidents/training_records/case_002.md": {
        "2025-11-15"
    },
    "credit_card_declines_and_backend_incidents/training_records/case_003.md": {
        "2025-11-15",
        "2025-11-16",
    },
    "credit_card_declines_and_backend_incidents/training_records/case_004.md": {
        "2025-11-15"
    },
    "credit_card_declines_and_backend_incidents/training_records/case_005.md": {
        "2025-11-15",
        "2025-11-18",
    },
    "credit_card_declines_and_backend_incidents/training_records/case_006.md": {
        "2025-11-17",
        "2025-11-18",
    },
    "credit_card_declines_and_backend_incidents/training_records/case_007.md": {
        "2025-11-18"
    },
}

_MONTHS = {
    m: i + 1
    for i, m in enumerate(
        [
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ]
    )
}
_DATE_PATTERNS = [
    (
        re.compile(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b"),
        lambda m: (int(m.group(1)), int(m.group(2)), int(m.group(3))),
    ),
    (
        re.compile(r"\b(\d{1,2})/(\d{1,2})/(20\d{2})\b"),
        lambda m: (int(m.group(3)), int(m.group(1)), int(m.group(2))),
    ),
    (
        re.compile(
            r"\b(January|February|March|April|May|June|July|August"
            r"|September|October|November|December)\s+(\d{1,2})(?:st|nd|rd|th)?"
            r",?\s+(20\d{2})\b"
        ),
        lambda m: (int(m.group(3)), _MONTHS[m.group(1).lower()], int(m.group(2))),
    ),
    (
        re.compile(
            r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
            r"[a-z]*\.?\s+(20\d{2})\b",
            re.IGNORECASE,
        ),
        lambda m: (
            int(m.group(3)),
            _MONTHS[[k for k in _MONTHS if k.startswith(m.group(2).lower())][0]],
            int(m.group(1)),
        ),
    ),
]


def _dates_in(text: str) -> set[date]:
    found: set[date] = set()
    for pattern, parse in _DATE_PATTERNS:
        for match in pattern.finditer(text):
            try:
                found.add(date(*parse(match)))
            except ValueError:
                continue
    return found


def test_domain_clock_constants_agree() -> None:
    assert KNOWLEDGE_FIXED_DATE == FROZEN_DATE

    front_matter = BANKING_SOP.read_text().splitlines()[:10]
    stated = [line for line in front_matter if "Current System Time" in line]
    assert stated, "banking_sop.md lost its Current System Time front matter"
    assert FROZEN_CLOCK in stated[0]

    import tau2.domains.banking_knowledge.tools as banking_tools

    tools_source = Path(banking_tools.__file__).read_text()
    assert f"The current time is {FROZEN_CLOCK}." in tools_source


def test_every_corpus_checker_pins_the_frozen_date() -> None:
    offenders = []
    for checker in sorted(SECTIONS_ROOT.glob("*/*/check_corpus.py")):
        match = re.search(
            r"^ANCHOR_DATE\s*=\s*[\"'](\d{4}-\d{2}-\d{2})[\"']",
            checker.read_text(),
            re.MULTILINE,
        )
        if match and match.group(1) != FROZEN_DATE.isoformat():
            offenders.append(f"{checker.relative_to(SECTIONS_ROOT)}: {match.group(1)}")
    assert not offenders, (
        "check_corpus ANCHOR_DATE must equal the frozen domain clock; offenders:\n"
        + "\n".join(offenders)
    )


def test_training_records_carry_no_future_events() -> None:
    offenders = []
    for record in sorted(SECTIONS_ROOT.glob("*/training_records/case_*.md")):
        rel = str(record.relative_to(SECTIONS_ROOT))
        allowed = TRAINING_RECORD_FUTURE_DATES.get(rel, set())
        for found in sorted(_dates_in(record.read_text())):
            if found > FROZEN_DATE and found.isoformat() not in allowed:
                offenders.append(f"{rel}: {found.isoformat()}")
    assert not offenders, (
        "training records mention dates after the frozen clock "
        f"{FROZEN_DATE.isoformat()} (add genuinely forward-looking references "
        "to TRAINING_RECORD_FUTURE_DATES):\n" + "\n".join(offenders)
    )
