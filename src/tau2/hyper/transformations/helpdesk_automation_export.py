"""Helpdesk automation exports used as machine-configuration policy evidence."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from tau2.hyper.transformations.base import (
    KitFile,
    SectionTransformation,
    TransformationArtifact,
    register_transformation,
)
from tau2.utils.utils import DATA_DIR

_FORMAT = "helpdesk_automation_export_v2"
_JSON_COLLECTIONS = (
    ("macros.json", "macros"),
    ("triggers.json", "triggers"),
    ("policy_contracts.json", "policy_contracts"),
    ("sla_policies.json", "sla_policies"),
    ("views.json", "views"),
)
_REQUIRED_KEYS = {
    "snapshot",
    "cover_email",
    "macros",
    "triggers",
    "policy_contracts",
    "fields",
    "sla_policies",
    "views",
}
_BANNED_COVER_LANGUAGE = {
    "current authority comes from",
    "usage is context only",
    "distinguish workflow authority",
    "authoritative fact",
    "evaluator",
}


def _zip_timestamp(spec: dict[str, Any]) -> tuple[int, int, int, int, int, int]:
    """Use the authored snapshot time for deterministic, credible ZIP metadata."""
    exported_at = str(spec["snapshot"]["exported_at"]).replace("Z", "+00:00")
    timestamp = datetime.fromisoformat(exported_at)
    # ZIP stores seconds at two-second resolution.
    return (
        timestamp.year,
        timestamp.month,
        timestamp.day,
        timestamp.hour,
        timestamp.minute,
        timestamp.second - timestamp.second % 2,
    )


def helpdesk_export_files(spec: dict[str, Any]) -> list[tuple[str, bytes]]:
    """Render the files delivered inside a helpdesk export ZIP.

    Every export carries the seven core members; a spec may additionally
    carry a ``tickets`` collection (the rolling ticket sample some vendor
    accounts include with full-account exports), rendered as a trailing
    ``tickets.json`` member.
    """
    files: list[tuple[str, bytes]] = [
        ("cover_email.eml", str(spec["cover_email"]).encode())
    ]
    snapshot = spec["snapshot"]
    for filename, key in _JSON_COLLECTIONS[:3]:
        payload = {
            "export_format": _FORMAT,
            "snapshot": snapshot,
            key: spec[key],
        }
        files.append(
            (
                filename,
                (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode(),
            )
        )

    field_rows = spec["fields"]
    columns = list(spec.get("field_columns") or [])
    if not columns and field_rows:
        columns = list(field_rows[0])
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(field_rows)
    files.append(("fields.csv", output.getvalue().encode()))

    for filename, key in _JSON_COLLECTIONS[3:]:
        payload = {
            "export_format": _FORMAT,
            "snapshot": snapshot,
            key: spec[key],
        }
        files.append(
            (
                filename,
                (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode(),
            )
        )
    if spec.get("tickets"):
        payload = {
            "export_format": _FORMAT,
            "snapshot": snapshot,
            "tickets": spec["tickets"],
        }
        files.append(
            (
                "tickets.json",
                (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode(),
            )
        )
    return files


def build_helpdesk_export_zip(spec: dict[str, Any]) -> bytes:
    """Build deterministic ZIP bytes from an authored export specification."""
    output = io.BytesIO()
    timestamp = _zip_timestamp(spec)
    with zipfile.ZipFile(
        output,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for filename, content in helpdesk_export_files(spec):
            info = zipfile.ZipInfo(filename, date_time=timestamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, content)
    return output.getvalue()


class HelpdeskAutomationExportTransformation(SectionTransformation):
    """Deliver a production-like helpdesk administrator export ZIP."""

    representation = "helpdesk_automation_export"
    aliases = ("helpdesk_export", "ticketing_automation_export")
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
                "helpdesk_automation_export transformation for section schema "
                f"{schema.get('id', '<unknown>')!r} must declare artifacts"
            )

        shared = {
            key: self._resolve(spec[key])
            for key in (
                "eval_manifest_path",
                "fact_map_path",
                "object_adjudication_path",
            )
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
            content=build_helpdesk_export_zip(spec),
        )

    def to_text(self, artifact: TransformationArtifact) -> str:
        spec = json.loads(artifact.source_path.read_text())
        blocks = []
        for filename, content in helpdesk_export_files(spec):
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
                issues.append(f"{name}: authored export specification must be JSON")
                continue
            if not artifact.source_path.is_file():
                issues.append(f"{name}: authored export specification not found")
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
                spec = json.loads(artifact.source_path.read_text())
            except json.JSONDecodeError as error:
                issues.append(f"{name}: invalid authored export JSON ({error})")
                continue
            issues.extend(self._validate_spec(name, spec))
            try:
                archive_bytes = build_helpdesk_export_zip(spec)
                with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
                    expected = [filename for filename, _ in helpdesk_export_files(spec)]
                    if archive.namelist() != expected:
                        issues.append(f"{name}: ZIP member order or names drifted")
            except (KeyError, TypeError, ValueError) as error:
                issues.append(f"{name}: cannot build helpdesk export ZIP ({error})")

            manifest_path = artifact.metadata.get("eval_manifest_path")
            if manifest_path:
                issues.extend(
                    self._validate_eval_manifest(
                        Path(manifest_path), artifact, self._object_ids(spec)
                    )
                )
            fact_map_path = artifact.metadata.get("fact_map_path")
            if fact_map_path:
                issues.extend(
                    self._validate_fact_map(Path(fact_map_path), artifact, spec)
                )
            adjudication_path = artifact.metadata.get("object_adjudication_path")
            if adjudication_path:
                issues.extend(
                    self._validate_adjudication(
                        Path(adjudication_path), self._object_ids(spec)
                    )
                )
        return issues

    @staticmethod
    def _validate_spec(name: str, spec: Any) -> list[str]:
        if not isinstance(spec, dict):
            return [f"{name}: authored export root must be an object"]
        issues = []
        if spec.get("format") != _FORMAT:
            issues.append(f"{name}: format must be {_FORMAT!r}")
        missing = sorted(_REQUIRED_KEYS - set(spec))
        if missing:
            issues.append(f"{name}: missing required keys {missing}")
            return issues
        snapshot = spec.get("snapshot")
        if not isinstance(snapshot, dict):
            issues.append(f"{name}: snapshot must be an object")
        elif snapshot.get("environment") != "production":
            issues.append(f"{name}: snapshot environment must be production")
        cover_email = str(spec.get("cover_email", ""))
        if not cover_email.startswith("From:"):
            issues.append(f"{name}: cover_email must be an RFC-style email export")
        lowered_cover = cover_email.lower()
        leaked = sorted(
            phrase for phrase in _BANNED_COVER_LANGUAGE if phrase in lowered_cover
        )
        if leaked:
            issues.append(
                f"{name}: cover_email contains evaluator-facing language {leaked}"
            )

        collections = {
            "macros": "macro_id",
            "triggers": "trigger_id",
            "policy_contracts": "contract_id",
            "fields": "row_id",
            "sla_policies": "policy_id",
            "views": "view_id",
        }
        if "tickets" in spec:
            collections["tickets"] = "ticket_id"
        for key, id_key in collections.items():
            values = spec.get(key)
            if not isinstance(values, list) or not values:
                issues.append(f"{name}: {key} must be a non-empty list")
                continue
            ids = [
                str(value.get(id_key, ""))
                for value in values
                if isinstance(value, dict)
            ]
            if len(ids) != len(values) or any(not object_id for object_id in ids):
                issues.append(f"{name}: every {key} entry needs {id_key}")
            elif len(ids) != len(set(ids)):
                issues.append(f"{name}: duplicate {id_key} values in {key}")

        columns = spec.get("field_columns")
        if not isinstance(columns, list) or not columns:
            issues.append(f"{name}: field_columns must be a non-empty list")
        else:
            expected = set(columns)
            for row in spec.get("fields") or []:
                if isinstance(row, dict) and set(row) != expected:
                    issues.append(
                        f"{name}: fields row {row.get('row_id')!r} columns drifted"
                    )

        field_keys = {
            str(row.get("field_key"))
            for row in spec.get("fields") or []
            if isinstance(row, dict) and row.get("field_key")
        }
        referenced_fields = set()

        def collect_field_references(value: Any) -> None:
            if isinstance(value, dict):
                field = value.get("field")
                if field:
                    referenced_fields.add(str(field))
                for nested in value.values():
                    collect_field_references(nested)
            elif isinstance(value, list):
                for nested in value:
                    collect_field_references(nested)

        for trigger in spec.get("triggers") or []:
            if not HelpdeskAutomationExportTransformation._is_current(trigger):
                continue
            collect_field_references(trigger.get("conditions"))
            collect_field_references(trigger.get("actions"))
        for view in spec.get("views") or []:
            if not HelpdeskAutomationExportTransformation._is_current(view):
                continue
            collect_field_references(view.get("filters"))
        unknown_fields = sorted(referenced_fields - field_keys)
        if unknown_fields:
            issues.append(
                f"{name}: current automation references unknown fields {unknown_fields}"
            )
        return issues

    @staticmethod
    def _is_current(value: Any) -> bool:
        return (
            isinstance(value, dict)
            and value.get("active") is True
            and value.get("environment") == "production"
            and value.get("status", "published") == "published"
            and not value.get("superseded_by")
        )

    @staticmethod
    def _object_ids(spec: dict[str, Any]) -> set[str]:
        ids = set()
        for key, id_key in (
            ("macros", "macro_id"),
            ("triggers", "trigger_id"),
            ("policy_contracts", "contract_id"),
            ("fields", "row_id"),
            ("sla_policies", "policy_id"),
            ("views", "view_id"),
            ("tickets", "ticket_id"),
        ):
            ids.update(
                str(value[id_key])
                for value in spec.get(key) or []
                if isinstance(value, dict) and value.get(id_key)
            )
        return ids

    @staticmethod
    def _validate_eval_manifest(
        path: Path,
        artifact: TransformationArtifact,
        object_ids: set[str],
    ) -> list[str]:
        if not path.is_file():
            return ["helpdesk export eval_manifest_path not found"]
        try:
            manifest = json.loads(path.read_text())
        except json.JSONDecodeError as error:
            return [f"helpdesk export eval manifest is invalid JSON ({error})"]
        issues = []
        if manifest.get("filename") != artifact.metadata.get("kit_filename"):
            issues.append("helpdesk export eval manifest filename does not match")
        declared = set(manifest.get("authoritative_fact_ids") or [])
        if declared != set(artifact.included_fact_ids):
            issues.append(
                "helpdesk export eval manifest authoritative facts must exactly "
                "match included_fact_ids"
            )
        evidence = manifest.get("fact_evidence") or []
        evidence_ids = {
            str(entry.get("fact_id"))
            for entry in evidence
            if isinstance(entry, dict) and entry.get("fact_id")
        }
        if evidence_ids != declared:
            issues.append(
                "helpdesk export fact_evidence must cover every authoritative fact"
            )
        referenced = {
            str(object_id)
            for entry in evidence
            if isinstance(entry, dict)
            for object_id in entry.get("object_ids") or []
        }
        unknown = sorted(referenced - object_ids)
        if unknown:
            issues.append(
                f"helpdesk export evidence references unknown objects {unknown}"
            )
        return issues

    @staticmethod
    def _validate_fact_map(
        path: Path,
        artifact: TransformationArtifact,
        spec: dict[str, Any],
    ) -> list[str]:
        if not path.is_file():
            return ["helpdesk export fact_map_path not found"]
        try:
            fact_map = json.loads(path.read_text())
        except json.JSONDecodeError as error:
            return [f"helpdesk export fact map is invalid JSON ({error})"]
        facts = fact_map.get("facts") if isinstance(fact_map, dict) else None
        if not isinstance(facts, dict):
            return ["helpdesk export fact map must contain a facts object"]
        issues = []
        if set(facts) != set(artifact.included_fact_ids):
            issues.append(
                "helpdesk export fact map must exactly match included_fact_ids"
            )
        object_ids = HelpdeskAutomationExportTransformation._object_ids(spec)
        referenced = {
            str(object_id)
            for entry in facts.values()
            if isinstance(entry, dict)
            for object_id in entry.get("object_ids") or []
        }
        unknown = sorted(referenced - object_ids)
        if unknown:
            issues.append(
                f"helpdesk export fact map references unknown objects {unknown}"
            )
        contract_index = {
            str(contract.get("contract_id")): contract
            for contract in spec.get("policy_contracts") or []
            if isinstance(contract, dict) and contract.get("contract_id")
        }
        valid_claim_types = {
            "positive_capability",
            "authoritative_definition",
            "conditional_schema_rule",
            "deterministic_machine_rule",
            "closed_world_policy",
        }
        for fact_id, entry in facts.items():
            if not isinstance(entry, dict):
                issues.append(f"helpdesk export fact {fact_id!r} must be an object")
                continue
            claim_type = entry.get("claim_type")
            if claim_type not in valid_claim_types:
                issues.append(
                    f"helpdesk export fact {fact_id!r} has invalid claim_type"
                )
            closure_ids = entry.get("closure_object_ids") or []
            if claim_type != "closed_world_policy" and closure_ids:
                issues.append(
                    f"helpdesk export fact {fact_id!r} has unnecessary closure evidence"
                )
            if claim_type != "closed_world_policy":
                continue
            if not closure_ids:
                issues.append(
                    f"helpdesk export closed-world fact {fact_id!r} needs "
                    "closure_object_ids"
                )
                continue
            for contract_id in closure_ids:
                contract = contract_index.get(str(contract_id))
                closed_world = (
                    contract.get("closed_world", {})
                    if isinstance(contract, dict)
                    else {}
                )
                if not (
                    isinstance(contract, dict)
                    and contract.get("active") is True
                    and contract.get("environment") == "production"
                    and contract.get("status") == "published"
                    and not contract.get("superseded_by")
                    and closed_world.get("complete") is True
                    and closed_world.get("unlisted_behavior")
                    in {"deny", "reject", "reject_transaction"}
                ):
                    issues.append(
                        f"helpdesk export closed-world fact {fact_id!r} references "
                        f"non-enforcing contract {contract_id!r}"
                    )
        return issues

    @staticmethod
    def _validate_adjudication(path: Path, object_ids: set[str]) -> list[str]:
        if not path.is_file():
            return ["helpdesk export object_adjudication_path not found"]
        with path.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        adjudicated = {str(row.get("object_id") or "") for row in rows}
        if adjudicated != object_ids:
            return [
                "helpdesk export object adjudication must classify every export object"
            ]
        return []

    @staticmethod
    def _resolve(path: str | Path) -> Path:
        resolved = Path(path)
        if resolved.is_absolute():
            return resolved
        return DATA_DIR / resolved


register_transformation(HelpdeskAutomationExportTransformation())
