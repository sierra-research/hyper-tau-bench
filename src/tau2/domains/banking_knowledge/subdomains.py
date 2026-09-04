"""Journey-scoped banking subdomains.

Each subdomain packages a coherent set of banking journeys (sections) as a
policy-embedding domain in the style of retail/airline/telecom: the agent
prompt inlines the subdomain's knowledge-base documents in full and no
retrieval tools are exposed. The transactional DB, banking tools, user tools,
and task definitions are shared with ``banking_knowledge`` — a subdomain only
scopes which tasks run and which documents the policy carries.

Membership is materialized in ``data/tau2/domains/banking_knowledge/
subdomains/manifest.json`` (written by :func:`write_manifest`; regenerate
after editing tasks or section schemas). The manifest is derived data:
``SUBDOMAIN_SECTIONS`` below
is the authoritative grouping of sections into subdomains, and task
assignment follows each task's ``required_documents``.

Task assignment rule: a task belongs to the subdomain owning its *primary
section* — the section whose source documents overlap the task's required
documents the most (ties broken toward the section with fewer source
documents, then alphabetically). A subdomain's document set is the union of
its sections' source documents plus every member task's required documents,
so shared product reference documents may appear in more than one subdomain's
policy — that overlap is intentional, the task partition itself is exact.
"""

from __future__ import annotations

import json
from functools import lru_cache, partial
from pathlib import Path
from typing import Callable, Iterator, Optional

from tau2.data_model.tasks import Task
from tau2.domains.banking_knowledge.data_model import KnowledgeBase, TransactionalDB
from tau2.domains.banking_knowledge.retrieval import PROMPTS_DIR, load_prompt_template
from tau2.domains.banking_knowledge.retrieval_toolkits import KnowledgeToolsPlain
from tau2.domains.banking_knowledge.tools import KnowledgeUserTools
from tau2.domains.banking_knowledge.utils import (
    KNOWLEDGE_DATA_DIR,
    KNOWLEDGE_DOCUMENTS_DIR,
    KNOWLEDGE_TASK_SET_PATH,
)
from tau2.environment.environment import Environment
from tau2.utils.utils import DATA_DIR

SUBDOMAINS_DATA_DIR = KNOWLEDGE_DATA_DIR / "subdomains"
MANIFEST_PATH = SUBDOMAINS_DATA_DIR / "manifest.json"
SUBDOMAIN_PROMPT_TEMPLATE = PROMPTS_DIR / "subdomain_kb.md"
SECTIONS_DIR = DATA_DIR / "tau2" / "hyper" / "sops" / "banking_knowledge" / "sections"

# Registered domain names are ``banking_<key>``.
DOMAIN_NAME_PREFIX = "banking_"

# Authoritative grouping of banking journeys (hyper sections) into subdomains.
# write_manifest() materializes the manifest from this grouping.
SUBDOMAIN_SECTIONS: dict[str, list[str]] = {
    "deposit_opening": [
        "personal_checking_opening_recommendation",
        "personal_savings_opening_recommendation",
        "green_checking_faq",
    ],
    "deposit_services": [
        "savings_apy_boosts_interest_discrepancies",
        "checking_atm_fee_rebates_and_credits",
        "checking_referral_programs_and_optimization",
        "mobile_check_deposit",
        "direct_deposit_delay_and_escalation",
    ],
    "card_selection": [
        "personal_credit_card_application_recommendation",
        "personal_credit_card_rewards_and_promos",
        "cash_back_disputes_and_corrections",
        "credit_card_referrals",
    ],
    "card_servicing": [
        "credit_card_transaction_disputes",
        "credit_limit_increases",
        "credit_card_declines_and_backend_incidents",
        "credit_card_replacements",
        "personal_credit_card_account_services",
        "credit_card_closure_retention_downgrade_payoff",
    ],
    "business": [
        "business_checking_opening_promotions",
        "business_savings_opening_promotions",
        "business_credit_card_selection_promos",
    ],
    "debit_security": [
        "debit_card_lost_stolen_freeze_replace",
        "debit_card_disputes_declines_pin_limits",
        "personal_account_closure_and_debit_cleanup",
        "transfer_and_account_recovery_boundaries",
    ],
}

