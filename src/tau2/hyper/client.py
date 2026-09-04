"""
Client simulator for the Hyper-τ outer loop.

The ClientSimulator plays the role of a human stakeholder who has hired
a developer to build or fix a customer service agent. Its behavior is
entirely driven by the ``client_instructions`` field in the task JSON —
that string IS the system prompt, giving maximum per-task flexibility.

The Client does NOT receive the solution policy or the base policy. It
only knows what the task author wrote in ``client_instructions``.

Implementation-wise, :class:`ClientSimulator` subclasses
:class:`tau2.user.user_simulator.UserSimulator` so that the outer-loop
User-role participant uses the same contract
(``get_init_state`` / ``generate_next_message``) as the inner-loop user
simulator. We override the system prompt to bypass the global user
simulation guidelines — the Client is a business stakeholder, not a
customer placing an order — and relabel the generation calls so
recordings stay distinguishable from inner-loop user turns.
"""

import json
from dataclasses import dataclass, field
from typing import Literal, Optional, Tuple

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, model_validator

from tau2.data_model.message import (
    AssistantMessage,
    SystemMessage,
    UserMessage,
)
from tau2.environment.tool import Tool, as_tool
from tau2.hyper.data_model import ClientState
from tau2.user.user_simulator import UserSimulator
from tau2.user.user_simulator_base import ValidUserInputMessage
from tau2.utils.llm_utils import generate

_CAPABILITY_CONTROL_TOOL_NAME = "respond_about_deployable_capability"


@dataclass
class ClientContext:
    """Client conversation and deployment state passed to a sandbox builder."""

    client: object
    client_state: object
    turns_used: int = 0
    deployment_manifest_id: Optional[str] = None
    deployment_manifest_sha256: Optional[str] = None
    discussions: list[dict[str, object]] = field(default_factory=list)
    capability_session: Optional[object] = None

    def talk(self, message: str) -> str:
        """Ask the Client and record the attributed exchange once."""

        response_text, self.client_state = self.client.generate_response(
            message, self.client_state
        )
        capability_offers = []
        deployment_actions = []
        take_intent = getattr(self.client, "take_capability_intent", None)
        intent = take_intent() if callable(take_intent) else None
        if intent is not None and intent.action != "respond":
            if self.capability_session is None:
                raise RuntimeError(
                    "Client produced a capability action without a deployment session"
                )
            from tau2.hyper.client_api.capabilities import (
                EnableCapabilityAction,
                OfferCapabilityAction,
            )

            if intent.action == "offer":
                assert intent.capability_id is not None
                offer = OfferCapabilityAction(capability_id=intent.capability_id)
                if self.capability_session.offer(offer):
                    capability_offers.append(offer.model_dump(mode="json"))
            else:
                assert intent.capability_id is not None
                action = EnableCapabilityAction(capability_id=intent.capability_id)
                if self.capability_session.enable_offered(action):
                    deployment_actions.append(action.model_dump(mode="json"))
                operation = json.loads(
                    self.capability_session.render_enabled_contract(
                        intent.capability_id
                    )
                )
                response_text = (
                    f"{response_text.rstrip()}\n\n"
                    f"I've enabled {operation['method']} {operation['path']}. "
                    "Use this deployed operation contract:\n"
                    f"```json\n{json.dumps(operation, indent=2)}\n```"
                )
        if deployment_actions and hasattr(self.client_state, "messages"):
            messages = getattr(self.client_state, "messages", None)
            if messages:
                messages[-1].content = response_text
        self.turns_used += 1
        discussion: dict[str, object] = {
            "turn": self.turns_used,
            "developer_message": message,
            "client_response": response_text,
        }
        if capability_offers:
            discussion["capability_offers"] = capability_offers
        if deployment_actions:
            discussion["deployment_actions"] = deployment_actions
        self.discussions.append(discussion)
        return response_text

    def result_metadata(self) -> dict[str, object]:
        """Return host result metadata without exposing private Client facts."""

        metadata: dict[str, object] = {
            "turns_used": self.turns_used,
            "discussions": list(self.discussions),
        }
        if self.deployment_manifest_id and self.deployment_manifest_sha256:
            metadata["deployment"] = {
                "manifest_id": self.deployment_manifest_id,
                "manifest_sha256": self.deployment_manifest_sha256,
            }
        if self.capability_session is not None:
            snapshot = self.capability_session.freeze()
            metadata["capabilities"] = {
                "snapshot_sha256": snapshot.sha256,
                "enabled_capability_ids": list(snapshot.enabled_capability_ids),
                "offers": [
                    offer.model_dump(mode="json")
                    for offer in self.capability_session.offers
                ],
                "actions": [
                    action.model_dump(mode="json")
                    for action in self.capability_session.actions
                ],
            }
        return metadata


