"""Helpers for projecting generated DB state through reference schemas."""

from typing import Any


def dump_db_for_projection(db) -> dict[str, Any]:
    """Dump a DB for cross-schema projection using public JSON names."""

    return db.model_dump(mode="json", by_alias=True)


def _project_reference_visible_table_rows(
    source_state: dict[str, Any],
    target_state: dict[str, Any],
) -> dict[str, Any]:
    """Trim raw table rows to fields visible in the target DB state.

    Some domains, such as ``banking_knowledge``, intentionally store table rows
    as ``dict[str, Any]`` in the reference DB. Pydantic projection cannot
    discard generated-only fields inside those raw dicts, so do a table-aware
    cleanup after top-level schema projection.
    """

    if not isinstance(source_state, dict) or not isinstance(target_state, dict):
        return source_state

    projected = dict(source_state)
    for table_name, source_table in source_state.items():
        target_table = target_state.get(table_name)
        if not (
            isinstance(source_table, dict)
            and isinstance(target_table, dict)
            and isinstance(source_table.get("data"), dict)
            and isinstance(target_table.get("data"), dict)
        ):
            continue

        target_records = target_table["data"]
        allowed_keys = {
            key
            for record in target_records.values()
            if isinstance(record, dict)
            for key in record
        }
        source_records = source_table["data"]
        trimmed_records = {}
        for record_id, source_record in source_records.items():
            if not isinstance(source_record, dict):
                trimmed_records[record_id] = source_record
                continue

            target_record = target_records.get(record_id)
            if not isinstance(target_record, dict):
                target_record = {}
            trimmed_record = {}
            for key, value in source_record.items():
                projected_key = key
                if (
                    isinstance(key, str)
                    and key not in allowed_keys
                    and key.endswith("_")
                    and key[:-1] in allowed_keys
                ):
                    projected_key = key[:-1]

                if allowed_keys and projected_key not in allowed_keys:
                    continue
                if value is None and projected_key not in target_record:
                    continue
                trimmed_record[projected_key] = value
            trimmed_records[record_id] = trimmed_record

        projected_table = dict(source_table)
        projected_table["data"] = trimmed_records
        projected[table_name] = projected_table
    return projected


def project_db_state_to_target_schema(source_db, target_db) -> dict[str, Any]:
    """Project one DB instance through another DB instance's schema.

    Construction submissions may add internal helper fields that are meaningful
    only inside the generated toolkit. Reference assertions, DB hashes, and
    reference-user routing should compare only the target-schema-visible state.
    """

    source_state = dump_db_for_projection(source_db)
    target_state = dump_db_for_projection(target_db)
    if isinstance(source_state, dict) and isinstance(target_state, dict):
        # Generated schemas may model a reference table as Optional and leave it
        # at None when no task setup touched it. Treat that as "use the target
        # default" instead of failing projection and comparing raw,
        # incompatible DB shapes.
        source_state = {
            key: value
            for key, value in source_state.items()
            if value is not None or target_state.get(key) is None
        }
    projected = target_db.__class__.model_validate(
        source_state,
        extra="ignore",
    ).model_dump(mode="json", by_alias=True)
    return _project_reference_visible_table_rows(projected, target_state)