SUBDOMAIN_SCOPES: dict[str, str] = {
    "deposit_opening": (
        "personal deposit account opening: checking and savings account "
        "recommendation and opening, including the Green checking lineup"
    ),
    "deposit_services": (
        "deposit account servicing: savings APY boosts and interest "
        "discrepancies, ATM fee rebates and credits, checking referral "
        "programs, mobile check deposit, and direct deposit delays"
    ),
    "card_selection": (
        "personal credit card selection and rewards: application "
        "recommendations, rewards and promotions, cash-back disputes and "
        "corrections, and credit card referrals"
    ),
    "card_servicing": (
        "credit card account servicing: transaction disputes, credit limit "
        "increases, declines and backend incidents, card replacements, "
        "account services, and closure/retention/downgrade/payoff"
    ),
    "business": (
        "business banking: business checking and savings account opening "
        "promotions and business credit card selection"
    ),
    "debit_security": (
        "debit cards and account security: lost/stolen/freeze/replace, debit "
        "disputes, declines, PIN and limits, personal account closure and "
        "debit cleanup, and transfer/account-recovery boundaries"
    ),
}


# ---------------------------------------------------------------------------
# Manifest generation (used by write_manifest() and the freshness test;
# runtime reads the committed manifest instead).
# ---------------------------------------------------------------------------


def _load_section_index() -> dict[str, dict]:
    """Map each section to its source document ids and fact count."""
    index: dict[str, dict] = {}
    for schema_path in sorted(SECTIONS_DIR.glob("*/schema.json")):
        section = schema_path.parent.name
        with open(schema_path) as fp:
            schema = json.load(fp)
        doc_ids = set()
        for source_path in schema.get("domain_constraints", {}).get("source_paths", []):
            if "/documents/" in source_path:
                doc_ids.add(Path(source_path).stem)
        index[section] = {
            "doc_ids": doc_ids,
            "facts": len(schema.get("facts", [])),
        }
    return index


def _load_raw_tasks() -> list[dict]:
    """Load raw task dicts from the shared banking tasks directory."""
    tasks = []
    for task_path in sorted(Path(KNOWLEDGE_TASK_SET_PATH).glob("task_*.json")):
        with open(task_path) as fp:
            tasks.append(json.load(fp))
    return tasks


def _primary_section(
    required_docs: set[str], section_index: dict[str, dict]
) -> Optional[str]:
    """The section whose source docs overlap the task's required docs most.

    Ties break toward the section with fewer source documents (the more
    specific journey), then alphabetically, so assignment is deterministic.
    """
    best_key = None
    best_section = None
    for section, info in section_index.items():
        overlap = len(required_docs & info["doc_ids"])
        if overlap == 0:
            continue
        key = (-overlap, len(info["doc_ids"]), section)
        if best_key is None or key < best_key:
            best_key = key
            best_section = section
    return best_section


def _policy_chars(doc_ids: list[str]) -> int:
    total = 0
    for doc_id in doc_ids:
        doc_path = KNOWLEDGE_DOCUMENTS_DIR / f"{doc_id}.json"
        with open(doc_path) as fp:
            doc = json.load(fp)
        total += len(doc.get("title", "")) + len(doc.get("content", ""))
    return total


