from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from tau2.data_model.message import (
    AssistantMessage,
    MultiToolMessage,
    UserMessage,
)
from tau2.hyper.agent_context import get_agent_context


JOURNEYS: Dict[str, Tuple[str, ...]] = {
    "identity_and_information": (
        "Identify the request and determine whether account-specific information is involved.",
        "Verify identity with two matching factors before disclosure.",
        "Retrieve only the documented information needed.",
        "Explain the answer accurately without inventing policy.",
    ),
    "account_or_card_change": (
        "Identify the requested change and applicable procedure.",
        "Verify identity with two matching factors.",
        "Check eligibility, state, and prerequisites.",
        "Explain the proposed change and obtain explicit confirmation.",
        "Execute the documented operation.",
        "Report completion only after success.",
    ),
    "payment_or_transfer": (
        "Identify source, destination, and amount.",
        "Verify identity with two matching factors.",
        "Check ownership, balances, limits, and prerequisites.",
        "Explain the proposed payment and obtain authorization.",
        "Execute the documented operation.",
        "Report completion only after success.",
    ),
    "dispute": (
        "Identify the transaction and dispute reason.",
        "Verify identity with two matching factors.",
        "Check dispute and provisional-credit criteria.",
        "Explain eligibility and required customer steps.",
        "File only after any required confirmation.",
        "Report the recorded result without promising an outcome.",
    ),
    "human_transfer": (
        "Determine whether a documented self-service procedure applies.",
        "Attempt applicable assistance when policy requires it.",
        "Provide the exact transfer notice when transfer is warranted.",
        "Submit one non-retryable transfer request.",
        "End after successful transfer.",
    ),
}


SYSTEM_PROMPT = """You are Rho-Bank customer support. Be concise, polite, and accurate.

Rules:
- Never disclose account-specific information or act until identity is verified with
  two matching factors: date of birth, email, phone, or home address. A full name or
  user ID alone is insufficient.
- Before changing an account or record, explain the action and obtain explicit
  confirmation containing yes.
- Use only documented tools and procedures. Never invent fields, fees, limits,
  eligibility rules, dates, or outcomes.
- Use get_current_time when a current date or time is needed.
- Treat tool errors as unresolved and never claim success.
- Lost or stolen debit cards should be permanently closed rather than merely frozen.
- Bank-initiated fraud alerts require security-team review.
- Customer-owned actions remain customer-owned unless a procedure explicitly
  authorizes support to perform them.
- For unsupported requests, offer transfer. When transferring, say exactly:
  "YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON."
- Do not report a journey complete until its applicable checklist is exhausted.
"""


@dataclass
class AgentState:
    messages: List[Any] = field(default_factory=list)
    journey: Optional[str] = None
    checklist_index: int = 0
    checklist_notes: List[str] = field(default_factory=list)
    verified: bool = False
    transferred: bool = False
    stopped: bool = False


class BankingAgent:
    def __init__(self, context: Any) -> None:
        self.context = context
        self.actions = tuple(context.action_interface.available)
        self.model = self._select_model()

    def _select_model(self) -> str:
        models = tuple(getattr(self.context.model_gateway, "models", ()))
        if not models:
            raise RuntimeError("No allowed model is available.")
        preferred = (
            "anthropic/claude-haiku-4-5",
            "google/gemini-3-flash-preview",
            "google/gemma-4-31b-it",
        )
        for name in preferred:
            for configuration in models:
                if getattr(configuration, "model", None) == name:
                    return name
        return str(getattr(models[0], "model"))

    def get_init_state(self, message_history=None) -> AgentState:
        state = AgentState()
        if message_history:
            state.messages.extend(message_history)
        return state

    @staticmethod
    def _message_text(message: Any) -> str:
        content = getattr(message, "content", "")
        if content is None:
            return ""
        return content if isinstance(content, str) else str(content)

    @staticmethod
    def _classify_journey(text: str) -> str:
        value = text.lower()
        if any(
            term in value
            for term in ("human", "person", "representative", "transfer me")
        ):
            return "human_transfer"
        if any(
            term in value
            for term in ("dispute", "charge", "transaction", "fraud", "unauthorized")
        ):
            return "dispute"
        if any(
            term in value
            for term in ("pay", "payment", "transfer", "move money", "send money")
        ):
            return "payment_or_transfer"
        if any(
            term in value
            for term in (
                "close",
                "activate",
                "replace",
                "freeze",
                "unfreeze",
                "increase",
                "open",
                "order",
                "change",
            )
        ):
            return "account_or_card_change"
        return "identity_and_information"

    def _record_progress(self, state: AgentState, message: Any) -> None:
        text = self._message_text(message)
        if state.journey is None and text:
            state.journey = self._classify_journey(text)
        lower = text.lower()
        if any(
            marker in lower
            for marker in (
                "identity verified",
                "identity check is complete",
                "verification passed",
                "verified successfully",
            )
        ):
            state.verified = True
        if state.journey is not None:
            state.checklist_notes.append(text[:500])

    def _model_messages(self, state: AgentState) -> List[Any]:
        journey = state.journey or "identity_and_information"
        checklist = "\n".join(
            f"{index + 1}. {step}"
            for index, step in enumerate(JOURNEYS[journey])
        )
        messages: List[Any] = [
            UserMessage(role="user", content=SYSTEM_PROMPT),
            UserMessage(
                role="user",
                content=(
                    f"Identified journey: {journey}\n"
                    f"Checklist:\n{checklist}\n"
                    "Track each checklist item as completed, skipped with a reason, "
                    "or blocked pending customer information."
                ),
            ),
        ]
        messages.extend(state.messages)
        return messages

    def generate_next_message(
        self,
        message: Any,
        state: AgentState,
    ) -> Tuple[AssistantMessage, AgentState]:
        if state.stopped:
            return (
                AssistantMessage(
                    role="assistant",
                    content="This conversation has ended.",
                ),
                state,
            )

        state.messages.append(message)
        self._record_progress(state, message)

        if isinstance(message, MultiToolMessage):
            if state.journey is None:
                state.journey = "identity_and_information"
            state.checklist_index = min(
                state.checklist_index + 1,
                len(JOURNEYS[state.journey]),
            )

        response = self.context.model_gateway.generate(
            model=self.model,
            messages=self._model_messages(state),
            actions=self.actions,
            tool_choice="auto",
        )
        if not isinstance(response, AssistantMessage):
            response = AssistantMessage(
                role="assistant",
                content=str(getattr(response, "content", response)),
            )

        state.messages.append(response)
        response_text = self._message_text(response)
        if (
            "YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON."
            in response_text.upper()
        ):
            state.transferred = True
            state.stopped = True
        return response, state

    def is_stop(self, message: Any) -> bool:
        text = self._message_text(message).upper()
        return (
            "YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON."
            in text
            or "THIS CONVERSATION HAS ENDED" in text
        )

    def stop(self, message: Any = None, state: Any = None) -> None:
        if isinstance(state, AgentState):
            state.stopped = True

    def set_seed(self, seed: int) -> None:
        return None


def create_agent():
    return BankingAgent(get_agent_context())
