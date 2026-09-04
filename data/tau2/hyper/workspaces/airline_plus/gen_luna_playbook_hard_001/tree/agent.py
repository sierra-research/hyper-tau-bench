from dataclasses import dataclass, field
from typing import Any, List

from tau2.data_model.message import AssistantMessage, MultiToolMessage, UserMessage
from tau2.hyper.agent_context import get_agent_context


PLAYBOOKS = {
    "new_booking": {
        "steps": [
            "Clarify origin, destination, dates, trip type, travelers, cabin, and airport.",
            "Verify the customer profile before searching.",
            "Search only after the itinerary is unambiguous.",
            "Never purchase or select without explicit instruction.",
        ],
        "tools": ["get_customer", "search_flights"],
    },
    "reservation_information": {
        "steps": [
            "Verify the customer or reservation.",
            "Retrieve the current reservation.",
            "Answer from the record without modifying it.",
        ],
        "tools": ["get_customer", "get_reservation", "get_flight_status"],
    },
    "flight_change": {
        "steps": [
            "Retrieve the reservation.",
            "Confirm eligible unchanged itinerary constraints.",
            "Identify the replacement flight and date.",
            "Price the change.",
            "Require explicit confirmation before submission.",
        ],
        "tools": [
            "get_reservation",
            "search_flights",
            "price_reservation_change",
            "change_reservation_flight",
        ],
    },
    "cancellation": {
        "steps": [
            "Retrieve the reservation.",
            "Explain the consequence.",
            "Require explicit confirmation.",
            "Cancel once and report the result.",
        ],
        "tools": ["get_reservation", "cancel_reservation"],
    },
    "check_in": {
        "steps": [
            "Retrieve the reservation.",
            "Confirm eligibility.",
            "Check in only at the customer's request.",
            "Provide boarding-pass information.",
        ],
        "tools": ["get_customer", "get_reservation", "check_in"],
    },
    "disruption_status": {
        "steps": [
            "Verify the reservation.",
            "Identify the exact flight and date.",
            "Check current status.",
            "Explain the result from the record.",
        ],
        "tools": ["get_customer", "get_reservation", "get_flight_status"],
    },
    "disruption_compensation": {
        "steps": [
            "Verify the account and affected flight.",
            "Confirm disruption and reservation details.",
            "Review eligibility.",
            "Communicate the actual result.",
        ],
        "tools": [
            "get_customer",
            "get_reservation",
            "get_flight_status",
            "review_compensation",
        ],
    },
    "service_feedback": {
        "steps": [
            "Verify the customer and identify the flight.",
            "Separate feedback from compensation or changes.",
            "Record the feedback accurately.",
            "Confirm that no unrelated workflow was opened.",
        ],
        "tools": ["get_customer", "get_reservation", "add_feedback"],
    },
    "specialist_transfer": {
        "steps": [
            "Explain the specialist limitation.",
            "Summarize relevant facts.",
            "Transfer only after customer agreement.",
            "Do not claim unavailable work was completed.",
        ],
        "tools": ["transfer_to_human_agents"],
    },
    "payment_or_receipt": {
        "steps": [
            "Review supported payment information.",
            "Explain limits and balances.",
            "Do not invent receipt or payment capabilities.",
            "Transfer unsupported requests.",
        ],
        "tools": ["get_customer", "get_reservation", "transfer_to_human_agents"],
    },
    "baggage_or_accessibility": {
        "steps": [
            "Verify the customer and affected trip.",
            "Clarify the passenger and issue.",
            "Transfer to the specialist queue.",
        ],
        "tools": ["get_customer", "get_reservation", "transfer_to_human_agents"],
    },
    "unclear_request": {
        "steps": [
            "Ask one focused clarification question.",
            "Do not act until intent and identifiers are clear.",
        ],
        "tools": [],
    },
}


SYSTEM_INSTRUCTIONS = """You are Meridian Airlines customer support.

Follow the selected playbook in order. Use only the available tools. Never invent records, prices, statuses, policies, identifiers, or completed actions.

Clarify ambiguity before acting. Distinguish calendar dates, airports, origin and destination, trip type, and the customer's own flight from other people's information. Ignore side conversations, echoes, and accidental words. Do not treat vague speech as authorization when it may be directed to someone else.

Searches and previews do not modify reservations. Never perform a consequential write without clear, current customer authorization. For changes and cancellations, explain the exact action and obtain explicit confirmation immediately before submission.

Protect sensitive information. Never request passwords, full payment numbers, full certificate numbers, or unnecessary personal data. A third party cannot access another customer's account merely by knowing its identifier.

If a request is outside the available tools or requires a specialist, explain that plainly and offer transfer. Do not claim to generate receipts, handle loyalty ledgers, process baggage claims, or resolve accessibility workflows unless confirmed by a tool result. Be concise, patient, and conversational."""


