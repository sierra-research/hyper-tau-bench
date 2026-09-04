"""Rewrite Banking knowledge materials as direct Client API documentation."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from email import policy
from email.generator import BytesGenerator
from email.parser import BytesParser
from io import BytesIO
from pathlib import Path
from typing import Any, get_args, get_origin

from pydantic import BaseModel

from tau2.hyper.client_api.catalog import ClientOperation
from tau2.hyper.client_api.catalogs.banking import operations

_WRAPPER_REPLACEMENTS = {
    "unlock_discoverable_agent_tool": "review the documented API operation",
    "call_discoverable_agent_tool": "send the documented API request",
    "list_discoverable_agent_tools": "search the retrieved API documentation",
}

_SPECIAL_TRANSFER_REFERENCES = {
    "initial_transfer_to_human_agent_0218",
    "initial_transfer_to_human_agent_1822",
    "emergency_credit_bureau_incident_transfer_1114",
}

_SELF_SERVICE_ACTIONS = {
    "deposit_check_3847",
    "get_card_last_4_digits",
    "get_referral_link",
    "submit_cash_back_dispute_0589",
}

_TEXT_SUFFIXES = {".cjs", ".html", ".md", ".py", ".txt", ".vtt"}


@dataclass(frozen=True)
class RewrittenDocument:
    """One rewritten document and the operations it teaches."""

    content: bytes
    operations: tuple[ClientOperation, ...]


def _operation_index() -> dict[str, ClientOperation]:
    indexed = {
        reference_name: operation
        for operation in operations()
        for reference_name in operation.reference_tool_names
    }
    transfer = next(
        operation
        for operation in operations()
        if operation.operation_id == "createConversationTransfer"
    )
    indexed.update({name: transfer for name in _SPECIAL_TRANSFER_REFERENCES})
    return indexed


def _schema_type(schema: dict[str, Any]) -> str:
    if "type" in schema:
        value = schema["type"]
        return "/".join(value) if isinstance(value, list) else str(value)
    variants = schema.get("anyOf") or schema.get("oneOf") or []
    names = [_schema_type(item) for item in variants if item.get("type") != "null"]
    return "/".join(dict.fromkeys(names)) or "value"


def _model_fields(model: Any) -> list[str]:
    if not isinstance(model, type) or not issubclass(model, BaseModel):
        return []
    schema = model.model_json_schema()
    required = set(schema.get("required", []))
    return [
        f"`{name}` ({_schema_type(field)}, "
        f"{'required' if name in required else 'optional'})"
        for name, field in schema.get("properties", {}).items()
    ]


def _response_description(operation: ClientOperation) -> str:
    response_type = operation.response_type
    if response_type is str:
        shape = "JSON string containing the operation result"
    elif isinstance(response_type, type) and issubclass(response_type, BaseModel):
        fields = ", ".join(_model_fields(response_type))
        shape = f"JSON object ({fields})" if fields else "JSON object"
    elif get_origin(response_type) is list:
        item_type = get_args(response_type)[0]
        fields = ", ".join(_model_fields(item_type))
        shape = f"JSON array of objects ({fields})" if fields else "JSON array"
    else:
        shape = "JSON value matching the documented response schema"
    return f"`{operation.success_status}` with a {shape}."


def _operation_contract(operation: ClientOperation) -> str:
    path_parameters = re.findall(r"{([^{}]+)}", operation.path)
    request_parts = []
    if path_parameters:
        request_parts.append(
            "Path parameters: "
            + ", ".join(f"`{name}` (string, required)" for name in path_parameters)
            + "."
        )
    query_fields = _model_fields(operation.query_type)
    if query_fields:
        request_parts.append("Query parameters: " + ", ".join(query_fields) + ".")
    body_fields = _model_fields(operation.body_type)
    if body_fields:
        request_parts.append("Request body: " + ", ".join(body_fields) + ".")
    elif operation.body_type is not None:
        request_parts.append("Request body: JSON value matching the documented schema.")
    if not request_parts:
        request_parts.append("Request body: none.")
    retry = (
        "Do not retry automatically."
        if operation.automatic_retries == "forbidden"
        else "Automatic retries are allowed."
    )
    return "\n".join(
        [
            "### API operation",
            "",
            f"`{operation.method} {operation.path}`",
            "",
            f"Purpose: {operation.description}",
            "",
            *request_parts,
            "",
            f"Response: {_response_description(operation)}",
            "",
            (
                "Errors: `400` invalid request schema; `404` resource not found; "
                "`405` method not allowed; `409` resource-state conflict; `413` "
                "request too large; `422` business-rule rejection; `502` invalid "
                "or oversized upstream response. "
                f"{retry}"
            ),
        ]
    )


def _rewrite_sop_sections(text: str) -> str:
    if "# Rho-Bank — Customer Service Agent Handbook" not in text:
        return text

    replacements = {
        "4": """## 4. Knowledge-discovered API operations