def build_manifest() -> dict:
    """Compute the subdomain manifest from section schemas and task files.

    Raises if any task cannot be assigned, any referenced document file is
    missing, or a member task requires a document outside its subdomain's
    document set (the latter cannot happen by construction, but is asserted
    as a guard against future rule changes).
    """
    section_index = _load_section_index()
    known_sections = set(section_index)
    grouped_sections = {s for secs in SUBDOMAIN_SECTIONS.values() for s in secs}
    if grouped_sections != known_sections:
        raise ValueError(
            "SUBDOMAIN_SECTIONS is out of sync with the section schemas: "
            f"missing={sorted(known_sections - grouped_sections)} "
            f"unknown={sorted(grouped_sections - known_sections)}"
        )

    section_to_subdomain = {
        section: key for key, secs in SUBDOMAIN_SECTIONS.items() for section in secs
    }

    tasks = _load_raw_tasks()
    assignments: dict[str, list[dict]] = {key: [] for key in SUBDOMAIN_SECTIONS}
    task_primary_section: dict[str, str] = {}
    for task in tasks:
        required = set(task.get("required_documents") or [])
        primary = _primary_section(required, section_index)
        if primary is None:
            raise ValueError(
                f"Task {task['id']} has no required document overlapping any "
                "section's source documents; cannot assign a subdomain."
            )
        key = section_to_subdomain[primary]
        assignments[key].append(task)
        task_primary_section[task["id"]] = primary

    subdomains: dict[str, dict] = {}
    for key, sections in SUBDOMAIN_SECTIONS.items():
        member_tasks = assignments[key]
        doc_ids = set()
        for section in sections:
            doc_ids |= section_index[section]["doc_ids"]
        for task in member_tasks:
            doc_ids |= set(task.get("required_documents") or [])

        missing_files = [
            doc_id
            for doc_id in doc_ids
            if not (KNOWLEDGE_DOCUMENTS_DIR / f"{doc_id}.json").exists()
        ]
        if missing_files:
            raise ValueError(
                f"Subdomain {key} references missing document files: "
                f"{sorted(missing_files)}"
            )

        task_ids = sorted(task["id"] for task in member_tasks)
        doc_ids_sorted = sorted(doc_ids)
        subdomains[key] = {
            "domain_name": f"{DOMAIN_NAME_PREFIX}{key}",
            "scope": SUBDOMAIN_SCOPES[key],
            "sections": list(sections),
            "task_ids": task_ids,
            "doc_ids": doc_ids_sorted,
            "stats": {
                "sections": len(sections),
                "tasks": len(task_ids),
                "facts": sum(section_index[s]["facts"] for s in sections),
                "documents": len(doc_ids_sorted),
                "policy_chars": _policy_chars(doc_ids_sorted),
            },
        }

    return {
        "generated_by": f"{__name__}.write_manifest",
        "note": (
            "Derived data - do not edit by hand. Regenerate after editing "
            "banking tasks or section schemas."
        ),
        "task_primary_sections": dict(sorted(task_primary_section.items())),
        "subdomains": subdomains,
    }


def write_manifest() -> dict:
    """Recompute the subdomain manifest and write it to ``MANIFEST_PATH``.

    Run this after editing banking tasks or the hyper banking section
    schemas; ``test_subdomains.py`` fails while the committed manifest
    differs from a fresh recompute.
    """
    manifest = build_manifest()
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w") as fp:
        json.dump(manifest, fp, indent=2)
        fp.write("\n")
    return manifest


# ---------------------------------------------------------------------------
# Runtime: manifest loading, environment, and tasks
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def load_manifest() -> dict:
    """Load the committed subdomain manifest."""
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"Banking subdomain manifest not found: {MANIFEST_PATH}. "
            "Call write_manifest() in this module to generate it."
        )
    with open(MANIFEST_PATH) as fp:
        return json.load(fp)


def get_subdomain_keys() -> list[str]:
    return list(load_manifest()["subdomains"].keys())


def get_subdomain_domain_names() -> list[str]:
    return [entry["domain_name"] for entry in load_manifest()["subdomains"].values()]


def is_banking_subdomain(domain: Optional[str]) -> bool:
    """True if *domain* is a registered banking subdomain name.

    Used by the runner to extend banking_knowledge-only plumbing (e.g. the
    per-task ``read_log_allowlist``) to the subdomains. Tolerates a missing
    manifest so non-banking code paths never fail on it.
    """
    if not domain or not domain.startswith(DOMAIN_NAME_PREFIX):
        return False
    try:
        return domain in get_subdomain_domain_names()
    except FileNotFoundError:
        return False


