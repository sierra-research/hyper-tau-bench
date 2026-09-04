"""Exported email-thread archives used as business-policy evidence."""

from __future__ import annotations

import json
from datetime import date
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any

from tau2.hyper.transformations.base import (
    KitFile,
    SectionTransformation,
    TransformationArtifact,
    register_transformation,
)
from tau2.utils.utils import DATA_DIR


class EmailThreadArchiveTransformation(SectionTransformation):
    """Deliver RFC-style ``.eml`` exports while keeping fact labels author-side."""

    representation = "email_thread_archive"
    aliases = ("email_threads", "exported_email_threads")
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
                "email_thread_archive transformation for section schema "
                f"{schema.get('id', '<unknown>')!r} must declare artifacts"
            )

        manifest_path = spec.get("eval_manifest_path")
        resolved_manifest = self._resolve(manifest_path) if manifest_path else None
        artifacts = []
        for entry in declared:
            metadata = {
                key: value
                for key, value in entry.items()
                if key not in {"included_fact_ids", "path"}
            }
            if resolved_manifest:
                metadata["eval_manifest_path"] = resolved_manifest
            elif metadata.get("eval_manifest_path"):
                metadata["eval_manifest_path"] = self._resolve(
                    metadata["eval_manifest_path"]
                )
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
        message = BytesParser(policy=policy.default).parsebytes(
            artifact.source_path.read_bytes()
        )
        body = message.get_body(preferencelist=("plain",))
        body_text = body.get_content() if body is not None else message.get_payload()
        visible_headers = [
            f"{name}: {message.get(name, '')}"
            for name in ("From", "To", "Cc", "Date", "Subject")
            if message.get(name)
        ]
        return "\n".join(visible_headers) + "\n\n" + str(body_text)

    def validate(
        self, schema: dict[str, Any], artifacts: list[TransformationArtifact]
    ) -> list[str]:
        issues = super().validate(schema, artifacts)
        seen_kit_filenames: set[str] = set()
        seen_thread_ids: set[str] = set()
        seen_message_ids: set[str] = set()

        for artifact in artifacts:
            name = artifact.source_path.name
            if artifact.source_path.suffix.lower() != ".eml":
                issues.append(f"{name}: exported email thread must end in .eml")
                continue
            if not artifact.source_path.is_file():
                issues.append(f"{name}: exported email thread file not found")
                continue

            kit_filename = str(artifact.metadata.get("kit_filename", ""))
            if not kit_filename:
                issues.append(f"{name}: kit_filename is required")
            elif Path(kit_filename).name != kit_filename:
                issues.append(f"{name}: kit_filename must be a bare filename")
            elif Path(kit_filename).suffix.lower() != ".eml":
                issues.append(f"{name}: kit_filename must end in .eml")
            elif kit_filename in seen_kit_filenames:
                issues.append(f"{name}: duplicate kit_filename {kit_filename!r}")
            seen_kit_filenames.add(kit_filename)

            try:
                message = BytesParser(policy=policy.default).parsebytes(
                    artifact.source_path.read_bytes()
                )
            except (OSError, ValueError) as error:
                issues.append(f"{name}: invalid email export ({error})")
                continue

            for header in (
                "From",
                "To",
                "Date",
                "Subject",
                "Message-ID",
                "MIME-Version",
                "Thread-Topic",
                "Thread-Index",
            ):
                if not message.get(header):
                    issues.append(f"{name}: missing required {header} header")

            thread_id = str(message.get("Thread-Index", ""))
            if thread_id in seen_thread_ids:
                issues.append(f"{name}: duplicate Thread-Index {thread_id!r}")
            seen_thread_ids.add(thread_id)

            message_id = str(message.get("Message-ID", ""))
            if message_id in seen_message_ids:
                issues.append(f"{name}: duplicate Message-ID {message_id!r}")
            seen_message_ids.add(message_id)

            body = message.get_body(preferencelist=("plain",))
            body_text = (
                body.get_content() if body is not None else message.get_payload()
            )
            quoted_count = str(body_text).count("-----Original Message-----")
            if quoted_count < 3:
                issues.append(f"{name}: thread must contain at least four messages")

        manifest_paths = {
            Path(path)
            for artifact in artifacts
            if (path := artifact.metadata.get("eval_manifest_path"))
        }
        if len(manifest_paths) > 1:
            issues.append("email artifacts declare more than one eval manifest")
        elif manifest_paths:
            issues.extend(
                self._validate_eval_manifest(next(iter(manifest_paths)), artifacts)
            )
        return issues

    @staticmethod
    def _validate_eval_manifest(
        manifest_path: Path,
        artifacts: list[TransformationArtifact],
    ) -> list[str]:
        if not manifest_path.is_file():
            return ["email archive eval_manifest_path not found"]
        try:
            manifest = json.loads(manifest_path.read_text())
        except json.JSONDecodeError as error:
            return [f"email archive has invalid eval manifest JSON ({error})"]

        manifest_threads = [
            thread
            for thread in manifest.get("threads") or []
            if isinstance(thread, dict) and thread.get("filename")
        ]
        declared = {
            str(thread["filename"]): set(thread.get("authoritative_fact_ids", []))
            for thread in manifest_threads
        }
        actual = {
            str(artifact.metadata.get("kit_filename") or ""): set(
                artifact.included_fact_ids
            )
            for artifact in artifacts
        }
        issues = []
        if declared != actual:
            issues.append(
                "email archive eval manifest must exactly match artifact filenames "
                "and included_fact_ids"
            )
        if manifest.get("thread_count") != len(artifacts):
            issues.append("email archive eval manifest thread_count is incorrect")

        histories = manifest.get("scope_change_histories")
        has_historical_facts = any(
            thread.get("historical_fact_ids") for thread in manifest_threads
        )
        if histories is None and has_historical_facts:
            issues.append(
                "email archive scope_change_histories is required when threads "
                "declare historical_fact_ids"
            )
        elif histories is not None:
            issues.extend(
                EmailThreadArchiveTransformation._validate_scope_histories(
                    histories, manifest_threads
                )
            )
        return issues

    @staticmethod
    def _validate_scope_histories(
        histories: Any,
        manifest_threads: list[dict[str, Any]],
    ) -> list[str]:
        if not isinstance(histories, dict):
            return ["email archive scope_change_histories must be an object"]

        issues = []
        threads_by_name = {
            str(thread["filename"]): thread for thread in manifest_threads
        }
        declared_historical_facts = {
            str(fact_id)
            for thread in manifest_threads
            for fact_id in thread.get("historical_fact_ids", [])
        }
        if set(histories) != declared_historical_facts:
            issues.append(
                "email archive scope_change_histories must exactly cover "
                "historical_fact_ids"
            )

        for thread in manifest_threads:
            authoritative = set(thread.get("authoritative_fact_ids", []))
            historical = set(thread.get("historical_fact_ids", []))
            if authoritative & historical:
                issues.append(
                    f"{thread['filename']}: a fact cannot be both current and historical"
                )

        for fact_id, events in histories.items():
            if not isinstance(events, list) or len(events) < 2:
                issues.append(
                    f"scope history {fact_id!r} must contain at least two events"
                )
                continue

            statuses = []
            decision_dates = []
            for event in events:
                if not isinstance(event, dict):
                    issues.append(
                        f"scope history {fact_id!r} contains a non-object event"
                    )
                    continue
                filename = str(event.get("thread", ""))
                status = str(event.get("status", ""))
                decision_date = str(event.get("decision_date", ""))
                thread = threads_by_name.get(filename)
                if thread is None:
                    issues.append(
                        f"scope history {fact_id!r} references unknown thread "
                        f"{filename!r}"
                    )
                    continue
                try:
                    date.fromisoformat(decision_date)
                except ValueError:
                    issues.append(
                        f"scope history {fact_id!r} has invalid decision_date "
                        f"{decision_date!r}"
                    )
                    continue
                thread_decision_date = thread.get("decision_date")
                if thread_decision_date is not None and decision_date != str(
                    thread_decision_date
                ):
                    issues.append(
                        f"scope history {fact_id!r} decision date does not match "
                        f"thread {filename!r}"
                    )

                statuses.append(status)
                decision_dates.append(decision_date)
                if status == "superseded":
                    if fact_id not in thread.get("historical_fact_ids", []):
                        issues.append(
                            f"scope history {fact_id!r} superseded event must "
                            f"reference a historical thread"
                        )
                elif status == "final_current":
                    if fact_id not in thread.get("authoritative_fact_ids", []):
                        issues.append(
                            f"scope history {fact_id!r} final event must reference "
                            f"a current authoritative thread"
                        )
                else:
                    issues.append(
                        f"scope history {fact_id!r} has unknown status {status!r}"
                    )

            if statuses and (
                statuses[-1] != "final_current"
                or any(status != "superseded" for status in statuses[:-1])
            ):
                issues.append(
                    f"scope history {fact_id!r} must end with one final_current "
                    "event after superseded events"
                )
            if decision_dates != sorted(decision_dates):
                issues.append(f"scope history {fact_id!r} events must be chronological")
        return issues

    @staticmethod
    def _resolve(path: str | Path) -> Path:
        resolved = Path(path)
        if resolved.is_absolute():
            return resolved
        return DATA_DIR / resolved


register_transformation(EmailThreadArchiveTransformation())
