"""Cross-section fact ownership and dependency resolution for transformations.

Section headings are useful source-provenance boundaries, but they are not
independent policy modules. A journey such as booking can depend on global
identity rules without owning or re-representing them. This module resolves
that domain-level graph while keeping every atomic fact owned by exactly one
section schema.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

SECTION_ROLES = (
    "standalone",
    "global_prerequisite",
    "shared_reference",
    "journey",
)


@dataclass(frozen=True)
class InheritedFact:
    """One fact inherited from another section."""

    owner_section_id: str
    fact_id: str
    statement: str
    category: str
    depth: int

    @property
    def qualified_fact_id(self) -> str:
        return f"{self.owner_section_id}.{self.fact_id}"

    def view(self) -> dict[str, Any]:
        """Return a deterministic JSON-serializable representation."""
        return {
            "qualified_fact_id": self.qualified_fact_id,
            "owner_section_id": self.owner_section_id,
            "fact_id": self.fact_id,
            "statement": self.statement,
            "category": self.category,
            "depth": self.depth,
        }


@dataclass(frozen=True)
class SectionRequirement:
    """A direct dependency declared by one section."""

    section_id: str
    fact_ids: tuple[str, ...]
    relationship: str = "requires"
    description: str = ""

    def view(self) -> dict[str, Any]:
        """Return a deterministic JSON-serializable representation."""
        return {
            "section_id": self.section_id,
            "fact_ids": list(self.fact_ids),
            "qualified_fact_ids": [
                f"{self.section_id}.{fact_id}" for fact_id in self.fact_ids
            ],
            "relationship": self.relationship,
            "description": self.description,
        }


@dataclass
class SectionFactHierarchy:
    """Resolved domain role and inherited facts for one section."""

    section_id: str
    role: str = "standalone"
    requirements: list[SectionRequirement] = field(default_factory=list)
    inherited_facts: list[InheritedFact] = field(default_factory=list)
    validation_issues: list[str] = field(default_factory=list)

    @property
    def inherited_fact_ids(self) -> list[str]:
        return [fact.qualified_fact_id for fact in self.inherited_facts]

    def view(self) -> dict[str, Any]:
        """Return the Studio/report view of this section's hierarchy."""
        return {
            "role": self.role,
            "requires": [requirement.view() for requirement in self.requirements],
            "inherited_facts": [fact.view() for fact in self.inherited_facts],
            "validation_issues": list(self.validation_issues),
        }


def _facts_by_id(schema: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(fact["id"]): fact
        for fact in schema.get("facts") or []
        if isinstance(fact, dict) and "id" in fact
    }


