"""Task-board assistant runtime entry point.

The evaluator imports this file and calls create_agent(). The assistant is a
single-model loop: playbook + transcript in, next message out.
"""

from dataclasses import dataclass, field
from typing import cast

from tau2.data_model.message import (
    AssistantMessage,
    Message,
    MultiToolMessage,
    SystemMessage,
)
from tau2.hyper.agent_context import get_agent_context

PLAYBOOK = """
You are the task-board assistant. Help teammates review the board, open
work items, and move items between columns. Confirm which teammate you are
acting for before writing to the board, and summarize every change you
make. Hand off to the support rotation only when asked or stuck.
""".strip()


@dataclass
class BoardSession:
    transcript: list[Message] = field(default_factory=list)


class BoardAssistant:
    """Single-model assistant over the task-board toolkit."""

    def __init__(self, *, actions, gateway):
        self.actions = actions
        self.gateway = gateway
        self.model_config = gateway.models[0]

    def get_init_state(self, message_history=None) -> BoardSession:
        return BoardSession(transcript=list(message_history or []))

    def generate_next_message(
        self, message, state: BoardSession
    ) -> tuple[AssistantMessage, BoardSession]:
        if isinstance(message, MultiToolMessage):
            state.transcript.extend(message.tool_messages)
        else:
            state.transcript.append(message)

        response = cast(
            AssistantMessage,
            self.gateway.generate(
                model=self.model_config.model,
                actions=self.actions,
                messages=[
                    SystemMessage(role="system", content=PLAYBOOK),
                    *state.transcript,
                ],
                **dict(self.model_config.constrained_args),
            ),
        )
        state.transcript.append(response)
        return response, state

    def is_stop(self, message) -> bool:
        # The assistant never ends the conversation itself; the runtime asks
        # after every turn and the customer side decides when to hang up.
        return False

    def stop(self, message=None, state=None) -> None:
        pass


def create_agent():
    """Build the task-board assistant from the shared runtime context."""
    context = get_agent_context()
    return BoardAssistant(
        actions=context.action_interface.available,
        gateway=context.model_gateway,
    )