The initial OpenAPI document lists the operations available before procedural
research. Some specialized operations are intentionally documented only in the
relevant knowledge-base material. Once a retrieved procedure supplies an HTTP
method, resource path, request fields, response shape, and errors, call that
API operation directly; there is no separate unlock or wrapper request.

Customer self-service actions are different: when a procedure instructs the
customer to complete a documented action in their own app, make it available
through `POST /v1/customer-self-service-actions` and explain how to use it.
Only expose an action that the applicable procedure actually requires.
""",
        "5": """## 5. What the REST API tracks

The REST API exposes customer profiles, accounts, cards, transactions,
applications, disputes, referrals, verification records, and related workflow
resources. Treat the documented request and response schemas as authoritative.
Do not invent fields or resources that are absent from those contracts.
""",
        "6": """## 6. Working within the documented API schemas

Send only documented path, query, and JSON-body fields. Handle the documented
HTTP errors explicitly, especially validation failures and resource-state
conflicts. If a request requires an unsupported field or operation, treat it as
outside the standard process and offer a human transfer.
""",
    }
    for section, replacement in replacements.items():
        next_section = int(section) + 1
        text = re.sub(
            rf"## {section}\.[\s\S]*?(?=\n## {next_section}\.)",
            replacement.rstrip(),
            text,
            count=1,
        )
    text = text.replace(
        "Operational specifics — eligibility, step-by-step procedures, fee "
        "amounts, tool names, edge cases — are not in this handbook.",
        "Operational specifics — eligibility, step-by-step procedures, fee "
        "amounts, API operations, and edge cases — are not in this handbook.",
    )
    text = re.sub(
        r"Documents reference the tools to use by name[^\n]*",
        (
            "Documents that authorize specialized operations include the direct "
            "HTTP method, resource path, request fields, response shape, and errors."
        ),
        text,
    )
    text = re.sub(
        r"\nThe platform wrapper functions in Section 4[\s\S]*?(?=\n---\n\n## 8\.)",
        (
            "\nThe initial API contract ships with these materials. Retrieved "
            "procedures extend that documented surface with directly callable "
            "operations; the retrieval architecture remains your choice.\n"
        ),
        text,
        count=1,
    )
    return text


def _replace_operation_references(
    text: str,
) -> tuple[str, tuple[ClientOperation, ...]]:
    referenced = []
    for name, operation in sorted(
        _operation_index().items(), key=lambda item: len(item[0]), reverse=True
    ):
        if name not in text:
            continue
        text = text.replace(name, f"{operation.method} {operation.path}")
        if operation not in referenced:
            referenced.append(operation)
    self_service = next(
        operation
        for operation in operations()
        if operation.operation_id == "offerCustomerSelfServiceAction"
    )
    for action_name in sorted(_SELF_SERVICE_ACTIONS, key=len, reverse=True):
        if action_name not in text:
            continue
        text = text.replace(action_name, f"action_name={action_name}")
        if self_service not in referenced:
            referenced.append(self_service)
    for wrapper, replacement in _WRAPPER_REPLACEMENTS.items():
        text = text.replace(wrapper, replacement)
    text = text.replace("Tool unlocked.", "Operation documentation reviewed.")
    text = text.replace("tool unlocked.", "operation documentation reviewed.")
    text = text.replace("Tool remains locked", "Operation was not called")
    text = text.replace("tool remains locked", "operation was not called")
    text = re.sub(r"\b[Dd]iscoverable[- ]tool wrapper\b", "REST API", text)
    text = re.sub(r"\b[Aa]gent discoverable tools?\b", "API operations", text)
    text = re.sub(r"\b[Dd]iscoverable tools?\b", "documented operations", text)
    text = re.sub(r"\b[Tt]ool [Aa]rguments\b", "Request fields", text)
    text = re.sub(r"\btool_name\b", "operation", text)
    text = re.sub(r"\barguments_json\b", "request_body", text)
    text = re.sub(r"\bTools\b", "Operations", text)
    text = re.sub(r"\btools\b", "operations", text)
    text = re.sub(r"\bTool\b", "Operation", text)
    text = re.sub(r"\btool\b", "operation", text)
    text = re.sub(r"\bDatabase\b", "Core system", text)
    text = re.sub(r"\bdatabase\b", "core system", text)
    text = re.sub(
        r"\bdiscoverable wrapper\b",
        "direct API documentation",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bunlock (?=(?:GET|POST|PUT|PATCH|DELETE) /v1/)",
        "review the contract for ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?:operation|action) (?:was |would )?not unlocked or called\b",
        "request was not sent",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?:operation|action) unlocked for this session\b",
        "operation contract reviewed for this request",
        text,
        flags=re.IGNORECASE,
    )
    text = text.replace(
        "requires a session unlock before it can be called",
        "requires a complete validated request",
    )
    text = text.replace(
        "Stale tabs lose the unlock along with the session.",
        "Stale request drafts must be rebuilt from the current contract.",
    )
    text = text.replace(
        "A cold call without the unlock returns a locked error, never a transfer.",
        "An incomplete request returns a validation error, never a transfer.",
    )
    text = text.replace(
        "The unlock is per-session, not per-agent.",
        "No separate unlock state is required.",
    )
    text = text.replace(
        "Unlock precedes invocation within the same session.",
        "Contract review precedes request construction.",
    )
    return text, tuple(referenced)


def _append_contracts(text: str, referenced: Iterable[ClientOperation]) -> str:
    referenced = tuple(referenced)
    if not referenced:
        return text
    contracts = "\n\n---\n\n".join(_operation_contract(op) for op in referenced)
    return (
        text.rstrip() + "\n\n---\n\n## Referenced API contracts\n\n" + contracts + "\n"
    )


def rewrite_banking_client_api_text(text: str) -> str:
    """Return Developer-visible Banking prose using direct HTTP operations."""

    text = _rewrite_sop_sections(text)
    text, referenced = _replace_operation_references(text)
    return _append_contracts(text, referenced)


def _rewrite_json_value(value: Any) -> tuple[Any, tuple[ClientOperation, ...]]:
    if isinstance(value, str):
        rewritten, referenced = _replace_operation_references(value)
        return rewritten, referenced
    if isinstance(value, list):
        result = []
        referenced = []
        for item in value:
            rewritten, item_references = _rewrite_json_value(item)
            result.append(rewritten)
            referenced.extend(item_references)
        return result, tuple(dict.fromkeys(referenced))
    if isinstance(value, dict):
        result = {}
        referenced = []
        for key, item in value.items():
            rewritten_key, key_references = _replace_operation_references(str(key))
            rewritten, item_references = _rewrite_json_value(item)
            result[rewritten_key] = rewritten
            referenced.extend(key_references)
            referenced.extend(item_references)
        return result, tuple(dict.fromkeys(referenced))
    return value, ()


def _rewrite_email(content: bytes) -> RewrittenDocument:
    message = BytesParser(policy=policy.default).parsebytes(content)
    referenced = []
    parts = message.walk() if message.is_multipart() else (message,)
    for part in parts:
        if part.get_content_maintype() != "text":
            continue
        text = part.get_content()
        rewritten = rewrite_banking_client_api_text(text)
        _, part_references = _replace_operation_references(text)
        referenced.extend(part_references)
        if rewritten == text:
            continue
        subtype = part.get_content_subtype()
        charset = part.get_content_charset() or "utf-8"
        transfer_encoding = part.get("Content-Transfer-Encoding", "").lower()
        cte = (
            transfer_encoding
            if transfer_encoding in {"7bit", "8bit", "base64", "quoted-printable"}
            else None
        )
        del part["Content-Transfer-Encoding"]
        del part["Content-Type"]
        del part["MIME-Version"]
        part.set_content(rewritten, subtype=subtype, charset=charset, cte=cte)

    output = BytesIO()
    BytesGenerator(output, policy=policy.SMTP).flatten(message)
    return RewrittenDocument(output.getvalue(), tuple(dict.fromkeys(referenced)))


def rewrite_banking_client_api_document(
    content: bytes, suffix: str
) -> RewrittenDocument:
    """Rewrite one text-capable Banking document while preserving its format."""

    normalized_suffix = suffix.lower()
    if normalized_suffix == ".json":
        payload = json.loads(content.decode())
        payload, referenced = _rewrite_json_value(payload)
        if referenced and isinstance(payload, dict):
            if isinstance(payload.get("content"), str):
                payload["content"] = _append_contracts(payload["content"], referenced)
            else:
                payload["client_api_operations"] = [
                    {
                        "heading": "API operation",
                        "method": operation.method,
                        "path": operation.path,
                        "description": operation.description,
                        "contract": _operation_contract(operation),
                    }
                    for operation in referenced
                ]
        return RewrittenDocument(
            content=(json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode(),
            operations=referenced,
        )
    if normalized_suffix == ".eml":
        return _rewrite_email(content)
    if normalized_suffix in _TEXT_SUFFIXES:
        text = content.decode(errors="replace")
        rewritten = rewrite_banking_client_api_text(text)
        _, referenced = _replace_operation_references(text)
        return RewrittenDocument(rewritten.encode(), referenced)
    return RewrittenDocument(content, ())


def rewrite_banking_client_api_file(path: Path) -> tuple[ClientOperation, ...]:
    """Rewrite a copied kit document in place and return referenced operations."""

    original = path.read_bytes()
    rewritten = rewrite_banking_client_api_document(original, path.suffix)
    if rewritten.content != original:
        path.write_bytes(rewritten.content)
    return rewritten.operations
