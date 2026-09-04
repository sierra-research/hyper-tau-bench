"""
Render Client-simulator instructions from section fact schemas.

The Client plays the business stakeholder who hired the Developer. Its
scope is three explicit lists derived from the task's variant:

- **held** facts (``client_knowledge`` bundle members) exist in no kit
  artifact; the Client answers questions about them plainly — it is the
  only source.
- **confirmable** facts (``confirmable_fact_ids`` on the same member)
  stay artifact-carried; the Client confirms or denies a specific reading
  the Developer proposes, and never supplies the correct version.
- **everything else** the Client points back to the records — it will
  not confirm, deny, or discuss it.

The prompt embeds only the held and confirmable fact statements, so the
Client cannot adjudicate (or leak) anything outside its declared scope
and the artifact-reading stays load-bearing. Rendering is fully
deterministic (no LLM calls) so the prompt can be inspected, diffed, and
unit-tested.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from tau2.utils.utils import DATA_DIR

SOPS_ROOT = Path("tau2/hyper/sops")

# Stakeholder-facing description of each source domain's business.
DOMAIN_BUSINESS: dict[str, str] = {
    "airline": "a mid-size airline",
    "airline_plus": "a mid-size airline",
    "retail": "an online retail company",
    "retail_plus": "an online retail company",
    "telecom": "a telecom carrier",
    "banking_knowledge": "a retail bank",
}


class Fact(BaseModel):
    """One atomic policy fact from a section fact schema."""

    id: str
    category: str = "general"
    statement: str


class SectionFacts(BaseModel):
    """The facts one SOP section decomposes into."""

    section_id: str
    facts: list[Fact]

    @property
    def categories(self) -> list[str]:
        seen: dict[str, None] = {}
        for fact in self.facts:
            seen.setdefault(fact.category, None)
        return list(seen)


class RenderedClientInstructions(BaseModel):
    """A rendered Client system prompt plus its provenance."""

    domain: str
    section_ids: list[str]
    prompt: str
    #: Total facts in the rendered sections (provenance; the prompt embeds
    #: only the held and confirmable subsets).
    fact_count: int
    #: Facts the Client alone holds (``client_knowledge`` bundle members);
    #: these appear in no kit artifact and the Client answers them directly.
    held_fact_count: int = 0
    #: Artifact-carried facts the Client may confirm or deny a reading of.
    confirmable_fact_count: int = 0
    #: Held facts whose kit artifacts carry declared divergent readings;
    #: the Client states the current version when asked to settle them.
    contested_fact_count: int = 0


def _sections_dir(domain: str, data_dir: Path | None = None) -> Path:
    return (data_dir or DATA_DIR) / SOPS_ROOT / domain / "sections"


def list_section_ids(domain: str, data_dir: Path | None = None) -> list[str]:
    """Section ids of a domain that have a fact schema."""
    sections_dir = _sections_dir(domain, data_dir)
    if not sections_dir.is_dir():
        raise FileNotFoundError(
            f"No sections directory for domain {domain!r}: {sections_dir}"
        )
    return sorted(p.parent.name for p in sections_dir.glob("*/schema.json"))


def load_section_facts(
    domain: str, section_id: str, data_dir: Path | None = None
) -> SectionFacts:
    """Load one section's fact schema into a :class:`SectionFacts`."""
    schema_path = _sections_dir(domain, data_dir) / section_id / "schema.json"
    if not schema_path.is_file():
        raise FileNotFoundError(
            f"No fact schema for section {section_id!r}: {schema_path}"
        )
    schema = json.loads(schema_path.read_text())
    facts = [
        Fact(
            id=str(entry["id"]),
            category=str(entry.get("category") or "general"),
            statement=str(entry["statement"]),
        )
        for entry in schema.get("facts") or []
        if isinstance(entry, dict) and "id" in entry and "statement" in entry
    ]
    if not facts:
        raise ValueError(f"Section {section_id!r} declares no well-formed facts")
    return SectionFacts(section_id=section_id, facts=facts)


def _humanize(identifier: str) -> str:
    return identifier.replace("_", " ").strip()


