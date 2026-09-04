## Credit-limit increase request, eligibility, approval, and denial

Bundle id: `credit_limit_increases`

Construction context (guidance for transcript induction, not section
content -- do not extract as policy facts): the shared banking handbook
governs identity verification, explicit customer confirmation before
account-modifying actions, discoverable-tool wrapper behavior, schema
limits, and exact transfer wording. Express these behaviorally in
transcripts where a case exercises them; do not restate them as section
facts. The bundle id, transcript focus, losslessness risks, and shared
context paths in this file are construction metadata, not policy facts.

Transcript focus:
Customer CLI requests, tier-specific eligibility, payment-history checks, approval/denial processing, and related blockers.

Losslessness risks:
- Preserve tier-specific CLI thresholds.
- Preserve waiting periods and recent-request blockers.
- Do not claim an increase is approved before the internal approval action succeeds.

Source documents:

### doc_credit_cards_credit_card_account_logistics_004: How can I request a CLI?

### Overview

You can request a credit limit increase (CLI) on your Rho-Bank credit card if you meet eligibility criteria. For specific requirements by card tier, refer to the document titled “CLI Eligibility Requirements by Card Tier.”

### How to Submit a Request

Follow these steps to request a CLI:

1. Gather your details
   - Your current credit card account information
   - The new total credit limit you are requesting or the dollar amount of the increase you want
   - A brief reason for the increase (for example: upcoming large purchase, business expansion, improved financial position)

2. Contact Rho-Bank customer support
   - Use secure in-app chat or secure message from your online account
   - Or contact customer support by phone through the number listed in your app or on the website

3. Provide the requested information
   - Share the details listed above
   - Be prepared to supply any additional information if asked during review

4. Confirm submission
   - Ask the support agent to confirm your request has been submitted and to provide a reference confirmation

Notes:
- Only the account owner or an authorized account manager may submit a CLI request for the account.
- Make sure your contact information is up to date so you receive notifications without delay.

### What Happens After You Submit

- Review and decision: Rho-Bank will review your account and the reason for your request. You will receive a decision notification by email within a few business days.
- If approved: Your new credit limit takes effect as soon as the change is processed. You will see the updated limit in your account once the update completes.
- If denied: You will receive an explanation and information about when you can submit another request.

### Tips for a Smooth Request

- State a clear, specific requested limit or increase amount.
- Provide a concise reason tied to your expected spending needs.
- Ensure your account information and communication preferences are current.

### doc_credit_cards_credit_card_account_logistics_005: CLI Eligibility Requirements by Card Tier

### Overview

Use this guide to determine whether you meet the credit limit increase (CLI) eligibility requirements for your card tier. All three criteria must be met at the time you submit your request.

#### Tier Summary

| Card tier     | Minimum account age (days) | Cooldown between requests (days) | Max utilization at request (%) |
|---------------|-----------------------------|-----------------------------------|---------------------------------|
| Entry-tier    | 120 | 120 | 70% |
| Mid-tier      | 90   | 90   | 80%   |
| Premium-tier  | 60 | 60 | 90% |

### 1. Minimum Account Age

Your credit card account must be open for a minimum number of days before you can request a CLI. You qualify on or after the day the minimum is reached.

- Entry-tier: 120 days
- Mid-tier: 90 days
- Premium-tier: 60 days

Example: An entry-tier account open for 119 days does not qualify; on day 120 and beyond it does (assuming other criteria are met).

### 2. Cooldown Period Between Requests

You must wait the required number of days between CLI submissions. This applies only if your most recent request was approved. Denied requests do not trigger a cooldown period.

- Entry-tier: 120 days
- Mid-tier: 90 days
- Premium-tier: 60 days

Tip: Count the cooldown from the date you last submitted a CLI request. For example, if you submitted a mid-tier request recently, you must wait until 90 full days have passed before submitting another.

### 3. Credit Utilization Threshold

