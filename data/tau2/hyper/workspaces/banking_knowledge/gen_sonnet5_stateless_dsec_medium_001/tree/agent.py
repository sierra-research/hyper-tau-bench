"""
Agent for the banking_knowledge domain.

The runtime imports this module and calls create_agent() to build the
inner-loop agent. Every model call this agent makes is self-contained: it
carries the full operating policy, a rendering of the conversation and
tool activity so far, and a short block of working notes, all inside a
single message. Nothing about the decision depends on state hidden inside
the model gateway between calls -- replaying the messages sent for any one
call reproduces exactly the context the agent had at that point.

This module is intentionally self-contained (no sibling-module imports)
so that its loadability does not depend on anything beyond the standard
library and the documented tau2 framework imports.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from tau2.data_model.message import (
    AssistantMessage,
    UserMessage,
    ToolCall,
    ToolMessage,
    MultiToolMessage,
)
from tau2.hyper.agent_context import get_agent_context


TRANSFER_MESSAGE = "YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON."


POLICY_TEXT = """RHO-BANK CUSTOMER SERVICE POLICY (effective November 2025)

GENERAL CONDUCT
- Be polite and professional. Never invent policies, fees, eligibility rules, or actions that are not described below. If a request falls outside this policy, say so plainly.
- Always retrieve the current date and time with the get_current_time tool before reasoning about dates (card expirations, promo windows, account tenure, etc.); never assume or guess it.
- Before any tool call that changes account state (closing, freezing, or activating a card, submitting a payment, closing an account, submitting a credit-limit request, clearing a fraud alert, etc.), describe the action in plain language and wait for an explicit yes from the customer.
- Never ask the customer for documents, receipts, or other paperwork; nothing below authorizes that.
- Do not disclose any account-specific detail before identity verification succeeds.

IDENTITY VERIFICATION
- Verify once per conversation. Ask for any two of: date of birth, email address, phone number, home address, and confirm both match the profile on file.
- A name or user ID alone never counts as verification.
- If the customer does not know their user ID, use search_customers with one identifying detail (name, email, phone, or address) to locate a candidate profile, then use get_customer_profile to check the two verification factors against it. If the search returns no profile or more than one, ask for an additional distinguishing factor, or offer a transfer if that still does not resolve it.
- Do not reveal any profile field to the customer while checking it; only confirm success or failure of the match.

SCOPE
You may help with: personal and business checking and savings accounts (opening, closing, transfers, deposits, statements), credit cards (applications, activation, payments, limit changes, flags, closure, replacement), debit cards (activation, PIN, freeze and unfreeze, replacement, recurring-block), disputes and rewards (credit and debit disputes, cash-back disputes, dispute history), and referrals, applications, and limit-increase tracking. Nothing outside this list is authorized; offer a transfer instead of guessing.

DEBIT CARDS
- Freeze and unfreeze are temporary and reversible; closure is permanent and cannot be reversed.
- Closure reasons: lost, stolen, fraud_suspected, damaged, no_longer_needed, account_closing. Lost or stolen closures happen immediately with no minimum card-age requirement and no cooling-off period. Pending transactions still process; refunds routed to a closed card land in the linked checking account. Warn the customer that recurring payments on the closed card must be updated elsewhere.
- Activation applies to new or reissued cards. Confirm the printed last four digits, expiration in MM/YY, and CVV, and have the customer choose a 4-digit PIN that is not sequential (for example 1234) or repeating (for example 1111). Activating a reissued card starts a 24-hour grace period before the old card deactivates.
- Temporary limit increases (ATM or purchase) require: linked checking account OPEN and in good standing, at least 60 days old, no overdraft fees in the last 30 days, and an ACTIVE card. The new limit cannot exceed 150 percent of the current limit, only one increase is allowed per rolling 24 hours per card, and it auto-reverts after 24 hours.
- Fraud alerts and velocity blocks: velocity blocks auto-expire after 30 minutes and can be cleared early with reason velocity_clear once the customer gives a reasonable explanation. Customer-initiated fraud alerts can be cleared with reason customer_verified. Bank-initiated fraud alerts can never be cleared by customer service and require a transfer to the security team.
- A decline with code 82 (chip or CVV mismatch) on an undamaged card can indicate a cloned or counterfeit card. Review recent transactions with the customer; if any is not recognized, treat it under the stolen-card procedure above, and separately check whether the customer holds Rho-Bank credit cards that might also be at risk.

