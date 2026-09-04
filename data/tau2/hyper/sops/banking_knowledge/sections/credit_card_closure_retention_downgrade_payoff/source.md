## Credit-card closure, retention, downgrade, payoff, and statement-credit handling

Bundle id: `credit_card_closure_retention_downgrade_payoff`

Construction context (guidance for transcript induction, not section
content -- do not extract as policy facts): the shared banking handbook
governs identity verification, explicit customer confirmation before
account-modifying actions, discoverable-tool wrapper behavior, schema
limits, and exact transfer wording. Express these behaviorally in
transcripts where a case exercises them; do not restate them as section
facts. The bundle id, transcript focus, losslessness risks, and shared
context paths in this file are construction metadata, not policy facts.

Transcript focus:
Closure blockers, retention offers, downgrade eligibility, payoff from checking, statement-credit use, and annual-fee waiver/benefit constraints.

Losslessness risks:
- Preserve pre-closure blocker ordering.
- Preserve payoff and statement-credit tools as distinct actions.
- Preserve downgrade and retention eligibility without making offers universal.

Source documents:

### doc_credit_cards_credit_card_account_logistics_002: Internal: Processing Credit Card Account Closures

### Closure Process

1. Verify the customer's identity using standard verification procedures.
2. Confirm all eligibility requirements are met per 'How can I close a credit card account?':
   - Outstanding balance must be $0.00 dollars
   - No pending disputes (pending disputes allowed: No)
   - Account age at least 60 days
   - No pending replacement cards
3. Use the close_credit_card_account_7834 tool to process the closure. Refer to 'How can I close a credit card account?' for eligibility requirements.

#### Tool Arguments

- credit_card_account_id (string): The unique identifier for the credit card account to be closed. This can be found in the customer's account profile or by looking up their credit card accounts.
- user_id (string): The unique identifier for the customer requesting the closure. This should match the authenticated user.

#### Post-Closure Communication

- The customer will receive a confirmation email and a final statement within several business days after the account is closed.
- If asked, remind the customer:
  - Unredeemed rewards can be redeemed for 45 days after the closure request; thereafter, they are forfeited.
  - If an annual fee posted recently, a full refund may apply if the closure occurs within 37 days of the fee charge.

### doc_credit_cards_credit_card_account_logistics_003: Internal: Credit Card Retention Protocol

### Step 1: Verify Closure Eligibility

Before attempting retention, confirm the customer is eligible to close their account. Check these in order:

1. Pending disputes: The account must not have any active or pending transaction disputes. If present, advise the customer to wait for resolution before closing.
2. No pending replacement cards: If a replacement has been ordered and not yet received or activated, a closure cannot proceed.
3. Minimum account age: The account must be open for at least 60 days. If not, inform the customer they cannot close yet.
4. Outstanding balance: The account must have no outstanding balance. If a balance remains, the customer must pay it off before closure.

If any requirement is not met, explain what must be resolved and do not proceed with retention offers.

### Step 2: Check for Previous Retention Attempts (Abuse Prevention)

Use the get_closure_reason_history_8293 tool to determine whether this specific credit card account has any closure reason records within the past year. If records exist for this account within that time frame, skip retention offers and proceed directly to processing the closure.

Tool arguments for get_closure_reason_history_8293:
- credit_card_account_id (string, required): The credit card account ID the customer wants to close.

If records are found within the past year, inform the customer you will proceed with their closure request and move to Step 6.

### Step 3: Understand and Log the Reason

Ask the customer why they want to close their account. Then log it using log_credit_card_closure_reason_4521.

Tool arguments for log_credit_card_closure_reason_4521:
- credit_card_account_id (string, required): The credit card account ID the customer wants to close.
- user_id (string, required): The customer's unique identifier in the system.
- closure_reason (string, required): One of: 'annual_fee', 'not_using_card', 'found_better_card', 'unhappy_with_rewards', 'simplifying_finances', 'negative_experience', 'other'.

Note: Only these three arguments are accepted. Do not add additional parameters.

### Step 4: Address the Concern

Offer tailored solutions based on the customer's reason:

- Annual fee concerns: If they have been a customer for 2+ years, offer to waive their annual fee for one year as a loyalty benefit. Use apply_credit_card_account_flag_6147 (see tool arguments below). If they have been a customer for less than 2 years, offer a permanent downgrade to a no-annual-fee card while preserving account history.

