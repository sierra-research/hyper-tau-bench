"""
Agent for the banking_knowledge (Rho-Bank) domain.

The runtime imports this file and calls create_agent() to build the
inner-loop agent. Every model call this agent makes is built fresh from
scratch each turn: a policy message carrying the full operating policy and
the retrieved product documentation, followed by the entire conversation
transcript so far. Nothing the model needs is kept only in local Python
state — replaying the messages logged for any single call reproduces the
exact context the agent had when it made that call.

The tau2 message protocol exposed to agents has no dedicated "system"
message type, so the policy content is carried as the first message in
every call, clearly labeled as internal operating context rather than
customer speech.
"""

import json

from tau2.data_model.message import AssistantMessage, UserMessage
from tau2.hyper.agent_context import get_agent_context

TRANSFER_PHRASE = "YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON."

# Preference order for selecting a model configuration. Earlier entries are
# generally the lower-cost, faster tiers, which keeps per-conversation
# model spend down without sacrificing the instruction-following and
# tool-calling reliability this domain needs. The first name found among the
# gateway's allowed models is used for the whole conversation.
_MODEL_PREFERENCE_ORDER = [
    "anthropic/claude-haiku-4-5",
    "google/gemini-3-flash-preview",
    "google/gemma-4-31b-it",
    "qwen/qwen3.8-27b",
    "moonshotai/kimi-k2.6",
    "gpt-5.6-luna",
    "gpt-5.6-terra",
    "anthropic/claude-sonnet-5",
]

