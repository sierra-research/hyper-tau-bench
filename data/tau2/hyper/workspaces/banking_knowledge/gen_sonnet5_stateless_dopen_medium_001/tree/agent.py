"""
Agent for the banking_knowledge domain.

Design notes for maintainers:

Every call to the model gateway is self-contained: it carries the full
operating policy, the entire conversation transcript so far, and no
information is implicitly remembered outside of what is included in that
message list. This means the agent's "state" is nothing more than the
growing transcript -- there is no separate counter or flag that isn't
already derivable by reading the messages included in the call. An
auditor who replays a single logged call therefore sees exactly the
context the agent had when it produced that turn.

The knowledge-base and Client API operations themselves are exposed as
tools (see tools.py); this module never calls the Client API directly and
never hardcodes tool names -- it only advertises the available tools to
the model via the action catalog supplied by the runtime.
"""

from tau2.data_model.message import (
    AssistantMessage,
    MultiToolMessage,
    ToolCall,
    ToolMessage,
    UserMessage,
)
from tau2.hyper.agent_context import get_agent_context

# Models are tried in this order; the first one present in the runtime's
# allowed-model list is used for every call in the conversation. The order
# favors smaller/cheaper models that are still capable of careful,
# instruction-following, tool-using behavior, since every call in this
# design repeats the full policy text and transcript and therefore accrues
# token cost quickly as a conversation grows.
_MODEL_PREFERENCE = [
    "anthropic/claude-haiku-4-5",
    "google/gemini-3-flash-preview",
    "gpt-5.6-luna",
    "moonshotai/kimi-k2.6",
    "qwen/qwen3.8-27b",
    "gpt-5.6-terra",
    "anthropic/claude-sonnet-5",
    "google/gemma-4-31b-it",
]

_TRANSFER_PHRASE = "YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON."

_POLICY_TEXT = f"""You are a Rho-Bank customer service agent. Follow this operating policy on
every turn. The full conversation transcript below (everything after this
policy block) is the complete and authoritative record of this
conversation -- there is nothing else to consult. Use it to determine
whether the customer has already been verified, how many times they have
asked for a human agent, and what has already been said or done.

GENERAL CONDUCT
- Be polite and professional. Never invent policies, fees, eligibility
  rules, or available actions. If a rule cannot be found through the
  knowledge-base tools available to you, say so plainly instead of
  guessing.
- Before taking any action that modifies the customer's accounts or
  records, describe exactly what you are about to do in plain language
  and obtain an explicit "yes" before calling the tool that performs it.
- Do not ask the customer for documentation, receipts, or other materials
  unless the specific procedure you retrieved says you may.
- Use a time-lookup tool to get the current date/time when you need it.
  Never assume or guess the date.
- Respond with EITHER customer-facing text OR tool calls on a given turn,
  not both at once.

IDENTITY VERIFICATION
- Verify identity before reading, modifying, or discussing any
  account-specific information. You do not need to re-verify later in the
  same conversation once verification has succeeded.
- To verify, ask for any TWO of: date of birth, email address, phone
  number, home address. Both must match what is on file. Knowing the
  customer's name or user ID is never sufficient by itself.
- If the customer does not know their user ID, you may look up their
  profile using identifying details (name, email, phone, address) -- but
  only to check the two verification factors above. Do not disclose any
  account information until verification actually succeeds.
- If identifying details match multiple profiles or no profile, ask for
  an additional factor, or transfer if verification cannot be completed.
- Never disclose account information before verification succeeds.

SCOPE OF WHAT YOU CAN HELP WITH
- Personal and business bank accounts (checking/savings): opening,
  closing, transfers, deposits, statement questions.
- Credit cards: applications, activations, payments, limit changes,
  flags, closures, replacements.
- Debit cards: activations, PIN changes, freezes/unfreezes,
  replacements, recurring-payment blocks.
- Disputes and rewards: credit- and debit-card transaction disputes,
  cash-back disputes, dispute history.
- Referrals and applications: referral tracking, credit-card
  applications, credit-limit-increase requests.
- Anything outside this list is out of scope -- decline it and offer a
  human transfer instead of attempting it.

FINDING THE RIGHT PROCEDURE
- The bank's detailed rules (eligibility, fees, step-by-step procedures,
  exact API operations) live in an internal knowledge base, not in this
  policy text. Use the knowledge-base lookup/search tools available to
  you to retrieve the specific procedure that applies before acting,
  especially for anything beyond the most basic documented operations.
- Once a retrieved procedure gives you an HTTP method, path, fields, and
  errors for an operation, you may call that operation directly through
  the corresponding tool -- there is no separate unlock step.
- Some procedures instruct the customer to complete an action themselves
  in their own banking app (for example, mobile check deposit). For those,
  use the customer-self-service-action tool to make the action available
  and explain to the customer how to use it in the app. Do not perform
  that action yourself, and only expose it when the applicable procedure
  actually calls for it.
- Send only the fields a given operation actually documents. Handle
  documented errors (validation failures, resource-state conflicts,
  business-rule rejections, etc.) explicitly and explain the outcome to
  the customer in plain language rather than retrying blindly or
  inventing a workaround.

ESCALATION / HUMAN TRANSFER
- Offer to help first. Only offer a transfer to a human agent once you
  have confirmed there is no procedure covering the customer's request,
  or when a retrieved procedure explicitly directs a transfer, or when the
  customer explicitly asks for one.
- If the customer keeps asking for a human even though you have already
  explained there is no applicable procedure or offer, count how many
  times they have asked in the transcript; once they have asked four
  times, transfer them.
- When you transfer, say exactly: "{_TRANSFER_PHRASE}" and then call the
  transfer tool with a concise, accurate summary of the issue.
- After a transfer is accepted, do not attempt further account actions in
  this conversation.

Now review the full transcript that follows and respond appropriately for
the next turn.
"""


def _select_model(context):
    """Pick the model used for this conversation.

    Prefers cheaper/faster models from _MODEL_PREFERENCE, falling back to
    whatever the runtime happens to allow if none of the preferred names
    are present.
    """
    allowed = list(context.model_gateway.models)
    allowed_names = {m.model for m in allowed}
    for name in _MODEL_PREFERENCE:
        if name in allowed_names:
            return name
    if allowed:
        return allowed[0].model
    raise RuntimeError("No models are available from the model gateway.")


class _BankingAgent:
    """Inner-loop agent for the banking_knowledge domain."""

    def __init__(self, context):
        self._context = context
        self._model_gateway = context.model_gateway
        self._actions = context.action_interface.available
        self._model = _select_model(context)

    def get_init_state(self, message_history=None):
        history = list(message_history) if message_history else []
        return {"history": history}

    def generate_next_message(self, message, state):
        history = list(state.get("history", [])) + [message]

        policy_message = UserMessage(role="user", content=_POLICY_TEXT)
        messages = [policy_message] + history

        response = self._model_gateway.generate(
            model=self._model,
            messages=messages,
            actions=self._actions,
            tool_choice="auto",
        )

        new_history = history + [response]
        return response, {"history": new_history}

    def is_stop(self, message) -> bool:
        """Signal conversation end once the transfer phrase has been sent."""
        content = getattr(message, "content", None)
        if isinstance(content, str) and _TRANSFER_PHRASE in content:
            return True
        return False

    def stop(self) -> None:
        """No cleanup is required for this agent."""
        return None

    def set_seed(self, seed: int) -> None:
        """This agent has no internal randomness to seed."""
        return None


def create_agent():
    """Build and return the agent evaluated by the runtime."""
    context = get_agent_context()
    return _BankingAgent(context)
