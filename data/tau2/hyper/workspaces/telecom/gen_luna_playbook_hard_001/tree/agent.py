"""Playbook-driven telecom customer-care agent."""

from typing import Any, Dict, List, Tuple

from tau2.data_model.message import AssistantMessage, MultiToolMessage, UserMessage
from tau2.hyper.agent_context import get_agent_context


PLAYBOOKS: Dict[str, Dict[str, Any]] = {
    "identify_customer": {
        "intent": "customer identification and line access",
        "steps": [
            {"name": "collect_supported_identifier", "tools": ["search_customers"]},
            {"name": "confirm_account_identity", "tools": ["get_customer"]},
            {"name": "select_target_line", "tools": ["get_line"]},
        ],
        "checks": [
            "Do not guess verification values.",
            "Name lookup requires full name and date of birth.",
            "Do not use postal code as a fallback.",
        ],
    },
    "billing_and_suspension": {
        "intent": "overdue bills, suspended lines, and billing questions",
        "steps": [
            {"name": "verify_customer_and_line", "tools": ["search_customers", "get_line"]},
            {"name": "inspect_billing_state", "tools": ["get_bill", "list_line_bills"]},
        ],
        "checks": [
            "Explain the current bill and line state before any mutation.",
            "Do not promise unsupported restoration or waive a balance.",
        ],
    },
    "data_refuel": {
        "intent": "assisted data refueling",
        "steps": [
            {"name": "verify_line", "tools": ["search_customers", "get_line"]},
            {"name": "check_allowance_and_history", "tools": ["get_line_usage", "list_refuels"]},
            {"name": "quote_requested_amount", "tools": ["create_refuel_quote"]},
            {"name": "confirm_amount_and_price", "tools": []},
            {"name": "purchase_only_after_confirmation", "tools": ["purchase_refuel"]},
        ],
        "checks": [
            "Respect the current-cycle refuel limit.",
            "Splitting a request does not bypass the limit.",
            "A quote is not a purchase.",
            "Never purchase without explicit confirmation of amount and price.",
        ],
    },
    "plan_change": {
        "intent": "assisted monthly plan changes",
        "steps": [
            {"name": "verify_line", "tools": ["search_customers", "get_line"]},
            {"name": "load_eligible_plans", "tools": ["list_available_plans"]},
            {"name": "present_information_or_quote", "tools": ["create_plan_quote"]},
            {"name": "confirm_selected_plan_and_price", "tools": []},
            {"name": "apply_change_after_confirmation", "tools": ["change_plan"]},
        ],
        "checks": [
            "Separate a plan change from a device move or travel offer.",
            "Keep information-only requests mutation-free.",
            "Confirmation must name the selected plan and calculated new monthly price.",
        ],
    },
    "roaming_recovery": {
        "intent": "restore mobile data abroad",
        "steps": [
            {"name": "verify_line", "tools": ["search_customers", "get_line"]},
            {"name": "inspect_roaming_state", "tools": ["get_roaming_status"]},
            {"name": "restore_supported_roaming", "tools": ["restore_roaming"]},
            {"name": "verify_result", "tools": ["get_roaming_status"]},
        ],
        "checks": [
            "Distinguish roaming from ordinary domestic data troubleshooting.",
            "Do not claim success until the resulting state is checked.",
        ],
    },
    "cellular_recovery": {
        "intent": "cellular service recovery",
        "steps": [
            {"name": "verify_line_and_service", "tools": ["search_customers", "get_line", "get_service_status"]},
            {"name": "follow_supported_device_checks", "tools": ["get_device"]},
            {"name": "record_successful_recovery", "tools": ["record_service_recovery"]},
        ],
        "checks": [
            "Follow the supported diagnostic sequence.",
            "Do not treat an unsuccessful detour as a successful resolution.",
            "Escalate when the supported sequence cannot resolve the issue.",
        ],
    },
    "mobile_data_guidance": {
        "intent": "unavailable or slow mobile data",
        "steps": [
            {"name": "verify_line", "tools": ["search_customers", "get_line"]},
            {"name": "check_usage_and_service_state", "tools": ["get_line_usage", "get_service_status"]},
            {"name": "apply_relevant_guidance", "tools": ["get_device"]},
        ],
        "checks": [
            "Separate signal indication from usable data.",
            "Check allowance before proposing a refuel.",
            "Do not use an early handoff shortcut.",
        ],
    },
    "mms_guidance": {
        "intent": "MMS picture messaging",
        "steps": [
            {"name": "verify_line", "tools": ["search_customers", "get_line"]},
            {"name": "check_service_and_device", "tools": ["get_service_status", "get_device"]},
            {"name": "follow_supported_messaging_checks", "tools": []},
        ],
        "checks": [
            "Treat MMS configuration separately from general mobile data.",
            "Use only supported device checks.",
        ],
    },
}