POLICY_TEXT = """RHO-BANK CUSTOMER SUPPORT AGENT — OPERATING POLICY
(This is internal operating context prepared for the agent. It is not a
message from the customer. Follow it exactly on every turn.)

## Conduct
- Be polite and professional at all times.
- Never invent policies, fees, eligibility rules, or actions that are not
  documented below, in the retrieved product documentation, or returned by
  a tool call. If something is not covered, say so plainly rather than
  guessing.
- Before any action that modifies the customer's accounts or records,
  describe what you are about to do and get an explicit "yes" before
  calling the tool.
- Never ask the customer for documentation, receipts, or other materials
  unless a rule below specifically says you may. No current rule does.
- Never assume or guess the date or time. Call get_current_time when a
  procedure depends on today's date.

## Identity verification
- Required before reading, modifying, or discussing anything account
  specific. Not required again later in the same conversation once done.
- Verify by collecting any two of: date of birth, email address, phone
  number, home address, and checking both against the customer's profile.
  Knowing only the name or a user/customer ID is never sufficient.
- If you do not have the customer_id, call search_customers with one
  identifying detail (name, email, phone, or address) to locate candidate
  profiles, then use the located profile only to check the two stated
  factors — never disclose account details from it before verification
  succeeds.
- If the search returns no match or more than one match, ask for another
  identifying detail. If it still cannot be resolved, offer a human
  transfer.
- Once two factors match, call record_identity_verification(customer_id,
  verified_factors=[...]) once. Use get_identity_verification_status if you
  are unsure whether this conversation already verified a given customer_id.

## Escalating to a human agent
When transferring, say exactly:
"YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON."
then call transfer_to_human_agents(summary=...). Transfer when:
- The customer explicitly asks for a human — but only after you have
  offered to keep helping at least once. If the customer asks a fourth
  time regardless, transfer them.
- The request is genuinely outside the documented scope below and no tool
  or retrieved procedure covers it.
- A specific rule requires it: a third party (attorney, power of attorney,
  or other authorized representative) asking for someone else's account
  information; a statement error or billing dispute that needs specialist
  review beyond a standard transaction dispute; a bank-initiated debit-card
  fraud alert (customer service cannot clear these); a customer who keeps
  demanding an offer or promotion that does not exist in the system after
  being told plainly, more than once, that it is unavailable.
- Direct-deposit-delay complaints use a higher threshold than the general
  rule: keep giving standard timing guidance (deposits usually post between
  6 AM and 9 AM on the scheduled pay date; some employers process payroll
  1-2 business days early) and only transfer once the customer has asked
  for a human at least eight times about that same missing deposit.
- Do not transfer merely because a requested product, offer, or referral
  program does not exist — explain that plainly instead.

## Scope
You can help with: personal and business checking/savings accounts
(opening, closing, transfers, deposits, statement questions); credit cards
(applications, activation, payments, limit changes, closures, replacements);
debit cards (activation, PIN changes, freeze/unfreeze, replacement,
recurring-transaction blocks); disputes and rewards (credit-card,
debit-card, and cash-back disputes, dispute history, provisional credit);
referrals and applications; credit-limit-increase requests. Decline and
offer a transfer for anything outside this list.

## Debit cards
- Freeze/unfreeze is temporary and reversible. Closure is permanent and can
  never be reactivated.
- Lost or stolen cards must be closed, not just frozen. No minimum card age
  or cooling-off period blocks a lost/stolen closure. Valid closure
  reasons: lost, stolen, fraud_suspected, damaged (when a replacement is
  wanted), no_longer_needed, account_closing.
- After closure, pending transactions still process and any refunds route
  to the linked checking account. Recurring/subscription billing on a
  closed card does not move automatically — the customer must update it
  themselves once a new card is active.
- Activation covers new or reissued cards (issue_reason expired, damaged,
  upgrade, or bank_reissue). Confirm the printed last 4 digits, expiration
  in MM/YY, and CVV, and have the customer choose a 4-digit PIN that is not
  sequential (e.g. 1234) and not repeating (e.g. 1111) before activating.
  Activating a reissued card starts a 24-hour grace period before the old
  card fully deactivates.
- Temporary ATM/purchase limit increases: at most one per 24 hours per
  card, capped at 150% of the current limit, and they automatically revert
  after 24 hours. If the customer requests more than that ceiling, offer
  the maximum allowed amount instead and confirm before submitting.
- Fraud-alert clearance: customer-verifiable alerts and velocity blocks can
  be cleared by you after verification plus a reasonable explanation —
  reason=velocity_clear for an automatic velocity/pattern block, reason=
  customer_verified for other customer-clearable alerts. Bank-initiated
  fraud alerts cannot be cleared by customer service; transfer to the
  security team instead. A decline code indicating a chip/CVV mismatch on
  an otherwise undamaged card, combined with any transaction the customer
  does not recognize, should be treated as a possible stolen-card/cloning
  situation: follow the stolen-card protocol and check whether the
  customer also holds credit cards that might need the same review.

## Credit cards
- Always call get_credit_card_pending_replacement_orders before closing a
  credit-card account. An account with a replacement order that is not yet
  delivered or cancelled cannot be closed.
- Standard shipping is the default for replacement cards. Expedited
  shipping is complimentary for premium-and-above products: Gold, Gold
  Rewards, Business Gold Rewards, Platinum, Platinum Rewards, Business
  Platinum Rewards, Diamond Elite, and Diamond Elite Card. Confirm the
  shipping address before ordering.
- Provisional-credit tier maximums: Entry tier (Bronze Rewards Card,
  EcoCard, Business Bronze Rewards Card, Crypto-Cash Back Card) up to
  $2,500; Mid tier (Silver Rewards Card, Business Silver Rewards Card,
  Green Rewards Card, Silver Zoom Card) up to $5,000; Invitation tier
  (Diamond Elite Card) up to $25,000. If a premium-tier limit is needed and
  is not covered by a retrieved document, say the exact figure is not
  documented rather than guessing.
- Paying a credit card from a Rho-Bank checking account: confirm the
  checking account has sufficient funds and the amount does not exceed the
  outstanding balance, get explicit authorization, then call
  pay_credit_card_from_checking.
- Credit-limit-increase workflow, strictly in order: (1) submit the request
  with request_credit_limit_increase — this only creates the formal record,
  never state an outcome yet; (2) check basic eligibility: account current
  with no past-due balance, no pending disputes (use get_credit_card_disputes),
  sufficient account age, no pending replacement card; (3) call
  approve_credit_limit_increase if every requirement is met, otherwise call
  deny_credit_limit_increase with the single best-fitting denial_reason
  (insufficient_account_age, cooldown_period_active, pending_disputes,
  pending_replacement_card, past_due_balance, high_utilization,
  insufficient_payment_history, requested_amount_exceeds_limit, or other);
  (4) only after that decision call, tell the customer the outcome.

## Disputes and provisional credit
Provisional credit is a temporary credit for the disputed amount while a
dispute is investigated. It is available only if every one of these is
true: the credit-card account has been open at least 60 days; the disputed
amount is at least $25.00 and does not exceed the card's tier maximum
above; the customer has filed no more than 2 disputes in the past 12
months; and, for any reason other than an unauthorized/fraudulent charge
(for example duplicate charge or goods/services not received), the
customer contacted the merchant first. Any single failed criterion makes
the dispute ineligible for provisional credit, but the dispute itself
should still be filed either way. File credit-card disputes with
file_credit_card_dispute, debit-card disputes with file_debit_card_dispute,
and cash-back/rewards miscalculation disputes with file_cashback_dispute,
then tell the customer the provisional-credit outcome and why. If a
customer says an already-resolved dispute was decided incorrectly, use
correct_resolved_dispute rather than filing a new dispute.

## Personal savings account closure
Notice period and early-closure fee depend on tier; the fee is deducted
directly from the account balance with no alternative payment method, so
confirm the balance covers it (or is $0 when no fee applies) and that there
are no pending transactions before closing:
- Entry tier (Bronze Account): $20 fee if closed within 60 days of opening;
  1-day notice.
- Mid tier (Silver Account, Silver Plus Account): $35 fee within 90 days;
  5-day notice.
- Premium tier (Gold Account, Gold Plus Account, Gold Years Account): $75
  fee within 180 days; 10-day notice.
- Elite tier (Platinum Account, Platinum Plus Account, Diamond Elite
  Account): $150 fee within 270 days; 21-day notice; manager approval
  required.

## Linked checking + savings APY boosts
Certain checking-account classes paired with a savings account under the
same profile qualify for an automatic linked-checking APY boost on the
savings balance. The boost applies automatically with no customer action;
if more than one checking account qualifies, only the highest applicable
boost is used; checking APY boosts never stack with each other, but they
do stack with credit-card APY bonuses, relationship bonuses, and
account-tier bonuses. Credit-card APY bonuses on a savings account follow
the same rule among themselves (only the highest qualifying card bonus
applies, and card bonuses do not stack with each other). The exact
percentage for either boost type is documented per savings product — only
state a number that is confirmed by a retrieved product document; if you
do not have it, say the boost applies but the exact rate is not documented
here.

## ATM fees
Domestic and foreign out-of-network ATM fees vary by checking product;
only quote a figure that appears in the retrieved product documentation.
Purple Account ATM-operator-fee rebates are capped at $30 per month; once
that cap is reached, further ATM operator fees that month are not
rebated, and a charge not coded as an ATM operator fee by the merchant or
network also will not be rebated. Use request_atm_fee_credit for an
individual fee-credit request tied to a specific transaction.

## Mobile check deposit
Depositing a check is a customer self-service action performed in the
Rho-Bank app — you never deposit a check yourself. Before the customer
starts, confirm the check is payable to the account owner, is not altered
or damaged, has a valid date with matching written and numeric amounts,
and is endorsed on the back with any required restrictive wording. Use
initiate_customer_self_service_action to make the deposit action available
and then talk the customer through the app steps yourself; do not call any
tool that would perform the deposit for them. Standard deposits are
typically available within 1-2 business days, but account type, amount, or
extended review can change that — once a deposit is submitted, trust the
availability date shown in the app over this general window. Error
guidance: image-quality issues — retake with better lighting and all
corners visible; missing endorsement — sign the back, add the required
wording, and resubmit; amount mismatch — correct the entered amount to
match the printed amount and resubmit; duplicate detected — do not
redeposit, use in-app support if the flag seems wrong; unsupported,
altered, or incomplete check — use a different, eligible check.

## Referrals and applications
Only create a referral link or discuss referral terms for a product that
has a documented, active referral program. If no documented program exists
for the requested product, say so plainly. That absence alone is not a
reason to transfer to a human.

## Business accounts
Business checking and savings opening and product selection follow the
same shape as personal accounts: verify identity, check eligibility
(existing account counts and limits, tenure or balance thresholds when a
procedure specifies them, no accounts closed for cause recently), then
open only after the customer explicitly confirms. Business credit cards
can carry limited-time promotions (for example a first-year annual-fee
waiver for new customers opening within a stated window) and
product-specific merchant exclusions from cash back — only state
exclusions or promo terms that appear in a retrieved product document.

## General reminders
- Act only through the available tools; never tell the customer an action
  succeeded before the corresponding tool call actually returns success.
- If a request needs a field, operation, or scenario that no tool or
  documented rule covers, say so plainly and offer a human transfer rather
  than guessing at a policy.
- Each turn, either give the customer a clear answer or next step, or make
  the necessary tool call(s) — do not mix both in the same turn.
"""


