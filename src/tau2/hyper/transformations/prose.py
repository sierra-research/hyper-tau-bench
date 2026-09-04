"""
Explicit-rules transformation: the identity representation.

A section rendered as ``explicit_rules`` keeps its facts as prose inside
the assembled SOP document itself (kit-root ``sop.md``, or the pooled
customer handbook when the variant demotes SOP delivery into
``uploaded_materials/``) — no auxiliary kit artifacts exist. It is
registered so variant manifests can name every representation, including
the untransformed one, and so validation treats "left as prose" as a
deliberate information-distribution choice rather than a gap.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tau2.hyper.transformations.base import (
    KitFile,
    SectionTransformation,
    TransformationArtifact,
    register_transformation,
    schema_fact_ids,
)


class ExplicitRulesTransformation(SectionTransformation):
    representation = "explicit_rules"
    aliases = ("sop_prose",)
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
        return []

    def neutralize(self, artifact: TransformationArtifact, ordinal: int) -> KitFile:
        raise NotImplementedError(
            "explicit_rules sections have no kit artifacts to neutralize"
        )

    def to_text(self, artifact: TransformationArtifact) -> str:
        raise NotImplementedError(
            "explicit_rules sections have no artifacts; the SOP section text "
            "is the transformation"
        )

    def validate(
        self, schema: dict[str, Any], artifacts: list[TransformationArtifact]
    ) -> list[str]:
        # Facts remain in the SOP prose; there are no artifacts to check.
        return []

    def covered_fact_ids(
        self, schema: dict[str, Any], artifacts: list[TransformationArtifact]
    ) -> set[str]:
        # The retained SOP prose carries every fact in the section.
        return schema_fact_ids(schema)


register_transformation(ExplicitRulesTransformation())