CLIENT_SYSTEM_PROMPT = """\
<role>
You are the customer-support operations lead at {business}. You have hired an \
outside consultant — the developer — to write the standard operating policy for \
your customer-facing support agent. Instead of a rulebook, you handed the \
developer a package of company records: approved case transcripts, email \
archives, website captures, process decks, and similar material. {records_scope}
</role>

<what_you_want_built>
A complete, correct operating policy covering: {area_list}. The records are \
the source of truth — the developer's job is to work them out, not to \
interview you point by point.
</what_you_want_built>
{held_block}{contested_block}{confirmable_block}
<how_you_behave>
{rules}
</how_you_behave>

<opening>
When asked to open the conversation, briefly introduce yourself, say what you \
need built and what material you have handed over, and invite the developer to \
get started.
</opening>
""".strip()

_RECORDS_SCOPE_ALL = "The rules the agent must follow are all in those records."

_RECORDS_SCOPE_WITH_HELD = (
    "Nearly all the rules the agent must follow are in those records; a few "
    "points never made it into any document and live only in your head (see "
    "<what_only_you_know> below)."
)

_RECORDS_SCOPE_WITH_CONTESTED = (
    "The rules the agent must follow are in those records, but on a few "
    "points the documents do not agree with each other; you know which "
    "version is current (see <records_in_conflict> below)."
)

_RECORDS_SCOPE_WITH_HELD_AND_CONTESTED = (
    "Nearly all the rules the agent must follow are in those records, but a "
    "few points never made it into any document and live only in your head "
    "(see <what_only_you_know> below), and on a few others the documents do "
    "not agree with each other; you know which version is current (see "
    "<records_in_conflict> below)."
)

_HELD_BLOCK_TEMPLATE = """
<what_only_you_know>
These points never made it into the records you handed over — the developer \
cannot find them in any document, so they can only get them from you:

{held_knowledge}
</what_only_you_know>
"""

_CONTESTED_BLOCK_TEMPLATE = """
<records_in_conflict>
On these points the records you handed over do not agree — different \
documents show different versions, and nothing in the package settles which \
one is current. You know what is actually in force:

{contested_knowledge}
</records_in_conflict>
"""

_CONFIRMABLE_BLOCK_TEMPLATE = """
<questions_you_can_settle>
These points ARE in the records, but you know from experience that people \
misread them, so you are willing to check a specific reading against your own \
knowledge:

{confirmable_knowledge}
</questions_you_can_settle>
"""

_RULE_CHARACTER = (
    "Stay in character at all times: a busy operations manager. Plain, "
    "conversational language. Keep replies short — a few sentences."
)
_RULE_NO_RECITE = (
    "Never recite, list, or summarize policy rules — not even one, not at "
    "any level of detail. If the developer asks you what the rules are, "
    "tell them that is exactly what the records are for."
)
_RULE_HELD = (
    "The points in <what_only_you_know> appear in no record, so they are "
    "yours to hand over:\n"
    "  - When the developer asks about one of those areas, answer plainly "
    'and completely in your own words — "check the records" is not an '
    "acceptable answer for them.\n"
    "  - Answer only what was asked: do not append neighboring rules the "
    "developer did not raise, even ones you know well."
)
_RULE_CONTESTED = (
    "The points in <records_in_conflict> appear in the records in more than "
    "one version, and the documents cannot settle which is current — only "
    "you can:\n"
    "  - When the developer asks which version holds, or proposes any "
    "version they found, state the current one plainly in your own words — "
    "sending them back to the records is not an acceptable answer here.\n"
    "  - Settle only the point they raised; do not volunteer other "
    "conflicts they have not brought up."
)
_RULE_CONFIRMABLE = (
    "The points in <questions_you_can_settle> you check against your own "
    "knowledge, staying as close to yes/no as the question allows:\n"
    "  - If the developer states a specific reading and it matches your "
    'knowledge, confirm it plainly ("Yes, that\'s right.").\n'
    "  - If it contradicts your knowledge, say it is not right and tell "
    "them to take another look at the records.\n"
    "  - If they lay out two or more readings and ask which holds, name "
    "the one that matches — picking from what they put in front of you is "
    "still a check, not a briefing, so name it and stop there.\n"
    "  - Never volunteer a version they did not offer. If a reading is "
    "wrong, or none of the options they listed is right, say so and send "
    "them back to the records without supplying the correct version, in "
    "whole or in part."
)
_RULE_POINT_BACK = (
    "Any other policy question — asked outright, or floated as a reading "
    "for you to bless — you point back to the records. Do not confirm it, "
    "deny it, or discuss its substance. Outside your listed points your "
    "memory is unreliable and you know it."
)


