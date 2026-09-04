"""Operational case-ledger database extracts used as workload evidence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tau2.hyper.transformations.base import (
    KitFile,
    SectionTransformation,
    TransformationArtifact,
    register_transformation,
)
from tau2.utils.utils import DATA_DIR

_REQUIRED_TOP_LEVEL = {"export", "snapshot_at", "columns", "rows"}


def _parse_timestamp(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    # Offset-naive stamps are treated as UTC so ordering checks against an
    # offset-aware snapshot_at never raise on a mixed comparison.
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


class CaseLedgerExportTransformation(SectionTransformation):
    """Deliver a point-in-time case-database extract without author annotations."""

    representation = "case_ledger_export"
    aliases = ("case_ledger", "dispute_ledger_export")
    placement = "named"
    carries_agent_utterances = False

    def discover_artifacts(
        self,
        schema: dict[str, Any],
        schema_path: Path,
        spec: dict[str, Any],
    ) -> list[TransformationArtifact]:
        del schema_path
        declared = spec.get("artifacts")
        if not declared:
            raise ValueError(
                "case_ledger_export transformation for section schema "
                f"{schema.get('id', '<unknown>')!r} must declare artifacts"
            )
        artifacts = []
        for entry in declared:
            metadata = {
                key: value
                for key, value in entry.items()
                if key not in {"included_fact_ids", "path"}
            }
            artifacts.append(
                TransformationArtifact(
                    source_path=self._resolve(entry["path"]),
                    included_fact_ids=list(entry.get("included_fact_ids", [])),
                    metadata=metadata,
                )
            )
        return artifacts

    def neutralize(self, artifact: TransformationArtifact, ordinal: int) -> KitFile:
        del ordinal
        kit_filename = str(artifact.metadata["kit_filename"])
        return KitFile(
            relative_path=f"{self.kit_dirname}/{kit_filename}",
            content=artifact.source_path.read_bytes(),
        )

    def to_text(self, artifact: TransformationArtifact) -> str:
        payload = json.loads(artifact.source_path.read_text())
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def validate(
        self, schema: dict[str, Any], artifacts: list[TransformationArtifact]
    ) -> list[str]:
        issues = super().validate(schema, artifacts)
        seen_filenames: set[str] = set()
        for artifact in artifacts:
            name = artifact.source_path.name
            if artifact.source_path.suffix.lower() != ".json":
                issues.append(f"{name}: case ledger export must end in .json")
                continue
            if not artifact.source_path.is_file():
                issues.append(f"{name}: case ledger export file not found")
                continue

            kit_filename = str(artifact.metadata.get("kit_filename", ""))
            if not kit_filename:
                issues.append(f"{name}: kit_filename is required")
            elif Path(kit_filename).name != kit_filename:
                issues.append(f"{name}: kit_filename must be a bare filename")
            elif Path(kit_filename).suffix.lower() != ".json":
                issues.append(f"{name}: kit_filename must end in .json")
            elif kit_filename in seen_filenames:
                issues.append(f"{name}: duplicate kit_filename {kit_filename!r}")
            seen_filenames.add(kit_filename)

            try:
                payload = json.loads(artifact.source_path.read_text())
            except (OSError, json.JSONDecodeError) as error:
                issues.append(f"{name}: invalid case ledger JSON ({error})")
                continue
            issues.extend(self._validate_extract(name, payload))
        return issues

    @staticmethod
    def _validate_extract(name: str, payload: Any) -> list[str]:
        if not isinstance(payload, dict):
            return [f"{name}: extract root must be an object"]
        issues = []
        missing = sorted(_REQUIRED_TOP_LEVEL - set(payload))
        if missing:
            issues.append(f"{name}: missing required keys {missing}")
            return issues

        columns = payload["columns"]
        if not isinstance(columns, dict) or not columns:
            issues.append(f"{name}: columns must be a non-empty object")
            return issues
        column_keys = set(columns)

        rows = payload["rows"]
        if not isinstance(rows, list) or not rows:
            issues.append(f"{name}: rows must be a non-empty list")
            return issues
        declared_count = payload.get("row_count")
        if declared_count is not None and declared_count != len(rows):
            issues.append(
                f"{name}: row_count {declared_count} != {len(rows)} rows present"
            )

        snapshot_at = _parse_timestamp(payload["snapshot_at"])
        if snapshot_at is None:
            issues.append(f"{name}: snapshot_at is not an ISO timestamp")

        primary_key = payload.get("primary_key") or next(iter(columns))
        if primary_key not in columns:
            issues.append(
                f"{name}: primary_key {primary_key!r} is not a declared column"
            )
            return issues
        seen_keys: set[str] = set()
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                issues.append(f"{name}: row {index} must be an object")
                continue
            unknown = sorted(set(row) - column_keys)
            if unknown:
                issues.append(f"{name}: row {index} has undeclared columns {unknown}")
            key = str(row.get(primary_key, ""))
            if not key:
                issues.append(f"{name}: row {index} missing {primary_key}")
            elif key in seen_keys:
                issues.append(f"{name}: duplicate {primary_key} {key!r}")
            seen_keys.add(key)
            if snapshot_at is None:
                continue
            for field in ("filed_at", "resolved_at"):
                if row.get(field) is None:
                    continue
                stamp = _parse_timestamp(row[field])
                if stamp is None:
                    issues.append(
                        f"{name}: row {key or index} {field} is not an ISO timestamp"
                    )
                elif stamp > snapshot_at:
                    issues.append(
                        f"{name}: row {key or index} {field} is after snapshot_at"
                    )
        return issues

    @staticmethod
    def _resolve(path: str | Path) -> Path:
        resolved = Path(path)
        if resolved.is_absolute():
            return resolved
        return DATA_DIR / resolved


register_transformation(CaseLedgerExportTransformation())
