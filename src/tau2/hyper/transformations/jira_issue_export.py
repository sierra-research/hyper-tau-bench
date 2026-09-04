"""Jira issue exports used as versioned company-decision evidence."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from tau2.hyper.transformations.base import (
    KitFile,
    SectionTransformation,
    TransformationArtifact,
    register_transformation,
    schema_fact_ids,
)
from tau2.utils.utils import DATA_DIR

_FORMAT = "jira_cloud_issue_export_v1"
_ISSUE_KEY = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")
_ADJUDICATION_ROLES = {
    "authoritative_current",
    "supporting_current",
    "superseded",
    "rejected",
    "historical_context",
    "distractor_current",
    "distractor_closed",
}


def _timestamp(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.utcoffset() is not None else None


class JiraIssueExportTransformation(SectionTransformation):
    """Deliver a production-like Jira Cloud issue and changelog export."""

    representation = "jira_issue_export"
    aliases = ("jira_export", "work_item_tracker_export")
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
                "jira_issue_export transformation for section schema "
                f"{schema.get('id', '<unknown>')!r} must declare artifacts"
            )

        shared_manifest = spec.get("eval_manifest_path")
        artifacts = []
        for entry in declared:
            metadata = {
                key: value
                for key, value in entry.items()
                if key not in {"included_fact_ids", "path"}
            }
            manifest_path = metadata.get("eval_manifest_path") or shared_manifest
            if manifest_path:
                metadata["eval_manifest_path"] = self._resolve(manifest_path)
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
        return KitFile(
            relative_path=(
                f"{self.kit_dirname}/{str(artifact.metadata['kit_filename'])}"
            ),
            content=artifact.source_path.read_bytes(),
            artifact_kind=self.representation,
        )

    def to_text(self, artifact: TransformationArtifact) -> str:
        payload = json.loads(artifact.source_path.read_text())
        return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"

    def validate(
        self, schema: dict[str, Any], artifacts: list[TransformationArtifact]
    ) -> list[str]:
        issues = super().validate(schema, artifacts)
        seen_filenames: set[str] = set()
        for artifact in artifacts:
            name = artifact.source_path.name
            if artifact.source_path.suffix.lower() != ".json":
                issues.append(f"{name}: Jira issue export must end in .json")
                continue
            if not artifact.source_path.is_file():
                issues.append(f"{name}: Jira issue export file not found")
                continue

            kit_filename = str(artifact.metadata.get("kit_filename") or "")
            if not kit_filename:
                issues.append(f"{name}: kit_filename is required")
            elif Path(kit_filename).name != kit_filename:
                issues.append(f"{name}: kit_filename must be a bare filename")
            elif not kit_filename.endswith(".json"):
                issues.append(f"{name}: kit_filename must end in .json")
            elif kit_filename in seen_filenames:
                issues.append(f"{name}: duplicate kit_filename {kit_filename!r}")
            seen_filenames.add(kit_filename)

            try:
                payload = json.loads(artifact.source_path.read_text())
            except (OSError, json.JSONDecodeError) as error:
                issues.append(f"{name}: invalid Jira issue export JSON ({error})")
                continue
            issues.extend(self._validate_export(name, payload, schema))

            manifest_path = artifact.metadata.get("eval_manifest_path")
            if manifest_path:
                issues.extend(
                    self._validate_eval_manifest(
                        Path(manifest_path), artifact, payload, kit_filename
                    )
                )
        return issues

    @staticmethod
    def _validate_export(name: str, payload: Any, schema: dict[str, Any]) -> list[str]:
        if not isinstance(payload, dict):
            return [f"{name}: Jira issue export root must be an object"]
        issues = []
        if payload.get("export_format") != _FORMAT:
            issues.append(f"{name}: export_format must be {_FORMAT!r}")
        exported_at = _timestamp(payload.get("exported_at"))
        if exported_at is None:
            issues.append(f"{name}: exported_at must include a timezone offset")

        projects = payload.get("projects")
        project_keys = {
            str(project.get("key"))
            for project in projects or []
            if isinstance(project, dict) and project.get("key")
        }
        if not isinstance(projects, list) or not project_keys:
            issues.append(f"{name}: projects must be a non-empty list with keys")

        users = payload.get("users")
        user_ids = {
            str(user.get("accountId"))
            for user in users or []
            if isinstance(user, dict) and user.get("accountId")
        }
        if not isinstance(users, list) or len(user_ids) < 3:
            issues.append(f"{name}: users must contain at least three accountIds")

        exported_issues = payload.get("issues")
        if not isinstance(exported_issues, list) or len(exported_issues) < 4:
            return [*issues, f"{name}: issues must contain at least four entries"]

        issue_keys = [
            str(issue.get("key", ""))
            for issue in exported_issues
            if isinstance(issue, dict)
        ]
        if len(issue_keys) != len(exported_issues) or any(
            not _ISSUE_KEY.fullmatch(key) for key in issue_keys
        ):
            issues.append(f"{name}: every issue needs a Jira-style key")
        elif len(issue_keys) != len(set(issue_keys)):
            issues.append(f"{name}: issue keys must be unique")

        comment_ids: set[str] = set()
        history_ids: set[str] = set()
        comment_count = 0
        history_count = 0
        for issue in exported_issues:
            if not isinstance(issue, dict):
                issues.append(f"{name}: issue entries must be objects")
                continue
            key = str(issue.get("key", "<unknown>"))
            fields = issue.get("fields")
            if not isinstance(fields, dict):
                issues.append(f"{name}: {key} fields must be an object")
                continue
            for required in (
                "summary",
                "description",
                "issuetype",
                "status",
                "priority",
                "project",
                "created",
                "updated",
                "reporter",
                "comment",
                "issuelinks",
                "labels",
                "components",
                "fixVersions",
            ):
                if required not in fields:
                    issues.append(f"{name}: {key} missing fields.{required}")

            project = fields.get("project")
            project_key = (
                str(project.get("key", "")) if isinstance(project, dict) else ""
            )
            if project_key not in project_keys:
                issues.append(f"{name}: {key} references unknown project")
            for object_field in ("issuetype", "status", "priority"):
                value = fields.get(object_field)
                if not isinstance(value, dict) or not value.get("name"):
                    issues.append(f"{name}: {key} fields.{object_field} needs a name")
            for list_field in ("labels", "components", "fixVersions", "issuelinks"):
                if not isinstance(fields.get(list_field), list):
                    issues.append(f"{name}: {key} fields.{list_field} must be a list")
            for person_field in ("reporter", "assignee"):
                person = fields.get(person_field)
                if person is not None and (
                    not isinstance(person, dict)
                    or str(person.get("accountId", "")) not in user_ids
                ):
                    issues.append(
                        f"{name}: {key} {person_field} references unknown user"
                    )

            created = _timestamp(fields.get("created"))
            updated = _timestamp(fields.get("updated"))
            if created is None or updated is None:
                issues.append(f"{name}: {key} dates must include timezone offsets")
            elif created > updated or (exported_at and updated > exported_at):
                issues.append(f"{name}: {key} has impossible created/updated dates")

            comment_container = fields.get("comment")
            comments = (
                comment_container.get("comments")
                if isinstance(comment_container, dict)
                else None
            )
            if not isinstance(comments, list) or not comments:
                issues.append(f"{name}: {key} must contain comments")
                comments = []
            for comment in comments:
                if not isinstance(comment, dict):
                    issues.append(f"{name}: {key} comment entries must be objects")
                    continue
                comment_count += 1
                comment_id = str(comment.get("id", ""))
                if not comment_id or comment_id in comment_ids:
                    issues.append(f"{name}: Jira comment ids must be unique")
                comment_ids.add(comment_id)
                author = comment.get("author")
                author_id = (
                    str(author.get("accountId", "")) if isinstance(author, dict) else ""
                )
                if author_id not in user_ids:
                    issues.append(f"{name}: {key} comment references unknown author")
                if not str(comment.get("body", "")).strip():
                    issues.append(f"{name}: {key} comment body is required")
                comment_date = _timestamp(comment.get("created"))
                if comment_date is None:
                    issues.append(f"{name}: {key} comment date needs a timezone")
                elif exported_at and comment_date > exported_at:
                    issues.append(f"{name}: {key} comment postdates the export")

            changelog = issue.get("changelog")
            histories = (
                changelog.get("histories") if isinstance(changelog, dict) else None
            )
            if not isinstance(histories, list) or not histories:
                issues.append(f"{name}: {key} must contain changelog histories")
                histories = []
            for history in histories:
                if not isinstance(history, dict):
                    issues.append(f"{name}: {key} history entries must be objects")
                    continue
                history_count += 1
                history_id = str(history.get("id", ""))
                if not history_id or history_id in history_ids:
                    issues.append(f"{name}: Jira history ids must be unique")
                history_ids.add(history_id)
                author = history.get("author")
                author_id = (
                    str(author.get("accountId", "")) if isinstance(author, dict) else ""
                )
                if author_id not in user_ids:
                    issues.append(f"{name}: {key} history references unknown author")
                history_date = _timestamp(history.get("created"))
                if history_date is None:
                    issues.append(f"{name}: {key} history date needs a timezone")
                elif exported_at and history_date > exported_at:
                    issues.append(f"{name}: {key} history postdates the export")
                items = history.get("items")
                if not isinstance(items, list) or not items:
                    issues.append(f"{name}: {key} history must contain changed items")

            links = fields.get("issuelinks")
            for link in links if isinstance(links, list) else []:
                if not isinstance(link, dict):
                    issues.append(f"{name}: {key} issue links must be objects")
                    continue
                linked_key = str(link.get("issueKey", ""))
                if linked_key and linked_key not in issue_keys:
                    issues.append(f"{name}: {key} links unknown issue {linked_key!r}")

        if comment_count < 8:
            issues.append(f"{name}: Jira issue export must contain at least 8 comments")
        if history_count < 4:
            issues.append(
                f"{name}: Jira issue export must contain at least 4 history entries"
            )

        raw = json.dumps(payload, ensure_ascii=False)
        leaked = sorted(
            fact_id for fact_id in schema_fact_ids(schema) if fact_id in raw
        )
        if leaked:
            issues.append(f"{name}: author-only fact ids leaked into export: {leaked}")
        leaked_roles = sorted(
            role for role in _ADJUDICATION_ROLES if "_" in role and role in raw
        )
        if leaked_roles:
            issues.append(
                f"{name}: author-only adjudication roles leaked into export: "
                f"{leaked_roles}"
            )
        return issues

    @staticmethod
    def _validate_eval_manifest(
        manifest_path: Path,
        artifact: TransformationArtifact,
        payload: dict[str, Any],
        kit_filename: str,
    ) -> list[str]:
        if not manifest_path.is_file():
            return ["Jira eval_manifest_path not found"]
        try:
            manifest = json.loads(manifest_path.read_text())
        except json.JSONDecodeError as error:
            return [f"Jira eval manifest is invalid JSON ({error})"]
        if not isinstance(manifest, dict):
            return ["Jira eval manifest root must be an object"]
        if not isinstance(payload, dict):
            return ["Jira export root must be an object for manifest validation"]

        issues = []
        declared_artifact = manifest.get("artifact")
        if not isinstance(declared_artifact, dict):
            declared_artifact = {}
            issues.append("Jira eval manifest artifact must be an object")
        if declared_artifact.get("filename") != kit_filename:
            issues.append("Jira eval manifest filename does not match kit_filename")
        declared_facts = set(declared_artifact.get("authoritative_fact_ids") or [])
        if declared_facts != set(artifact.included_fact_ids):
            issues.append(
                "Jira eval manifest authoritative facts do not match artifact coverage"
            )

        exported_issues = payload.get("issues")
        exported_issues = exported_issues if isinstance(exported_issues, list) else []
        issues_by_key = {
            str(issue.get("key")): issue
            for issue in exported_issues
            if isinstance(issue, dict)
        }
        decisions = manifest.get("decisions")
        decision_entries = decisions if isinstance(decisions, list) else []
        decision_facts = [
            str(decision.get("fact_id"))
            for decision in decision_entries
            if isinstance(decision, dict)
        ]
        if not isinstance(decisions, list) or set(decision_facts) != declared_facts:
            issues.append("Jira decisions must cover every authoritative fact once")
        elif len(decision_facts) != len(set(decision_facts)):
            issues.append("Jira decisions contain duplicate fact ownership")
        for decision in decision_entries:
            if not isinstance(decision, dict):
                issues.append("Jira decision entries must be objects")
                continue
            issue_key = str(decision.get("issue_key", ""))
            issue = issues_by_key.get(issue_key)
            if issue is None:
                issues.append(f"Jira decision references unknown issue {issue_key!r}")
                continue
            if decision.get("status") != "final_current":
                issues.append(f"Jira decision for {issue_key} must be final_current")
            evidence = decision.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                issues.append(f"Jira decision for {issue_key} needs evidence")
                continue
            issue_text = json.dumps(issue, ensure_ascii=False)
            fields = issue.get("fields")
            fields = fields if isinstance(fields, dict) else {}
            comment_container = fields.get("comment")
            issue_comments = (
                comment_container.get("comments", [])
                if isinstance(comment_container, dict)
                else []
            )
            issue_comment_ids = {
                str(comment.get("id"))
                for comment in issue_comments
                if isinstance(comment, dict)
            }
            for span in evidence:
                if not isinstance(span, dict):
                    issues.append(f"Jira evidence for {issue_key} must be an object")
                    continue
                excerpt = str(span.get("excerpt", ""))
                if not excerpt or issue_text.count(excerpt) != 1:
                    issues.append(
                        f"Jira evidence for {issue_key} must have one unique excerpt"
                    )
                comment_id = span.get("comment_id")
                if comment_id and str(comment_id) not in issue_comment_ids:
                    issues.append(
                        f"Jira evidence for {issue_key} references unknown comment"
                    )

        adjudication = manifest.get("issue_adjudication")
        adjudication_entries = adjudication if isinstance(adjudication, list) else []
        adjudicated_keys = [
            str(entry.get("issue_key"))
            for entry in adjudication_entries
            if isinstance(entry, dict)
        ]
        if set(adjudicated_keys) != set(issues_by_key) or len(adjudicated_keys) != len(
            set(adjudicated_keys)
        ):
            issues.append("Jira issue adjudication must classify every issue once")
        for entry in adjudication_entries:
            if not isinstance(entry, dict):
                issues.append("Jira adjudication entries must be objects")
                continue
            if entry.get("role") not in _ADJUDICATION_ROLES:
                issues.append(
                    f"Jira issue {entry.get('issue_key')!r} has unknown adjudication role"
                )
        manifest_snapshot = _timestamp(manifest.get("snapshot"))
        if manifest_snapshot is None:
            issues.append("Jira eval manifest snapshot must include a timezone")
        elif manifest_snapshot != _timestamp(payload.get("exported_at")):
            issues.append("Jira eval manifest snapshot must match exported_at")
        return issues

    @staticmethod
    def _resolve(path: str | Path) -> Path:
        resolved = Path(path)
        if resolved.is_absolute():
            return resolved
        return DATA_DIR / resolved


register_transformation(JiraIssueExportTransformation())
