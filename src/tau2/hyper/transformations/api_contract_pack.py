"""API contract packs used as authoritative record-schema evidence."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from tau2.hyper.transformations.base import (
    KitFile,
    SectionTransformation,
    TransformationArtifact,
    register_transformation,
)
from tau2.utils.utils import DATA_DIR

_FORMAT = "api_contract_pack_v1"
# Fallback only: used when a spec's release block carries no in-world date.
# Member timestamps normally come from the pack's own release record (see
# _zip_timestamp) so the delivered archive never carries a build-era or
# obviously synthetic constant.
_FIXED_ZIP_TIMESTAMP = (2026, 1, 1, 0, 0, 0)
_REQUIRED_KEYS = {
    "format",
    "release",
    "cover_email",
    "openapi",
    "postman_collection",
    "error_behavior_columns",
    "error_behavior",
    "record_contract_notes",
}


def api_contract_files(spec: dict[str, Any]) -> list[tuple[str, bytes]]:
    """Render the five files delivered inside an API contract pack."""
    openapi = yaml.safe_dump(
        spec["openapi"],
        sort_keys=False,
        allow_unicode=True,
        width=100,
    )
    postman = (
        json.dumps(spec["postman_collection"], indent=2, ensure_ascii=False) + "\n"
    )

    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=list(spec["error_behavior_columns"]),
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(spec["error_behavior"])

    return [
        ("cover_email.eml", str(spec["cover_email"]).encode()),
        ("openapi.yaml", openapi.encode()),
        ("postman_collection.json", postman.encode()),
        ("error_behavior.csv", output.getvalue().encode()),
        ("record_contract_notes.md", str(spec["record_contract_notes"]).encode()),
    ]


def _zip_timestamp(spec: dict[str, Any]) -> tuple[int, int, int, int, int, int]:
    """Member timestamp for the delivered archive, derived from the spec.

    The pack is fiction-side evidence, so its zip members carry the
    release record's own in-world date — ``release.snapshot_at`` (full
    RFC3339 stamp) when present, else ``release.published_on`` (bare
    date), else the legacy fixed constant. Deterministic either way.
    """
    release = spec.get("release")
    if isinstance(release, dict):
        snapshot = release.get("snapshot_at")
        if isinstance(snapshot, str) and snapshot:
            try:
                moment = datetime.fromisoformat(snapshot)
            except ValueError:
                moment = None
            if moment is not None:
                return (
                    moment.year,
                    moment.month,
                    moment.day,
                    moment.hour,
                    moment.minute,
                    moment.second,
                )
        published = release.get("published_on")
        if isinstance(published, str) and published:
            try:
                moment = datetime.fromisoformat(published)
            except ValueError:
                moment = None
            if moment is not None:
                return (moment.year, moment.month, moment.day, 0, 0, 0)
    return _FIXED_ZIP_TIMESTAMP


def build_api_contract_zip(spec: dict[str, Any]) -> bytes:
    """Build deterministic ZIP bytes from an authored contract specification."""
    timestamp = _zip_timestamp(spec)
    output = io.BytesIO()
    with zipfile.ZipFile(
        output,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for filename, content in api_contract_files(spec):
            info = zipfile.ZipInfo(filename, date_time=timestamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, content)
    return output.getvalue()


class APIContractPackTransformation(SectionTransformation):
    """Deliver a production API/data-contract handoff as one ZIP."""

    representation = "api_contract_pack"
    aliases = ("api_contract", "openapi_contract_pack")
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
                "api_contract_pack transformation for section schema "
                f"{schema.get('id', '<unknown>')!r} must declare artifacts"
            )

        shared = {
            key: self._resolve(spec[key])
            for key in ("eval_manifest_path", "fact_map_path")
            if spec.get(key)
        }
        artifacts = []
        for entry in declared:
            metadata = shared | {
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
        spec = json.loads(artifact.source_path.read_text())
        return KitFile(
            relative_path=(
                f"{self.kit_dirname}/{str(artifact.metadata['kit_filename'])}"
            ),
            content=build_api_contract_zip(spec),
        )

    def to_text(self, artifact: TransformationArtifact) -> str:
        spec = json.loads(artifact.source_path.read_text())
        blocks = []
        for filename, content in api_contract_files(spec):
            blocks.append(f"## {filename}\n\n{content.decode().rstrip()}")
        return "\n\n".join(blocks) + "\n"

    def validate(
        self, schema: dict[str, Any], artifacts: list[TransformationArtifact]
    ) -> list[str]:
        issues = super().validate(schema, artifacts)
        seen_filenames: set[str] = set()
        for artifact in artifacts:
            name = artifact.source_path.name
            if artifact.source_path.suffix.lower() != ".json":
                issues.append(f"{name}: authored contract specification must be JSON")
                continue
            if not artifact.source_path.is_file():
                issues.append(f"{name}: authored contract specification not found")
                continue

            kit_filename = str(artifact.metadata.get("kit_filename") or "")
            if not kit_filename:
                issues.append(f"{name}: kit_filename is required")
            elif Path(kit_filename).name != kit_filename:
                issues.append(f"{name}: kit_filename must be a bare filename")
            elif not kit_filename.endswith(".zip"):
                issues.append(f"{name}: kit_filename must end in .zip")
            elif kit_filename in seen_filenames:
                issues.append(f"{name}: duplicate kit_filename {kit_filename!r}")
            seen_filenames.add(kit_filename)

            try:
                authored = json.loads(artifact.source_path.read_text())
            except json.JSONDecodeError as error:
                issues.append(f"{name}: invalid authored contract JSON ({error})")
                continue
            issues.extend(self._validate_spec(name, authored))

            manifest_path = artifact.metadata.get("eval_manifest_path")
            if manifest_path:
                issues.extend(
                    self._validate_eval_manifest(Path(manifest_path), artifact)
                )
            fact_map_path = artifact.metadata.get("fact_map_path")
            if fact_map_path:
                issues.extend(self._validate_fact_map(Path(fact_map_path), artifact))

            try:
                archive_bytes = build_api_contract_zip(authored)
                with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
                    expected = [
                        filename for filename, _ in api_contract_files(authored)
                    ]
                    if archive.namelist() != expected:
                        issues.append(f"{name}: ZIP member order or names drifted")
            except (KeyError, TypeError, ValueError, yaml.YAMLError) as error:
                issues.append(f"{name}: cannot build API contract ZIP ({error})")
        return issues

    @staticmethod
    def _validate_spec(name: str, spec: Any) -> list[str]:
        if not isinstance(spec, dict):
            return [f"{name}: authored contract root must be an object"]
        issues = []
        if spec.get("format") != _FORMAT:
            issues.append(f"{name}: format must be {_FORMAT!r}")
        missing = sorted(_REQUIRED_KEYS - set(spec))
        if missing:
            issues.append(f"{name}: missing required keys {missing}")
            return issues

        release = spec.get("release")
        if not isinstance(release, dict):
            issues.append(f"{name}: release must be an object")
        elif not (
            release.get("environment") == "production"
            and release.get("status") == "published"
            and release.get("current") is True
            and release.get("superseded_by") is None
        ):
            issues.append(
                f"{name}: release must identify a current production contract"
            )

        openapi = spec.get("openapi")
        if not isinstance(openapi, dict) or openapi.get("openapi") != "3.1.0":
            issues.append(f"{name}: openapi must be an OpenAPI 3.1 document")
        if not str(spec.get("cover_email", "")).startswith("From:"):
            issues.append(f"{name}: cover_email must be an RFC-style email export")

        columns = spec.get("error_behavior_columns")
        rows = spec.get("error_behavior")
        if not isinstance(columns, list) or not columns:
            issues.append(f"{name}: error_behavior_columns must be non-empty")
        elif not isinstance(rows, list) or not rows:
            issues.append(f"{name}: error_behavior must be non-empty")
        else:
            expected = set(columns)
            for row in rows:
                if not isinstance(row, dict) or set(row) != expected:
                    issues.append(f"{name}: error_behavior row columns drifted")
                    break
        return issues

    @staticmethod
    def _validate_eval_manifest(
        path: Path, artifact: TransformationArtifact
    ) -> list[str]:
        if not path.is_file():
            return ["API contract eval_manifest_path not found"]
        try:
            manifest = json.loads(path.read_text())
        except json.JSONDecodeError as error:
            return [f"API contract eval manifest is invalid JSON ({error})"]
        issues = []
        if manifest.get("filename") != artifact.metadata.get("kit_filename"):
            issues.append("API contract eval manifest filename does not match")
        declared = set(manifest.get("authoritative_fact_ids") or [])
        if declared != set(artifact.included_fact_ids):
            issues.append(
                "API contract eval manifest authoritative facts must exactly "
                "match included_fact_ids"
            )
        evidence_ids = {
            str(entry.get("fact_id"))
            for entry in manifest.get("fact_evidence") or []
            if isinstance(entry, dict) and entry.get("fact_id")
        }
        if evidence_ids != declared:
            issues.append(
                "API contract fact_evidence must cover every authoritative fact"
            )
        return issues

    @staticmethod
    def _validate_fact_map(path: Path, artifact: TransformationArtifact) -> list[str]:
        if not path.is_file():
            return ["API contract fact_map_path not found"]
        try:
            fact_map = json.loads(path.read_text())
        except json.JSONDecodeError as error:
            return [f"API contract fact map is invalid JSON ({error})"]
        facts = fact_map.get("facts") if isinstance(fact_map, dict) else None
        if not isinstance(facts, dict):
            return ["API contract fact map must contain a facts object"]
        if set(facts) != set(artifact.included_fact_ids):
            return ["API contract fact map must exactly match included_fact_ids"]
        issues = []
        for fact_id, evidence in facts.items():
            if not isinstance(evidence, dict):
                issues.append(f"API contract fact {fact_id!r} must be an object")
                continue
            if evidence.get("claim_type") not in {
                "published_schema_rule",
                "published_storage_rule",
            }:
                issues.append(f"API contract fact {fact_id!r} has invalid claim_type")
            if not evidence.get("authority_source_ids"):
                issues.append(
                    f"API contract fact {fact_id!r} needs authority_source_ids"
                )
        return issues

    @staticmethod
    def _resolve(path: str | Path) -> Path:
        resolved = Path(path)
        if resolved.is_absolute():
            return resolved
        return DATA_DIR / resolved


register_transformation(APIContractPackTransformation())
