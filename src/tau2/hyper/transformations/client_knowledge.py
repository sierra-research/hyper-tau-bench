"""
Client-held knowledge: facts the Client simulator carries instead of the kit.

A bundle member rendered as ``client_knowledge`` assigns its authoritative
facts to the simulated stakeholder rather than to any delivered artifact.
The facts appear in no kit file — the only way the Developer can learn
them is to ask the Client (``talk_to_client``). Registering the channel as
a transformation lets variant compilation account for it honestly: the
facts count as covered (they are learnable), fact ownership stays
explicit, and their absence from the materialized kit is a declared
property rather than an accident.

The spec may also declare ``confirmable_fact_ids``: facts the Client can
adjudicate but does not own. They stay artifact-carried by other bundle
members (they are NOT part of this member's authority), and the Client
will confirm or deny a specific reading of them — never supply the
correct version. Everything outside the held and confirmable lists the
Client points back to the records.

An optional ``discovery_tiers`` map records how discoverable each held
fact is from the delivered kit (``pointer`` / ``caveat`` / ``silent``,
one entry per held fact) so the signposting design is machine-readable
rather than implicit in artifact prose.

Only meaningful as a transformation-bundle member on a task that enables
the Client (``client_sections``); compilation rejects it as a standalone
primary or additional transformation because nothing outside a bundle
enforces that the paired artifacts genuinely omit the client-held facts.
The bundle itself is an overlay on an artifact-only base bundle and must
declare ``client_overlay_of`` (see ``_check_client_overlay`` in
``compile.py``): held facts are carved out of declared member
substitutions, and everything else must match the base verbatim.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tau2.hyper.transformations.base import (
    KitFile,
    SectionTransformation,
    TransformationArtifact,
    register_transformation,
)

# How discoverable each held fact is from the delivered kit. ``pointer``:
# an artifact explicitly refers the question to the customer working group.
# ``caveat``: the only trail is mundane document-quality boilerplate (e.g.
# an export "has not been refreshed since" its capture date). ``silent``:
# no trail in any delivered artifact.
DISCOVERY_TIERS = frozenset({"pointer", "caveat", "silent"})


class ClientKnowledgeTransformation(SectionTransformation):
    """Assign a subset of a section's facts to the Client simulator."""

    representation = "client_knowledge"
    aliases = ("client_held",)
    placement = "named"
    kit_dirname = ""
    carries_agent_utterances = False
    materializes = False

    def discover_artifacts(
        self,
        schema: dict[str, Any],
        schema_path: Path,
        spec: dict[str, Any],
    ) -> list[TransformationArtifact]:
        fact_ids = spec.get("fact_ids")
        if (
            not isinstance(fact_ids, list)
            or not fact_ids
            or not all(isinstance(fact_id, str) for fact_id in fact_ids)
        ):
            raise ValueError(
                "client_knowledge transformation for section schema "
                f"{schema.get('id', '<unknown>')!r} must declare a non-empty "
                "fact_ids list of strings"
            )
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError(
                "client_knowledge transformation for section schema "
                f"{schema.get('id', '<unknown>')!r} declares duplicate "
                "fact_ids"
            )
        confirmable = spec.get("confirmable_fact_ids") or []
        if not isinstance(confirmable, list) or not all(
            isinstance(fact_id, str) for fact_id in confirmable
        ):
            raise ValueError(
                "client_knowledge transformation for section schema "
                f"{schema.get('id', '<unknown>')!r}: confirmable_fact_ids "
                "must be a list of strings"
            )
        if len(confirmable) != len(set(confirmable)):
            raise ValueError(
                "client_knowledge transformation for section schema "
                f"{schema.get('id', '<unknown>')!r} declares duplicate "
                "confirmable_fact_ids"
            )
        overlap = sorted(set(confirmable) & set(fact_ids))
        if overlap:
            raise ValueError(
                "client_knowledge transformation for section schema "
                f"{schema.get('id', '<unknown>')!r}: confirmable_fact_ids "
                f"overlap the held fact_ids: {overlap}; a fact is either "
                "held (answered plainly) or confirmable (adjudicated), "
                "never both"
            )
        known = {
            str(fact.get("id"))
            for fact in schema.get("facts") or []
            if isinstance(fact, dict)
        }
        unknown = sorted(set(confirmable) - known)
        if unknown:
            raise ValueError(
                "client_knowledge transformation for section schema "
                f"{schema.get('id', '<unknown>')!r}: confirmable_fact_ids "
                f"name facts not in the section schema: {unknown}"
            )
        tiers = spec.get("discovery_tiers")
        if tiers is not None:
            if not isinstance(tiers, dict) or not all(
                isinstance(key, str) and isinstance(value, str)
                for key, value in tiers.items()
            ):
                raise ValueError(
                    "client_knowledge transformation for section schema "
                    f"{schema.get('id', '<unknown>')!r}: discovery_tiers must "
                    "map held fact ids to tier names"
                )
            if set(tiers) != set(fact_ids):
                raise ValueError(
                    "client_knowledge transformation for section schema "
                    f"{schema.get('id', '<unknown>')!r}: discovery_tiers keys "
                    "must match the held fact_ids exactly"
                )
            bad = sorted({value for value in tiers.values()} - DISCOVERY_TIERS)
            if bad:
                raise ValueError(
                    "client_knowledge transformation for section schema "
                    f"{schema.get('id', '<unknown>')!r}: unknown discovery "
                    f"tiers {bad}; allowed: {sorted(DISCOVERY_TIERS)}"
                )
        # One carrier artifact records which facts the Client holds. The
        # schema path is provenance for auditing tools; nothing is read
        # from it at kit-build time because nothing is built.
        return [
            TransformationArtifact(
                source_path=schema_path,
                included_fact_ids=list(fact_ids),
            )
        ]

    def neutralize(self, artifact: TransformationArtifact, ordinal: int) -> KitFile:
        raise NotImplementedError(
            "client_knowledge facts live in the Client simulator; there is "
            "no kit artifact to neutralize"
        )

    def to_text(self, artifact: TransformationArtifact) -> str:
        schema = json.loads(artifact.source_path.read_text())
        held = set(artifact.included_fact_ids)
        statements = [
            str(fact.get("statement", ""))
            for fact in schema.get("facts") or []
            if isinstance(fact, dict) and str(fact.get("id")) in held
        ]
        lines = ["Client-held facts (in no kit artifact; ask the Client):", ""]
        lines.extend(f"- {statement}" for statement in statements)
        return "\n".join(lines)


register_transformation(ClientKnowledgeTransformation())