def _knowledge_block(section: SectionFacts, facts: list[Fact]) -> str:
    lines = [f"## {_humanize(section.section_id).capitalize()}"]
    for category in section.categories:
        in_category = [fact for fact in facts if fact.category == category]
        if not in_category:
            continue
        lines.append(f"### {_humanize(category).capitalize()}")
        lines.extend(f"- {fact.statement}" for fact in in_category)
    return "\n".join(lines)


def _validated_subset(
    label: str,
    by_section: dict[str, list[str]] | None,
    sections: list[SectionFacts],
) -> dict[str, set[str]]:
    subset = {
        section_id: set(fact_ids)
        for section_id, fact_ids in (by_section or {}).items()
        if fact_ids
    }
    unknown_sections = sorted(set(subset) - {s.section_id for s in sections})
    if unknown_sections:
        raise ValueError(
            f"{label} names sections not being rendered: {unknown_sections}"
        )
    for section in sections:
        unknown_facts = sorted(
            subset.get(section.section_id, set()) - {fact.id for fact in section.facts}
        )
        if unknown_facts:
            raise ValueError(
                f"{label} names unknown facts in section "
                f"{section.section_id!r}: {unknown_facts}"
            )
    return subset


def render_client_instructions(
    domain: str,
    section_ids: list[str],
    data_dir: Path | None = None,
    client_held: dict[str, list[str]] | None = None,
    client_confirmable: dict[str, list[str]] | None = None,
    client_contested: dict[str, list[str]] | None = None,
) -> RenderedClientInstructions:
    """Render the Client system prompt for a domain's sections.

    ``client_held`` maps section ids to fact ids assigned to the Client
    via ``client_knowledge`` bundle members (``<what_only_you_know>``:
    answered plainly — they exist in no kit artifact). ``client_confirmable``
    maps section ids to artifact-carried fact ids the Client may confirm
    or deny a specific reading of (``<questions_you_can_settle>`` — a denial
    never includes the correct version). ``client_contested`` maps section
    ids to the subset of held facts whose kit artifacts carry declared
    divergent readings (``<records_in_conflict>``: the Client states the
    current version when asked to settle the conflict). Every other policy
    question is pointed back to the records; with all maps empty the Client
    is a pure point-back stakeholder.
    """
    sections = [load_section_facts(domain, sid, data_dir) for sid in section_ids]
    held_by_section = _validated_subset("client_held", client_held, sections)
    confirmable_by_section = _validated_subset(
        "client_confirmable", client_confirmable, sections
    )
    contested_by_section = _validated_subset(
        "client_contested", client_contested, sections
    )
    for section in sections:
        overlap = sorted(
            held_by_section.get(section.section_id, set())
            & confirmable_by_section.get(section.section_id, set())
        )
        if overlap:
            raise ValueError(
                f"section {section.section_id!r}: facts are both held and "
                f"confirmable: {overlap}"
            )
        # Contested facts are held facts with declared divergent renditions
        # in the kit — the truth lives with the Client either way, the
        # conflict just changes how the Client talks about it.
        not_held = sorted(
            contested_by_section.get(section.section_id, set())
            - held_by_section.get(section.section_id, set())
        )
        if not_held:
            raise ValueError(
                f"section {section.section_id!r}: contested facts must be "
                f"held by the Client: {not_held}"
            )

    business = DOMAIN_BUSINESS.get(domain, "a company")
    area_list = ", ".join(_humanize(s.section_id) for s in sections)

    held_blocks: list[str] = []
    contested_blocks: list[str] = []
    confirmable_blocks: list[str] = []
    held_fact_count = 0
    contested_fact_count = 0
    confirmable_fact_count = 0
    for section in sections:
        contested_ids = contested_by_section.get(section.section_id, set())
        held_ids = held_by_section.get(section.section_id, set()) - contested_ids
        confirmable_ids = confirmable_by_section.get(section.section_id, set())
        held_facts = [fact for fact in section.facts if fact.id in held_ids]
        contested_facts = [fact for fact in section.facts if fact.id in contested_ids]
        confirmable_facts = [
            fact for fact in section.facts if fact.id in confirmable_ids
        ]
        if held_facts:
            held_blocks.append(_knowledge_block(section, held_facts))
            held_fact_count += len(held_facts)
        if contested_facts:
            contested_blocks.append(_knowledge_block(section, contested_facts))
            contested_fact_count += len(contested_facts)
        if confirmable_facts:
            confirmable_blocks.append(_knowledge_block(section, confirmable_facts))
            confirmable_fact_count += len(confirmable_facts)

    rules = [_RULE_CHARACTER, _RULE_NO_RECITE]
    if held_blocks:
        rules.append(_RULE_HELD)
    if contested_blocks:
        rules.append(_RULE_CONTESTED)
    if confirmable_blocks:
        rules.append(_RULE_CONFIRMABLE)
    rules.append(_RULE_POINT_BACK)

    if held_blocks and contested_blocks:
        records_scope = _RECORDS_SCOPE_WITH_HELD_AND_CONTESTED
    elif held_blocks:
        records_scope = _RECORDS_SCOPE_WITH_HELD
    elif contested_blocks:
        records_scope = _RECORDS_SCOPE_WITH_CONTESTED
    else:
        records_scope = _RECORDS_SCOPE_ALL

    prompt = CLIENT_SYSTEM_PROMPT.format(
        business=business,
        area_list=area_list,
        records_scope=records_scope,
        held_block=(
            _HELD_BLOCK_TEMPLATE.format(held_knowledge="\n\n".join(held_blocks))
            if held_blocks
            else ""
        ),
        contested_block=(
            _CONTESTED_BLOCK_TEMPLATE.format(
                contested_knowledge="\n\n".join(contested_blocks)
            )
            if contested_blocks
            else ""
        ),
        confirmable_block=(
            _CONFIRMABLE_BLOCK_TEMPLATE.format(
                confirmable_knowledge="\n\n".join(confirmable_blocks)
            )
            if confirmable_blocks
            else ""
        ),
        rules="\n".join(f"- {rule}" for rule in rules),
    )
    return RenderedClientInstructions(
        domain=domain,
        section_ids=list(section_ids),
        prompt=prompt,
        fact_count=sum(len(s.facts) for s in sections),
        held_fact_count=held_fact_count,
        confirmable_fact_count=confirmable_fact_count,
        contested_fact_count=contested_fact_count,
    )