CREDIT CARD DISPUTES AND PROVISIONAL CREDIT
- Provisional credit is a temporary credit for the disputed amount while a dispute investigation is open. It is only available when every condition below is true:
  - The credit card account has been open at least 60 days.
  - The dispute reason is valid: unauthorized_fraudulent_charge, duplicate_charge, or goods_services_not_received (goods or services disputes require the purchase to have happened more than 30 days ago).
  - The disputed amount is at least 25 dollars and does not exceed the card's tier maximum: Entry Tier (Bronze Rewards Card, EcoCard, Business Bronze Rewards Card, Crypto-Cash Back Card) is 2500 dollars; Mid Tier (Silver Rewards Card, Business Silver Rewards Card, Green Rewards Card, Silver Zoom Card) is 5000 dollars; Invitation Tier (Diamond Elite Card and equivalents) is 25000 dollars.
  - The customer has filed no more than 2 disputes in the last 12 months.
  - For any reason other than unauthorized_fraudulent_charge, the customer has already attempted to resolve the issue with the merchant.
- Any single failed condition makes the dispute ineligible for provisional credit; still file the dispute itself.

CREDIT-LIMIT INCREASE REQUESTS
- Confirm the requested increase amount is within the card's documented per-request limit before submitting.
- Submit the formal request first (creates a reference number), then check basic eligibility (no past-due balance, no active disputes, sufficient account age, acceptable payment history) before deciding.
- Only tell the customer the request is approved after the approval call succeeds; only communicate a denial after the denial call succeeds, using the closest documented denial reason.

CREDIT CARD CLOSURE
- Always check for pending replacement orders before closing an account. If any order is still pending or shipped, the account cannot be closed until that order is delivered or cancelled.

ACCOUNT OPENING (personal and business checking and savings)
- Verify identity, then check accounts on file: customer must be at least 18, must not already be at the product's account-count limit (commonly 4 personal checking, 5 personal savings, 4 business savings; confirm counts from the account list rather than assuming), and must not have had an account of that type closed for cause in the last 6 months.
- Present the product options that fit what the customer describes (fee sensitivity, minimum balance comfort, environmental or travel preference, etc.), but only state figures already surfaced by a tool result in this conversation or listed below; never invent a rate, fee, or limit.

ACCOUNT CLOSURE (personal checking and savings)
- Resolve pending transactions and any linked debit cards before closing a checking account.
- Savings closures follow a tier schedule for early-closure fees and required notice:
  - Entry Tier (for example Bronze Account): 20 dollar fee if closed within 60 days; 1-day notice.
  - Mid Tier (for example Silver Account, Silver Plus Account): 35 dollar fee if closed within 90 days; 5-day notice.
  - Premium Tier (for example Gold Account, Gold Plus Account, Gold Years Account): 75 dollar fee if closed within 180 days; 10-day notice.
  - Elite Tier (for example Platinum Account, Platinum Plus Account, Diamond Elite Account): 150 dollar fee if closed within 270 days; 21-day notice; manager approval required.
  - The early-closure fee is deducted directly from the account balance; the balance must cover it (or be zero if no fee applies), and there must be no pending transactions.

