"""Contact-center QA review exports used as approved interaction evidence."""

from __future__ import annotations

import json
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

_FORMAT = "contact_center_qa_export_v1"
_CHANNELS = {"chat", "email", "messaging", "voice"}
_SPEAKER_ROLES = {"agent", "customer", "supervisor", "system", "third_party"}
_EVALUATION_STATUSES = {
    "appealed",
    "calibrated",
    "draft",
    "final",
    "in_review",
    "submitted",
}
_ITEM_RESULTS = {"fail", "not_applicable", "pass"}
_RUBRIC_STATUSES = {"draft", "published", "retired"}
_REVIEW_EVENT_TYPES = {
    "appealed",
    "assigned",
    "calibrated",
    "finalized",
    "reopened",
    "returned",
    "submitted",
}
_ADJUDICATION_ROLES = {
    "authoritative_current",
    "calibration_history",
    "distractor",
    "failed_example",
    "supporting_current",
}


def _timestamp(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.utcoffset() is not None else None


def _number(value: Any) -> bool:
    """True numeric score; bool is an int subclass and must not count."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class ContactCenterQAExportTransformation(SectionTransformation):
    """Deliver reviewed interactions and their final contact-center scorecards."""

    representation = "contact_center_qa_export"
    aliases = ("contact_center_quality_export", "qa_review_export")
    placement = "named"
    carries_agent_utterances = True

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
                "contact_center_qa_export transformation for section schema "
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
            path = artifact.source_path
            name = path.name
            if path.suffix.lower() != ".json":
                issues.append(f"{name}: contact-center QA export must end in .json")
                continue
            if not path.is_file():
                issues.append(f"{name}: contact-center QA export file not found")
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
                payload = json.loads(path.read_text())
            except (OSError, json.JSONDecodeError) as error:
                issues.append(f"{name}: invalid contact-center QA JSON ({error})")
                continue
            issues.extend(self._validate_export(name, payload, schema))

            manifest_path = artifact.metadata.get("eval_manifest_path")
            if not manifest_path:
                issues.append(f"{name}: eval_manifest_path is required")
            else:
                issues.extend(
                    self._validate_eval_manifest(
                        Path(manifest_path), artifact, payload, kit_filename
                    )
                )
            raw = json.dumps(payload, ensure_ascii=False)
            leaked_author_paths = [
                value
                for value in (str(path), str(manifest_path or ""))
                if value and value in raw
            ]
            if leaked_author_paths:
                issues.append(f"{name}: author-only source or manifest path leaked")
        return issues

    @classmethod
    def _validate_export(
        cls, name: str, payload: Any, schema: dict[str, Any]
    ) -> list[str]:
        if not isinstance(payload, dict):
            return [f"{name}: contact-center QA export root must be an object"]
        issues: list[str] = []
        if payload.get("export_format") != _FORMAT:
            issues.append(f"{name}: export_format must be {_FORMAT!r}")
        exported_at = _timestamp(payload.get("exported_at"))
        if exported_at is None:
            issues.append(f"{name}: exported_at must include a timezone offset")

        source_system = payload.get("source_system")
        if not isinstance(source_system, dict) or not all(
            source_system.get(field) for field in ("name", "environment")
        ):
            issues.append(f"{name}: source_system needs name and environment")

        users = payload.get("users")
        user_ids = [
            str(user.get("user_id"))
            for user in users or []
            if isinstance(user, dict) and user.get("user_id")
        ]
        if not isinstance(users, list) or len(set(user_ids)) < 3:
            issues.append(f"{name}: users must contain at least three unique users")
        elif len(user_ids) != len(users) or len(user_ids) != len(set(user_ids)):
            issues.append(f"{name}: every user needs a unique user_id")
        known_users = set(user_ids)

        rubrics = payload.get("rubrics")
        rubric_items: dict[str, dict[str, float]] = {}
        rubric_ids: list[str] = []
        if not isinstance(rubrics, list) or not rubrics:
            issues.append(f"{name}: rubrics must be a non-empty list")
        else:
            for rubric in rubrics:
                if not isinstance(rubric, dict):
                    issues.append(f"{name}: rubric entries must be objects")
                    continue
                rubric_id = str(rubric.get("rubric_id") or "")
                if not rubric_id:
                    issues.append(f"{name}: every rubric needs rubric_id")
                    continue
                rubric_ids.append(rubric_id)
                if not all(
                    rubric.get(field) for field in ("name", "version", "status")
                ):
                    issues.append(
                        f"{name}: rubric {rubric_id} needs name, version, and status"
                    )
                elif str(rubric.get("status")) not in _RUBRIC_STATUSES:
                    issues.append(
                        f"{name}: rubric {rubric_id} has invalid status "
                        f"{rubric.get('status')!r}"
                    )
                items = rubric.get("items")
                if not isinstance(items, list) or not items:
                    issues.append(f"{name}: rubric {rubric_id} needs items")
                    continue
                item_scores: dict[str, float] = {}
                for item in items:
                    if not isinstance(item, dict):
                        issues.append(
                            f"{name}: rubric {rubric_id} item must be an object"
                        )
                        continue
                    item_id = str(item.get("item_id") or "")
                    max_score = item.get("max_score")
                    if not item_id or not item.get("title"):
                        issues.append(
                            f"{name}: rubric {rubric_id} items need id and title"
                        )
                    if not _number(max_score) or max_score <= 0:
                        issues.append(
                            f"{name}: rubric {rubric_id} item {item_id!r} needs "
                            "positive max_score"
                        )
                        continue
                    if item_id in item_scores:
                        issues.append(
                            f"{name}: rubric {rubric_id} has duplicate item {item_id!r}"
                        )
                    item_scores[item_id] = float(max_score)
                rubric_items[rubric_id] = item_scores
        if len(rubric_ids) != len(set(rubric_ids)):
            issues.append(f"{name}: rubric_id values must be unique")

        interactions = payload.get("interactions")
        if not isinstance(interactions, list) or len(interactions) < 4:
            return [*issues, f"{name}: interactions must contain at least four records"]
        interaction_ids = [
            str(interaction.get("interaction_id") or "")
            for interaction in interactions
            if isinstance(interaction, dict)
        ]
        if len(interaction_ids) != len(interactions) or any(
            not interaction_id for interaction_id in interaction_ids
        ):
            issues.append(f"{name}: every interaction needs interaction_id")
        elif len(interaction_ids) != len(set(interaction_ids)):
            issues.append(f"{name}: interaction_id values must be unique")

        turn_ids: set[str] = set()
        evaluation_ids: set[str] = set()
        review_event_ids: set[str] = set()
        evaluation_count = 0
        final_evaluation_count = 0
        for interaction in interactions:
            if not isinstance(interaction, dict):
                issues.append(f"{name}: interaction entries must be objects")
                continue
            interaction_id = str(interaction.get("interaction_id") or "<unknown>")
            issues.extend(
                cls._validate_interaction(
                    name=name,
                    interaction_id=interaction_id,
                    interaction=interaction,
                    exported_at=exported_at,
                    known_users=known_users,
                    rubric_items=rubric_items,
                    turn_ids=turn_ids,
                    evaluation_ids=evaluation_ids,
                    review_event_ids=review_event_ids,
                )
            )
            evaluations = interaction.get("evaluations")
            if isinstance(evaluations, list):
                evaluation_count += len(evaluations)
                final_evaluation_count += sum(
                    isinstance(evaluation, dict) and evaluation.get("status") == "final"
                    for evaluation in evaluations
                )

        if final_evaluation_count < 1:
            issues.append(f"{name}: export must contain at least one final evaluation")
        if payload.get("interaction_count") != len(interactions):
            issues.append(f"{name}: interaction_count is incorrect")
        if payload.get("evaluation_count") != evaluation_count:
            issues.append(f"{name}: evaluation_count is incorrect")

        raw = json.dumps(payload, ensure_ascii=False)
        leaked_facts = sorted(
            fact_id for fact_id in schema_fact_ids(schema) if fact_id in raw
        )
        if leaked_facts:
            issues.append(f"{name}: author-only fact ids leaked: {leaked_facts}")
        leaked_roles = sorted(role for role in _ADJUDICATION_ROLES if role in raw)
        if leaked_roles:
            issues.append(
                f"{name}: author-only adjudication roles leaked: {leaked_roles}"
            )
        return issues

    @classmethod
    def _validate_interaction(
        cls,
        *,
        name: str,
        interaction_id: str,
        interaction: dict[str, Any],
        exported_at: datetime | None,
        known_users: set[str],
        rubric_items: dict[str, dict[str, float]],
        turn_ids: set[str],
        evaluation_ids: set[str],
        review_event_ids: set[str],
    ) -> list[str]:
        issues: list[str] = []
        channel = str(interaction.get("channel") or "")
        if channel not in _CHANNELS:
            issues.append(
                f"{name}: {interaction_id} channel must be one of {sorted(_CHANNELS)}"
            )
        if not all(
            interaction.get(field)
            for field in ("queue", "language", "customer_reference", "disposition")
        ):
            issues.append(
                f"{name}: {interaction_id} needs queue, language, customer_reference, "
                "and disposition"
            )
        if str(interaction.get("agent_id") or "") not in known_users:
            issues.append(f"{name}: {interaction_id} references unknown agent")

        started_at = _timestamp(interaction.get("started_at"))
        ended_at = _timestamp(interaction.get("ended_at"))
        if started_at is None or ended_at is None:
            issues.append(f"{name}: {interaction_id} timestamps need timezone offsets")
        elif started_at > ended_at or (exported_at and ended_at > exported_at):
            issues.append(f"{name}: {interaction_id} has impossible timestamps")

        transcript = interaction.get("transcript")
        if not isinstance(transcript, list) or len(transcript) < 4:
            issues.append(f"{name}: {interaction_id} transcript needs four turns")
            transcript = []
        roles: set[str] = set()
        previous_turn_start: datetime | None = None
        local_turn_ids: set[str] = set()
        for turn in transcript:
            if not isinstance(turn, dict):
                issues.append(f"{name}: {interaction_id} turns must be objects")
                continue
            turn_id = str(turn.get("turn_id") or "")
            if not turn_id:
                issues.append(f"{name}: {interaction_id} turn needs turn_id")
                continue
            if turn_id in turn_ids:
                issues.append(f"{name}: transcript turn ids must be globally unique")
            turn_ids.add(turn_id)
            local_turn_ids.add(turn_id)
            role = str(turn.get("speaker_role") or "")
            roles.add(role)
            if role not in _SPEAKER_ROLES:
                issues.append(
                    f"{name}: {interaction_id} turn {turn_id!r} has invalid role"
                )
            if not str(turn.get("text") or "").strip():
                issues.append(f"{name}: {interaction_id} turn {turn_id!r} needs text")
            turn_start = _timestamp(turn.get("started_at"))
            turn_end = _timestamp(turn.get("ended_at"))
            if turn_start is None or turn_end is None:
                issues.append(
                    f"{name}: {interaction_id} turn {turn_id!r} needs timestamps"
                )
            elif turn_start > turn_end:
                issues.append(
                    f"{name}: {interaction_id} turn {turn_id!r} ends before it starts"
                )
            else:
                if started_at and turn_start < started_at:
                    issues.append(
                        f"{name}: {interaction_id} turn {turn_id!r} predates contact"
                    )
                if ended_at and turn_end > ended_at:
                    issues.append(
                        f"{name}: {interaction_id} turn {turn_id!r} exceeds contact"
                    )
                if previous_turn_start and turn_start < previous_turn_start:
                    issues.append(
                        f"{name}: {interaction_id} transcript is not chronological"
                    )
                previous_turn_start = turn_start
        if not {"agent", "customer"}.issubset(roles):
            issues.append(
                f"{name}: {interaction_id} transcript needs agent and customer turns"
            )

        evaluations = interaction.get("evaluations")
        if not isinstance(evaluations, list) or not evaluations:
            issues.append(f"{name}: {interaction_id} needs evaluations")
            evaluations = []
        for evaluation in evaluations:
            if not isinstance(evaluation, dict):
                issues.append(f"{name}: {interaction_id} evaluations must be objects")
                continue
            issues.extend(
                cls._validate_evaluation(
                    name=name,
                    interaction_id=interaction_id,
                    evaluation=evaluation,
                    exported_at=exported_at,
                    interaction_ended_at=ended_at,
                    known_users=known_users,
                    rubric_items=rubric_items,
                    local_turn_ids=local_turn_ids,
                    evaluation_ids=evaluation_ids,
                )
            )

        history = interaction.get("review_history")
        if not isinstance(history, list) or not history:
            issues.append(f"{name}: {interaction_id} needs review_history")
            history = []
        previous_event_at: datetime | None = None
        for event in history:
            if not isinstance(event, dict):
                issues.append(f"{name}: {interaction_id} review events need objects")
                continue
            event_id = str(event.get("event_id") or "")
            if not event_id:
                issues.append(f"{name}: {interaction_id} review event needs event_id")
            elif event_id in review_event_ids:
                issues.append(f"{name}: review event ids must be globally unique")
            else:
                review_event_ids.add(event_id)
            if str(event.get("actor_id") or "") not in known_users:
                issues.append(
                    f"{name}: {interaction_id} review event references unknown actor"
                )
            event_type = str(event.get("event_type") or "")
            if event_type not in _REVIEW_EVENT_TYPES:
                issues.append(f"{name}: {interaction_id} review event has invalid type")
            event_at = _timestamp(event.get("created_at"))
            if event_at is None:
                issues.append(f"{name}: {interaction_id} review event needs timezone")
            else:
                if ended_at and event_at < ended_at:
                    issues.append(
                        f"{name}: {interaction_id} review predates interaction end"
                    )
                if exported_at and event_at > exported_at:
                    issues.append(f"{name}: {interaction_id} review postdates export")
                if previous_event_at and event_at < previous_event_at:
                    issues.append(
                        f"{name}: {interaction_id} review history is not chronological"
                    )
                previous_event_at = event_at
        return issues

    @staticmethod
    def _validate_evaluation(
        *,
        name: str,
        interaction_id: str,
        evaluation: dict[str, Any],
        exported_at: datetime | None,
        interaction_ended_at: datetime | None,
        known_users: set[str],
        rubric_items: dict[str, dict[str, float]],
        local_turn_ids: set[str],
        evaluation_ids: set[str],
    ) -> list[str]:
        issues: list[str] = []
        evaluation_id = str(evaluation.get("evaluation_id") or "")
        if not evaluation_id or evaluation_id in evaluation_ids:
            issues.append(f"{name}: evaluation ids must be globally unique")
        evaluation_ids.add(evaluation_id)
        rubric_id = str(evaluation.get("rubric_id") or "")
        expected_items = rubric_items.get(rubric_id)
        if expected_items is None:
            issues.append(
                f"{name}: {interaction_id} evaluation references unknown rubric"
            )
            expected_items = {}
        if str(evaluation.get("reviewer_id") or "") not in known_users:
            issues.append(
                f"{name}: {interaction_id} evaluation references unknown reviewer"
            )
        status = str(evaluation.get("status") or "")
        if status not in _EVALUATION_STATUSES:
            issues.append(f"{name}: {interaction_id} evaluation has invalid status")

        created_at = _timestamp(evaluation.get("created_at"))
        finalized_at = _timestamp(evaluation.get("finalized_at"))
        if created_at is None:
            issues.append(f"{name}: {interaction_id} evaluation needs created_at")
        elif interaction_ended_at and created_at < interaction_ended_at:
            issues.append(f"{name}: {interaction_id} evaluation predates contact end")
        if status == "final" and finalized_at is None:
            issues.append(
                f"{name}: {interaction_id} final evaluation needs finalized_at"
            )
        if finalized_at:
            if created_at and finalized_at < created_at:
                issues.append(
                    f"{name}: {interaction_id} evaluation finalizes before creation"
                )
            if exported_at and finalized_at > exported_at:
                issues.append(f"{name}: {interaction_id} evaluation postdates export")

        items = evaluation.get("items")
        if not isinstance(items, list) or not items:
            issues.append(f"{name}: {interaction_id} evaluation needs scored items")
            return issues
        seen_item_ids: set[str] = set()
        awarded = 0.0
        possible = 0.0
        for item in items:
            if not isinstance(item, dict):
                issues.append(
                    f"{name}: {interaction_id} evaluation items must be objects"
                )
                continue
            item_id = str(item.get("item_id") or "")
            if item_id in seen_item_ids:
                issues.append(
                    f"{name}: {interaction_id} evaluation repeats item {item_id!r}"
                )
            seen_item_ids.add(item_id)
            if item_id not in expected_items:
                issues.append(
                    f"{name}: {interaction_id} evaluation has unknown item {item_id!r}"
                )
                continue
            result = str(item.get("result") or "")
            if result not in _ITEM_RESULTS:
                issues.append(
                    f"{name}: {interaction_id} item {item_id!r} has invalid result"
                )
            score = item.get("score")
            max_score = expected_items[item_id]
            if not _number(score) or not 0 <= score <= max_score:
                issues.append(
                    f"{name}: {interaction_id} item {item_id!r} has invalid score"
                )
            elif result != "not_applicable":
                awarded += float(score)
                possible += max_score
            evidence_ids = item.get("evidence_turn_ids")
            if result != "not_applicable" and (
                not isinstance(evidence_ids, list) or not evidence_ids
            ):
                issues.append(
                    f"{name}: {interaction_id} item {item_id!r} needs turn evidence"
                )
            elif isinstance(evidence_ids, list) and not set(evidence_ids).issubset(
                local_turn_ids
            ):
                issues.append(
                    f"{name}: {interaction_id} item {item_id!r} references unknown turn"
                )

        overall_score = evaluation.get("overall_score")
        expected_score = round(100 * awarded / possible, 2) if possible else 0.0
        if (
            not _number(overall_score)
            or abs(float(overall_score) - expected_score) > 0.01
        ):
            issues.append(f"{name}: {interaction_id} overall_score is incorrect")
        if not isinstance(evaluation.get("critical_failure"), bool):
            issues.append(f"{name}: {interaction_id} critical_failure must be boolean")
        return issues

    @classmethod
    def _validate_eval_manifest(
        cls,
        manifest_path: Path,
        artifact: TransformationArtifact,
        payload: dict[str, Any],
        kit_filename: str,
    ) -> list[str]:
        if not manifest_path.is_file():
            return ["contact-center QA eval_manifest_path not found"]
        try:
            manifest = json.loads(manifest_path.read_text())
        except json.JSONDecodeError as error:
            return [f"contact-center QA eval manifest is invalid JSON ({error})"]
        if not isinstance(manifest, dict):
            return ["contact-center QA eval manifest root must be an object"]
        if not isinstance(payload, dict):
            return [
                "contact-center QA export root must be an object for manifest "
                "validation"
            ]

        issues: list[str] = []
        rubric_status = {
            str(rubric.get("rubric_id")): str(rubric.get("status") or "")
            for rubric in payload.get("rubrics") or []
            if isinstance(rubric, dict)
        }
        declared_artifact = manifest.get("artifact")
        if not isinstance(declared_artifact, dict):
            declared_artifact = {}
            issues.append("contact-center QA manifest artifact must be an object")
        if declared_artifact.get("filename") != kit_filename:
            issues.append("contact-center QA manifest filename does not match")
        declared_facts = set(declared_artifact.get("authoritative_fact_ids") or [])
        if declared_facts != set(artifact.included_fact_ids):
            issues.append(
                "contact-center QA manifest facts do not match artifact coverage"
            )

        interactions = payload.get("interactions")
        interactions = interactions if isinstance(interactions, list) else []
        interactions_by_id = {
            str(interaction.get("interaction_id")): interaction
            for interaction in interactions
            if isinstance(interaction, dict)
        }
        decisions = manifest.get("decisions")
        decisions = decisions if isinstance(decisions, list) else []
        decision_facts = [
            str(decision.get("fact_id"))
            for decision in decisions
            if isinstance(decision, dict)
        ]
        if set(decision_facts) != declared_facts:
            issues.append(
                "contact-center QA decisions must cover every authoritative fact"
            )
        elif len(decision_facts) != len(set(decision_facts)):
            issues.append("contact-center QA decisions duplicate fact ownership")

        authoritative_interactions: set[str] = set()
        for decision in decisions:
            if not isinstance(decision, dict):
                issues.append("contact-center QA decisions must be objects")
                continue
            interaction_id = str(decision.get("interaction_id") or "")
            interaction = interactions_by_id.get(interaction_id)
            if interaction is None:
                issues.append(
                    f"contact-center QA decision references unknown interaction "
                    f"{interaction_id!r}"
                )
                continue
            authoritative_interactions.add(interaction_id)
            if decision.get("status") != "final_current":
                issues.append(
                    f"contact-center QA decision for {interaction_id} is not current"
                )
            evaluation_id = str(decision.get("evaluation_id") or "")
            evaluations = interaction.get("evaluations")
            evaluations = evaluations if isinstance(evaluations, list) else []
            evaluation = next(
                (
                    item
                    for item in evaluations
                    if isinstance(item, dict)
                    and str(item.get("evaluation_id")) == evaluation_id
                ),
                None,
            )
            if evaluation is None:
                issues.append(
                    f"contact-center QA decision references unknown evaluation "
                    f"{evaluation_id!r}"
                )
                continue
            if evaluation.get("status") != "final":
                issues.append(
                    f"contact-center QA evidence {evaluation_id!r} must be final"
                )
            if rubric_status.get(str(evaluation.get("rubric_id") or "")) != "published":
                issues.append(
                    f"contact-center QA decision for {interaction_id} cites "
                    f"evaluation {evaluation_id!r} on a non-current rubric"
                )
            if evaluation.get("critical_failure") is True:
                issues.append(
                    f"contact-center QA evidence {evaluation_id!r} carries a "
                    "critical failure and cannot warrant a current fact"
                )
            rubric_item_id = str(decision.get("rubric_item_id") or "")
            evaluation_items = evaluation.get("items")
            evaluation_items = (
                evaluation_items if isinstance(evaluation_items, list) else []
            )
            score_item = next(
                (
                    item
                    for item in evaluation_items
                    if isinstance(item, dict)
                    and str(item.get("item_id")) == rubric_item_id
                ),
                None,
            )
            if score_item is None or score_item.get("result") != "pass":
                issues.append(
                    f"contact-center QA decision item {rubric_item_id!r} must pass"
                )
                continue
            issues.extend(
                cls._validate_manifest_evidence(
                    interaction_id=interaction_id,
                    interaction=interaction,
                    score_item=score_item,
                    evidence=decision.get("evidence"),
                )
            )

        adjudication = manifest.get("interaction_adjudication")
        adjudication = adjudication if isinstance(adjudication, list) else []
        adjudicated_ids = [
            str(entry.get("interaction_id"))
            for entry in adjudication
            if isinstance(entry, dict)
        ]
        if set(adjudicated_ids) != set(interactions_by_id) or len(
            adjudicated_ids
        ) != len(set(adjudicated_ids)):
            issues.append(
                "contact-center QA adjudication must classify every interaction once"
            )
        authoritative_roles: set[str] = set()
        for entry in adjudication:
            if not isinstance(entry, dict):
                issues.append("contact-center QA adjudication entries need objects")
                continue
            role = str(entry.get("role") or "")
            interaction_id = str(entry.get("interaction_id") or "")
            if role not in _ADJUDICATION_ROLES:
                issues.append(
                    f"contact-center QA interaction {interaction_id!r} has invalid role"
                )
            if role == "authoritative_current":
                authoritative_roles.add(interaction_id)
        if not authoritative_interactions.issubset(authoritative_roles):
            issues.append(
                "contact-center QA fact carriers must be authoritative_current"
            )

        snapshot = _timestamp(manifest.get("snapshot"))
        if snapshot is None:
            issues.append("contact-center QA manifest snapshot needs timezone")
        elif snapshot != _timestamp(payload.get("exported_at")):
            issues.append("contact-center QA manifest snapshot does not match export")
        return issues

    @staticmethod
    def _validate_manifest_evidence(
        *,
        interaction_id: str,
        interaction: dict[str, Any],
        score_item: dict[str, Any],
        evidence: Any,
    ) -> list[str]:
        if not isinstance(evidence, list) or not evidence:
            return [f"contact-center QA decision for {interaction_id} needs evidence"]
        issues: list[str] = []
        transcript = interaction.get("transcript")
        transcript = transcript if isinstance(transcript, list) else []
        turns_by_id = {
            str(turn.get("turn_id")): turn
            for turn in transcript
            if isinstance(turn, dict)
        }
        for span in evidence:
            if not isinstance(span, dict):
                issues.append(
                    f"contact-center QA evidence for {interaction_id} needs objects"
                )
                continue
            source = str(span.get("source") or "")
            excerpt = str(span.get("excerpt") or "")
            if source == "turn":
                turn_id = str(span.get("turn_id") or "")
                turn = turns_by_id.get(turn_id)
                if (
                    turn is None
                    or not excerpt
                    or str(turn.get("text") or "").count(excerpt) != 1
                ):
                    issues.append(
                        f"contact-center QA turn evidence for {interaction_id} "
                        "must resolve uniquely"
                    )
                elif turn_id not in set(score_item.get("evidence_turn_ids") or []):
                    issues.append(
                        f"contact-center QA turn evidence for {interaction_id} "
                        "must be cited by the scored rubric item"
                    )
            elif source == "reviewer_note":
                note = str(score_item.get("reviewer_note") or "")
                if not excerpt or note.count(excerpt) != 1:
                    issues.append(
                        f"contact-center QA reviewer evidence for {interaction_id} "
                        "must resolve uniquely"
                    )
            else:
                issues.append(
                    f"contact-center QA evidence for {interaction_id} has invalid source"
                )
        return issues

    @staticmethod
    def _resolve(path: str | Path) -> Path:
        resolved = Path(path)
        if resolved.is_absolute():
            return resolved
        return DATA_DIR / resolved


register_transformation(ContactCenterQAExportTransformation())