Your current credit utilization must be below the maximum threshold at the time you submit your request. Utilization at or above the threshold does not qualify.

- Entry-tier: below 70%
- Mid-tier: below 80%
- Premium-tier: below 90%

Examples:
- If your entry-tier utilization is 71%, it is above 70% and will not qualify.
- If your premium-tier utilization is exactly 90%, it does not meet the “below” requirement; reduce utilization before requesting.

### Quick Eligibility Checklist

Before submitting a CLI request, confirm all of the following for your card tier:

- Your account age is at least the minimum: 120 / 90 / 60 days (based on tier).
- The cooldown since your last CLI submission has fully elapsed: 120 / 90 / 60 days.
- Your current utilization is below the applicable threshold: 70% / 80% / 90%.

If any single criterion is not met, wait until it is (or lower your utilization) before submitting your request.

### doc_credit_cards_credit_card_account_logistics_006: Internal: CLI Payment History and Approval Criteria

This document outlines the payment history requirements and maximum increase limits for CLI requests by card tier.

### Payment History Requirements

The required number of consecutive on-time payment months varies by card tier:

- Entry-tier cards: Requires 6 consecutive months of on-time payments.
- Mid-tier cards: Requires 3 consecutive months of on-time payments.
- Premium-tier cards: Requires 3 consecutive months of on-time payments.

Use the get_payment_history_6183 tool to verify the customer's payment history meets the requirement for their card tier.

### Tool Arguments for get_payment_history_6183

- credit_card_account_id (string, required): The credit card account ID to check.
- months (integer, required): Number of months of payment history to retrieve. Use the appropriate value based on the card tier.

### Maximum Credit Limit Increase Amounts

The maximum increase allowed per request depends on the card tier:

- Entry-tier cards: Maximum increase of 25% of current credit limit per request.
- Mid-tier cards: Maximum increase of 50% of current credit limit per request.
- Premium-tier cards: Maximum increase of 50% of current credit limit per request.

If the customer requests more than the maximum allowed for their tier, inform them of the maximum amount they are eligible for and ask if they would like to proceed with that amount instead.

### doc_credit_cards_credit_card_account_logistics_007: Internal: Processing CLI Approvals and Denials

### Purpose

This document outlines the step-by-step workflow for agents to process CLI requests, including verification and final decision. These steps MUST be followed in the exact order listed.

### Step 0: Confirm Requested Amount is Within Limits

BEFORE submitting any CLI request, verify that the customer's requested increase amount is within the maximum allowed for their card tier. If the requested amount exceeds the limit, inform the customer of the maximum allowed and ask them to adjust their request. Do NOT submit a request that exceeds the tier limit.

### Step 1: Submit the CLI Request

Once the customer has confirmed a valid increase amount within their tier's limits, submit the request on their behalf using the submit_credit_limit_increase_request_7392 tool. This creates a formal record of the request before eligibility checks are performed. Eligibility checks are internal and not exposed to customers, so the submission must happen first.

#### Tool Arguments: submit_credit_limit_increase_request_7392

- credit_card_account_id (string, required): The credit card account ID.
- user_id (string, required): The customer's unique identifier.
- requested_increase_amount (integer, required): The dollar amount by which to increase the credit limit (e.g., 1000 for a $1,000 increase).

### Step 2: Verify Basic Eligibility

After submitting the request, verify the customer meets all eligibility requirements. You MUST check ALL of the following eligibility criteria before making an approval or denial decision as this ensures complete audit records.

1. Account Age: Verify the account has been open for the minimum required days for their card tier.
2. Cooldown Period: Use the get_credit_limit_increase_history_4829 tool to check if the customer has submitted a request within the cooldown period for their card tier. If a request exists within this period, deny the new request and inform the customer when they will be eligible to submit again.
3. No Pending Disputes: Verify the account has no active disputes.
4. No Pending Replacement Cards: Verify there are no outstanding replacement card orders for this account. If a replacement is pending, the CLI cannot be processed until the replacement is delivered or cancelled.
5. Account Good Standing: The account must be current with no past-due balance.
6. Credit Utilization: Verify current utilization is below the maximum threshold for their card tier.