def _load_knowledge_base_text(resources) -> str:
    """Read every knowledge_base/*.json document available in this kit.

    Reads defensively: a pruned kit directory, a missing file, or a
    malformed document is skipped rather than raised, since deployments may
    not ship every kit directory.
    """
    try:
        files = tuple(resources.files)
    except Exception:
        files = ()

    sections = []
    for rel_path in sorted(files):
        if not rel_path.startswith("knowledge_base/") or not rel_path.endswith(".json"):
            continue
        try:
            raw = resources.read_text(rel_path)
            doc = json.loads(raw)
        except Exception:
            continue
        title = doc.get("title") or rel_path
        doc_id = doc.get("id") or rel_path
        content = doc.get("content") or ""
        sections.append(f"### {title} (id: {doc_id})\n{content}".strip())

    if not sections:
        return "(No knowledge-base product documents are available in this deployment.)"

    return "\n\n".join(sections)


def _build_policy_text(kb_text: str) -> str:
    return (
        POLICY_TEXT.strip()
        + "\n\n## Retrieved product documentation (knowledge base)\n\n"
        + kb_text.strip()
    )


def _resolve_model_choice(context):
    """Fix one model configuration for the whole conversation.

    Each entry in context.model_gateway.models is a directly callable
    model configuration: a model name plus whatever constraints that
    configuration pins or leaves open as a choice. We pick one
    configuration up front from a cost-conscious preference order and reuse
    it for every call so behavior stays consistent and reproducible.
    Constraints already pinned by the configuration are left out of the
    resolved kwargs, since the gateway supplies those automatically; only
    open ("one_of") choices are resolved and passed explicitly, since
    omitting a choice is an error.
    """
    models = list(context.model_gateway.models)
    if not models:
        raise RuntimeError("No models are available from the model gateway.")

    by_name = {}
    for entry in models:
        by_name.setdefault(getattr(entry, "model", None), []).append(entry)

    chosen = None
    for name in _MODEL_PREFERENCE_ORDER:
        if name in by_name:
            chosen = by_name[name][0]
            break
    if chosen is None:
        chosen = models[0]

    constraints = getattr(chosen, "constraints", None) or {}
    resolved_kwargs = {}
    for key, value in constraints.items():
        if isinstance(value, dict) and "one_of" in value:
            options = value["one_of"]
            if options:
                resolved_kwargs[key] = options[0]

    return getattr(chosen, "model"), resolved_kwargs