def resolve_domain_fact_hierarchy(
    schemas: Mapping[str, Mapping[str, Any]],
) -> dict[str, SectionFactHierarchy]:
    """Resolve roles and transitive fact dependencies across section schemas.

    Schemas opt in with a ``domain_hierarchy`` object:

    .. code-block:: json

       {
         "role": "journey",
         "requires": [
           {
             "section_id": "customer_identity",
             "fact_ids": ["every_interaction_starts_with_identity"]
           }
         ]
       }

    Fact references are section-qualified in resolved output, so schemas may
    continue using compact local ids without creating ambiguous ownership.
    """

    resolved = {
        str(section_id): SectionFactHierarchy(section_id=str(section_id))
        for section_id in schemas
    }
    parsed_requirements: dict[str, list[SectionRequirement]] = {
        str(section_id): [] for section_id in schemas
    }

    for raw_section_id, schema in schemas.items():
        section_id = str(raw_section_id)
        section = resolved[section_id]
        raw_hierarchy = schema.get("domain_hierarchy")
        if raw_hierarchy is None:
            continue
        if not isinstance(raw_hierarchy, dict):
            section.validation_issues.append("domain_hierarchy must be an object")
            continue

        role = raw_hierarchy.get("role", "standalone")
        if not isinstance(role, str) or role not in SECTION_ROLES:
            section.validation_issues.append(
                f"domain_hierarchy.role must be one of {list(SECTION_ROLES)}"
            )
        else:
            section.role = role

        raw_requirements = raw_hierarchy.get("requires") or []
        if not isinstance(raw_requirements, list):
            section.validation_issues.append("domain_hierarchy.requires must be a list")
            continue

        seen_qualified_ids: set[str] = set()
        for index, raw_requirement in enumerate(raw_requirements):
            if not isinstance(raw_requirement, dict):
                section.validation_issues.append(
                    f"domain_hierarchy.requires[{index}] must be an object"
                )
                continue
            owner_section_id = raw_requirement.get("section_id")
            if not isinstance(owner_section_id, str) or not owner_section_id:
                section.validation_issues.append(
                    f"domain_hierarchy.requires[{index}].section_id must be "
                    "a non-empty string"
                )
                continue
            raw_fact_ids = raw_requirement.get("fact_ids")
            if (
                not isinstance(raw_fact_ids, list)
                or not raw_fact_ids
                or not all(
                    isinstance(fact_id, str) and fact_id for fact_id in raw_fact_ids
                )
            ):
                section.validation_issues.append(
                    f"domain_hierarchy.requires[{index}].fact_ids must be a "
                    "non-empty list of strings"
                )
                continue
            fact_ids = tuple(dict.fromkeys(raw_fact_ids))
            if len(fact_ids) != len(raw_fact_ids):
                section.validation_issues.append(
                    f"domain_hierarchy.requires[{index}].fact_ids contains duplicates"
                )
            relationship = raw_requirement.get("relationship", "requires")
            if not isinstance(relationship, str) or not relationship:
                section.validation_issues.append(
                    f"domain_hierarchy.requires[{index}].relationship must be "
                    "a non-empty string"
                )
                relationship = "requires"
            description = raw_requirement.get("description", "")
            if not isinstance(description, str):
                section.validation_issues.append(
                    f"domain_hierarchy.requires[{index}].description must be a string"
                )
                description = ""

            requirement = SectionRequirement(
                section_id=owner_section_id,
                fact_ids=fact_ids,
                relationship=relationship,
                description=description,
            )
            parsed_requirements[section_id].append(requirement)
            section.requirements.append(requirement)

            if owner_section_id == section_id:
                section.validation_issues.append(
                    "domain_hierarchy cannot require facts from its own section"
                )
                continue
            owner_schema = schemas.get(owner_section_id)
            if owner_schema is None:
                section.validation_issues.append(
                    f"requires unknown section {owner_section_id!r}"
                )
                continue
            owner_fact_ids = set(_facts_by_id(owner_schema))
            unknown_fact_ids = sorted(set(fact_ids) - owner_fact_ids)
            if unknown_fact_ids:
                section.validation_issues.append(
                    f"requires unknown facts from {owner_section_id!r}: "
                    f"{unknown_fact_ids}"
                )
            for fact_id in fact_ids:
                qualified_id = f"{owner_section_id}.{fact_id}"
                if qualified_id in seen_qualified_ids:
                    section.validation_issues.append(
                        f"requires fact {qualified_id!r} more than once"
                    )
                seen_qualified_ids.add(qualified_id)

    def collect(
        root_section_id: str,
        current_section_id: str,
        depth: int,
        path: tuple[str, ...],
        inherited: dict[str, InheritedFact],
    ) -> None:
        for requirement in parsed_requirements[current_section_id]:
            owner_section_id = requirement.section_id
            if (
                owner_section_id not in schemas
                or owner_section_id == current_section_id
            ):
                continue
            if owner_section_id in path:
                cycle = " -> ".join((*path, owner_section_id))
                issue = f"domain_hierarchy dependency cycle: {cycle}"
                if issue not in resolved[root_section_id].validation_issues:
                    resolved[root_section_id].validation_issues.append(issue)
                continue

            owner_facts = _facts_by_id(schemas[owner_section_id])
            for fact_id in requirement.fact_ids:
                fact = owner_facts.get(fact_id)
                if fact is None:
                    continue
                candidate = InheritedFact(
                    owner_section_id=owner_section_id,
                    fact_id=fact_id,
                    statement=str(fact.get("statement", "")),
                    category=str(fact.get("category", "")),
                    depth=depth,
                )
                existing = inherited.get(candidate.qualified_fact_id)
                if existing is None or candidate.depth < existing.depth:
                    inherited[candidate.qualified_fact_id] = candidate
            collect(
                root_section_id,
                owner_section_id,
                depth + 1,
                (*path, owner_section_id),
                inherited,
            )

    for section_id, section in resolved.items():
        inherited: dict[str, InheritedFact] = {}
        collect(section_id, section_id, 1, (section_id,), inherited)
        section.inherited_facts = sorted(
            inherited.values(),
            key=lambda fact: (fact.depth, fact.qualified_fact_id),
        )

    return resolved