def task_client_knowledge_fact_ids(
    task,
) -> tuple[dict[str, list[str]], dict[str, list[str]], dict[str, list[str]]]:
    """The (held, confirmable, contested) fact-id maps of the task's variant.

    Compiled from the task's ``sop_variant_manifest_path``; all empty for
    tasks without a manifest (or without ``client_knowledge`` bundle
    members). Contested facts (held facts whose kit artifacts carry
    declared divergent readings) are returned as plain fact-id lists — the
    reading labels stay in the compilation.
    """
    if not getattr(task, "sop_variant_manifest_path", None):
        return {}, {}, {}
    from tau2.hyper.transformations import compile_hyper_task

    compilation = compile_hyper_task(task)
    # A broken manifest must fail loudly here: silently returning partial
    # maps would render a Client that is missing knowledge the variant
    # assigned to it.
    compilation.raise_on_errors()
    contested = {
        section_id: sorted(facts)
        for section_id, facts in compilation.client_contested_fact_ids.items()
        if facts
    }
    return (
        compilation.client_held_fact_ids,
        compilation.client_confirmable_fact_ids,
        contested,
    )


def resolve_task_client_instructions(task) -> str:
    """The Client system prompt for a :class:`~tau2.hyper.data_model.HyperTask`.

    Rendered from the task's ``client_sections`` fact schemas when declared
    (with held and confirmable facts derived from the task's variant
    manifest), else the task's hand-authored ``client_instructions``.
    (Duck-typed to avoid importing the task model here.)
    """
    if task.client_sections:
        held, confirmable, contested = task_client_knowledge_fact_ids(task)
        unreachable = sorted(set(held) - set(task.client_sections))
        if unreachable:
            raise ValueError(
                f"Task {task.id!r} assigns client_knowledge facts in "
                f"sections {unreachable} that are not in client_sections; "
                "the Client would never know them"
            )
        # Confirmable facts stay artifact-carried, so a section outside
        # client_sections just loses its adjudication channel — not fatal.
        confirmable = {
            section_id: fact_ids
            for section_id, fact_ids in confirmable.items()
            if section_id in task.client_sections
        }
        # Contested facts are held, so the unreachable check above already
        # guarantees their sections are in client_sections.
        return render_client_instructions(
            task.source_domain,
            list(task.client_sections),
            client_held=held,
            client_confirmable=confirmable,
            client_contested=contested,
        ).prompt
    return task.client_instructions
