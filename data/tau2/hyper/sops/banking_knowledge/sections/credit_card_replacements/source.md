## Credit-card replacement ordering, shipping, rejection, and pending-order checks

Bundle id: `credit_card_replacements`

Construction context (guidance for transcript induction, not section
content -- do not extract as policy facts): the shared banking handbook
governs identity verification, explicit customer confirmation before
account-modifying actions, discoverable-tool wrapper behavior, schema
limits, and exact transfer wording. Express these behaviorally in
transcripts where a case exercises them; do not restate them as section
facts. The bundle id, transcript focus, losslessness risks, and shared
context paths in this file are construction metadata, not policy facts.

Transcript focus:
Replacement-card eligibility, shipping options and fees, consequences of replacement, rejected requests, and pending replacement order checks.

Losslessness risks:
- Preserve shipping fees, timing, and option-specific restrictions.
- Preserve pending-order blockers.
- Preserve rejection reasons separately from transfer or dispute handling.

Source documents:

### doc_credit_cards_credit_card_replacements_001: How to Order a Replacement Credit Card (Internal)

### Before you order
- Verify the customer's identity using standard verification procedures.
- Look up the customer's credit card account.
- Confirm the shipping address with the customer (primary or alternate, including any unit or suite information).
- Ask for the replacement reason and record exactly one of: fraud_suspected, lost, stolen, damaged, expired, or other.
- Ask whether they want expedited shipping (advise on possible fees by tier; see Shipping selection).
- Confirm eligibility for replacement in the knowledge base before proceeding. Do not unlock or call the tool unless the customer is eligible. If not eligible, explain next steps per the knowledge base.

### Shipping selection
- Standard delivery: 7–10 business days; no fee.
- Expedited shipping: 2–3 business days; fees by tier:
  - Entry-tier (Bronze Rewards, EcoCard, Business Bronze): $15.00.
  - Mid-tier (Silver Rewards, Business Silver, Green Rewards, Silver Zoom): $10.00.
  - Premium-tier and above (Gold, Platinum, Diamond Elite): $0.00 (complimentary).
- If the reason is fraud_suspected or stolen, strongly recommend expedited shipping to minimize exposure and remind the customer to review recent transactions for unauthorized activity.

### Tool workflow
- Unlock the tool:
  - Use unlock_discoverable_agent_tool with tool_name: order_replacement_credit_card_7291.
- Call the tool:
  - Use call_discoverable_agent_tool with tool_name: order_replacement_credit_card_7291 and include:
    - Customer credit card account identifier (e.g., account_id or card_id from the account lookup).
    - Reason: fraud_suspected, lost, stolen, damaged, expired, or other.
    - Shipping_address: the confirmed address.
    - Shipping_speed: standard or expedited.
    - Expedited_fee_acknowledgement: customer consent captured if a fee applies based on tier.
    - Notes: any relevant context (e.g., travel dates, fraud report reference, delivery instructions).

### After you submit the order
- The old card is automatically cancelled for security and will no longer work for new purchases.
- Communicate the expected delivery window based on the selected method (standard: 7–10 business days; expedited: 2–3 business days).
- Advise the customer to watch for email notifications when the order is placed and when the card ships.
- If the reason was fraud_suspected or stolen, remind the customer to review recent transactions and dispute any unauthorized charges in the app or website.
- Document the interaction and the replacement order details in the customer record.

### doc_credit_cards_credit_card_replacements_002: Credit Card Replacement Shipping Options and Fees

### Delivery timeframes
- Standard delivery: 7–10 business days; free for all cardholders.
- Expedited shipping: 2–3 business days.

### Expedited shipping fees by card tier
- Entry-tier (Bronze Rewards Card, EcoCard, Business Bronze Rewards Card): $15.00.
- Mid-tier (Silver Rewards Card, Business Silver Rewards Card, Green Rewards Card, Silver Zoom Card): $10.00.
- Premium-tier and above (Gold Rewards Card, Business Gold Rewards Card, Platinum Rewards Card, Business Platinum Rewards Card, Diamond Elite Card): $0.00 (complimentary).

### When to choose expedited shipping
- If your card was stolen or you suspect fraud, we strongly recommend expedited shipping to reduce the window for potential misuse.
- If you have upcoming travel or urgent payment needs, expedited shipping can help ensure you receive your card within the accelerated timeframe noted above.