@dataclass
class AgentState:
    messages: List[Any] = field(default_factory=list)
    intent: str = "unclear_request"
    stopped: bool = False


def _content(message: Any) -> str:
    value = getattr(message, "content", "")
    return value if isinstance(value, str) else str(value or "")


def _infer_intent(text: str) -> str:
    value = text.lower()
    if any(x in value for x in ("mileage", "miles", "points", "loyalty")):
        return "specialist_transfer"
    if any(x in value for x in ("itemized receipt", "receipt")):
        return "payment_or_receipt"
    if any(x in value for x in ("damaged bag", "baggage claim", "wheelchair", "accessibility")):
        return "baggage_or_accessibility"
    if any(x in value for x in ("cancel", "cancellation")):
        return "cancellation"
    if any(x in value for x in ("check in", "check-in", "boarding pass")):
        return "check_in"
    if any(x in value for x in ("compensation", "reimbursement")):
        return "disruption_compensation"
    if any(x in value for x in ("feedback", "complaint", "report")):
        return "service_feedback"
    if any(x in value for x in ("change", "move", "switch", "reschedule", "rebook")):
        return "flight_change"
    if any(x in value for x in ("status", "cancelled", "canceled", "gate", "delayed")):
        return "disruption_status"
    if any(x in value for x in ("charge", "payment", "card", "certificate", "gift card")):
        return "payment_or_receipt"
    if any(x in value for x in ("reservation", "confirmation")):
        return "reservation_information"
    if any(x in value for x in ("book", "booking", "search", "flight", "fly", "trip")):
        return "new_booking"
    return "unclear_request"


class AirlineAgent:
    def __init__(self, context: Any) -> None:
        self.context = context
        self.gateway = context.model_gateway
        self.actions = tuple(context.action_interface.available)
        self.playbooks = PLAYBOOKS
        self.stopped = False
        self.model_name, self.model_options = self._choose_model()

    def _choose_model(self):
        preferred = (
            "gpt-4.1-mini",
            "qwen/qwen3-30b-a3b-instruct-2507",
            "gpt-5.4-nano",
        )
        configurations = tuple(self.gateway.models)
        selected = None
        for name in preferred:
            selected = next(
                (item for item in configurations if item.model == name),
                None,
            )
            if selected is not None:
                break
        if selected is None:
            if not configurations:
                raise RuntimeError("No allowed model is available.")
            selected = configurations[0]
        options = {}
        constraints = getattr(selected, "constraints", {})
        for key, value in constraints.items():
            if isinstance(value, dict) and value.get("one_of"):
                options[key] = value["one_of"][0]
        return selected.model, options

    def get_init_state(self, message_history=None):
        state = AgentState()
        for message in message_history or []:
            state.messages.append(message)
            if isinstance(message, UserMessage):
                state.intent = _infer_intent(_content(message))
        return state

    def _selected_actions(self, intent: str):
        names = set(self.playbooks[intent]["tools"])
        result = []
        for action in self.actions:
            action_name = getattr(action, "name", None)
            function_name = getattr(action, "function", None)
            if action_name in names or function_name in names:
                result.append(action)
        return tuple(result)

    def generate_next_message(self, message, state):
        if state is None:
            state = self.get_init_state()
        if state.stopped:
            return AssistantMessage(
                role="assistant",
                content="This conversation has ended. Please start a new conversation if you still need help.",
            ), state

        if isinstance(message, UserMessage):
            state.intent = _infer_intent(_content(message))
        state.messages.append(message)

        playbook = self.playbooks.get(
            state.intent,
            self.playbooks["unclear_request"],
        )
        instruction = (
            SYSTEM_INSTRUCTIONS
            + "\n\nSelected playbook: "
            + state.intent
            + "\n"
            + repr(playbook)
        )
        prompt = UserMessage(role="user", content=instruction)
        response = self.gateway.generate(
            model=self.model_name,
            messages=[prompt] + list(state.messages),
            actions=self._selected_actions(state.intent),
            tool_choice="auto",
            **self.model_options,
        )
        state.messages.append(response)
        return response, state

    def is_stop(self, message) -> bool:
        if not isinstance(message, AssistantMessage):
            return False
        text = _content(message).lower()
        return any(
            phrase in text
            for phrase in ("conversation has ended", "goodbye", "take care")
        )

    def stop(self) -> None:
        self.stopped = True

    def set_seed(self, seed: int) -> None:
        return None


def create_agent():
    return AirlineAgent(get_agent_context())