SYSTEM_GUIDANCE = """You are Northline Care's telecom customer-support agent.

Follow the applicable playbook. Identify the customer before discussing or changing
an account. Phone lookup is permitted. Name lookup requires full name and date of
birth; never ask a customer to guess and never use postal code as a fallback.

Keep information-only requests mutation-free. Distinguish data refuels, monthly
plan changes, device moves, and travel offers. Before purchasing a refuel, inspect
usage and refuel history, create a quote, and obtain explicit confirmation of the
amount and price. Splitting requests cannot bypass a cycle limit. Before changing
a plan, load eligible plans, quote the selected plan, and obtain confirmation that
names both the plan and calculated new monthly price. Never claim that a quote
changed the account.

For technical issues, inspect line and relevant service/device state before advice.
Distinguish signal from usable data, follow supported recovery checks, verify
successful outcomes, and transfer when the supported path cannot resolve the issue.
Be concise, transparent, and customer-friendly. Do not expose internal playbook
names or policy sources.
"""


def _catalog_text(actions: Tuple[Any, ...]) -> str:
    result: List[str] = []
    for action in actions:
        name = getattr(action, "name", None)
        description = getattr(action, "description", None)
        if name:
            result.append(f"- {name}: {description or ''}")
    return "\n".join(result)


def create_agent():
    context = get_agent_context()
    actions = tuple(context.action_interface.available)
    models = tuple(context.model_gateway.models)
    if not models:
        raise RuntimeError("No model is available for the telecom agent.")
    model_name = models[0].model
    playbook_text = "\n".join(
        f"{name}: {plan}" for name, plan in PLAYBOOKS.items()
    )
    action_text = _catalog_text(actions)

    class TelecomAgent:
        def __init__(self) -> None:
            self.playbooks = PLAYBOOKS
            self._stopped = False

        def get_init_state(self, message_history=None):
            return {
                "messages": list(message_history or []),
                "turns": 0,
            }

        def generate_next_message(self, message, state):
            if self._stopped:
                return AssistantMessage(
                    role="assistant",
                    content="This conversation has ended. Please start a new conversation if you still need help.",
                ), state

            next_state = dict(state)
            messages = list(next_state.get("messages", []))
            messages.append(message)
            next_state["messages"] = messages
            next_state["turns"] = int(next_state.get("turns", 0)) + 1

            prompt = list(messages)
            prompt.insert(
                0,
                UserMessage(
                    role="user",
                    content=(
                        SYSTEM_GUIDANCE
                        + "\n\nInspectable playbooks:\n"
                        + playbook_text
                        + "\n\nAvailable actions:\n"
                        + action_text
                    ),
                ),
            )
            response = context.model_gateway.generate(
                model=model_name,
                messages=prompt,
                actions=actions,
                tool_choice="auto",
            )
            next_state["messages"].append(response)
            return response, next_state

        def is_stop(self, message) -> bool:
            content = getattr(message, "content", "")
            text = content if isinstance(content, str) else str(content)
            lowered = text.lower()
            return any(
                phrase in lowered
                for phrase in (
                    "conversation has ended",
                    "no further assistance",
                )
            )

        def stop(self) -> None:
            self._stopped = True

        def set_seed(self, seed: int) -> None:
            return None

    return TelecomAgent()