Tool arguments for apply_credit_card_account_flag_6147 (Annual Fee Waiver):
- credit_card_account_id (string, required): The credit card account ID to apply the waiver to.
- user_id (string, required): The customer's unique identifier.
- flag_type (string, required): Use 'annual_fee_waived'.
- expiration_date (string, required): Set to a date a year from today in MM/DD/YYYY format.
- reason (string, required): Use 'loyalty_benefit' for long-tenured customers.

- Not using the card: Remind them of benefits they may be missing and suggest setting up a recurring subscription to keep the card active.
- Found a better card: Ask what features attracted them. If Rho-Bank offers a card with similar or better benefits, offer to help them apply instead of closing the current account.
- Unhappy with rewards: Check enrollment in available bonus categories and suggest ways to maximize rewards based on spending patterns.
- Negative experience: Apologize and gather details. Escalate to a supervisor if warranted. Consider offering a modest goodwill credit for service-related complaints.

Step 5: Make a Retention Offer**

If the customer still wants to close after addressing their concerns, make one retention offer based on their card tier:

- Entry-tier cards: Offer 500 bonus points or a $5 statement credit
- Mid-tier cards: Offer 2,000 bonus points or a $20 statement credit
- Premium and above: Offer 5,000 bonus points or a $50 statement credit

### Step 6: Accept the Decision

If the customer declines the retention offer (or was ineligible due to prior attempts), thank them for being a Rho-Bank customer and proceed with closure. Do not apply pressure.

### Important Reminders When Closure Proceeds

- Inform the customer they have 45 days after submitting the closure request to redeem unredeemed rewards; after that, rewards are forfeited.
- If the annual fee posted recently, advise that a full refund may be available if the closure occurs within 37 days of the fee being charged.

### doc_credit_cards_credit_card_account_logistics_008: Internal: Downgrading a Credit Card to a No-Annual-Fee Card

### When to Offer a Downgrade

Offer a downgrade in these scenarios:

1. Retention protocol: The customer wants to close due to annual fee concerns and has been a customer for less than 2 years (not eligible for annual fee waiver).
2. Customer request: The customer explicitly asks to downgrade to avoid annual fees.

### Available No-Annual-Fee Card Options

- Personal cards: Bronze Rewards Card (no annual fee)
- Business cards: Business Bronze Rewards Card (no annual fee)

Customers may only downgrade within the same category (personal to personal, business to business).

### Downgrade Process

1. Verify the customer's identity using standard procedures.
2. Confirm the customer wants to proceed and understands benefit changes.
3. Inform the customer that account history and credit line will be preserved, and rewards rates/benefits will change to match the new tier.
4. Use downgrade_credit_card_3847 to process the downgrade.

Tool arguments for downgrade_credit_card_3847:
- credit_card_account_id (string, required): The credit card account ID to downgrade.
- user_id (string, required): The customer's unique identifier.
- target_card_type (string, required): One of 'Bronze Rewards Card' (personal) or 'Business Bronze Rewards Card' (business).

### Important Notes

- Credit limit, account number, and account history are preserved during a downgrade.
- Unredeemed rewards points transfer at the same value.
- The downgrade takes effect immediately; the customer continues using the existing physical card until the new card arrives, typically within several business days.
- If the annual fee was paid recently, the customer may be eligible for a prorated refund.

### doc_credit_cards_credit_card_account_logistics_009: Paying Off Credit Card Balance from Checking Account (Internal)

### Purpose

When a customer needs to pay off their credit card balance using funds from their Rho-Bank checking account, you can process the payment directly.

### Prerequisites

1. Verify the customer's identity using standard procedures.
2. Confirm the customer has a Rho-Bank checking account with sufficient funds to cover the payment amount.
3. Look up both the checking account and credit card account to obtain account IDs and verify balances.

### Process

1. Verify the customer's identity.
2. Look up the customer's checking account to confirm sufficient funds.
3. Look up the customer's credit card account to confirm the outstanding balance.
4. Confirm the payment amount with the customer and obtain authorization to transfer.
5. Unlock the pay_credit_card_from_checking_9182 tool using unlock_discoverable_agent_tool.
6. Call the tool using call_discoverable_agent_tool with the required arguments listed below.

### Tool Arguments for pay_credit_card_from_checking_9182

- user_id (string, required): The customer's unique identifier in the system.
- checking_account_id (string, required): The ID of the Rho-Bank checking account to debit.
- credit_card_account_id (string, required): The ID of the credit card account to credit.
- amount (float, required): The payment amount in dollars. Must be positive and cannot exceed the checking account balance or the credit card outstanding balance.

The tool will debit the specified amount from the checking account and reduce the credit card balance by the same amount. A confirmation will include the new balances for both accounts.

### Instructions for Passing the Tool

