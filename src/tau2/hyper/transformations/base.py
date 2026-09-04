"""
Section-transformation registry for information-distribution variants.

A *transformation* re-encodes a SOP section's fact schema into a different
artifact type: support transcripts, customer documents, flowcharts, and
so on. Each representation registers a :class:`SectionTransformation` that knows
how to

- discover its artifacts from a section fact schema,
- neutralize them for inclusion in a construction kit (strip section ids,
  generation filenames, and anything else the Developer should not see),
- convert an artifact to plain text for fact-coverage judging, and
- validate that the declared artifacts cover the schema's atomic facts.

The kit builder is representation-agnostic: it selects the active transformation
for each section, asks the registry for the transformation, and writes whatever
:class:`KitFile` objects the transformation emits.

Two placement modes exist:

- ``pooled``: artifacts from every section are flattened into one shared,
  anonymized kit directory (transcripts use this so section boundaries are
  hidden — hiding the section map is itself an information-distribution
  choice).
- ``named``: each artifact is neutralized independently before the kit assembler
  replaces its business filename with a generic artifact-genre name.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional

from tau2.hyper.transformations.modality import (
    ModalityProfile,
    modality_for_path,
)
from tau2.utils.utils import DATA_DIR


@dataclass
class TransformationArtifact:
    """One source artifact of a section transformation."""

    source_path: Path
    included_fact_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class KitFile:
    """A neutralized artifact ready to be written into a construction kit."""

    relative_path: str
    content: bytes
    artifact_kind: Optional[str] = None
    #: Preserve an explicitly neutral basename when another delivered artifact
    #: cites it. The transformation validator is responsible for ensuring the
    #: name is safe and non-topic-bearing.
    preserve_filename: bool = False
    #: Sibling files renamed together with this file: a companion keeps its
    #: own suffix but always shares the primary's final stem, so a paired
    #: delivery (``case_file_07.md`` + ``case_file_07.m4a``) survives the
    #: generic-name pooling pass.
    companions: list["KitFile"] = field(default_factory=list)
    #: Set when modality substitution replaced the native rendition; holds
    #: the modality that was substituted away (e.g. ``"image"``). Recorded
    #: in the transformation report, never shown to the Developer.
    substituted_from: Optional[str] = None
    #: True when this file was delivered by a client-overlay substituted
    #: member. At kit assembly it replaces any base-member file of the same
    #: carrier (same kit path AND same source basename): a shared carrier
    #: must reach the kit in exactly one version. The source-basename half
    #: of the identity keeps unrelated artifacts that pinned the same
    #: neutral kit_filename in different sections from shadowing each other.
    client_substitute: bool = False
    #: Basename of the artifact source file this kit file was delivered
    #: from. Client-overlay forks live at the same corpus-relative path as
    #: the base file they replace, so the basename is a stable carrier
    #: identity across the base and client arms; kit assembly uses it for
    #: shared-carrier shadowing and pinned-name de-collision ordering.
    source_name: Optional[str] = None


def schema_fact_ids(schema: dict[str, Any]) -> set[str]:
    """Ids of the well-formed facts a section schema declares.

    Malformed entries (non-objects, or objects without an ``id``) are
    skipped here — variant compilation reports them as errors; the
    transformation layer must simply not crash on them.
    """
    return {
        str(fact["id"])
        for fact in schema.get("facts") or []
        if isinstance(fact, dict) and "id" in fact
    }


class SectionTransformation(ABC):
    """Adapter between one artifact representation and the kit builder."""

    #: Canonical representation name used in schema ``transformations`` entries.
    representation: str
    #: Alternate names accepted in manifests (e.g. ``example_transcripts``).
    aliases: tuple[str, ...] = ()
    #: ``pooled`` artifacts are flattened/anonymized across sections;
    #: ``named`` artifacts are neutralized independently before final naming.
    placement: Literal["pooled", "named"]
    #: Kit-root directory the artifacts are written under. All delivered
    #: materials share one flat folder so the kit reads like a customer's
    #: file drop, not a taxonomy of artifact types.
    kit_dirname: str = "uploaded_materials"
    #: Whether artifacts contain customer-facing agent utterances. Gates
    #: response-phrasing generation context and compliance validation.
    carries_agent_utterances: bool
    #: Whether this transformation writes kit files. Non-materializing
    #: representations claim fact coverage through another channel — SOP
    #: prose (``explicit_rules``) or the Client simulator
    #: (``client_knowledge``) — so the kit builder must not try to
    #: neutralize their artifacts.
    materializes: bool = True

    @abstractmethod
    def discover_artifacts(
        self,
        schema: dict[str, Any],
        schema_path: Path,
        spec: dict[str, Any],
    ) -> list[TransformationArtifact]:
        """Resolve artifacts from the section fact schema.

        ``spec`` is the schema's ``transformations`` entry that activated
        this transformation (representation, stub_path, artifacts, ...).
        """

    @abstractmethod
    def neutralize(self, artifact: TransformationArtifact, ordinal: int) -> KitFile:
        """Prepare one artifact for the kit.

        ``ordinal`` is a 1-based counter over all pooled artifacts of this
        transformation in the kit; ``named`` transformations may ignore it.
        """

    @abstractmethod
    def to_text(self, artifact: TransformationArtifact) -> str:
        """Render the artifact as plain text for NL fact-coverage judging."""

    def kit_text(self, artifact: TransformationArtifact) -> Optional[str]:
        """Shippable text rendition for text-only kit materialization.

        Unlike :meth:`to_text` — an author-side rendering that may carry
        annotations the Developer must never see (fixture labels, timeline
        notes) — this must be safe to write into the kit verbatim. The
        default honors an explicit per-artifact ``kit_text_path`` metadata
        declaration; representations whose ``to_text`` is already a clean
        in-world rendering (visible-text parses of authored HTML, plain-text
        exports) override this to derive it automatically.

        Returning ``None`` means the artifact has no shippable text
        rendition; materializing it under a profile that excludes its
        native modality is then a hard error.
        """
        kit_text_path = artifact.metadata.get("kit_text_path")
        if not kit_text_path:
            return None
        return Path(kit_text_path).read_text().rstrip() + "\n"

    def deliver(
        self,
        artifact: TransformationArtifact,
        ordinal: int,
        profile: ModalityProfile,
    ) -> KitFile:
        """Materialize one artifact for the kit under a modality profile.

        The default selects between the native neutralized rendition and a
        text substitute: when the neutralized file's modality (per-artifact
        ``modality`` metadata override, else delivered-suffix
        classification) falls outside the profile, the artifact ships as
        its :meth:`kit_text` rendition with a ``.txt`` suffix instead —
        same placement, same generic-name pooling. Representations with
        richer renditions to offer (audio upgrades of text-native records)
        override this.
        """
        kit_file = self.neutralize(artifact, ordinal)
        modality = str(
            artifact.metadata.get("modality")
            or modality_for_path(kit_file.relative_path)
        )
        if profile.allows(modality):
            return kit_file
        text = self.kit_text(artifact)
        if text is None or not text.strip():
            raise ValueError(
                f"{artifact.source_path.name} ({self.representation}) delivers "
                f"{modality} content but has no shippable text rendition; "
                f"cannot materialize under modality profile {profile}. "
                "Declare kit_text_path on the artifact or use a profile "
                f"that allows {modality}."
            )
        return KitFile(
            relative_path=str(Path(kit_file.relative_path).with_suffix(".txt")),
            content=text.encode(),
            preserve_filename=kit_file.preserve_filename,
            substituted_from=modality,
        )

    def validate(
        self, schema: dict[str, Any], artifacts: list[TransformationArtifact]
    ) -> list[str]:
        """Structural validation of the artifacts themselves.

        Returns a list of human-readable issues; empty means valid.
        Subclasses may extend this with format-specific checks.

        Fact *coverage* is deliberately not checked here: a variant may
        activate several transformations over one section, so whether
        every fact is represented is a property of the compiled variant
        (see :mod:`tau2.hyper.transformations.compile`), not of any
        single transformation.
        """
        issues: list[str] = []
        fact_ids = schema_fact_ids(schema)
        for artifact in artifacts:
            unknown = set(artifact.included_fact_ids) - fact_ids
            if unknown:
                issues.append(
                    f"{artifact.source_path.name} declares unknown fact ids: "
                    f"{sorted(unknown)}"
                )
        return issues

    def covered_fact_ids(
        self, schema: dict[str, Any], artifacts: list[TransformationArtifact]
    ) -> set[str]:
        """Fact ids this transformation's artifacts represent.

        Default: the union of the artifacts' ``included_fact_ids``.
        Representations whose coverage is not artifact-based (prose kept
        in the SOP, legacy transcript plans) override this.
        """
        return {
            fact_id for artifact in artifacts for fact_id in artifact.included_fact_ids
        }


_REGISTRY: dict[str, SectionTransformation] = {}


def register_transformation(
    transformation: SectionTransformation,
) -> SectionTransformation:
    """Register a transformation under its representation name and aliases."""
    for name in (transformation.representation, *transformation.aliases):
        existing = _REGISTRY.get(name)
        if existing is not None and existing is not transformation:
            raise ValueError(
                f"Representation {name!r} is already registered by "
                f"{type(existing).__name__}"
            )
        _REGISTRY[name] = transformation
    return transformation


def has_transformation(representation: str) -> bool:
    return representation in _REGISTRY


def get_transformation(representation: str) -> SectionTransformation:
    try:
        return _REGISTRY[representation]
    except KeyError:
        known = sorted({r.representation for r in _REGISTRY.values()})
        raise KeyError(
            f"Unknown section representation {representation!r}. "
            f"Registered representations: {known}"
        ) from None


def known_representations() -> list[str]:
    return sorted({r.representation for r in _REGISTRY.values()})


def resolve_transformation_imports(schema: dict[str, Any]) -> list[dict[str, Any]]:
    """Load external transformation packs declared by a section schema.

    Large evidence variants can contain hundreds of artifact declarations. Keeping
    those declarations in a sibling pack makes the atomic fact schema reviewable
    while preserving the same compile-time validation as inline transformations.
    """
    raw_imports = schema.get("transformation_imports") or []
    if not isinstance(raw_imports, list):
        raise ValueError("transformation_imports must be a list")

    imports: list[dict[str, Any]] = []
    for index, raw_import in enumerate(raw_imports):
        if not isinstance(raw_import, dict) or not isinstance(
            raw_import.get("path"), str
        ):
            raise ValueError(
                f"transformation_imports[{index}] must be an object with a path"
            )
        path = Path(raw_import["path"])
        resolved = path if path.is_absolute() else DATA_DIR / path
        try:
            payload = json.loads(resolved.read_text())
        except FileNotFoundError as error:
            raise ValueError(f"transformation import not found: {path}") from error
        except json.JSONDecodeError as error:
            raise ValueError(
                f"transformation import has invalid JSON: {path} ({error})"
            ) from error
        if not isinstance(payload, dict):
            raise ValueError(f"transformation import must be an object: {path}")
        imported_section = payload.get("section_id")
        if imported_section is not None and imported_section != schema.get(
            "section_id"
        ):
            raise ValueError(
                f"transformation import {path} targets section "
                f"{imported_section!r}, not {schema.get('section_id')!r}"
            )
        imports.append(payload)
    return imports


def resolve_section_transformations(schema: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the transformation specs declared by a section fact schema.

    New-style schemas declare an explicit ``transformations`` list, which is
    authoritative even when empty (``[]`` means the section deliberately
    declares none — e.g. retail_plus legacy sections whose canonical
    training records were never ported). Legacy transcript-induction schemas
    lacking the key entirely (``rendered_section_path`` + ``transcripts``)
    are adapted to an equivalent ``support_transcripts`` transformation so
    existing data needs no migration.
    """
    transformations = schema.get("transformations")
    imported = [
        transformation
        for payload in resolve_transformation_imports(schema)
        for transformation in payload.get("transformations") or []
    ]
    if not all(isinstance(item, dict) for item in imported):
        raise ValueError("imported transformations must be objects")
    if transformations is not None:
        if not isinstance(transformations, list):
            raise ValueError("transformations must be a list")
        return [*transformations, *imported]
    if (
        schema.get("rendered_section_path")
        or schema.get("case_records_dir")
        or schema.get("transcripts") is not None
    ):
        return [
            {
                "representation": "support_transcripts",
                "stub_path": schema.get("rendered_section_path"),
                "artifacts": None,
            },
            *imported,
        ]
    return imported


def select_section_transformation(
    schema: dict[str, Any], active_stub_path: Optional[str] = None
) -> dict[str, Any]:
    """Pick the transformation a variant manifest activated for this section.

    When a schema declares multiple transformations, the manifest's replacement
    (or appended) stub path identifies which one is in play. Falls back to
    the first declared transformation.
    """
    transformations = resolve_section_transformations(schema)
    if not transformations:
        raise ValueError(
            f"Section schema {schema.get('id', '<unknown>')!r} declares no "
            "transformations and has no legacy transcript fields"
        )
    if active_stub_path:
        for transformation in transformations:
            if transformation.get("stub_path") == str(active_stub_path):
                return transformation
    return transformations[0]