#### Tool Arguments: get_credit_limit_increase_history_4829

- credit_card_account_id (string, required): The credit card account ID to check.

### Step 3: Verify Payment History and Requested Amount

.

### Step 4: Process the Decision

If all requirements are met and the requested amount is within limits:

1. Use the approve_credit_limit_increase_5847 tool to approve and apply the increase.

#### Tool Arguments: approve_credit_limit_increase_5847

- credit_card_account_id (string, required): The credit card account ID.
- user_id (string, required): The customer's unique identifier.
- new_credit_limit (float, required): The new total credit limit to set.

If any requirements are not met:

1. Use the deny_credit_limit_increase_5848 tool to record the denial.

#### Tool Arguments: deny_credit_limit_increase_5848

- credit_card_account_id (string, required): The credit card account ID.
- user_id (string, required): The customer's unique identifier.
- denial_reason (string, required): Must be one of: 'insufficient_account_age', 'cooldown_period_active', 'pending_disputes', 'pending_replacement_card', 'past_due_balance', 'high_utilization', 'insufficient_payment_history', 'requested_amount_exceeds_limit', 'other'.

### Step 5: Communicate the Decision

Inform the customer of the decision and provide next steps. For approvals, confirm the new credit limit. For denials, explain the reason and when they may be eligible to reapply.

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

### doc_credit_cards_credit_cards_(general)_015: Provisional Credit Eligibility Guidelines (Internal)

### Overview
When processing a credit card transaction dispute, you must determine whether the customer is eligible for provisional credit. Provisional credit means the disputed amount is temporarily credited back to the customer's account while the investigation is ongoing.

### Eligibility Criteria — Customer is ELIGIBLE for provisional credit if ALL of the following are true:
1. Account Standing: The customer's credit card account has been open for at least 60 days
2. Dispute Reason Category: The dispute reason is one of the following:
   - 'unauthorized_fraudulent_charge'
   - 'duplicate_charge'
   - 'goods_services_not_received' (only if purchase was made more than 30 days ago)
3. Dispute Amount: The transaction amount must be at least $25.00 and must not exceed the card's maximum provisional credit limit based on card tier (see below)
4. Previous Disputes: The customer has not filed more than 2 disputes in the past 12 months
5. Contacted Merchant: For non-fraud disputes (anything other than 'unauthorized_fraudulent_charge'), the customer must have attempted to resolve with the merchant first

### Maximum Provisional Credit Limits by Card Tier
- Entry Tier (Bronze Rewards Card, EcoCard, Business Bronze Rewards Card, Crypto-Cash Back Card): Maximum $2500.00
- Mid Tier (Silver Rewards Card, Business Silver Rewards Card, Green Rewards Card, Silver Zoom Card): Maximum $5000.00
- Premium Tier (Gold Rewards Card, Business Gold Rewards Card): Maximum $10000.00
- Elite Tier (Platinum Rewards Card, Business Platinum Rewards Card): Maximum $15000.00
- Invitation Tier (Diamond Elite Card): Maximum $25000.00

### NOT Eligible Scenarios
- Account is less than 60 days old
- Dispute reason is 'incorrect_amount', 'goods_services_not_as_described', 'canceled_subscription_still_charging', or 'refund_never_processed'
- Transaction amount is under $25.00 or exceeds the card's maximum limit based on tier
- For non-fraud disputes: customer did not contact merchant first
- 'goods_services_not_received' where purchase was made within the last 30 days (merchant may still be processing delivery)

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

Shared context paths (construction metadata, not policy facts):
- `tau2/hyper/sops/banking_sop.md`