- Use unlock_discoverable_agent_tool to enable pay_credit_card_from_checking_9182 for the session.
- Then pass the arguments via call_discoverable_agent_tool exactly as listed above, ensuring the account IDs and user_id match the authenticated customer and the amount is authorized.

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

### doc_credit_cards_credit_cards_(general)_016: Checking User Dispute History (Internal)

### Summary

To retrieve a user's credit card dispute history, use the get_user_dispute_history_7291 tool. Call it with the user's user_id to get a list of all disputes filed by that user, including dispute dates, statuses, and transaction details.

### When to Use

- You need a consolidated list of all credit card disputes filed by a specific user.
- You are reviewing the current status or historical progression of a user’s disputes.
- You need transaction-level context for each dispute.

### Required Input

- user_id (required): The user’s canonical internal identifier.

Tip: Ensure you are using the correct and current user_id before making the call.

### Procedure

1. Obtain the user_id for the user whose dispute history you need to review.
2. Invoke the tool with the user_id parameter.
3. Review the returned list of disputes and associated transaction details.

Example invocation (pseudocode):
```
result = get_user_dispute_history_7291(user_id="<user_id>")
```

### Expected Output

- A list of dispute records for the specified user.
- Each record includes:
  - Dispute identifiers and metadata:
    - dispute_id
    - dispute_date
    - status (for example: open, under_review, closed)
    - last_updated_at
  - Transaction details related to the dispute:
    - transaction_id
    - transaction_date
    - merchant_name
    - amount
    - currency
    - card_last4
  - Additional dispute context (if available):
    - reason_code
    - outcome
    - notes or internal comments

Example response shape (illustrative):
```
[
  {
    "dispute_id": "<dispute_id>",
    "dispute_date": "<timestamp>",
    "status": "<status>",
    "last_updated_at": "<timestamp>",
    "transaction": {
      "transaction_id": "<transaction_id>",
      "transaction_date": "<timestamp>",
      "merchant_name": "<merchant>",
      "amount": "<amount>",
      "currency": "<currency>",
      "card_last4": "<last4>"
    },
    "reason_code": "<reason>",
    "outcome": "<outcome>",
    "notes": "<internal_notes>"
  }
]
```

### Interpreting Results

- Verify the list is complete for the user_id you queried.
- Use dispute_date and last_updated_at to understand timeline and recency.
- Use status to determine whether action is needed.
- Review transaction details to confirm the disputed transaction context.

### Error Handling and Troubleshooting

- Empty result set:
  - The user has not filed any credit card disputes, or the user_id is incorrect.
  - Confirm you are using the correct user_id and try again.
- Permission or access error:
  - Ensure you have the necessary internal privileges to view dispute histories.
- Invalid or malformed user_id:
  - Validate the format of user_id and reissue the request.
- Partial or truncated data:
  - Retry the call.
  - If the issue persists, capture the request context and escalate through internal support channels.

### Operational Notes

- This tool returns only credit card disputes associated with the specified user_id.
- Always handle user data in accordance with internal data handling and privacy requirements.

### doc_credit_cards_credit_cards_(general)_017: (Internal) Applying a Credit Card Statement Credit

### Purpose

When an agent needs to apply a statement credit to a customer's credit card account (for goodwill adjustments, promotional credits, fee reversals, or other account credits), use the apply_statement_credit_8472 tool. First unlock the tool using unlock_discoverable_agent_tool, then call it using call_discoverable_agent_tool with the tool name and a JSON string containing all required arguments.

### Steps to Apply a Statement Credit

1. Unlock the tool:
   - Call unlock_discoverable_agent_tool with the tool name apply_statement_credit_8472.

2. Prepare the arguments JSON:
   - Include all required fields exactly as specified in Tool Arguments below.

3. Call the tool:
   - Use call_discoverable_agent_tool with:
     - Tool name: apply_statement_credit_8472
     - Arguments: JSON string containing user_id, credit_card_account_id, amount, and reason

4. Confirm the result:
   - Verify the credit appears as a negative transaction in the customer’s credit card transaction history and reduces the statement balance.

### Tool Arguments

1. user_id (string, required) - The customer's unique user identifier in the system.

2. credit_card_account_id (string, required) - The credit card account ID to apply the credit to. This can be found by calling get_credit_card_accounts_by_user.

3. amount (number, required) - The credit amount in dollars. Must be a positive number (e.g., 25.00 for a $25 credit).