class BankingSupportAgent:
    """Turn-by-turn customer service agent for the Rho-Bank domain.

    Every call to the model gateway is built from scratch: a policy message
    (operating policy plus retrieved product documentation) followed by the
    full conversation transcript so far. The only state threaded between
    turns is that transcript, so a logged call's messages fully capture the
    decision context that produced it.
    """

    def __init__(self, context, model_name, model_kwargs, policy_message):
        self._context = context
        self._model_name = model_name
        self._model_kwargs = model_kwargs
        self._policy_message = policy_message
        self._stopped = False

    def get_init_state(self, message_history=None):
        transcript = list(message_history) if message_history else []
        return {"transcript": transcript}

    def generate_next_message(self, message, state):
        transcript = list(state.get("transcript", []))
        transcript.append(message)

        call_messages = [self._policy_message] + transcript

        assistant_message = self._context.model_gateway.generate(
            model=self._model_name,
            messages=call_messages,
            actions=self._context.action_interface.available,
            tool_choice="auto",
            **self._model_kwargs,
        )

        transcript.append(assistant_message)
        new_state = {"transcript": transcript}
        return assistant_message, new_state

    def is_stop(self, message) -> bool:
        content = getattr(message, "content", None)
        if isinstance(content, str) and TRANSFER_PHRASE in content:
            self._stopped = True
            return True
        return False

    def stop(self) -> None:
        self._stopped = True

    def set_seed(self, seed: int) -> None:
        # No internal randomness to seed; kept for interface compatibility.
        return None


def create_agent():
    """Build and return the agent evaluated by the runtime."""
    context = get_agent_context()

    kb_text = _load_knowledge_base_text(context.resources)
    policy_text = _build_policy_text(kb_text)
    policy_message = UserMessage(role="user", content=policy_text)

    model_name, model_kwargs = _resolve_model_choice(context)

    return BankingSupportAgent(context, model_name, model_kwargs, policy_message)
