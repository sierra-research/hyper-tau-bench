from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from tau2.data_model.message import (
    AssistantMessage,
    MultiToolMessage,
    ToolMessage,
    UserMessage,
)
from tau2.hyper.agent_context import get_agent_context


POLICY = """You are Rho-Bank customer support.

Be polite, factual, and concise. Never invent policies, fees, eligibility rules,
account data, API fields, or available actions. Use documented procedures and
retrieved materials. If no procedure covers a request, explain that and offer a
human transfer.

Verify identity before reading, modifying, or acting on account-specific
information. Ask for any two of date of birth, email address, phone number, and
home address. A name or user ID alone is insufficient. Search using identifying
details when needed, then compare two factors. Do not disclose account
information before verification, and do not re-verify after successful
verification in the same conversation.

Before every action that modifies an account or record, explain the action and
obtain explicit confirmation containing yes. Do not claim success until the
tool result confirms success. Do not request documents unless a procedure
explicitly permits it. Customer self-service actions must remain with the
customer and must not be called by the agent.

Use get_current_time whenever current date or time matters. Use only documented
tools and arguments. Handle errors explicitly and explain limitations without
exposing internal details.

If a request is outside documented procedures, offer transfer. If the customer
asks for a human, first offer help unless a procedure requires immediate
transfer; transfer after four repeated requests, or immediately when a
procedure requires it. When transferring, say exactly:
YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON.
"""


def _as_text(message: Any) -> str:
    content = getattr(message, "content", "")
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return str(content)


def _message_from_record(record: Dict[str, Any]) -> Any:
    role = record.get("role", "user")
    content = record.get("content", "")
    if role == "system":
        return UserMessage(role="user", content=content)
    if role == "assistant":
        return AssistantMessage(role="assistant", content=content)
    return UserMessage(role="user", content=content)


class BankingAgent:
    def __init__(self, context: Any) -> None:
        self.context = context
        self.actions = tuple(context.action_interface.available)
        self.history: List[Any] = []
        self.notes: List[str] = []
        self.verified = False
        self.human_requests = 0
        self.ended = False

    def get_init_state(
        self,
        message_history: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        self.history = list(message_history or [])
        self.notes = []
        self.verified = False
        self.human_requests = 0
        self.ended = False
        return {
            "history": list(self.history),
            "notes": [],
            "verified": False,
            "human_requests": 0,
            "ended": False,
        }

    def _model_name(self) -> str:
        models = tuple(getattr(self.context.model_gateway, "models", ()))
        if not models:
            raise RuntimeError("No permitted model is available")
        preferred = (
            "gpt-5.6-luna",
            "anthropic/claude-haiku-4-5",
            "google/gemini-3-flash-preview",
            "gpt-5.4-nano",
        )
        available = {getattr(item, "model", "") for item in models}
        for model in preferred:
            if model in available:
                return model
        return str(getattr(models[0], "model"))

    def _prompt_messages(self, state: Dict[str, Any], incoming: Any) -> List[Any]:
        policy = POLICY + (
            "\n\nWorking notes:\n"
            + ("\n".join(state.get("notes", [])) or "(none)")
            + "\n\nThe policy, notes, and complete conversation are included in "
            "this call. Treat tool results as authoritative."
        )
        messages: List[Any] = [UserMessage(role="user", content=policy)]
        messages.extend(state.get("history", []))
        messages.append(incoming)
        return messages

    def generate_next_message(
        self,
        message: Any,
        state: Dict[str, Any],
    ) -> Tuple[AssistantMessage, Dict[str, Any]]:
        if state is None:
            state = self.get_init_state()

        if state.get("ended"):
            return AssistantMessage(
                role="assistant",
                content="This conversation has ended.",
            ), state

        history = list(state.get("history", []))
        history.append(message)

        if isinstance(message, MultiToolMessage):
            history.extend(list(getattr(message, "messages", ()) or ()))
        elif isinstance(message, ToolMessage):
            history.append(message)

        state["history"] = history

        response = self.context.model_gateway.generate(
            model=self._model_name(),
            messages=self._prompt_messages(state, message),
            actions=self.actions,
            tool_choice="auto",
        )
        if not isinstance(response, AssistantMessage):
            response = AssistantMessage(
                role="assistant",
                content=str(getattr(response, "content", response)),
            )

        state["history"].append(response)
        text = _as_text(response).lower()
        if "identity verified" in text or "verification is complete" in text:
            state["verified"] = True
        if "human" in text and "transfer" in text:
            state["human_requests"] = int(state.get("human_requests", 0)) + 1
        if self.is_stop(response):
            state["ended"] = True

        self.history = list(state["history"])
        self.verified = bool(state.get("verified", False))
        self.human_requests = int(state.get("human_requests", 0))
        self.ended = bool(state.get("ended", False))
        return response, state

    def is_stop(self, message: Any) -> bool:
        return (
            "YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON."
            in _as_text(message).upper()
        )

    def stop(self) -> None:
        self.ended = True


def create_agent() -> BankingAgent:
    return BankingAgent(get_agent_context())