4. reason (string, required) - The reason for the statement credit. Must be exactly one of:
   - 'goodwill_adjustment': One-time courtesy credit for customer satisfaction
   - 'promotional_credit': Credit from a promotional offer or campaign
   - 'annual_fee_reversal': Reversal of an annual fee charge
   - 'late_fee_reversal': Reversal of a late payment fee
   - 'interest_charge_reversal': Reversal of interest charges
   - 'dispute_resolution': Credit issued as part of dispute resolution
   - 'price_match': Credit for a price match guarantee
   - 'retention_offer': Credit offered to retain a customer
   - 'error_correction': Credit to correct a billing error
   - 'other': Other reasons not covered above

### doc_credit_cards_platinum_rewards_card_001: Platinum Rewards Card: Getting Started with Your Platinum Account

### Activate and Set Up
- Activate your card as soon as it arrives, then add it to your digital wallet for immediate use.
- Set up account alerts for transactions, payments, and unusual activity.

### Understand Your Rates and Limits
- Your purchase APR is 16.99% (variable). Review it in your account details before your first transaction.
- Typical approved credit limits range from $25,000 to $150,000. Your exact limit appears in your approval details.

### Payments and Autopay
- Choose an autopay option (minimum due, statement balance, or custom amount) to avoid interest and fees.
- The minimum monthly payment is 2.5% of your outstanding balance.
- A late payment triggers a fee of $32.50. Set due-date reminders to stay on track.

### Fees to Know on Day One
- Annual fee: $200.00.
- Foreign transaction fee: 0% on international purchases.

### Virtual Cards
- Free virtual cards are included: Yes. Use them to protect your primary card number for online purchases.
- Virtual card management is available in your account: Yes. Create, pause, or delete virtual card numbers as needed.

### First Purchases Checklist
- Confirm your billing address and contact details are current.
- Enroll in alerts and autopay.
- Add your card to frequently used merchants and services.
- Use virtual cards for new online merchants to reduce exposure.

### If You Are Still Applying
- Minimum credit score required: $750.

### doc_credit_cards_platinum_rewards_card_002: Platinum Rewards Card: Earning 10% Cash Back

### How You Earn
- You earn 10.0% cash back on all eligible purchases.
- Returns or credits reduce previously earned rewards on a per-transaction basis.

### Eligible and Ineligible Transactions
- Eligible: point-of-sale and online purchases posted to your account.
- Not eligible: cash advances, balance transfers, fees, interest, and other cash-equivalent transactions.

### Posting Timeline
- Rewards accrue when transactions post to your account and typically become available after the purchase posts and clears any return window.

### Redeeming Your Rewards
- You can redeem once your available rewards balance reaches at least $15.
- Common redemption options include statement credits or other available channels in your account dashboard.

### Tips to Maximize Earnings
- Use the card for everyday spend to capture 10.0% on all categories.
- Set the card as your default payment at frequently used merchants.
- Consider your net rewards after the $200.00 annual fee when planning large purchases.

### doc_business_credit_cards_business_platinum_rewards_card_008: Business Platinum Rewards Card: Understanding Your Annual Fee and Premium Perks

### Annual Fee Structure
- Standard annual fee: $450.00
- First-year promotional annual fee: 0

### Premium Perks Included
- Airport lounge visits unlimited: Yes
- Annual travel credits: $400
- Travel insurance maximum per trip: $62,500
- Purchase protection maximum per claim: $17,500
- Foreign transaction fee on international purchases: 0%
- Dedicated account manager assigned: Yes

### How Fees Are Assessed
- The annual fee is billed to your account and renews automatically unless the account is closed before renewal.
- If the promotional first-year fee applies, your first statement will reflect 0 for that period.

### Getting the Most from Your Perks
- Enroll eligible travel services early to use $400.
- Add traveler and loyalty details to streamline lounge access and insurance eligibility.
- Use your card for covered purchases to activate benefits tied to $17,500 and $62,500.

### doc_business_credit_cards_business_platinum_rewards_card_011: Business Platinum Rewards Card: New Customer First Year Fee Waiver

### Promotion Window
- Offer start date: 2025-11-01
- Offer end date: 2026-02-28

### First-Year Annual Fee
- First-year annual fee for new customers: 0
- After the first year, the standard annual fee applies: $450.00

### How the Waiver Is Applied
- The fee waiver is reflected on your account during the first year of membership, provided your account is opened within the promotion dates.
- If you upgrade or change products during the promotional period, the waiver continues only if the account remains eligible.

### Eligibility Guidelines
- Offer is for new customers only and applies to new accounts opened within the promotion window.
- The account must remain open and in good standing to retain the waived first-year fee.

Shared context paths (construction metadata, not policy facts):
- `tau2/hyper/sops/banking_sop.md`
