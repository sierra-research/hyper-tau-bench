from typing import Any, List, Optional

from tau2.data_model.message import AssistantMessage, UserMessage
from tau2.hyper.agent_context import get_agent_context


_POLICY = """You are Meridian Airlines customer support.
Be accurate, calm, concise, and transparent. Never invent information. Use
available tools for account, reservation, flight, pricing, and state changes.
Verify exact identifiers and resolve ambiguity before acting. Never guess dates,
airports, flights, names, passengers, or payment methods. Treat searches and
previews as noncommittal. Before any chargeable or irreversible action, state the
exact change, amount, and payment method and obtain explicit confirmation.
Do not treat background speech or ambiguous agreement as authorization. Do not
access another person's account without that person's verification. If a
request is outside the available tools, explain the limitation and transfer
when appropriate. Report actual tool results; never claim an unsuccessful
operation succeeded.
"""


class AirlineAgent:
    def __init__(self, context: Any) -> None:
        self.context = context
        self.model = self._choose_model()

    def _choose_model(self) -> str:
        models = getattr(self.context.model_gateway, "models", ())
        preferred = (
            "gpt-5.6-terra",
            "gpt-5.6-luna",
            "anthropic/claude-haiku-4-5",
            "google/gemini-3-flash-preview",
        )
        available = {getattr(item, "model", "") for item in models}
        for name in preferred:
            if name in available:
                return name
        return next(iter(available), "gpt-5.6-terra")

    def get_init_state(self, message_history: Optional[List[Any]] = None) -> dict:
        return {
            "history": list(message_history or []),
            "notes": "",
            "stopped": False,
        }

    def _build_messages(self, state: dict, message: Any) -> List[Any]:
        policy = _POLICY
        notes = state.get("notes", "")
        if notes:
            policy += "\nWorking notes:\n" + notes

        system_message = UserMessage(role="user", content=policy)
        history = list(state.get("history", []))
        history.append(message)
        return [system_message, *history]

    def generate_next_message(self, message: Any, state: dict):
        if state.get("stopped"):
            return (
                AssistantMessage(
                    role="assistant",
                    content="This conversation has ended. Please start a new conversation if you still need help.",
                ),
                state,
            )

        messages = self._build_messages(state, message)
        response = self.context.model_gateway.generate(
            model=self.model,
            messages=messages,
            actions=self.context.action_interface.available,
            tool_choice="auto",
        )

        history = list(state.get("history", []))
        history.extend((message, response))
        state["history"] = history

        content = getattr(response, "content", None)
        if content:
            state["notes"] = (state.get("notes", "") + "\n" + str(content))[-4000:]

        return response, state

    def is_stop(self, message: Any) -> bool:
        content = str(getattr(message, "content", "") or "").strip().lower()
        return content.endswith(
            ("goodbye", "bye", "take care", "have a good day")
        )

    def stop(self) -> None:
        return None


def create_agent():
    return AirlineAgent(get_agent_context())