class ClientCapabilityIntent(BaseModel):
    """Structured LLM intent for one deployable Client API capability."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action: Literal["respond", "offer", "enable"]
    capability_id: Optional[str] = None
    response: str = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_capability_id(self) -> "ClientCapabilityIntent":
        if self.action in {"offer", "enable"} and not self.capability_id:
            raise ValueError(f"action {self.action!r} requires a capability ID")
        return self


def respond_about_deployable_capability(
    action: Literal["respond", "offer", "enable"],
    capability_id: Optional[str],
    response: str,
) -> None:
    """Respond about one private deployable API capability.

    Use ``respond`` for every ordinary or vague question that does not warrant
    a capability action. Use ``offer`` when the Developer clearly identifies
    functionality missing from the supplied API, even if they use different
    wording from the Client's description. Use ``enable`` only after the
    Developer accepts the prior offer or explicitly asks for that offered
    capability to be deployed.

    Args:
        action: Whether to respond normally, offer, or enable an accepted offer.
        capability_id: Exact private capability ID for offer/enable; otherwise null.
        response: Concise natural-language response to show the Developer.
    """


def client_capability_control_tools() -> list[Tool]:
    """Return the private structured control tool available to the Client LLM."""

    return [as_tool(respond_about_deployable_capability)]


class ClientSimulator(UserSimulator[ClientState]):
    """Simulated human stakeholder for the Hyper-τ outer loop.

    The Client's behavior is entirely controlled by
    ``client_instructions``, which is used verbatim as the LLM system
    prompt. This allows each Hyper-τ task JSON to define exactly how
    the Client should behave — what it knows, how it communicates, and
    what it says first.

    Args:
        llm: LLM model name to power the Client.
        client_instructions: The full system prompt for the Client LLM.
            Comes directly from the task JSON ``client_instructions``.
        llm_args: Additional LLM arguments (e.g. ``reasoning_effort``).
        tools: Optional tools; unused by the default Client but accepted
            so that :func:`tau2.runner.build.build_user`-style factories
            can plumb through whatever the registry provides.
    """

    def __init__(
        self,
        llm: str,
        client_instructions: str,
        llm_args: Optional[dict] = None,
        tools: Optional[list[Tool]] = None,
    ):
        super().__init__(
            llm=llm,
            instructions=client_instructions,
            tools=tools,
            llm_args=llm_args,
        )
        self.client_instructions = client_instructions
        self._pending_capability_intent: Optional[ClientCapabilityIntent] = None

    @property
    def system_prompt(self) -> str:
        """Bypass the global user-sim guidelines; Client is driven entirely by task-authored instructions."""
        return self.client_instructions

    def get_init_state(self, message_history=None) -> ClientState:  # type: ignore[override]
        """Create the initial Client state.

        Returns a :class:`ClientState` (a thin subclass of
        :class:`tau2.user.user_simulator_base.UserState`) seeded with the
        Client's system prompt.
        """
        return ClientState(
            system_messages=[SystemMessage(role="system", content=self.system_prompt)],
            messages=list(message_history or []),
        )

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def _generate_next_message(
        self,
        message: ValidUserInputMessage,
        state: ClientState,
    ) -> UserMessage:
        """Relabel the generation trace to ``client_simulator_response``.

        Otherwise identical to the parent implementation. Kept separate
        so outer-loop recordings stay distinguishable from inner-loop
        user simulator turns when both coexist in a run.
        """
        if isinstance(message, AssistantMessage) and message.is_audio:
            raise ValueError("ClientSimulator does not support audio messages.")
        state.messages.append(message)
        messages = state.system_messages + state.flip_roles()
        logger.debug(f"Client responding to: {getattr(message, 'content', '')[:100]}")
        assistant_message: AssistantMessage = generate(
            model=self.llm,
            messages=messages,
            tools=self.tools,
            tool_choice="required" if self.tools else None,
            call_name="client_simulator_response",
            **self.llm_args,
        )
        self._pending_capability_intent = None
        response_content = assistant_message.content
        if assistant_message.tool_calls:
            if len(assistant_message.tool_calls) != 1:
                raise ValueError(
                    "Client capability control requires exactly one action"
                )
            tool_call = assistant_message.tool_calls[0]
            if tool_call.name != _CAPABILITY_CONTROL_TOOL_NAME:
                raise ValueError(
                    f"Unsupported Client control action {tool_call.name!r}"
                )
            intent = ClientCapabilityIntent.model_validate(tool_call.arguments)
            self._pending_capability_intent = intent
            response_content = intent.response
        return UserMessage(
            role="user",
            content=response_content,
            cost=assistant_message.cost,
            usage=assistant_message.usage,
            raw_data=assistant_message.raw_data,
        )

    def take_capability_intent(self) -> Optional[ClientCapabilityIntent]:
        """Consume the structured capability intent from the latest response."""

        intent = self._pending_capability_intent
        self._pending_capability_intent = None
        return intent

    # ------------------------------------------------------------------
    # Outer-loop-specific helpers (kept for backwards compatibility
    # with callers and tests that predate the UserSimulator subclassing).
    # ------------------------------------------------------------------

    def generate_initial_brief(self) -> Tuple[UserMessage, ClientState]:
        """Generate the Client's opening message to kick off the conversation.

        The Client LLM generates its own opening based on its system
        prompt, so different tasks can produce completely different
        opening messages. The brief is stored in the Client's state as
        a ``"user"`` role message (the Client's own turn from the
        LLM's perspective, after ``flip_roles`` is applied on the next
        call).

        Returns:
            ``(brief_message, initial_client_state)`` — the
            ``brief_message`` is a :class:`UserMessage` ready to feed
            directly into the Developer.
        """
        state = self.get_init_state()
        prompt = UserMessage(
            role="user",
            content=(
                "Generate your opening message to the developer. "
                "Introduce yourself and describe what you need."
            ),
        )
        messages = state.system_messages + [prompt]
        assistant_message: AssistantMessage = generate(
            model=self.llm,
            messages=messages,
            tools=None,
            call_name="client_initial_brief",
            **self.llm_args,
        )
        brief_text = assistant_message.content or ""
        # Store the brief as the Client's own turn. With ``flip_roles``,
        # this will appear as role="assistant" to the LLM on the next
        # generation call, which is the correct frame ("I previously
        # said X").
        state.messages.append(UserMessage(role="user", content=brief_text))
        logger.info(f"Client sent initial brief ({len(brief_text)} chars)")
        return UserMessage(role="user", content=brief_text), state

    def generate_response(
        self,
        developer_message: str,
        state: ClientState,
    ) -> Tuple[str, ClientState]:
        """Generate a response to the Developer's question.

        Thin wrapper around :meth:`generate_next_message` that accepts
        the Developer's raw text (as the orchestrator supplies it) and
        returns raw text. Preserved for call-site stability.
        """
        dev_msg = AssistantMessage(role="assistant", content=developer_message)
        user_message, state = self.generate_next_message(dev_msg, state)
        response_text = user_message.content or ""
        logger.debug(f"Client response: {response_text[:100]}...")
        return response_text, state
