"""Render host-only deployed-API facts as a distinct Client prompt overlay."""

from __future__ import annotations

from tau2.hyper.client_api.defects import DefectProfile

_BASE_PROMPT = """You are the business stakeholder who hired the Developer to build a
customer-service agent against your company's Client API. Be cooperative and
concise. In your opening message, ask the Developer to build a reliable agent
from the supplied operational materials and API documentation. Do not mention
any deployment mismatch in your opening message.
"""


def render_api_defect_client_overlay(profile: DefectProfile) -> str:
    """Render evidence-gated deployment knowledge for the Client simulator.

    This text is used only as a host-side system-prompt overlay. It must never
    be copied into the Developer kit or opening brief verbatim.
    """

    facts = profile.client
    if facts is None and not profile.capabilities:
        return ""

    sampled_defect_ids = {
        defect.id
        for defect in profile.defects
        if defect.activation.developer_test is not None
    }
    rendered_facts = []
    for fact in facts.defects if facts is not None else ():
        conditions = "\n".join(
            f"    - {condition}" for condition in fact.disclosure_conditions
        )
        deployability = "yes" if fact.client_can_deploy_fix else "no"
        cohort_scope = (
            "  Developer-test scope: cohort-specific. A Developer-authored "
            "scenario is deterministically routed to a cohort where this "
            "behavior may be inactive. Never describe it as active for the "
            "Developer's scenario without matching observed evidence.\n"
            if fact.defect_id in sampled_defect_ids
            else ""
        )
        rendered_facts.append(
            f"- Defect {fact.defect_id!r}\n"
            f"{cohort_scope}"
            f"  Actual behavior: {fact.actual_behavior}\n"
            f"  Disclosure conditions:\n{conditions}\n"
            f"  Expected Developer remediation: {fact.expected_remediation}\n"
            f"  Can the Client deploy a fix: {deployability}"
        )

    rendered_capabilities = []
    for capability in profile.capabilities:
        rendered_capabilities.append(
            f"- Capability {capability.id!r}\n"
            f"  Missing functionality: {capability.missing_functionality}\n"
            "  Do not volunteer this capability. If the Developer clearly "
            "identifies that this functionality is missing from the supplied "
            "API, call `respond_about_deployable_capability` with action "
            "`offer`. Judge functional meaning, not keywords: the Developer "
            "does not need an operation name, status code, or exact wording. "
            "A vague claim that something is missing or broken is insufficient.\n"
            "  After offering it, call the same tool with action `enable` only "
            "if the Developer accepts the offer or explicitly asks you to "
            "deploy that functionality. Never enable it in the offer turn. "
            "For every other response, call the tool with action `respond` and "
            "a null capability ID."
        )
    capability_section = (
        "\n\n## Deployable API capabilities (private Client knowledge)\n\n"
        + "\n".join(rendered_capabilities)
        if rendered_capabilities
        else ""
    )
    defect_section = ""
    if facts is not None:
        defect_section = (
            "\n## API deployment facts (private Client knowledge)\n\n"
            f"Published API version: {facts.published_api_version}\n"
            f"Deployed API version: {facts.deployed_api_version}\n\n"
            + "\n\n".join(rendered_facts)
        )
    return (
        f"{_BASE_PROMPT}"
        + defect_section
        + capability_section
        + "\n\n## Disclosure rules\n\n"
        "- Do not volunteer any API defect, stale-documentation fact, actual "
        "behavior, or remediation.\n"
        "- Confirm or explain one defect only after the Developer supplies "
        "grounded observations satisfying that defect's disclosure conditions. "
        "Discuss only the matching defect.\n"
        "- For a cohort-specific defect, matching observed evidence is also "
        "required before treating it as active in the Developer's scenario. "
        "Do not enumerate other possible cohort behaviors.\n"
        "- The Developer can succeed by diagnosing and accommodating observable "
        "API behavior. Client confirmation is helpful, never required.\n"
        "- Do not imply that you can deploy a fix when the corresponding flag "
        "says no.\n\n"
        "VAGUE REPORT RESPONSE\n"
        "If the Developer merely asks whether the API is broken, respond in this "
        "general form: “I'm not sure, but it's possible. Can you be more specific "
        "about what you're seeing?” Do not coach them with a checklist or examples.\n"
    )
