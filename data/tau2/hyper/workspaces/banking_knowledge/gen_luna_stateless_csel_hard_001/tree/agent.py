from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Tuple

from tau2.data_model.message import AssistantMessage, MultiToolMessage, UserMessage
from tau2.hyper.agent_context import get_agent_context


POLICY = """You are Rho-Bank customer support.
Verify identity with two matching factors before account-specific information or actions.
Never disclose account information before verification.
Before any state-changing operation, explain it and obtain an explicit yes confirmation.
Use documented procedures, API schemas, and supplied reference material only.
Do not invent fees, eligibility rules, products, fields, or operations.
Use the current-time tool whenever current date or time is needed.
Customer self-service actions must be performed by the customer.
If a request is outside documented scope, offer a human transfer. If a customer
asks for a human four times, transfer them. When transferring, state exactly:
YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON.
Treat tool errors as authoritative and do not claim an operation succeeded unless
the tool result confirms success."""


def message_text(message: Any) -> str:
    content = getattr(message, "content", "")
    if content is None:
        return ""
    return content if isinstance(content, str) else str(content)


@dataclass
class State:
    history: List[Any] = field(default_factory=list)
    verified: bool = False
    transfer_requests: int = 0
    stopped: bool = False


class BankingAgent:
    def __init__(self, context: Any) -> None:
        self.context = context
        self.gateway = context.model_gateway
        self.actions = tuple(context.action_interface.available)
        self.domain = context.runtime_config.get("domain", "banking_knowledge")
        self.reference = self._read_reference()

    def _read_reference(self) -> str:
        resources = getattr(self.context, "resources", None)
        if resources is None:
            return ""
        result: List[str] = []
        for path in tuple(getattr(resources, "files", ())):
            path_text = str(path).replace("\\", "/")
            if not (
                path_text.startswith("knowledge_base/")
                or path_text.startswith("uploaded_materials/")
            ):
                continue
            try:
                content = resources.read_text(path)
            except Exception:
                continue
            if content:
                result.append(f"\n--- {path_text} ---\n{content}")
        return "".join(result)[:120000]

    def get_init_state(self, message_history=None) -> State:
        state = State()
        if message_history:
            state.history.extend(message_history)
        return state

    def _model(self) -> str:
        models = tuple(getattr(self.gateway, "models", ()))
        if not models:
            raise RuntimeError("No allowed model is configured.")
        return str(models[0].model)

    def _prompt(self, state: State) -> str:
        transcript: List[str] = []
        for item in state.history:
            if isinstance(item, UserMessage):
                transcript.append("CUSTOMER:\n" + message_text(item))
            elif isinstance(item, MultiToolMessage):
                transcript.append("TOOL RESULTS:\n" + message_text(item))
            elif isinstance(item, AssistantMessage):
                transcript.append("ASSISTANT:\n" + message_text(item))
            else:
                transcript.append(str(item))
        return (
            f"Domain: {self.domain}\n"
            f"Identity verified: {state.verified}\n"
            f"Human-transfer requests: {state.transfer_requests}\n\n"
            f"POLICY:\n{POLICY}\n\n"
            f"REFERENCE MATERIAL:\n{self.reference}\n\n"
            "CONVERSATION:\n"
            + "\n\n".join(transcript)
            + "\n\nAnswer the latest turn. Use available tools when needed. "
            "Return text or tool calls, not both."
        )

    def generate_next_message(
        self,
        message: Any,
        state: State,
    ) -> Tuple[AssistantMessage, State]:
        if state.stopped:
            return (
                AssistantMessage(
                    role="assistant",
                    content="This conversation has ended.",
                ),
                state,
            )

        state.history.append(message)
        if isinstance(message, UserMessage):
            lowered = message_text(message).lower()
            if any(
                phrase in lowered
                for phrase in (
                    "human",
                    "live agent",
                    "speak to a person",
                    "talk to a person",
                    "transfer me",
                )
            ):
                state.transfer_requests += 1

        response = self.gateway.generate(
            model=self._model(),
            messages=[UserMessage(role="user", content=self._prompt(state))],
            actions=self.actions,
            tool_choice="auto",
        )
        state.history.append(response)
        return response, state

    def is_stop(self, message: Any) -> bool:
        return (
            "YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON."
            in message_text(message).upper()
        )

    def stop(self, message: Any = None, state: Any = None) -> None:
        if isinstance(state, State):
            state.stopped = True


def create_agent():
    return BankingAgent(get_agent_context())