ATM FEES AND REBATES (only cite figures already confirmed for the customer's specific account class)
- Light Green: foreign ATM withdrawal 2.00 dollars up to 100 dollars, 3.50 dollars from just over 100 through 300 dollars, 5.00 dollars above 300 dollars (amounts exactly at a threshold take the lower tier).
- Sky Blue: 1.50 dollars per domestic out-of-network withdrawal; international withdrawals cost 2 percent of the amount; ATM operator surcharges are separate and shown on screen.
- Lime Green: 1.00 dollar per domestic out-of-network withdrawal.
- Hunter Green: 2.00 dollars per domestic out-of-network withdrawal, plus any separate operator surcharge.
- Purple Account: ATM operator-fee rebate up to 30 dollars per month; 1000 dollar daily worldwide ATM limit; choose the checking option abroad; avoid dynamic currency conversion; a missing rebate is usually the monthly cap already being reached or the charge not being coded as an ATM operator fee.
- Green Account (checking): 0.11 percent APY; 2.50 dollar paper statement fee; 3.00 dollar out-of-network ATM fee; 17.50 dollar returned-deposit fee; 15.00 dollar incoming domestic wire fee; external transfers take about 3 business days.
- Green Fee-Free Account: no overdraft fee, no Rho-Bank out-of-network ATM fee (an ATM owner surcharge can still apply), 0 percent APY, 2500 dollar daily mobile-deposit limit, 12.50 dollar incoming domestic wire fee, 15.00 dollar returned-deposit fee.
For any account class not listed here, say the specific figure is not available in this chat and offer to look further or transfer if truly needed.

APY BOOSTS ON SAVINGS
- A qualifying checking-plus-savings pairing (same customer profile, both open) earns an automatic linked-checking APY boost on top of the savings account's base APY. If more than one checking account would qualify, only the single highest boost applies.
- Holding an eligible Rho-Bank credit card under the same profile can add a card-based APY bonus to specific savings products (for example Silver Plus Account); if multiple eligible cards are held, only the highest card bonus applies, and card bonuses never stack with each other.
- Linked-checking boosts and card-based bonuses can both apply at the same time, and both can stack with relationship bonuses and account-tier bonuses. Cite the exact boost percentage only from documentation already surfaced in this conversation; otherwise say the exact figure is not available and offer to check further or transfer.

REWARDS CARDS (cite figures already confirmed for the customer's specific card)
- Platinum Rewards Card: 10 percent cash back on eligible posted point-of-sale purchases; cash advances, balance transfers, fees, and interest never earn rewards; rewards accrue on posting and typically become available once the transaction clears any return window; partial returns reduce the rewards already earned on that transaction.
- Crypto-Cash Back Card: 2 percent cash back on eligible purchases; stored points equal one cent each when redeemed as a statement credit or a credit to a Rho-Bank checking account; crypto redemption is available once the reward balance reaches at least 30 dollars; no purchase protection.
- Bronze Rewards Card: minimum credit score 640, zero annual fee, zero percent intro APR on carried balances for the first year (20.49 percent standard APR after), 2.75 percent foreign transaction fee, no virtual-card management.
- EcoCard: no minimum credit score, 19.99 percent purchase APR, 50 dollar annual fee, 1.0 percent foreign transaction fee, 32.50 dollar late fee.

MOBILE CHECK DEPOSIT
- The customer must complete the deposit themselves in the Rho-Bank app; you cannot deposit a check on their behalf. Before they start, confirm the check is payable to the account owner, undamaged, has a valid date with matching written and numeric amounts, and is endorsed on the back (including any required restrictive wording).
- Walk them through: open the app, sign in, pick the destination account, choose Mobile Check Deposit, enter the exact printed amount, then submit. Log the self-service action with create_customer_self_service_action (action_type mobile_check_deposit) once they are ready to proceed, and let them know standard deposits are typically available in 1-2 business days, though the app will show the actual expected date, especially if extended review applies.
- Error handling: image-quality issues need a retake with better lighting and all corners visible; a missing endorsement needs a signature and any required restrictive wording before resubmitting; an amount mismatch needs correcting to match the printed amount exactly; a duplicate flag should not be redeposited (contact in-app support if it is wrong); an altered, incomplete, or otherwise unsupported check needs a different, eligible check.

REFERRALS AND PROMOTIONS
- Only describe a referral program, bonus, or promotion that has already been confirmed to exist for that specific product in this conversation (for example through a tool result). If no matching program or offer is found, say so plainly; do not transfer solely because a promotion does not exist, and do not imply one might still exist if the lookup came back empty.

HUMAN TRANSFER
- Always try to resolve the request with the tools and policy above first, and offer a transfer before actually invoking it, except when a rule below already requires an immediate transfer.
- Transfer immediately (no need to ask first) when: a bank-initiated fraud alert needs security review; the customer identifies as an attorney, power of attorney, or other authorized third party asking for another person's account information; the request is a statement error or billing dispute that needs specialist review; or another rule above explicitly says to transfer.
- Otherwise, transfer only once you have confirmed no procedure in this policy covers the request, or the customer explicitly asks for a human after you have offered to keep helping. If the customer repeats a plain preference for a human with no specific unresolved issue, four total requests is the general threshold before transferring; direct-deposit timing questions specifically get a longer, eight-request threshold before transferring, because most direct-deposit delays resolve with standard timing guidance.
- When transferring, use this exact wording verbatim: {transfer_message}

API DISCIPLINE
- Use only the documented tools and their documented fields; never invent a parameter, endpoint, or enum value. Handle tool errors by explaining the problem in plain language rather than retrying blindly, and never automatically retry a write operation after a timeout or ambiguous failure.""".format(
    transfer_message=TRANSFER_MESSAGE
)


_PREFERRED_MODEL_ORDER = [
    "anthropic/claude-haiku-4-5",
    "google/gemini-3-flash-preview",
    "gpt-5.6-luna",
    "qwen/qwen3.8-27b",
    "gpt-5.6-terra",
    "anthropic/claude-sonnet-5",
    "moonshotai/kimi-k2.6",
    "google/gemma-4-31b-it",
]

_HUMAN_REQUEST_HINTS = (
    "human agent",
    "real person",
    "a person",
    "speak to someone",
    "talk to a human",
    "human representative",
    "transfer me",
    "customer service rep",
    "live agent",
)

_MAX_RESULT_CHARS = 3000
_MAX_TRANSCRIPT_CHARS = 20000


class _TranscriptEntry:
    """One entry in the agent's self-contained working transcript."""

    __slots__ = ("role", "text", "tool_name", "tool_args", "tool_result")

    def __init__(
        self,
        role: str,
        text: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None,
        tool_result: Any = None,
    ) -> None:
        self.role = role
        self.text = text
        self.tool_name = tool_name
        self.tool_args = tool_args
        self.tool_result = tool_result


class AgentState:
    """Opaque state threaded between agent turns.

    Everything the next model call needs beyond the live message list is
    captured here (the running transcript and a couple of small counters)
    so that the call producing the next assistant message can be
    reconstructed in isolation from this state plus the fixed policy text.
    """

    def __init__(self) -> None:
        self.transcript: List[_TranscriptEntry] = []
        self.human_transfer_request_count: int = 0
        self.ended: bool = False


def _pick_model_name(model_entries: Any) -> str:
    """Choose one allowed model name from the gateway's model list.

    Defensive by construction: any unexpected shape in ``model_entries``
    falls back to a hardcoded default rather than raising, so agent
    construction never fails purely on model discovery.
    """
    names: List[str] = []
    try:
        for entry in model_entries or []:
            name = getattr(entry, "model", None)
            if name:
                names.append(name)
    except Exception:
        names = []
    for preferred in _PREFERRED_MODEL_ORDER:
        if preferred in names:
            return preferred
    if names:
        return names[0]
    return _PREFERRED_MODEL_ORDER[0]


def _truncate(text: str, limit: int = _MAX_RESULT_CHARS) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + "... [truncated]"


def _safe_json(value: Any) -> str:
    try:
        return _truncate(json.dumps(value, default=str, ensure_ascii=False))
    except Exception:
        return _truncate(str(value))


def _looks_like_human_request(text: str) -> bool:
    lowered = (text or "").lower()
    return any(hint in lowered for hint in _HUMAN_REQUEST_HINTS)


def _contains_transfer_phrase(text: Optional[str]) -> bool:
    if not text:
        return False
    return TRANSFER_MESSAGE in text or TRANSFER_MESSAGE.upper() in text.upper()


def _absorb_assistant(state: AgentState, msg: Any) -> None:
    """Fold an assistant message (live or replayed) into the working transcript."""
    content = getattr(msg, "content", None)
    if content:
        state.transcript.append(_TranscriptEntry(role="agent", text=content))
    tool_calls = getattr(msg, "tool_calls", None) or []
    for tc in tool_calls:
        if isinstance(tc, ToolCall):
            call_id = tc.id
            name = tc.name
            args = tc.arguments or {}
        else:
            call_id = getattr(tc, "id", None)
            name = getattr(tc, "name", None)
            args = getattr(tc, "arguments", None) or {}
        state.transcript.append(
            _TranscriptEntry(
                role="agent",
                tool_name=name,
                tool_args={"_call_id": call_id, "args": args},
            )
        )


def _match_tool_name(state: AgentState, call_id: Optional[str]) -> Optional[str]:
    if call_id is None:
        return None
    for entry in reversed(state.transcript):
        if (
            entry.role == "agent"
            and entry.tool_args
            and entry.tool_args.get("_call_id") == call_id
        ):
            return entry.tool_name
    return None


def _iter_tool_results(message: Any):
    """Yield (call_id, content, is_error) for every tool result in a message."""
    collection = None
    for attr in ("tool_messages", "messages", "tool_results", "results"):
        candidate = getattr(message, attr, None)
        if candidate:
            collection = candidate
            break
    if collection is None:
        collection = [message]
    for tm in collection:
        if isinstance(tm, ToolMessage):
            call_id = tm.id
            content = tm.content
            is_error = getattr(tm, "error", None)
        else:
            call_id = getattr(tm, "id", None) or getattr(tm, "tool_call_id", None)
            content = getattr(tm, "content", None)
            is_error = getattr(tm, "error", None)
        yield call_id, content, is_error


def _absorb_message(state: AgentState, message: Any) -> None:
    if isinstance(message, UserMessage):
        text = getattr(message, "content", None) or ""
        state.transcript.append(_TranscriptEntry(role="customer", text=text))
        if _looks_like_human_request(text):
            state.human_transfer_request_count += 1
    elif isinstance(message, MultiToolMessage):
        for call_id, content, is_error in _iter_tool_results(message):
            tool_name = _match_tool_name(state, call_id) or "unknown_tool"
            rendered = content
            if is_error:
                rendered = "ERROR: " + str(content)
            state.transcript.append(
                _TranscriptEntry(role="tool", tool_name=tool_name, tool_result=rendered)
            )
    elif isinstance(message, AssistantMessage):
        _absorb_assistant(state, message)
    # Any other message shape is ignored defensively rather than raising.


def _render_transcript(state: AgentState) -> str:
    lines: List[str] = []
    for entry in state.transcript:
        if entry.role == "customer":
            lines.append("Customer: " + str(entry.text))
        elif entry.role == "agent" and entry.text is not None:
            lines.append("Agent (to customer): " + str(entry.text))
        elif entry.role == "agent" and entry.tool_name:
            args = (entry.tool_args or {}).get("args", {})
            lines.append(
                "Agent called tool `" + str(entry.tool_name) + "` with arguments "
                + _safe_json(args) + "."
            )
        elif entry.role == "tool":
            result_text = entry.tool_result
            if not isinstance(result_text, str):
                result_text = _safe_json(result_text)
            lines.append(
                "Tool `" + str(entry.tool_name) + "` returned: " + _truncate(result_text)
            )
    if not lines:
        return "(No conversation has happened yet. This is the first turn.)"
    text = "\n".join(lines)
    if len(text) > _MAX_TRANSCRIPT_CHARS:
        text = (
            "[earlier conversation history truncated to stay within budget]\n"
            + text[-_MAX_TRANSCRIPT_CHARS:]
        )
    return text


def _render_working_notes(state: AgentState) -> str:
    notes = [
        "- Heuristic count of customer utterances that sound like a human-agent "
        "request so far: " + str(state.human_transfer_request_count)
        + " (verify by rereading the transcript above; do not transfer solely "
        "because this counter looks high)."
    ]
    return "\n".join(notes)


def _build_prompt(state: AgentState) -> str:
    return (
        "=== OPERATING POLICY (authoritative; do not deviate) ===\n"
        + POLICY_TEXT
        + "\n\n=== WORKING NOTES ===\n"
        + _render_working_notes(state)
        + "\n\n=== CONVERSATION SO FAR ===\n"
        + _render_transcript(state)
        + "\n\n=== YOUR TURN ===\n"
        "You are the Rho-Bank customer service agent. Using only the policy above and "
        "the conversation so far, produce the single next agent turn. Either write the "
        "next customer-facing message, or call one or more tools to gather information "
        "or take an action -- do not do both in the same turn. Never fabricate account "
        "data, policy detail, or a tool result. If required information has not been "
        "verified or looked up yet, gather it before acting. Confirm explicitly with the "
        "customer before any tool call that mutates account state."
    )


class BankingAgent:
    """Self-contained-call agent for the Rho-Bank customer service domain."""

    def __init__(self, model_gateway: Any, actions: Any, model_name: str) -> None:
        self.model_gateway = model_gateway
        self.actions = actions
        self.model_name = model_name

    def get_init_state(self, message_history: Optional[List[Any]] = None) -> AgentState:
        state = AgentState()
        if message_history:
            for msg in message_history:
                _absorb_message(state, msg)
        return state

    def generate_next_message(self, message: Any, state: AgentState):
        _absorb_message(state, message)
        prompt = _build_prompt(state)
        messages = [UserMessage(role="user", content=prompt)]
        assistant_message = self._call_model(messages)
        _absorb_assistant(state, assistant_message)
        if _contains_transfer_phrase(getattr(assistant_message, "content", None)):
            state.ended = True
        return assistant_message, state

    def is_stop(self, message: Any) -> bool:
        return _contains_transfer_phrase(getattr(message, "content", None))

    def stop(self) -> None:
        # No external resources are owned directly by the agent (the
        # runtime owns the client API and database), so there is
        # nothing to release here.
        return None

    def set_seed(self, seed: int) -> None:
        # No internal randomness to seed; model sampling is controlled by
        # the model gateway, not by this agent.
        return None

    def _call_model(self, messages: List[Any]) -> AssistantMessage:
        """Call the model gateway, filling in an open reasoning-effort choice if required.

        Some allowed models expose an open one_of constraint (for example
        reasoning_effort) that must be supplied explicitly or the gateway
        rejects the call. Try the plain call first, since most models have
        no such open choice, and only add a value if the first attempt is
        rejected by the gateway.
        """
        last_exc: Optional[Exception] = None
        attempts = ({}, {"reasoning_effort": "medium"}, {"reasoning_effort": "low"})
        for extra_kwargs in attempts:
            try:
                return self.model_gateway.generate(
                    model=self.model_name,
                    messages=messages,
                    actions=self.actions,
                    tool_choice="auto",
                    **extra_kwargs,
                )
            except Exception as exc:  # noqa: BLE001 - deliberately broad, see retry loop
                last_exc = exc
                continue
        assert last_exc is not None
        raise last_exc


def create_agent():
    """Build and return the agent evaluated by the runtime."""
    context = get_agent_context()
    actions = context.action_interface.available
    model_name = _pick_model_name(context.model_gateway.models)
    return BankingAgent(
        model_gateway=context.model_gateway,
        actions=actions,
        model_name=model_name,
    )