def _subdomain_entry(key: str) -> dict:
    subdomains = load_manifest()["subdomains"]
    if key not in subdomains:
        raise KeyError(
            f"Unknown banking subdomain {key!r}. Available: {sorted(subdomains)}"
        )
    return subdomains[key]


@lru_cache(maxsize=None)
def _build_subdomain_policy(key: str) -> str:
    """Assemble the static policy for a subdomain.

    The policy is the shared banking policy header and instructions plus the
    subdomain's knowledge-base documents inlined in full (same format as the
    ``full_kb`` retrieval variant, restricted to the subdomain's documents).
    """
    entry = _subdomain_entry(key)
    knowledge_base = KnowledgeBase.load(str(KNOWLEDGE_DOCUMENTS_DIR))

    docs_markdown: list[str] = []
    missing: list[str] = []
    for doc_id in entry["doc_ids"]:
        doc = knowledge_base.get_document(doc_id)
        if doc is None:
            missing.append(doc_id)
            continue
        docs_markdown.append(f"## {doc.title}\n\n{doc.content}")
    if missing:
        raise ValueError(
            f"Subdomain {key} manifest references documents missing from the "
            f"knowledge base: {missing}. Regenerate the manifest."
        )

    policy = load_prompt_template(SUBDOMAIN_PROMPT_TEMPLATE)
    policy = policy.replace("{{subdomain_scope}}", entry["scope"])
    policy = policy.replace(
        "{{subdomain_documents}}", "\n\n---\n\n".join(docs_markdown)
    )
    return policy


def get_subdomain_environment(
    key: str,
    db: Optional[TransactionalDB] = None,
    task: Optional[Task] = None,
    solo_mode: bool = False,
    read_log_allowlist: Optional[set] = None,
    retrieval_variant: Optional[str] = None,
    retrieval_kwargs: Optional[dict] = None,
) -> Environment:
    """Environment for one banking subdomain.

    Same transactional DB and toolkits as ``banking_knowledge``, but the
    policy inlines the subdomain's documents and no retrieval tools exist.
    """
    if solo_mode:
        raise ValueError("banking subdomains do not support solo mode")
    if retrieval_variant is not None or retrieval_kwargs:
        raise ValueError(
            "Banking subdomains embed their knowledge in the policy; "
            "retrieval variants only apply to the banking_knowledge domain."
        )

    entry = _subdomain_entry(key)

    if db is None:
        from tau2.domains.banking_knowledge.environment import get_db

        db = get_db()

    tools = KnowledgeToolsPlain(db)
    tools.set_read_log_allowlist(read_log_allowlist)
    user_tools = KnowledgeUserTools(db)

    return Environment(
        domain_name=entry["domain_name"],
        policy=_build_subdomain_policy(key),
        tools=tools,
        user_tools=user_tools,
    )


def get_subdomain_tasks(key: str, task_split_name: Optional[str] = None) -> list[Task]:
    """The subdomain's slice of the shared banking task set."""
    from tau2.domains.banking_knowledge.environment import get_tasks

    entry = _subdomain_entry(key)
    wanted = set(entry["task_ids"])
    tasks = [task for task in get_tasks(task_split_name) if task.id in wanted]
    found = {task.id for task in tasks}
    if found != wanted:
        raise ValueError(
            f"Subdomain {key} manifest lists tasks missing from the banking "
            f"task set: {sorted(wanted - found)}. Regenerate the manifest."
        )
    return tasks


def iter_subdomain_registrations() -> Iterator[
    tuple[str, Callable[..., Environment], Callable[..., list[Task]]]
]:
    """Yield (domain_name, env_factory, tasks_loader) for each subdomain."""
    for key, entry in load_manifest()["subdomains"].items():
        yield (
            entry["domain_name"],
            partial(get_subdomain_environment, key),
            partial(get_subdomain_tasks, key),
        )
