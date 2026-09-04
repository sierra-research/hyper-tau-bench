"""Device-UI screenshot transformation for visually encoded support facts.

The Developer receives only raster reference images. Editable HTML or an
explicit text description stays author-side so coverage judging remains
deterministic without exposing fact labels in the construction kit.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any

from tau2.hyper.transformations.base import (
    KitFile,
    TransformationArtifact,
    register_transformation,
)
from tau2.hyper.transformations.website_screenshot import (
    WebsiteScreenshotTransformation,
)

_PLATFORMS = {"android", "cross_platform", "ios", "other"}
_NEUTRAL_KIT_FILENAME = re.compile(
    r"^device_(?:capture|screen)_\d{2,3}\.(?:jpeg|jpg|png|webp)$"
)


class DeviceUIScreenshotTransformation(WebsiteScreenshotTransformation):
    """Represent support facts in annotated phone or tablet UI screenshots."""

    representation = "device_ui_screenshot"
    aliases = ("device_screenshot", "phone_screenshot")
    placement = "pooled"
    carries_agent_utterances = False

    def neutralize(self, artifact: TransformationArtifact, ordinal: int) -> KitFile:
        suffix = artifact.source_path.suffix.lower()
        kit_filename = artifact.metadata.get("kit_filename")
        if kit_filename:
            filename = str(kit_filename)
        else:
            filename = f"device_screen_{ordinal:03d}{suffix}"
        return KitFile(
            relative_path=f"{self.kit_dirname}/{filename}",
            content=artifact.source_path.read_bytes(),
            preserve_filename=bool(kit_filename),
        )

    def validate(
        self, schema: dict[str, Any], artifacts: list[TransformationArtifact]
    ) -> list[str]:
        issues = super().validate(schema, artifacts)
        seen_reference_ids: set[str] = set()
        seen_kit_filenames: set[str] = set()
        for artifact in artifacts:
            name = artifact.source_path.name
            platform = str(artifact.metadata.get("platform") or "")
            if platform not in _PLATFORMS:
                issues.append(f"{name}: platform must be one of {sorted(_PLATFORMS)}")
            reference_id = str(artifact.metadata.get("reference_id") or "")
            if not reference_id:
                issues.append(f"{name}: reference_id is required")
            elif reference_id in seen_reference_ids:
                issues.append(f"{name}: duplicate reference_id {reference_id!r}")
            seen_reference_ids.add(reference_id)
            kit_filename = artifact.metadata.get("kit_filename")
            if kit_filename:
                candidate = PurePosixPath(str(kit_filename))
                if (
                    candidate.name != str(kit_filename)
                    or candidate.suffix.lower() != artifact.source_path.suffix.lower()
                ):
                    issues.append(
                        f"{name}: kit_filename must be a basename with the same suffix"
                    )
                elif not _NEUTRAL_KIT_FILENAME.fullmatch(str(kit_filename)):
                    issues.append(
                        f"{name}: kit_filename must use a neutral "
                        "device_capture_NN or device_screen_NN name"
                    )
                elif str(kit_filename) in seen_kit_filenames:
                    issues.append(f"{name}: duplicate kit_filename {kit_filename!r}")
                seen_kit_filenames.add(str(kit_filename))
        return issues


register_transformation(DeviceUIScreenshotTransformation())
