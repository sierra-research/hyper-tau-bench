"""
Variant compilation: resolve transformations, compute fact coverage, fallback.

A variant manifest declares which transformations are active over which
section fact schemas. Compiling a variant answers, for every atomic fact
in those schemas, *where the Developer can learn it*:

- **Covered** — one or more active transformations carry the fact in their
  artifacts (transcripts, customer documents, prose). The same fact may legally be
  carried by several transformations at once; redundant representation is
  an information-distribution choice, not an error, but it is always
  documented in the compilation report.
- **Fallback** — no active transformation carries the fact. Instead of
  failing the build, the fact is routed into a simple fallback
  representation (an explicit-rules appendix on the SOP) and a warning is
  emitted. Set ``"uncovered_fact_policy": "error"`` in the manifest to
  keep the old hard-fail behavior.

Genuine breakage stays an error either way: unknown fact ids, missing
artifact files, malformed artifact metadata, unknown representations.

The compilation result doubles as the build plan (the kit builder
materializes ``VariantCompilation.activations``) and as the audit trail
(``report()`` / ``summary()`` for experimenters). Report files must never
be written inside the kit directory — they enumerate fact schemas the
Developer is not supposed to see.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, Optional, Union

from tau2.hyper.transformations.base import (
    SectionTransformation,
    TransformationArtifact,
    get_transformation,
    has_transformation,
    known_representations,
    resolve_section_transformations,
    select_section_transformation,
)
from tau2.hyper.transformations.bundles import (
    normalize_section_bundle_selection,
    resolve_transformation_bundle,
    resolve_transformation_spec_by_id,
)
from tau2.hyper.transformations.fact_hierarchy import (
    SectionFactHierarchy,
    resolve_domain_fact_hierarchy,
)
from tau2.utils.utils import DATA_DIR

FALLBACK_HEADING = "## Additional Policy Notes"

UNCOVERED_FACT_POLICIES = ("fallback", "error")


@dataclass
class TransformationActivation:
    """One transformation active over one section in a compiled variant."""

    section_id: str
    representation: str
    spec: dict[str, Any]
    transformation: SectionTransformation
    artifacts: list[TransformationArtifact]
    #: True when this activation is the stub-path-selected primary (its stub
    #: is what appears in the assembled SOP); additional activations declared
    #: via ``additional_transformations`` are False.
    primary: bool = True
    #: Fact ids this activation actually covers, per the transformation's
    #: ``covered_fact_ids`` (sorted for determinism). Not derivable from the
    #: artifacts alone: prose and legacy-transcript coverage is not
    #: artifact-based.
    covered_fact_ids: list[str] = field(default_factory=list)
    #: Bundle that coordinated this activation, or None for a legacy
    #: independently selected transformation.
    bundle_id: Optional[str] = None
    #: Facts this member is declared authoritative for. None for legacy
    #: activations; bundle compilation requires this to exactly match
    #: ``covered_fact_ids``.
    authoritative_fact_ids: Optional[list[str]] = None
    #: Facts this member expects another member in the same bundle to carry.
    depends_on_fact_ids: list[str] = field(default_factory=list)
    #: Section-qualified facts inherited from declared upstream sections.
    #: These facts are available as context but remain covered by their owner.
    inherited_fact_ids: list[str] = field(default_factory=list)
    #: True when this member replaces a base-bundle member via a client
    #: overlay's ``member_substitutions``. Kit assembly treats its files as
    #: replacements for any base artifact at the same kit path — a shared
    #: carrier (one file backing several sections) must never appear in a
    #: kit in both its base and client versions.
    client_substitute: bool = False


@dataclass
class EvidenceRouteActivation:
    """Facts established only by following a linked, multi-artifact route."""

    route_id: str
    authoritative_fact_ids: list[str] = field(default_factory=list)
    hops: list[dict[str, str]] = field(default_factory=list)
    evidence_text: str = ""
    plausibility: str = ""
    scope_cue: str = ""
    forbidden_inference: str = ""


@dataclass
class TransformationBundleActivation:
    """One validated bundle active over one section."""

    section_id: str
    bundle_id: str
    description: str
    stub_path: Optional[str]
    fact_ids: list[str] = field(default_factory=list)
    members: list[TransformationActivation] = field(default_factory=list)
    evidence_routes: list[EvidenceRouteActivation] = field(default_factory=list)


@dataclass
class FactCoverage:
    """Where one atomic fact is represented in the compiled variant."""

    section_id: str
    fact_id: str
    statement: str
    #: Representations of every activation that carries this fact, in
    #: activation order. Empty means the fact fell through to the fallback.
    representations: list[str] = field(default_factory=list)
    #: Domain-level role of the section that owns this fact.
    owner_role: str = "standalone"
    #: Sections that inherit this fact without re-owning its coverage.
    inherited_by_section_ids: list[str] = field(default_factory=list)

    @property
    def covered(self) -> bool:
        return bool(self.representations)

    @property
    def multiply_represented(self) -> bool:
        return len(self.representations) > 1


@dataclass
class VariantCompilation:
    """Resolved build plan + fact-coverage audit for one variant manifest."""

    manifest_id: str
    activations: list[TransformationActivation] = field(default_factory=list)
    bundles: list[TransformationBundleActivation] = field(default_factory=list)
    facts: list[FactCoverage] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    uncovered_fact_policy: str = "fallback"
    section_hierarchy: dict[str, SectionFactHierarchy] = field(default_factory=dict)
    #: Declared record conflicts (``contested_fact_ids`` on bundles):
    #: section -> held fact -> the divergent readings its kit artifacts
    #: deliberately carry. The Client resolves which reading is current;
    #: fidelity gates exempt exactly these declared renditions.
    client_contested_fact_ids: dict[str, dict[str, list[str]]] = field(
        default_factory=dict
    )

    @property
    def uncovered_facts(self) -> list[FactCoverage]:
        """Facts no active transformation covers.

        Only routed into the fallback appendix when the compilation is
        error-free and ``uncovered_fact_policy`` is ``"fallback"`` —
        under the ``"error"`` policy (or alongside other errors) the kit
        build fails instead and no fallback is produced.
        """
        return [fact for fact in self.facts if not fact.covered]

    @property
    def fallback_applies(self) -> bool:
        """True when uncovered facts will actually be routed to fallback."""
        return (
            bool(self.uncovered_facts)
            and self.uncovered_fact_policy == "fallback"
            and not self.errors
        )

    @property
    def multiply_represented_facts(self) -> list[FactCoverage]:
        return [fact for fact in self.facts if fact.multiply_represented]

    @property
    def client_held_fact_ids(self) -> dict[str, list[str]]:
        """Facts assigned to the Client simulator, by section.

        These facts appear in no kit artifact; a task using this variant
        must enable the Client (``client_sections``) over every section
        listed here or the facts are unlearnable.
        """
        held: dict[str, list[str]] = {}
        for activation in self.activations:
            if activation.representation != "client_knowledge":
                continue
            held.setdefault(activation.section_id, []).extend(
                activation.covered_fact_ids
            )
        return {section_id: sorted(ids) for section_id, ids in held.items()}

    @property
    def client_confirmable_fact_ids(self) -> dict[str, list[str]]:
        """Facts the Client may adjudicate (confirm/deny a reading), by section.

        Unlike client-held facts these stay artifact-carried; the Client
        never owns or recites them, it only judges a specific reading the
        Developer proposes. Everything outside the held and confirmable
        lists the Client points back to the records.
        """
        confirmable: dict[str, list[str]] = {}
        for activation in self.activations:
            if activation.representation != "client_knowledge":
                continue
            ids = activation.spec.get("confirmable_fact_ids") or []
            if ids:
                confirmable.setdefault(activation.section_id, []).extend(ids)
        return {section_id: sorted(ids) for section_id, ids in confirmable.items()}

    def raise_on_errors(self) -> None:
        if self.errors:
            raise ValueError(
                f"Variant {self.manifest_id!r} failed transformation "
                "compilation: " + "; ".join(self.errors)
            )

    def report(self) -> dict[str, Any]:
        """JSON-serializable coverage report (deterministic)."""
        return {
            "manifest_id": self.manifest_id,
            "uncovered_fact_policy": self.uncovered_fact_policy,
            "totals": {
                "facts": len(self.facts),
                "covered": sum(1 for f in self.facts if f.covered),
                "uncovered": len(self.uncovered_facts),
                "multiply_represented": len(self.multiply_represented_facts),
            },
            "fallback_applies": self.fallback_applies,
            "client_contested_fact_ids": {
                section_id: {
                    fact_id: list(readings)
                    for fact_id, readings in sorted(contested.items())
                }
                for section_id, contested in sorted(
                    self.client_contested_fact_ids.items()
                )
            },
            "transformations": [
                {
                    "section_id": activation.section_id,
                    "representation": activation.representation,
                    "transformation_id": activation.spec.get("id"),
                    "bundle_id": activation.bundle_id,
                    "primary": activation.primary,
                    "artifact_count": len(activation.artifacts),
                    "fact_count": len(activation.covered_fact_ids),
                    "inherited_fact_count": len(activation.inherited_fact_ids),
                }
                for activation in self.activations
            ],
            "section_hierarchy": {
                section_id: hierarchy.view()
                for section_id, hierarchy in sorted(self.section_hierarchy.items())
            },
            "bundles": [
                {
                    "section_id": bundle.section_id,
                    "bundle_id": bundle.bundle_id,
                    "description": bundle.description,
                    "stub_path": bundle.stub_path,
                    "fact_ids": list(bundle.fact_ids),
                    "members": [
                        {
                            "transformation_id": member.spec.get("id"),
                            "representation": member.representation,
                            "authoritative_fact_ids": list(
                                member.authoritative_fact_ids or []
                            ),
                            "depends_on_fact_ids": list(member.depends_on_fact_ids),
                        }
                        for member in bundle.members
                    ],
                    "evidence_routes": [
                        {
                            "route_id": route.route_id,
                            "authoritative_fact_ids": list(
                                route.authoritative_fact_ids
                            ),
                            "hops": [dict(hop) for hop in route.hops],
                            "evidence_text": route.evidence_text,
                            "plausibility": route.plausibility,
                            "scope_cue": route.scope_cue,
                            "forbidden_inference": route.forbidden_inference,
                        }
                        for route in bundle.evidence_routes
                    ],
                }
                for bundle in self.bundles
            ],
            "facts": [
                {
                    "section_id": fact.section_id,
                    "fact_id": fact.fact_id,
                    "owner_role": fact.owner_role,
                    "inherited_by_section_ids": list(fact.inherited_by_section_ids),
                    "representations": list(fact.representations),
                    "uncovered": not fact.covered,
                }
                for fact in self.facts
            ],
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }

    def summary(self) -> str:
        """Human-readable coverage summary for terminal display."""
        totals = self.report()["totals"]
        lines = [
            f"Variant: {self.manifest_id}",
            f"Facts: {totals['facts']}  "
            f"covered: {totals['covered']}  "
            f"uncovered: {totals['uncovered']}  "
            f"multiply represented: {totals['multiply_represented']}",
            "",
            "Active transformations:",
        ]
        for activation in self.activations:
            marker = "primary" if activation.primary else "additional"
            bundle = (
                f", bundle {activation.bundle_id}"
                if activation.bundle_id is not None
                else ""
            )
            lines.append(
                f"  {activation.section_id}: {activation.representation} "
                f"({marker}{bundle}, {len(activation.artifacts)} artifacts)"
            )
        if self.multiply_represented_facts:
            lines.append("")
            lines.append("Multiply represented facts:")
            for fact in self.multiply_represented_facts:
                lines.append(
                    f"  {fact.section_id}.{fact.fact_id}: "
                    + ", ".join(fact.representations)
                )
        if self.uncovered_facts:
            lines.append("")
            if self.fallback_applies:
                lines.append("Facts routed to fallback (explicit-rules appendix):")
            else:
                # Under the "error" policy — or alongside other errors — the
                # build fails instead; no fallback appendix is produced.
                lines.append("Uncovered facts (no active transformation):")
            for fact in self.uncovered_facts:
                lines.append(f"  {fact.section_id}.{fact.fact_id}")
        for warning in self.warnings:
            lines.append(f"WARNING: {warning}")
        for error in self.errors:
            lines.append(f"ERROR: {error}")
        return "\n".join(lines)


def _resolve_data_relative(path: str | Path, *, data_dir: Path = DATA_DIR) -> Path:
    resolved = Path(path)
    if resolved.is_absolute():
        return resolved
    return data_dir / resolved


def _seeded_order(manifest_id: str, *parts: str) -> str:
    return sha256(":".join((manifest_id, *parts)).encode()).hexdigest()


def _match_additional_spec(
    schema: dict[str, Any],
    representation: str,
    stub_path: Optional[str],
) -> Optional[dict[str, Any]]:
    """Find the schema-declared spec an additional activation refers to."""
    transformation = get_transformation(representation)
    accepted = {transformation.representation, *transformation.aliases}
    matches = []
    for spec in resolve_section_transformations(schema):
        if spec.get("representation") not in accepted:
            continue
        if stub_path is not None and spec.get("stub_path") != stub_path:
            continue
        matches.append(spec)
    if len(matches) > 1:
        raise ValueError(
            f"additional transformation selector is ambiguous for "
            f"representation {representation!r} and stub_path {stub_path!r}"
        )
    return matches[0] if matches else None


def _declared_artifact_refs(spec: dict[str, Any]) -> set[str]:
    """Stable identifiers by which an evidence route may cite an artifact."""
    refs: set[str] = set()
    for artifact in spec.get("artifacts") or []:
        if not isinstance(artifact, dict):
            continue
        for key in ("artifact_ref", "reference_id", "kit_filename"):
            value = artifact.get(key)
            if isinstance(value, str) and value:
                refs.add(value)
    return refs


def _parse_evidence_routes(
    bundle: dict[str, Any],
    *,
    section_id: str,
    bundle_id: str,
    facts_by_id: dict[str, FactCoverage],
    member_specs: dict[str, dict[str, Any]],
    authority_in_bundle: dict[str, str],
    errors: list[str],
) -> list[EvidenceRouteActivation]:
    """Validate routes whose complete meaning spans two or more artifacts."""
    raw_routes = bundle.get("evidence_routes") or []
    if not isinstance(raw_routes, list):
        errors.append(
            f"section {section_id!r} bundle {bundle_id!r}: "
            "evidence_routes must be a list"
        )
        return []

    routes: list[EvidenceRouteActivation] = []
    seen_route_ids: set[str] = set()
    for route_index, raw_route in enumerate(raw_routes):
        prefix = (
            f"section {section_id!r} bundle {bundle_id!r} evidence route {route_index}"
        )
        if not isinstance(raw_route, dict):
            errors.append(f"{prefix} must be an object")
            continue
        route_id = raw_route.get("id")
        if not isinstance(route_id, str) or not route_id:
            errors.append(f"{prefix} must declare a non-empty id")
            continue
        prefix = (
            f"section {section_id!r} bundle {bundle_id!r} evidence route {route_id!r}"
        )
        if route_id in seen_route_ids:
            errors.append(f"{prefix}: duplicate route id")
        seen_route_ids.add(route_id)

        raw_authoritative = raw_route.get("authoritative_fact_ids") or []
        if not isinstance(raw_authoritative, list) or not all(
            isinstance(fact_id, str) for fact_id in raw_authoritative
        ):
            errors.append(f"{prefix}: authoritative_fact_ids must be a list of strings")
            continue
        if not raw_authoritative:
            errors.append(f"{prefix}: authoritative_fact_ids must not be empty")
        if len(raw_authoritative) != len(set(raw_authoritative)):
            errors.append(f"{prefix}: authoritative_fact_ids contains duplicates")
        for fact_id in raw_authoritative:
            if fact_id not in facts_by_id:
                errors.append(f"{prefix}: unknown fact id {fact_id!r}")
                continue
            previous_owner = authority_in_bundle.get(fact_id)
            if previous_owner is not None:
                errors.append(
                    f"{prefix}: fact {fact_id!r} has multiple authoritative "
                    f"owners ({previous_owner!r}, {route_id!r})"
                )
            else:
                authority_in_bundle[fact_id] = f"evidence_route:{route_id}"

        raw_hops = raw_route.get("hops") or []
        valid_hops: list[dict[str, str]] = []
        if not isinstance(raw_hops, list) or len(raw_hops) < 2:
            errors.append(f"{prefix}: hops must contain at least two artifacts")
        else:
            for hop_index, raw_hop in enumerate(raw_hops):
                if not isinstance(raw_hop, dict):
                    errors.append(f"{prefix}: hop {hop_index} must be an object")
                    continue
                transformation_id = raw_hop.get("transformation_id")
                artifact_ref = raw_hop.get("artifact_ref")
                if not isinstance(transformation_id, str) or not transformation_id:
                    errors.append(
                        f"{prefix}: hop {hop_index} must declare transformation_id"
                    )
                    continue
                if not isinstance(artifact_ref, str) or not artifact_ref:
                    errors.append(
                        f"{prefix}: hop {hop_index} must declare artifact_ref"
                    )
                    continue
                spec = member_specs.get(transformation_id)
                if spec is None:
                    errors.append(
                        f"{prefix}: hop {hop_index} references non-member "
                        f"transformation {transformation_id!r}"
                    )
                    continue
                if artifact_ref not in _declared_artifact_refs(spec):
                    errors.append(
                        f"{prefix}: hop {hop_index} artifact_ref {artifact_ref!r} "
                        f"does not resolve in {transformation_id!r}"
                    )
                    continue
                valid_hops.append(
                    {
                        "transformation_id": transformation_id,
                        "artifact_ref": artifact_ref,
                    }
                )
        if len({hop["transformation_id"] for hop in valid_hops}) < 2:
            errors.append(
                f"{prefix}: hops must span at least two bundle transformations"
            )

        narrative_fields: dict[str, str] = {}
        for field_name in (
            "evidence_text",
            "plausibility",
            "scope_cue",
            "forbidden_inference",
        ):
            value = raw_route.get(field_name)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{prefix}: {field_name} must be a non-empty string")
                narrative_fields[field_name] = ""
            else:
                narrative_fields[field_name] = value.strip()

        routes.append(
            EvidenceRouteActivation(
                route_id=route_id,
                authoritative_fact_ids=list(raw_authoritative),
                hops=valid_hops,
                **narrative_fields,
            )
        )
    return routes


def _is_client_knowledge_spec(spec: dict[str, Any]) -> bool:
    """Whether a transformation spec resolves to ``client_knowledge``.

    Resolves through the registry so representation aliases (e.g.
    ``client_held``) are recognized, and tolerates invalid representations
    — those are reported by the activation path, not here.
    """
    representation = spec.get("representation")
    if not isinstance(representation, str) or not has_transformation(representation):
        return False
    return get_transformation(representation).representation == "client_knowledge"


def _check_client_overlay(
    schema: dict[str, Any],
    bundle: dict[str, Any],
    *,
    section_id: str,
    bundle_id: str,
    declared_fact_ids: set[str],
    resolved_members: list[tuple[dict[str, Any], dict[str, Any], set[str], set[str]]],
    overlay_routes: list[EvidenceRouteActivation],
    facts_by_id: dict[str, FactCoverage],
    errors: list[str],
) -> None:
    """Client bundles are overlays on a declared artifact-only base bundle.

    ``client_knowledge`` is a modifier applied on top of an existing
    artifact bundle, not a freestanding representation: the held facts are
    carved out of specific base members (whose artifacts are rewritten to
    genuinely omit them), and everything else must be untouched. Requiring
    ``client_overlay_of`` — plus a ``member_substitutions`` map naming the
    rewritten members — makes that relationship declared and
    machine-checked instead of a hand-copied sibling bundle that can drift
    from its base.

    A bundle may also declare ``client_overlay_of`` with **no**
    client_knowledge member: a *carrier-lockstep overlay* holding no facts
    (held set is empty). This exists for sections that carry a shared
    artifact (a trio-spine QA export, a cross-section refdoc) which a
    sibling section's overlay forks: every section whose selected bundle
    delivers that carrier must substitute the same fork, or kit assembly
    ships both the unscrubbed base copy and the scrubbed fork —
    substitution-never-addition violated through the unsubstituted path.
    All contract checks below apply with ``held = {}``; in particular each
    replacement must keep its base member's authority *identical*, so a
    lockstep overlay can swap carrier bytes but can never silently drop
    fact coverage. Conversely, ``member_substitutions`` is only meaningful
    inside this contract, so declaring it without ``client_overlay_of`` is
    an error rather than an unchecked sibling bundle.

    Checks, given overlay bundle O declaring base B:
    - B exists in the same schema, is not O, and has no client members;
    - O and B declare the same fact set;
    - O's artifact members are exactly B's, minus the substituted members,
      plus their declared replacements (substitution, never addition);
    - each replacement's authority is its base member's authority minus
      the client-held facts; unchanged members keep identical authority;
    - every held fact was owned in B by a substituted member or shed from
      a re-declared evidence route (below);
    - B's primary member (or its replacement) stays primary in O, and a
      client member is never primary.

    Evidence routes (the routes-aware contract). Hop order carries
    semantics: ``hops[0]`` is the in-world pointer artifact, ``hops[-1]``
    the value-printing terminal. Given a base B with ``evidence_routes``:

    - **L1 carry-through** — O re-declares every base route: identical
      route id, identical ``authoritative_fact_ids``, identical hop
      sequence after mapping each hop's ``transformation_id`` through
      ``member_substitutions`` (identical ``artifact_ref``\\s), and
      identical narrative fields. Route-owned facts may not be client-held
      (they may be ``confirmable_fact_ids`` — route authority already
      counts as carried-by-others). Hop artifacts must stay
      content-identical; compile cannot hash files, so byte-identity is a
      gate check, not enforced here.
    - **L2 route substitution** — a re-declared route may shed a strict
      subset of its facts to the client member, but only when the base
      route's terminal (value-printing) member is in
      ``member_substitutions``; shed facts must be client-held; the shed
      route's narrative fields may be re-authored (the held-value scrub is
      gate-checked). A route may never shed to empty — dropping a route
      entirely must be declared in ``route_retirements`` (all its facts
      client-held, at least one hop member substituted), so no base route
      is ever silently absent. Full retirement does not require the terminal
      member to change because a route can derive its rule from an earlier
      hop and end at a neutral state capture.
    - O may never invent routes absent from B.
    """
    prefix = f"section {section_id!r} bundle {bundle_id!r}"
    client_members = [
        (member, spec, authoritative)
        for member, spec, authoritative, _dependencies in resolved_members
        if _is_client_knowledge_spec(spec)
    ]
    base_id = bundle.get("client_overlay_of")
    if not client_members and base_id is None:
        if bundle.get("member_substitutions"):
            errors.append(
                f"{prefix}: member_substitutions requires client_overlay_of "
                "naming the base bundle being shadowed; substitutions are "
                "only checkable inside the overlay contract"
            )
        return
    if not isinstance(base_id, str) or not base_id:
        errors.append(
            f"{prefix}: bundles with a client_knowledge member must declare "
            "client_overlay_of naming the artifact-only base bundle the "
            "client-held facts were carved out of"
        )
        return
    if base_id == bundle_id:
        errors.append(f"{prefix}: client_overlay_of may not name the bundle itself")
        return
    try:
        base = resolve_transformation_bundle(schema, base_id)
    except ValueError as error:
        errors.append(f"{prefix}: client_overlay_of: {error}")
        return
    for member, _spec, _authoritative in client_members:
        if member.get("primary") is True:
            errors.append(f"{prefix}: a client_knowledge member may not be primary")

    held: set[str] = set()
    for _member, _spec, authoritative in client_members:
        held |= authoritative

    base_members = base.get("members") or []
    base_authority: dict[str, set[str]] = {}
    base_member_specs: dict[str, dict[str, Any]] = {}
    base_primary: Optional[str] = None
    malformed = not isinstance(base_members, list) or not base_members
    if not malformed:
        for member in base_members:
            if not isinstance(member, dict) or not isinstance(
                member.get("transformation_id"), str
            ):
                malformed = True
                break
            transformation_id = member["transformation_id"]
            raw_authoritative = member.get("authoritative_fact_ids") or []
            if not isinstance(raw_authoritative, list):
                malformed = True
                break
            base_authority[transformation_id] = {
                str(fact_id) for fact_id in raw_authoritative
            }
            if member.get("primary") is True and base_primary is None:
                base_primary = transformation_id
            try:
                spec = resolve_transformation_spec_by_id(schema, transformation_id)
            except ValueError:
                malformed = True
                break
            if _is_client_knowledge_spec(spec):
                errors.append(
                    f"{prefix}: client_overlay_of must name an artifact-only "
                    f"bundle, but {base_id!r} has client_knowledge member "
                    f"{transformation_id!r}"
                )
                return
            base_member_specs[transformation_id] = spec
    if malformed:
        errors.append(
            f"{prefix}: client_overlay_of base {base_id!r} is malformed; "
            "fix the base bundle before declaring overlays on it"
        )
        return

    base_fact_ids = {str(fact_id) for fact_id in base.get("fact_ids") or []}
    if base_fact_ids != declared_fact_ids:
        missing = sorted(base_fact_ids - declared_fact_ids)
        extra = sorted(declared_fact_ids - base_fact_ids)
        errors.append(
            f"{prefix}: overlay must declare the same fact_ids as base "
            f"{base_id!r} (missing={missing}, extra={extra})"
        )
    # Base evidence routes are re-parsed against the base's own member
    # specs; the base is not necessarily selected in this variant, so its
    # own compilation pass may never run. Base breakage is the base
    # author's bug — summarize instead of duplicating per-route errors.
    base_route_errors: list[str] = []
    base_route_owner: dict[str, str] = {
        fact_id: member_id
        for member_id, authority in base_authority.items()
        for fact_id in authority
    }
    base_routes = _parse_evidence_routes(
        base,
        section_id=section_id,
        bundle_id=base_id,
        facts_by_id=facts_by_id,
        member_specs=base_member_specs,
        authority_in_bundle=base_route_owner,
        errors=base_route_errors,
    )
    if base_route_errors:
        errors.append(
            f"{prefix}: client_overlay_of base {base_id!r} has invalid "
            "evidence_routes; fix the base bundle before declaring overlays "
            "on it (" + "; ".join(base_route_errors) + ")"
        )
        return
    base_route_facts: dict[str, set[str]] = {
        route.route_id: set(route.authoritative_fact_ids) for route in base_routes
    }
    base_route_authority: set[str] = set()
    for route_fact_ids in base_route_facts.values():
        base_route_authority |= route_fact_ids

    base_covered: set[str] = set()
    for authority in base_authority.values():
        base_covered |= authority
    if base_covered | base_route_authority != base_fact_ids:
        errors.append(
            f"{prefix}: client_overlay_of base {base_id!r} member and "
            "evidence-route authority does not match its fact_ids; fix the "
            "base bundle before declaring overlays on it"
        )
        return

    substitutions = bundle.get("member_substitutions") or {}
    if not isinstance(substitutions, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in substitutions.items()
    ):
        errors.append(
            f"{prefix}: member_substitutions must map base member "
            "transformation_ids to their overlay replacements"
        )
        return
    unknown_bases = sorted(set(substitutions) - set(base_authority))
    if unknown_bases:
        errors.append(
            f"{prefix}: member_substitutions keys are not members of base "
            f"{base_id!r}: {unknown_bases}"
        )
        return
    if len(set(substitutions.values())) != len(substitutions):
        errors.append(f"{prefix}: member_substitutions replacements must be distinct")
        return

    overlay_authority: dict[str, set[str]] = {
        str(member["transformation_id"]): authoritative
        for member, spec, authoritative, _dependencies in resolved_members
        if not _is_client_knowledge_spec(spec)
    }
    expected_members = (set(base_authority) - set(substitutions)) | set(
        substitutions.values()
    )
    if set(overlay_authority) != expected_members:
        missing = sorted(expected_members - set(overlay_authority))
        extra = sorted(set(overlay_authority) - expected_members)
        errors.append(
            f"{prefix}: artifact members must be base {base_id!r} members "
            "with the declared member_substitutions applied — substitution, "
            f"never addition (missing={missing}, extra={extra})"
        )
        return

    substituted_base_authority: set[str] = set()
    for base_member_id, overlay_member_id in substitutions.items():
        substituted_base_authority |= base_authority[base_member_id]
        expected_authority = base_authority[base_member_id] - held
        actual_authority = overlay_authority[overlay_member_id]
        if actual_authority != expected_authority:
            missing = sorted(expected_authority - actual_authority)
            extra = sorted(actual_authority - expected_authority)
            errors.append(
                f"{prefix}: replacement member {overlay_member_id!r} must "
                f"keep base member {base_member_id!r}'s authority minus the "
                f"client-held facts (missing={missing}, extra={extra})"
            )
    # --- evidence-route correspondence (L1 carry-through / L2 sheds) ---
    raw_retirements = bundle.get("route_retirements") or []
    retirements: list[str] = []
    if not isinstance(raw_retirements, list) or not all(
        isinstance(route_id, str) and route_id for route_id in raw_retirements
    ):
        errors.append(f"{prefix}: route_retirements must be a list of base route ids")
    else:
        retirements = list(raw_retirements)
    if len(retirements) != len(set(retirements)):
        errors.append(f"{prefix}: route_retirements contains duplicates")
    retired = set(retirements)
    if retired and not base_routes:
        errors.append(
            f"{prefix}: route_retirements is only meaningful when base "
            f"{base_id!r} declares evidence_routes"
        )
    unknown_retired = sorted(retired - set(base_route_facts))
    if unknown_retired:
        errors.append(
            f"{prefix}: route_retirements names routes not declared by base "
            f"{base_id!r}: {unknown_retired}"
        )
    overlay_routes_by_id = {route.route_id: route for route in overlay_routes}
    if overlay_routes_by_id and not base_routes:
        errors.append(
            f"{prefix}: overlay declares evidence_routes but base "
            f"{base_id!r} declares none"
        )
    invented = sorted(set(overlay_routes_by_id) - set(base_route_facts))
    if invented:
        errors.append(
            f"{prefix}: overlay evidence_routes must re-declare base "
            f"{base_id!r} routes, never invent new ones: {invented}"
        )
    redeclared_retired = sorted(set(overlay_routes_by_id) & retired)
    if redeclared_retired:
        errors.append(
            f"{prefix}: routes are both re-declared and retired: {redeclared_retired}"
        )
    silently_absent = sorted(
        set(base_route_facts) - set(overlay_routes_by_id) - retired
    )
    if silently_absent:
        errors.append(
            f"{prefix}: base {base_id!r} evidence_routes must be re-declared "
            "by the overlay or listed in route_retirements — never silently "
            f"absent: {silently_absent}"
        )

    shed_route_facts: set[str] = set()
    for base_route in base_routes:
        base_facts = base_route_facts[base_route.route_id]
        route_members = {
            str(hop["transformation_id"])
            for hop in base_route.hops
            if hop.get("transformation_id") is not None
        }
        terminal_member = (
            base_route.hops[-1]["transformation_id"] if base_route.hops else None
        )
        if base_route.route_id in retired:
            shed_route_facts |= base_facts
            not_held = sorted(base_facts - held)
            if not_held:
                errors.append(
                    f"{prefix}: retired route {base_route.route_id!r} facts "
                    f"must be client-held: {not_held}"
                )
            if route_members and route_members.isdisjoint(substitutions):
                errors.append(
                    f"{prefix}: retiring route {base_route.route_id!r} "
                    "requires substituting at least one of its hop members"
                )
            continue
        overlay_route = overlay_routes_by_id.get(base_route.route_id)
        if overlay_route is None:
            continue  # already reported as silently absent
        overlay_facts = set(overlay_route.authoritative_fact_ids)
        extra_facts = sorted(overlay_facts - base_facts)
        if extra_facts:
            errors.append(
                f"{prefix}: re-declared route {base_route.route_id!r} may "
                f"not add facts beyond base {base_id!r}'s: {extra_facts}"
            )
        shed = base_facts - overlay_facts
        if shed:
            shed_route_facts |= shed
            not_held = sorted(shed - held)
            if not_held:
                errors.append(
                    f"{prefix}: route {base_route.route_id!r} shed facts "
                    f"must be client-held: {not_held}"
                )
            if terminal_member is not None and terminal_member not in substitutions:
                errors.append(
                    f"{prefix}: route {base_route.route_id!r} may shed facts "
                    f"only when its terminal member {terminal_member!r} "
                    "(the value-printing hop) is substituted"
                )
        else:
            # L1 carry-through: an unshed route is byte-equivalent modulo
            # member mapping — narrative drift is how held values leak.
            for field_name in (
                "evidence_text",
                "plausibility",
                "scope_cue",
                "forbidden_inference",
            ):
                if getattr(overlay_route, field_name) != getattr(
                    base_route, field_name
                ):
                    errors.append(
                        f"{prefix}: re-declared route {base_route.route_id!r} "
                        f"must keep base {base_id!r}'s {field_name} identical "
                        "unless the route sheds facts"
                    )
        expected_hops = [
            {
                "transformation_id": substitutions.get(
                    hop["transformation_id"], hop["transformation_id"]
                ),
                "artifact_ref": hop["artifact_ref"],
            }
            for hop in base_route.hops
        ]
        if overlay_route.hops != expected_hops:
            errors.append(
                f"{prefix}: re-declared route {base_route.route_id!r} hops "
                f"must match base {base_id!r}'s after member_substitutions "
                "mapping"
            )

    route_held_not_shed = sorted((held & base_route_authority) - shed_route_facts)
    if route_held_not_shed:
        errors.append(
            f"{prefix}: client-held facts owned by base evidence routes must "
            "be shed from the re-declared route (or the route retired): "
            f"{route_held_not_shed}"
        )

    unowned_held = sorted(held - substituted_base_authority - shed_route_facts)
    if unowned_held:
        errors.append(
            f"{prefix}: client-held facts must be carved out of substituted "
            f"base members or shed from re-declared evidence routes, but "
            f"base {base_id!r} carries these on members the overlay keeps "
            f"unchanged: {unowned_held}"
        )
    for member_id in set(base_authority) - set(substitutions):
        if overlay_authority[member_id] != base_authority[member_id]:
            missing = sorted(base_authority[member_id] - overlay_authority[member_id])
            extra = sorted(overlay_authority[member_id] - base_authority[member_id])
            errors.append(
                f"{prefix}: unchanged member {member_id!r} must keep base "
                f"{base_id!r}'s authority (missing={missing}, extra={extra})"
            )

    overlay_primary: Optional[str] = None
    for member, spec, _authoritative, _dependencies in resolved_members:
        if member.get("primary") is True and not _is_client_knowledge_spec(spec):
            overlay_primary = str(member["transformation_id"])
            break
    expected_primary = (
        substitutions.get(base_primary, base_primary)
        if base_primary is not None
        else None
    )
    if overlay_primary != expected_primary:
        errors.append(
            f"{prefix}: primary member must follow base {base_id!r} "
            f"(expected {expected_primary!r}, found {overlay_primary!r})"
        )


def _check_contested_facts(
    bundle: dict[str, Any],
    *,
    section_id: str,
    bundle_id: str,
    declared_fact_ids: set[str],
    resolved_members: list[tuple[dict[str, Any], dict[str, Any], set[str], set[str]]],
    errors: list[str],
) -> dict[str, list[str]]:
    """Validate a bundle's ``contested_fact_ids`` declaration.

    A contested fact is a client-held fact whose kit artifacts deliberately
    carry divergent readings — records that disagree, with nothing in the
    kit ranking them. The declaration is what separates an intentional
    conflict from an authoring bug: fidelity gates exempt exactly the
    declared renditions and nothing else. Shape::

        "contested_fact_ids": {
            "<fact_id>": [
                {"member_id": "<transformation_id>", "reading": "<label>"},
                ...
            ]
        }

    Rules: each contested fact is declared in the bundle and held
    (authoritative) by a ``client_knowledge`` member — the Client resolves
    the conflict, so an artifact-owned fact cannot be contested; at least
    two renditions with pairwise-distinct readings; every rendition names a
    non-client bundle member, and that member holds no authority over the
    fact (renditions are decoys, not carriers).

    Returns ``{fact_id: [readings]}`` for the valid declarations.
    """
    raw = bundle.get("contested_fact_ids")
    if raw is None:
        return {}
    prefix = f"section {section_id!r} bundle {bundle_id!r}"
    if not isinstance(raw, dict):
        errors.append(f"{prefix}: contested_fact_ids must be an object")
        return {}
    member_ids: set[str] = set()
    client_member_ids: set[str] = set()
    client_held: set[str] = set()
    authority_by_member: dict[str, set[str]] = {}
    for member, spec, authoritative, _dependencies in resolved_members:
        transformation_id = str(member["transformation_id"])
        member_ids.add(transformation_id)
        authority_by_member[transformation_id] = authoritative
        if _is_client_knowledge_spec(spec):
            client_member_ids.add(transformation_id)
            client_held |= authoritative
    contested: dict[str, list[str]] = {}
    for fact_id, renditions in sorted(raw.items()):
        fact_prefix = f"{prefix} contested fact {fact_id!r}"
        if fact_id not in declared_fact_ids:
            errors.append(f"{fact_prefix}: not in bundle fact_ids")
            continue
        if fact_id not in client_held:
            errors.append(
                f"{fact_prefix}: must be held by a client_knowledge member — "
                "the Client resolves the conflict, so an artifact-owned fact "
                "cannot be contested"
            )
            continue
        if not isinstance(renditions, list) or len(renditions) < 2:
            errors.append(f"{fact_prefix}: needs at least two renditions")
            continue
        readings: list[str] = []
        valid = True
        for index, rendition in enumerate(renditions):
            if not isinstance(rendition, dict):
                errors.append(f"{fact_prefix}: rendition {index} must be an object")
                valid = False
                continue
            member_id = rendition.get("member_id")
            reading = rendition.get("reading")
            if not isinstance(member_id, str) or member_id not in member_ids:
                errors.append(
                    f"{fact_prefix}: rendition {index} names unknown member "
                    f"{member_id!r}"
                )
                valid = False
                continue
            if member_id in client_member_ids:
                errors.append(
                    f"{fact_prefix}: the client member cannot carry a rendition"
                )
                valid = False
                continue
            if fact_id in authority_by_member.get(member_id, set()):
                errors.append(
                    f"{fact_prefix}: rendition member {member_id!r} has "
                    "authority over the fact; renditions carry no authority"
                )
                valid = False
                continue
            if not isinstance(reading, str) or not reading.strip():
                errors.append(
                    f"{fact_prefix}: rendition {index} needs a non-empty reading"
                )
                valid = False
                continue
            readings.append(reading.strip())
        if not valid:
            continue
        normalized = [" ".join(reading.lower().split()) for reading in readings]
        if len(set(normalized)) != len(normalized):
            errors.append(f"{fact_prefix}: readings must be pairwise distinct")
            continue
        contested[fact_id] = readings
    return contested


def compile_variant_transformations(
    manifest: dict[str, Any], *, data_dir: Path = DATA_DIR
) -> VariantCompilation:
    """Compile a variant manifest into a build plan + fact-coverage audit.

    For every section in ``section_source_schemas`` this resolves either:

    - first-class bundles selected under ``section_bundles``; or
    - the legacy primary transformation selected by stub path, plus any
      ``additional_transformations``.

    Bundle members assign authoritative facts explicitly and may depend on
    facts owned by another member. The compiler verifies those assignments
    against the facts actually carried by each member's artifacts.

    Coverage is the union over all activations; uncovered facts are routed
    to the fallback (with a warning) unless the manifest sets
    ``"uncovered_fact_policy": "error"``.
    """
    manifest_id = str(manifest.get("id", "<unknown>"))
    policy = str(manifest.get("uncovered_fact_policy", "fallback"))
    compilation = VariantCompilation(
        manifest_id=manifest_id, uncovered_fact_policy=policy
    )
    if policy not in UNCOVERED_FACT_POLICIES:
        compilation.errors.append(
            f"unknown uncovered_fact_policy {policy!r}; "
            f"expected one of {UNCOVERED_FACT_POLICIES}"
        )
        return compilation

    declared_representation = (manifest.get("information_distribution") or {}).get(
        "representation"
    )
    if declared_representation and not has_transformation(declared_representation):
        compilation.errors.append(
            f"manifest declares unknown representation "
            f"{declared_representation!r}; known representations: "
            f"{known_representations()}"
        )
        return compilation

    source_schemas = manifest.get("section_source_schemas") or {}
    try:
        bundles_by_section = normalize_section_bundle_selection(manifest)
    except ValueError as error:
        compilation.errors.append(str(error))
        return compilation
    for section_id in bundles_by_section:
        if section_id not in source_schemas:
            compilation.errors.append(
                f"section bundle selection targets unknown section "
                f"{section_id!r}; sections with schemas: "
                f"{sorted(source_schemas)}"
            )

    # The stub path a manifest splices (or appends) for a section identifies
    # which of the schema's transformations is the primary in this variant.
    active_stub_paths: dict[str, str] = {
        str(section_id): str(path)
        for section_id, path in (manifest.get("section_replacements") or {}).items()
    }
    for entry in manifest.get("append_sections") or []:
        if entry.get("id") and entry.get("path"):
            active_stub_paths.setdefault(str(entry["id"]), str(entry["path"]))

    additional_by_section: dict[str, list[dict[str, Any]]] = {}
    for entry in manifest.get("additional_transformations") or []:
        section_id = entry.get("section_id")
        representation = entry.get("representation")
        if not section_id or not representation:
            compilation.errors.append(
                "additional_transformations entries must declare "
                f"section_id and representation: {entry!r}"
            )
            continue
        if section_id not in source_schemas:
            compilation.errors.append(
                f"additional transformation targets unknown section "
                f"{section_id!r}; sections with schemas: "
                f"{sorted(source_schemas)}"
            )
            continue
        if not has_transformation(str(representation)):
            compilation.errors.append(
                f"additional transformation for section {section_id!r} names "
                f"unknown representation {representation!r}; known "
                f"representations: {known_representations()}"
            )
            continue
        if get_transformation(str(representation)).representation == "explicit_rules":
            # explicit_rules coverage comes from the section's prose in the
            # assembled SOP. An *additional* activation materializes nothing,
            # so it would claim coverage for facts that exist nowhere in the
            # kit. It is only meaningful as the primary (prose retained or
            # spliced via the stub path).
            compilation.errors.append(
                f"additional transformation for section {section_id!r} "
                "activates 'explicit_rules', which cannot be an additional "
                "transformation: it represents the section's prose in the "
                "assembled SOP and materializes no artifacts"
            )
            continue
        additional_by_section.setdefault(str(section_id), []).append(entry)
    for section_id in sorted(set(bundles_by_section) & set(additional_by_section)):
        compilation.errors.append(
            f"section {section_id!r} uses both section_bundles and "
            "additional_transformations; bundle members must be the only "
            "active artifact sets for a bundled section"
        )
    for section_id in sorted(
        set(bundles_by_section)
        & set((manifest.get("section_replacements") or {}).keys())
    ):
        compilation.errors.append(
            f"section {section_id!r} uses both section_bundles and "
            "section_replacements; the bundle's stub_path owns SOP assembly"
        )
    # Invalid additional entries are recorded as errors but do not abort the
    # audit: the section sweep below still runs so --compile-report shows the
    # primary coverage picture alongside the errors.

    # Section ids whose content (prose or stub) appears in the assembled SOP.
    # Only meaningful when the manifest declares a section_order; test
    # manifests without one skip the prose-placement check below.
    sop_section_ids = {
        str(entry["id"])
        for entry in manifest.get("section_order") or []
        if entry.get("id")
    }
    for entry in manifest.get("append_sections") or []:
        if entry.get("id"):
            sop_section_ids.add(str(entry["id"]))

    # Manifest-seeded shuffled section order, matching the kit builder's
    # pooled-artifact ordering so compilation and materialization agree.
    ordered_section_ids = sorted(
        source_schemas, key=lambda section_id: _seeded_order(manifest_id, section_id)
    )

    # Resolve cross-section ownership before compiling individual
    # transformations. Invalid or unreadable schemas are still diagnosed by
    # the existing section sweep below; this pre-pass only supplies the valid
    # schemas needed to validate declared domain dependencies.
    hierarchy_schemas: dict[str, dict[str, Any]] = {}
    for section_id in ordered_section_ids:
        schema_path = _resolve_data_relative(
            source_schemas[section_id], data_dir=data_dir
        )
        if not schema_path.is_file():
            continue
        try:
            hierarchy_schema = json.loads(schema_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(hierarchy_schema, dict):
            hierarchy_schemas[str(section_id)] = hierarchy_schema
    compilation.section_hierarchy = resolve_domain_fact_hierarchy(hierarchy_schemas)
    for section_id, hierarchy in compilation.section_hierarchy.items():
        compilation.errors.extend(
            f"section {section_id!r}: {issue}" for issue in hierarchy.validation_issues
        )

    inherited_by_fact: dict[tuple[str, str], list[str]] = {}
    for consumer_section_id, hierarchy in compilation.section_hierarchy.items():
        for inherited_fact in hierarchy.inherited_facts:
            inherited_by_fact.setdefault(
                (inherited_fact.owner_section_id, inherited_fact.fact_id), []
            ).append(consumer_section_id)

    for section_id in ordered_section_ids:
        schema_path = _resolve_data_relative(
            source_schemas[section_id], data_dir=data_dir
        )
        if not schema_path.exists():
            compilation.errors.append(f"SOP source schema not found: {schema_path}")
            continue
        try:
            schema = json.loads(schema_path.read_text())
        except (OSError, json.JSONDecodeError) as error:
            compilation.errors.append(
                f"SOP source schema for section {section_id!r} is not "
                f"readable JSON: {schema_path} ({error})"
            )
            continue
        if not isinstance(schema, dict):
            compilation.errors.append(
                f"SOP source schema for section {section_id!r} must be a "
                f"JSON object, got {type(schema).__name__}: {schema_path}"
            )
            continue

        section_facts: list[FactCoverage] = []
        seen_fact_ids: set[str] = set()
        section_hierarchy = compilation.section_hierarchy.get(str(section_id))
        for fact in schema.get("facts") or []:
            if not isinstance(fact, dict) or "id" not in fact:
                compilation.errors.append(
                    f"section {section_id!r} declares a malformed fact "
                    f"entry (expected an object with an 'id'): {fact!r}"
                )
                continue
            fact_id = str(fact["id"])
            if fact_id in seen_fact_ids:
                # A duplicate would make coverage bookkeeping ambiguous
                # (which copy did a transformation cover?), so it is
                # genuine schema breakage, not a coverage question.
                compilation.errors.append(
                    f"section {section_id!r} declares duplicate fact id {fact_id!r}"
                )
                continue
            seen_fact_ids.add(fact_id)
            section_facts.append(
                FactCoverage(
                    section_id=section_id,
                    fact_id=fact_id,
                    statement=str(fact.get("statement", "")),
                    owner_role=(
                        section_hierarchy.role
                        if section_hierarchy is not None
                        else "standalone"
                    ),
                    inherited_by_section_ids=sorted(
                        inherited_by_fact.get((str(section_id), fact_id), [])
                    ),
                )
            )
        facts_by_id = {fact.fact_id: fact for fact in section_facts}
        compilation.facts.extend(section_facts)

        specs: list[
            tuple[
                dict[str, Any],
                bool,
                Optional[str],
                Optional[set[str]],
                set[str],
            ]
        ] = []
        selected_bundle_definitions: list[
            tuple[dict[str, Any], list[str], list[EvidenceRouteActivation]]
        ] = []
        selected_bundle_ids = bundles_by_section.get(section_id, [])
        if selected_bundle_ids:
            bundle_error_count = len(compilation.errors)
            candidate_specs: list[
                tuple[dict[str, Any], bool, str, set[str], set[str]]
            ] = []
            candidate_bundle_definitions: list[
                tuple[dict[str, Any], list[str], list[EvidenceRouteActivation]]
            ] = []
            authority_across_bundles: dict[str, str] = {}
            for bundle_id in selected_bundle_ids:
                try:
                    bundle = resolve_transformation_bundle(schema, bundle_id)
                except ValueError as error:
                    compilation.errors.append(f"section {section_id!r}: {error}")
                    continue

                bundle_stub_path = bundle.get("stub_path")
                if not isinstance(bundle_stub_path, str):
                    compilation.errors.append(
                        f"section {section_id!r} bundle {bundle_id!r}: "
                        "stub_path must be a string"
                    )
                elif not _resolve_data_relative(
                    bundle_stub_path, data_dir=data_dir
                ).exists():
                    compilation.errors.append(
                        f"section {section_id!r} bundle {bundle_id!r}: "
                        f"stub not found: {bundle_stub_path}"
                    )

                raw_fact_ids = bundle.get("fact_ids") or []
                if not isinstance(raw_fact_ids, list) or not all(
                    isinstance(fact_id, str) for fact_id in raw_fact_ids
                ):
                    compilation.errors.append(
                        f"section {section_id!r} bundle {bundle_id!r}: "
                        "fact_ids must be a list of strings"
                    )
                    continue
                bundle_fact_ids = list(raw_fact_ids)
                if len(bundle_fact_ids) != len(set(bundle_fact_ids)):
                    compilation.errors.append(
                        f"section {section_id!r} bundle {bundle_id!r}: "
                        "fact_ids contains duplicates"
                    )
                unknown_bundle_facts = set(bundle_fact_ids) - set(facts_by_id)
                if unknown_bundle_facts:
                    compilation.errors.append(
                        f"section {section_id!r} bundle {bundle_id!r}: "
                        f"unknown fact ids {sorted(unknown_bundle_facts)}"
                    )

                members = bundle.get("members") or []
                if not isinstance(members, list) or not members:
                    compilation.errors.append(
                        f"section {section_id!r} bundle {bundle_id!r}: "
                        "members must be a non-empty list"
                    )
                    continue
                primary_members = [
                    member
                    for member in members
                    if isinstance(member, dict) and member.get("primary") is True
                ]
                if len(primary_members) > 1:
                    compilation.errors.append(
                        f"section {section_id!r} bundle {bundle_id!r}: "
                        "at most one member may be primary"
                    )

                authority_in_bundle: dict[str, str] = {}
                resolved_members: list[
                    tuple[dict[str, Any], dict[str, Any], set[str], set[str]]
                ] = []
                for member_index, member in enumerate(members):
                    if not isinstance(member, dict):
                        compilation.errors.append(
                            f"section {section_id!r} bundle {bundle_id!r}: "
                            f"member {member_index} must be an object"
                        )
                        continue
                    transformation_id = member.get("transformation_id")
                    if not isinstance(transformation_id, str):
                        compilation.errors.append(
                            f"section {section_id!r} bundle {bundle_id!r}: "
                            f"member {member_index} must declare transformation_id"
                        )
                        continue
                    raw_authoritative = member.get("authoritative_fact_ids") or []
                    raw_dependencies = member.get("depends_on_fact_ids") or []
                    if not isinstance(raw_authoritative, list) or not all(
                        isinstance(fact_id, str) for fact_id in raw_authoritative
                    ):
                        compilation.errors.append(
                            f"section {section_id!r} bundle {bundle_id!r} "
                            f"member {transformation_id!r}: "
                            "authoritative_fact_ids must be a list of strings"
                        )
                        continue
                    if not isinstance(raw_dependencies, list) or not all(
                        isinstance(fact_id, str) for fact_id in raw_dependencies
                    ):
                        compilation.errors.append(
                            f"section {section_id!r} bundle {bundle_id!r} "
                            f"member {transformation_id!r}: "
                            "depends_on_fact_ids must be a list of strings"
                        )
                        continue
                    authoritative = set(raw_authoritative)
                    dependencies = set(raw_dependencies)
                    if len(authoritative) != len(raw_authoritative):
                        compilation.errors.append(
                            f"section {section_id!r} bundle {bundle_id!r} "
                            f"member {transformation_id!r}: "
                            "authoritative_fact_ids contains duplicates"
                        )
                    if len(dependencies) != len(raw_dependencies):
                        compilation.errors.append(
                            f"section {section_id!r} bundle {bundle_id!r} "
                            f"member {transformation_id!r}: "
                            "depends_on_fact_ids contains duplicates"
                        )
                    for fact_id in authoritative:
                        previous_owner = authority_in_bundle.get(fact_id)
                        if previous_owner is not None:
                            compilation.errors.append(
                                f"section {section_id!r} bundle {bundle_id!r}: "
                                f"fact {fact_id!r} has multiple authoritative "
                                f"members ({previous_owner!r}, "
                                f"{transformation_id!r})"
                            )
                        else:
                            authority_in_bundle[fact_id] = transformation_id
                    try:
                        spec = resolve_transformation_spec_by_id(
                            schema, transformation_id
                        )
                    except ValueError as error:
                        compilation.errors.append(
                            f"section {section_id!r} bundle {bundle_id!r}: {error}"
                        )
                        continue
                    resolved_members.append((member, spec, authoritative, dependencies))

                evidence_routes = _parse_evidence_routes(
                    bundle,
                    section_id=section_id,
                    bundle_id=bundle_id,
                    facts_by_id=facts_by_id,
                    member_specs={
                        str(member["transformation_id"]): spec
                        for member, spec, _authoritative, _dependencies in resolved_members
                    },
                    authority_in_bundle=authority_in_bundle,
                    errors=compilation.errors,
                )

                declared = set(bundle_fact_ids)
                authoritative_union = set(authority_in_bundle)
                if authoritative_union != declared:
                    missing = sorted(declared - authoritative_union)
                    extra = sorted(authoritative_union - declared)
                    compilation.errors.append(
                        f"section {section_id!r} bundle {bundle_id!r}: member and "
                        "evidence-route authority must exactly match bundle fact_ids "
                        f"(missing={missing}, extra={extra})"
                    )
                for (
                    member,
                    member_spec,
                    authoritative,
                    _dependencies,
                ) in resolved_members:
                    if not _is_client_knowledge_spec(member_spec):
                        continue
                    transformation_id = str(member["transformation_id"])
                    confirmable = set(member_spec.get("confirmable_fact_ids") or [])
                    # Confirmable facts are adjudicated by the Client but
                    # owned by artifact members — the Client can say a
                    # reading is right or wrong only about facts the
                    # Developer can actually find in the kit.
                    not_carried = sorted(
                        confirmable - (authoritative_union - authoritative)
                    )
                    if not_carried:
                        compilation.errors.append(
                            f"section {section_id!r} bundle {bundle_id!r} "
                            f"member {transformation_id!r}: "
                            "confirmable_fact_ids must be carried by other "
                            f"bundle members: {not_carried}"
                        )
                _check_client_overlay(
                    schema,
                    bundle,
                    section_id=section_id,
                    bundle_id=bundle_id,
                    declared_fact_ids=declared,
                    resolved_members=resolved_members,
                    overlay_routes=evidence_routes,
                    facts_by_id=facts_by_id,
                    errors=compilation.errors,
                )
                contested = _check_contested_facts(
                    bundle,
                    section_id=section_id,
                    bundle_id=bundle_id,
                    declared_fact_ids=declared,
                    resolved_members=resolved_members,
                    errors=compilation.errors,
                )
                if contested:
                    compilation.client_contested_fact_ids.setdefault(
                        section_id, {}
                    ).update(contested)
                for member, _spec, authoritative, dependencies in resolved_members:
                    transformation_id = str(member["transformation_id"])
                    unresolved = dependencies - authoritative_union
                    if unresolved:
                        compilation.errors.append(
                            f"section {section_id!r} bundle {bundle_id!r} "
                            f"member {transformation_id!r}: dependencies are "
                            f"not represented inside the bundle: "
                            f"{sorted(unresolved)}"
                        )
                    self_dependencies = dependencies & authoritative
                    if self_dependencies:
                        compilation.errors.append(
                            f"section {section_id!r} bundle {bundle_id!r} "
                            f"member {transformation_id!r}: dependencies must "
                            "be owned by another member, not itself: "
                            f"{sorted(self_dependencies)}"
                        )

                for fact_id in authoritative_union:
                    previous_bundle = authority_across_bundles.get(fact_id)
                    if previous_bundle is not None:
                        compilation.errors.append(
                            f"section {section_id!r}: fact {fact_id!r} is "
                            "authoritative in multiple selected bundles "
                            f"({previous_bundle!r}, {bundle_id!r})"
                        )
                    else:
                        authority_across_bundles[fact_id] = bundle_id

                has_explicit_primary = bool(primary_members)
                substituted_member_ids = set(
                    (bundle.get("member_substitutions") or {}).values()
                )
                for member_index, (
                    member,
                    spec,
                    authoritative,
                    dependencies,
                ) in enumerate(resolved_members):
                    primary = (
                        member.get("primary") is True
                        if has_explicit_primary
                        else member_index == 0
                    )
                    candidate_specs.append(
                        (
                            spec,
                            primary,
                            bundle_id,
                            authoritative,
                            dependencies,
                            str(member["transformation_id"]) in substituted_member_ids,
                        )
                    )
                candidate_bundle_definitions.append(
                    (bundle, bundle_fact_ids, evidence_routes)
                )
            selected_stub_paths = {
                str(bundle["stub_path"])
                for bundle, _fact_ids, _routes in candidate_bundle_definitions
                if isinstance(bundle.get("stub_path"), str)
            }
            if len(selected_stub_paths) != 1:
                compilation.errors.append(
                    f"section {section_id!r}: selected bundles must resolve "
                    "to exactly one shared stub_path, got "
                    f"{sorted(selected_stub_paths)}"
                )
            if len(compilation.errors) == bundle_error_count:
                specs.extend(candidate_specs)
                selected_bundle_definitions.extend(candidate_bundle_definitions)
        else:
            active_stub_path = active_stub_paths.get(section_id)
            try:
                primary_spec = select_section_transformation(schema, active_stub_path)
            except ValueError as error:
                compilation.errors.append(str(error))
                continue
            if (
                active_stub_path is not None
                and primary_spec.get("stub_path") != active_stub_path
            ):
                # select_section_transformation fell back to the first
                # declared transformation: the SOP splices a stub the schema
                # knows nothing about while the kit materializes something
                # else.
                compilation.warnings.append(
                    f"section {section_id!r}: active stub path "
                    f"{active_stub_path!r} matches no declared "
                    "transformation; defaulting to "
                    f"{primary_spec.get('representation')!r} — the assembled "
                    "SOP and the materialized artifacts may disagree"
                )
            specs.append((primary_spec, True, None, None, set(), False))
            for entry in additional_by_section.get(section_id, []):
                try:
                    spec = _match_additional_spec(
                        schema,
                        str(entry["representation"]),
                        entry.get("stub_path"),
                    )
                except ValueError as error:
                    compilation.errors.append(f"section {section_id!r}: {error}")
                    continue
                if spec is None:
                    compilation.errors.append(
                        f"section {section_id!r} declares no "
                        f"{entry['representation']!r} transformation matching "
                        f"{entry!r}"
                    )
                    continue
                if any(existing is spec for existing, *_ in specs):
                    # Already active (as the primary or via an earlier
                    # duplicate entry); activating it twice would duplicate
                    # its artifacts in the kit.
                    if spec is not primary_spec:
                        compilation.warnings.append(
                            f"duplicate additional transformation entry for "
                            f"section {section_id!r} ignored: {entry!r}"
                        )
                    continue
                specs.append((spec, False, None, None, set(), False))

        activation_error_count = len(compilation.errors)
        candidate_activations: list[TransformationActivation] = []
        for (
            spec,
            primary,
            bundle_id,
            authoritative,
            dependencies,
            client_substitute,
        ) in specs:
            try:
                transformation = get_transformation(str(spec["representation"]))
            except KeyError as error:
                compilation.errors.append(
                    f"section {section_id!r} declares an unknown "
                    f"representation: {error}"
                )
                continue
            if (
                transformation.representation == "explicit_rules"
                and manifest.get("section_order")
                and section_id not in sop_section_ids
            ):
                # explicit_rules coverage is the section's prose in the
                # assembled SOP. If the section appears nowhere in the
                # manifest's section_order (or append_sections), that prose
                # is nowhere the Developer can read it — marking its facts
                # covered would be false.
                compilation.errors.append(
                    f"section {section_id!r} activates 'explicit_rules' but "
                    "does not appear in the manifest's section_order or "
                    "append_sections; its prose is not part of the assembled "
                    "SOP, so its facts cannot be covered by it"
                )
                continue
            if (
                transformation.representation == "client_knowledge"
                and bundle_id is None
            ):
                # client_knowledge assigns facts to the Client simulator, so
                # its coverage is only honest when a bundle makes the
                # ownership explicit and the paired artifact members
                # genuinely omit those facts. As a standalone primary or
                # additional transformation nothing enforces that pairing.
                compilation.errors.append(
                    f"section {section_id!r} activates 'client_knowledge' "
                    "outside a transformation bundle; client-held facts must "
                    "be assigned via a bundle member so artifact/client "
                    "ownership stays explicit"
                )
                continue
            try:
                artifacts = transformation.discover_artifacts(schema, schema_path, spec)
            except (KeyError, ValueError, FileNotFoundError) as error:
                compilation.errors.append(
                    f"section {section_id!r} "
                    f"{spec.get('representation')!r} transformation: {error}"
                )
                continue
            issues = transformation.validate(schema, artifacts)
            if issues:
                compilation.errors.append(
                    f"Section {section_id!r} {transformation.representation} "
                    "transformation failed validation: " + "; ".join(issues)
                )
                continue
            covered = transformation.covered_fact_ids(schema, artifacts)
            if authoritative is not None and covered != authoritative:
                compilation.errors.append(
                    f"section {section_id!r} bundle {bundle_id!r} member "
                    f"{spec.get('id')!r}: artifact coverage must exactly "
                    "match authoritative_fact_ids "
                    f"(missing={sorted(authoritative - covered)}, "
                    f"extra={sorted(covered - authoritative)})"
                )
                continue
            activation = TransformationActivation(
                section_id=section_id,
                representation=transformation.representation,
                spec=spec,
                transformation=transformation,
                artifacts=artifacts,
                primary=primary,
                covered_fact_ids=sorted(covered),
                bundle_id=bundle_id,
                authoritative_fact_ids=(
                    sorted(authoritative) if authoritative is not None else None
                ),
                depends_on_fact_ids=sorted(dependencies),
                inherited_fact_ids=(
                    list(section_hierarchy.inherited_fact_ids)
                    if section_hierarchy is not None
                    else []
                ),
                client_substitute=client_substitute,
            )
            candidate_activations.append(activation)

        activations_valid = (
            not selected_bundle_ids or len(compilation.errors) == activation_error_count
        )
        if activations_valid:
            compilation.activations.extend(candidate_activations)
            for activation in candidate_activations:
                for fact_id in activation.covered_fact_ids:
                    fact = facts_by_id.get(fact_id)
                    if fact is not None:
                        fact.representations.append(activation.representation)

            for bundle, bundle_fact_ids, evidence_routes in selected_bundle_definitions:
                bundle_id = str(bundle.get("id"))
                for route in evidence_routes:
                    for fact_id in route.authoritative_fact_ids:
                        fact = facts_by_id.get(fact_id)
                        if fact is not None:
                            fact.representations.append("linked_evidence_route")
                compilation.bundles.append(
                    TransformationBundleActivation(
                        section_id=section_id,
                        bundle_id=bundle_id,
                        description=str(bundle.get("description", "")),
                        stub_path=(
                            str(bundle["stub_path"])
                            if bundle.get("stub_path")
                            else None
                        ),
                        fact_ids=list(bundle_fact_ids),
                        members=[
                            activation
                            for activation in candidate_activations
                            if activation.bundle_id == bundle_id
                        ],
                        evidence_routes=list(evidence_routes),
                    )
                )

    uncovered = compilation.uncovered_facts
    if uncovered and not compilation.errors:
        described = ", ".join(f"{fact.section_id}.{fact.fact_id}" for fact in uncovered)
        if compilation.uncovered_fact_policy == "error":
            compilation.errors.append(
                f"facts not covered by any active transformation: {described}"
            )
        else:
            compilation.warnings.append(
                f"{len(uncovered)} fact(s) not covered by any active "
                f"transformation; routed to the explicit-rules fallback: "
                f"{described}"
            )
    return compilation


def render_fallback_markdown(
    facts: list[FactCoverage],
    *,
    manifest_id: str = "",
    heading: str = FALLBACK_HEADING,
) -> str:
    """Render uncovered facts as a simple explicit-rules appendix.

    Fact order is shuffled deterministically (seeded by the manifest id)
    so the appendix does not leak the section grouping of the fact
    schemas.
    """
    ordered = sorted(
        facts,
        key=lambda fact: _seeded_order(manifest_id, fact.section_id, fact.fact_id),
    )
    lines = [heading, "", "The following rules also apply:", ""]
    lines.extend(f"- {fact.statement}" for fact in ordered)
    return "\n".join(lines) + "\n"


def compile_hyper_task(
    task_or_id: Union[str, Any], *, data_dir: Path = DATA_DIR
) -> VariantCompilation:
    """Compile the variant manifest behind a Hyper-τ task.

    Accepts a task id or a loaded ``HyperTask``. Tasks without a
    ``sop_variant_manifest_path`` have no fact schemas to audit; the
    result carries a warning saying so.
    """
    from tau2.hyper.task_loader import load_hyper_tau_task
    from tau2.hyper.transformations.sop_variants import load_sop_variant_manifest

    task = (
        load_hyper_tau_task(task_or_id) if isinstance(task_or_id, str) else task_or_id
    )
    manifest_path = getattr(task, "sop_variant_manifest_path", None)
    if not manifest_path:
        compilation = VariantCompilation(manifest_id=f"<task:{task.id}>")
        compilation.warnings.append(
            f"task {task.id!r} has no sop_variant_manifest_path; no fact "
            "schemas are declared, so there is no coverage to report"
        )
        return compilation
    manifest = load_sop_variant_manifest(manifest_path, data_dir=data_dir)
    return compile_variant_transformations(manifest, data_dir=data_dir)