### doc_credit_cards_credit_card_replacements_003: What Happens When You Order a Replacement Card

### What changes immediately
- Your current card is cancelled for security and cannot be used for new purchases.
- A new card is created with a different card number and CVV.

### What stays the same
- Your account number remains unchanged, so recurring payments linked to your account continue without interruption.

### What you need to do next
- Update any saved card details with merchants after you receive the new card.
- If the replacement is due to suspected fraud, review recent transactions in the Rho-Bank app or website and report any unauthorized charges.

### Notifications
- You receive an email when your replacement order is placed and another email when the card ships.
- Track your email for updates and follow any activation instructions included with your new card.

### doc_credit_cards_credit_card_replacements_004: Why was your credit card replacement request rejected

### There is already a pending replacement request
- You cannot submit another replacement while an existing request is still being processed. Wait until the current replacement is delivered or cancelled before submitting a new request.

### You exceeded the replacement limit for your card tier
- Replacement requests are limited within a 60-day period to help protect your account.
- Limits by tier:
  - Entry-tier: up to 2 replacements per period.
  - Mid-tier: up to 3 replacements per period.
  - Premium-tier and above: up to 4 replacements per period.

### Need more help?
- If you believe you have a legitimate need for an additional replacement beyond these limits, contact customer support to request a manual review of your case.

### doc_credit_cards_credit_card_replacements_005: Checking Pending Replacement Card Orders (Internal)

### Purpose

To check if a credit card account has any pending replacement card orders, use the get_pending_replacement_orders_5765 tool. Call it with the credit_card_account_id to check if there are any outstanding replacement card orders for that account. This is important to verify before processing account closures, as accounts with pending replacement orders cannot be closed until the replacement is delivered or the order is cancelled.

### Prerequisites

- You have the correct credit_card_account_id.
- You have permission to use the get_pending_replacement_orders_5765 tool.
- You can authenticate to the internal environment where the tool is available.

### Procedure

1. Locate the credit_card_account_id for the account you are reviewing.
2. Invoke get_pending_replacement_orders_5765 with the credit_card_account_id parameter.
3. Review the response for any outstanding replacement card orders.
4. Document the result in the customer’s case notes before proceeding with any account closure steps.

#### Example invocation (pseudo)

- Input:
  - credit_card_account_id: <credit_card_account_id>

- Call:
  - get_pending_replacement_orders_5765({
    credit_card_account_id: "<credit_card_account_id>"
  })

#### Example response (structure)

- Successful response:
  - orders: a collection of replacement order records, or an empty collection if none are pending

- Order record fields (typical):
  - order_id
  - status (examples: pending, shipped, delivered, cancelled)
  - created_at
  - latest_event_at
  - notes (optional)

### Interpreting Results

- No pending orders:
  - The response contains an empty collection of orders.
  - You may proceed with account closure checks per standard procedures.

- One or more orders returned:
  - Treat the account as having pending replacement activity unless every order is clearly delivered or cancelled.
  - Do not proceed with account closure until at least one of the following is true:
    - The replacement is delivered.
    - The order is cancelled.

- Mixed statuses:
  - If any order is in a non-final state (for example, pending or shipped), consider the account blocked from closure.
  - If all orders are final (delivered or cancelled), proceed with standard closure checks.

### Required Actions Before Account Closure

- If orders are pending:
  - Inform the relevant team that the account cannot be closed.
  - Monitor until delivery or confirm cancellation of the order.
- If no orders are pending:
  - Note the check outcome in the case record and continue with the closure process.

### Troubleshooting

- Invalid credit_card_account_id:
  - Re-verify you are using the account-level identifier, not a card-level identifier.
  - Confirm the identifier format and source.

- Permission or access denied:
  - Ensure your role has access to run get_pending_replacement_orders_5765.
  - Re-authenticate if your session may have expired.

- Empty or ambiguous response:
  - Retry the call.
  - If ambiguity persists, escalate to the support engineering queue with the call context and the credit_card_account_id.

### Best Practices

- Always run this check immediately before initiating any account closure workflow.
- Record the timestamp and outcome of the check in the customer record.
- If multiple orders appear, review each status and proceed only when all orders are delivered or cancelled.

Shared context paths (construction metadata, not policy facts):
- `tau2/hyper/sops/banking_sop.md`
