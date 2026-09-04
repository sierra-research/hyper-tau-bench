"""Captured Slack MCP tool-call logs used as business-policy evidence."""

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
)
from tau2.utils.utils import DATA_DIR

_SLACK_TIMESTAMP = re.compile(r"^\d{10}\.\d{6}$")


class SlackMCPDumpTransformation(SectionTransformation):
    """Deliver structured Slack MCP call captures without author annotations."""

    representation = "slack_mcp_dump"
    aliases = ("slack_export", "slack_threads", "slack_mcp_output")
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
                "slack_mcp_dump transformation for section schema "
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
                issues.append(f"{name}: Slack MCP dump must end in .json")
                continue
            if not artifact.source_path.is_file():
                issues.append(f"{name}: Slack MCP dump file not found")
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
                issues.append(f"{name}: invalid Slack MCP JSON ({error})")
                continue
            issues.extend(self._validate_capture(name, payload))

        manifest_paths = {
            Path(path)
            for artifact in artifacts
            if (path := artifact.metadata.get("eval_manifest_path"))
        }
        if len(manifest_paths) > 1:
            issues.append("Slack MCP artifacts declare more than one eval manifest")
        elif manifest_paths:
            issues.extend(
                self._validate_eval_manifest(next(iter(manifest_paths)), artifacts)
            )
        return issues

    @staticmethod
    def _validate_capture(name: str, payload: Any) -> list[str]:
        if not isinstance(payload, dict):
            return [f"{name}: Slack MCP dump root must be an object"]
        issues = []
        if payload.get("capture_format") != "slack_mcp_tool_call_log":
            issues.append(f"{name}: unknown Slack MCP capture_format")
        if payload.get("server") != "slack":
            issues.append(f"{name}: Slack MCP server must be 'slack'")
        calls = payload.get("tool_calls")
        if not isinstance(calls, list) or not calls:
            return [*issues, f"{name}: tool_calls must be a non-empty list"]

        seen_call_ids: set[str] = set()
        thread_fetch_count = 0
        for call in calls:
            if not isinstance(call, dict):
                issues.append(f"{name}: tool_calls entries must be objects")
                continue
            call_id = str(call.get("call_id", ""))
            if not call_id:
                issues.append(f"{name}: Slack MCP call_id is required")
            elif call_id in seen_call_ids:
                issues.append(f"{name}: duplicate Slack MCP call_id {call_id!r}")
            seen_call_ids.add(call_id)

            request = call.get("request")
            response = call.get("response")
            if not isinstance(request, dict) or request.get("method") != "tools/call":
                issues.append(f"{name}: {call_id} must be an MCP tools/call request")
                continue
            params = request.get("params")
            tool_name = str(params.get("name", "")) if isinstance(params, dict) else ""
            if not tool_name.startswith("slack_"):
                issues.append(f"{name}: {call_id} has invalid Slack tool name")

            if not isinstance(response, dict) or response.get("is_error") is not False:
                issues.append(f"{name}: {call_id} must contain a successful response")
                continue
            structured = response.get("structured_content")
            if not isinstance(structured, dict):
                issues.append(f"{name}: {call_id} lacks structured_content")
                continue
            messages = structured.get("messages", [])
            if not isinstance(messages, list):
                issues.append(f"{name}: {call_id} messages must be a list")
                continue
            for message in messages:
                issues.extend(
                    SlackMCPDumpTransformation._validate_message(name, call_id, message)
                )
            messages_are_objects = all(
                isinstance(message, dict) for message in messages
            )
            if tool_name == "slack_get_thread_replies" and not messages:
                issues.append(f"{name}: {call_id} thread fetch must contain messages")
            elif tool_name == "slack_get_thread_replies" and messages_are_objects:
                thread_fetch_count += 1
                root_ts = str(messages[0].get("ts", ""))
                if str(messages[0].get("thread_ts", "")) != root_ts:
                    issues.append(
                        f"{name}: {call_id} first thread message must be the root"
                    )
                if any(
                    str(message.get("thread_ts", "")) != root_ts for message in messages
                ):
                    issues.append(
                        f"{name}: {call_id} contains replies from another thread"
                    )
                timestamps = [str(message.get("ts", "")) for message in messages]
                if timestamps != sorted(timestamps):
                    issues.append(
                        f"{name}: {call_id} thread messages are not chronological"
                    )

        if thread_fetch_count < 4:
            issues.append(f"{name}: Slack MCP dump must include at least four threads")
        return issues

    @staticmethod
    def _validate_message(name: str, call_id: str, message: Any) -> list[str]:
        if not isinstance(message, dict):
            return [f"{name}: {call_id} contains a non-object message"]
        issues = []
        for field in (
            "channel_id",
            "channel_name",
            "ts",
            "thread_ts",
            "user_id",
            "text",
            "permalink",
        ):
            if not message.get(field):
                issues.append(f"{name}: {call_id} message missing {field}")
        for field in ("ts", "thread_ts"):
            value = str(message.get(field, ""))
            if value and not _SLACK_TIMESTAMP.fullmatch(value):
                issues.append(
                    f"{name}: {call_id} message has invalid {field} {value!r}"
                )
        return issues

    @staticmethod
    def _validate_eval_manifest(
        manifest_path: Path,
        artifacts: list[TransformationArtifact],
    ) -> list[str]:
        if not manifest_path.is_file():
            return ["Slack MCP eval_manifest_path not found"]
        try:
            manifest = json.loads(manifest_path.read_text())
        except json.JSONDecodeError as error:
            return [f"Slack MCP eval manifest is invalid JSON ({error})"]

        declared = {
            str(entry.get("filename")): set(entry.get("authoritative_fact_ids", []))
            for entry in manifest.get("artifacts") or []
            if isinstance(entry, dict) and entry.get("filename")
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
                "Slack MCP eval manifest must exactly match artifact filenames "
                "and included_fact_ids"
            )

        history = manifest.get("decision_history")
        if not isinstance(history, list) or len(history) < 2:
            issues.append("Slack MCP decision_history must contain multiple versions")
            return issues
        if not all(isinstance(event, dict) for event in history):
            issues.append(
                "Slack MCP decision_history must end in one final_current event"
            )
            return issues

        # A capture may carry several concurrent decision arcs, labeled with
        # per-event ``arc_id`` values; an unlabeled history is a single arc.
        # Each arc must be its own chronological superseded* -> final_current
        # progression, and the union of the arcs' final facts must match the
        # artifacts' included_fact_ids. Client-overlay captures may instead
        # end an arc on a declared open gap: every event superseded, the
        # last one reopened by a live deliberation thread and owning no
        # facts — the ruling deliberately never lands (the overlay's Client
        # holds it), so a final_current event would be a leak.
        arc_events: dict[str, list[dict[str, Any]]] = {}
        for event in history:
            arc_events.setdefault(str(event.get("arc_id") or ""), []).append(event)
        final_fact_ids: set[str] = set()
        for arc_key, events in arc_events.items():
            label = f" (arc {arc_key})" if arc_key else ""
            statuses = [str(event.get("status", "")) for event in events]
            reopened_by = events[-1].get("reopened_by")
            open_gap_arc = (
                len(statuses) >= 2
                and all(status == "superseded" for status in statuses)
                and isinstance(reopened_by, dict)
                and reopened_by.get("mode") == "open_deliberation_thread"
                and reopened_by.get("thread_key")
                and not events[-1].get("authoritative_fact_ids")
            )
            if not open_gap_arc and (
                len(statuses) < 2
                or statuses[-1] != "final_current"
                or any(status != "superseded" for status in statuses[:-1])
            ):
                issues.append(
                    "Slack MCP decision_history must end in one final_current "
                    f"event{label}"
                )
            timestamps = [str(event.get("decision_timestamp", "")) for event in events]
            try:
                parsed_timestamps = [
                    datetime.fromisoformat(value.replace("Z", "+00:00"))
                    for value in timestamps
                ]
            except ValueError:
                issues.append(
                    f"Slack MCP decision_history has invalid timestamps{label}"
                )
            else:
                if any(
                    timestamp.tzinfo is None or timestamp.utcoffset() is None
                    for timestamp in parsed_timestamps
                ):
                    issues.append(
                        "Slack MCP decision_history timestamps must include "
                        f"timezone offsets{label}"
                    )
                elif parsed_timestamps != sorted(parsed_timestamps):
                    issues.append(
                        f"Slack MCP decision_history is not chronological{label}"
                    )
            final_fact_ids.update(events[-1].get("authoritative_fact_ids", []))

        all_actual_fact_ids = set().union(*actual.values()) if actual else set()
        if final_fact_ids != all_actual_fact_ids:
            issues.append("Slack MCP final decision facts must match included_fact_ids")
        return issues

    @staticmethod
    def _resolve(path: str | Path) -> Path:
        resolved = Path(path)
        if resolved.is_absolute():
            return resolved
        return DATA_DIR / resolved


register_transformation(SlackMCPDumpTransformation())
