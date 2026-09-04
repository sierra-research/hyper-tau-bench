## Personal savings opening and product recommendation

Bundle id: `personal_savings_opening_recommendation`

Construction context (guidance for transcript induction, not section
content -- do not extract as policy facts): the shared banking handbook
governs identity verification, explicit customer confirmation before
account-modifying actions, discoverable-tool wrapper behavior, schema
limits, and exact transfer wording. Express these behaviorally in
transcripts where a case exercises them; do not restate them as section
facts. The bundle id, transcript focus, losslessness risks, and shared
context paths in this file are construction metadata, not policy facts.

Transcript focus:
Choosing and opening a savings account from balance, existing accounts, product tiers, fee preferences, and desired APY/benefits.

Losslessness risks:
- Preserve APY, minimums, and account-tier differences from each product doc.
- Preserve customer profile/account lookup before personalized recommendations.
- Do not combine Plus, Platinum, and Diamond Elite eligibility into a vague premium-tier rule.

Source documents:

### doc_bank_accounts_bank_accounts_(general)_002: Internal: Opening Personal Savings Accounts

### Scope and Focus

Procedure for opening personal savings accounts. Eligibility requirements: 1) Customer must be verified, 2) Customer must already have at least one active Rho-Bank checking account, 3) Cannot have more than 5 personal savings accounts, 4) Must not have any accounts in collections or with negative balances, 5) Must have held their checking account for at least 14 days. Steps: 1) Verify customer identity, 2) Check eligibility requirements, 3) Confirm account selection with customer, 4) Use open_bank_account_4821 to open the account (note: account_class must use the full official name ending with 'Account', e.g., 'Silver Plus Account', 'Gold Account'), 5) Ask the customer if they would like you to transfer the opening deposit from their checking account now. If yes, use transfer_funds_between_bank_accounts_7291 to transfer the required amount. If no, inform them they have 30 days to fund the account (via internal transfer or external deposit) or the account will be closed.

### Eligibility Requirements (Internal Checklist)

Confirm all of the following before proceeding:
- Customer identity is verified in our systems.
- Customer has at least one active Rho-Bank checking account.
- Customer currently holds fewer than 5 personal savings accounts.
- Customer has no accounts in collections and no negative balances.
- The customer’s checking account tenure is at least 14 days.

Do not proceed if any item above is not met.

### Step-by-Step Procedure

1) Verify identity
- Authenticate the customer and confirm identity verification status on file.

2) Check eligibility
- Confirm an active checking account exists and meets the 14-day tenure requirement.
- Count existing personal savings accounts; ensure the customer is below the 5 limit.
- Review account status; there must be no collections activity and no negative balances.

3) Confirm account selection
- Discuss available personal savings account options with the customer.
- Capture the exact account_class string. It must be the full official name ending with “Account” (for example, “Silver Plus Account”, “Gold Account”).

4) Open the savings account (agent action)
- Use the open_bank_account_4821 tool with account_type set to 'savings' and the confirmed account_class.

5) Arrange opening deposit
- Ask the customer if they want you to transfer the opening deposit from their checking account now.
  - If yes: use transfer_funds_between_bank_accounts_7291 to transfer the required amount from the customer’s checking account to the newly opened savings account.
  - If no: inform the customer they have 30 days to fund the account (via internal transfer or external deposit) or the account will be closed.

6) Confirm completion
- Provide the new account details and confirm the funding status or the funding deadline.

### Agent Tool Usage (Internal Only)

The AGENT calls these tools directly to perform actions on behalf of the customer. Do not ask the customer to call tools or provide tool parameters.

- Tool: open_bank_account_4821(user_id, account_type, account_class)
  - When to call: After steps 1–3, once eligibility is confirmed and the customer has selected an account_class.
  - How to set parameters:
    - user_id: the authenticated customer’s user identifier.
    - account_type: 'savings' for personal savings accounts.
    - account_class: the full official account name ending with 'Account' exactly as confirmed with the customer.
  - Expected outcome: Creates a new personal savings account for the customer.

- Tool: transfer_funds_between_bank_accounts_7291(source_account_id, destination_account_id, amount)
  - When to call: In step 5, only if the customer authorizes an immediate transfer for the opening deposit.
  - How to set parameters:
    - source_account_id: the customer's Rho-Bank checking account to be debited.
    - destination_account_id: the newly opened personal savings account to be credited.
    - amount: the required opening deposit amount confirmed with the customer.
  - Expected outcome: Moves funds from checking to savings to complete the opening deposit.

### Decision Points and Handling

- Exceeds savings account limit: If the customer already has 5 personal savings accounts, do not open a new one. Inform the customer they have reached the maximum.
- Insufficient checking tenure: If the checking account has been open fewer than 14 days, advise the customer when they will become eligible.
- Collections or negative balances: Resolve these issues first; do not proceed until all accounts are in good standing.
- Customer defers funding: Clearly communicate the 30-day funding window and the consequence of closure if unfunded. Document the acknowledgment in the interaction notes.

### doc_bank_accounts_bank_accounts_(general)_009: Internal: Retrieving Customer Account Information

### Overview

Use get_all_user_accounts_by_user_id_3847 to retrieve the bank accounts (checkings, savings) for a customer.

### When to Use

This tool is essential for:
1. Checking eligibility requirements for opening new accounts (existing account status, balances, account tenure, number of accounts)
2. Verifying pre-closure requirements when closing accounts
3. Looking up account details for customer service inquiries

### Parameters

The tool requires the customer's user_id and returns all account information including:
- account_id
- account_type
- account_class
- status
- balance
- date_opened

### doc_savings_accounts_bronze_account_001: Bronze Savings Account: Complete Guide

### Key rates and fees

| Item | Value |
|---|---|
| Annual Percentage Yield (APY) | 2.0% |
| Monthly maintenance fee | $0.00 |
| Minimum opening deposit | $0 |

### Opening your account
- Fund your account with at least $0.
- You can add funds immediately after the account is opened.

### Earning interest
- You earn interest at an APY of 2.0% on your balance.
- Interest accrues automatically once your account is funded; no additional action is required.

### Fees
- The monthly maintenance fee is $0.00. If this value is $0, no monthly maintenance fee will be charged.

### Practical tips
- Keep the account funded to consistently earn 2.0% APY.
- Review your statements to confirm posted interest and any fees.

### doc_savings_accounts_silver_account_001: Silver Account specifications and requirements

### Key specifications

| Specification | Value |
| --- | --- |
| Minimum opening deposit | $500 |
| Ongoing minimum balance | $1,000 |
| Free withdrawals per statement cycle | 10 |
| Interest compounding | daily |
| Balance threshold for higher APY tier | $10,000 |

### Requirements to open and maintain
- Fund at least $500 when you open the account.
- Maintain at least $1,000 each statement cycle to meet account requirements and avoid monthly fees.
- Track your withdrawal activity; transactions beyond 10 in a cycle may incur an excess withdrawal fee as described in your account disclosures.
- To qualify for the higher APY tier, keep your balance at or above $10,000.
- Interest is compounded daily.

### Helpful tips
- Set up balance alerts to help you stay above $1,000 and, if desired, above $10,000.
- If you expect frequent withdrawals, consider spacing them to remain within 10 per cycle.

### doc_savings_accounts_silver_plus_account_001: Silver Plus Account specifications and requirements

### Account parameters

| Item | Detail |
|---|---|
| Minimum opening deposit | $1,000 |
| Ongoing minimum balance | $2,500 |
| Interest compounding | daily |
| Tier 2 balance threshold | $15,000 |
| Free withdrawals per month | 15 |

#### Opening and maintaining your account
- Fund your new account with at least $1,000 to open it.
- Keep your balance at or above $2,500 to meet the ongoing requirement.

#### Interest structure
- Interest is compounded daily to help maximize earnings.
- Balances at or above $15,000 qualify for Tier 2 interest; lower balances earn the Tier 1 rate.

#### Withdrawal access
- You have up to 15 free withdrawals each month.
- Transactions beyond this free limit may be subject to an excess withdrawal fee per our fee schedule.

### doc_savings_accounts_silver_plus_account_002: Silver Plus: Differences from Silver Account

## What changes with Silver Plus

### Tiered APY
- Silver Plus offers tiered APY with two levels:
  - Tier 1 APY: 3.0% for balances below the Tier 2 threshold.
  - Tier 2 APY: 4.5% for balances at or above the Tier 2 threshold.

### Withdrawal flexibility
- Increased access with up to 15 free withdrawals per month.

### ATM fee support
- Receive ATM fee rebates up to 25 each month.

### Statement delivery
- Paper statements are available for Silver Plus Account holders.
- The monthly paper statement fee is $0.00. You can enable paper statements in your account settings.
- Paperless statements are NOT required for this account (unlike Green Account (savings) which requires paperless).

### Relationship benefits
- Earn an additional relationship APY bonus of 0.025% when you qualify under the relationship criteria.

### doc_savings_accounts_green_account_(savings)_001: Green Account (savings) specifications and requirements

### Key specifications

| Item | Value |
|---|---|
| Minimum opening deposit | $100 |
| Ongoing minimum balance | $500 |
| Maximum free withdrawals per month | 8 |
| Interest compounding frequency | daily |
| Paperless statements required | Yes |
| Debit card made from recycled ocean plastic | Yes |

#### Requirements to open
- Fund the account with at least $100.
- Enroll in paperless statements, as indicated by Yes.

#### Ongoing maintenance
- Keep your balance at or above $500.
- Plan withdrawals to stay within 8 each month.

#### Interest handling
- Interest is compounded daily.

#### Card materials
- Your debit card is made from recycled ocean plastic: Yes.

### doc_savings_accounts_gold_account_001: Gold Savings Account: Complete Guide

### Eligibility and balance requirements
- Maintain at least $10,000 to keep your account in good standing.
- If your end-of-day balance falls below $10,000, you may incur the monthly charge described below.

### APY and earnings
- Your account earns an APY of 5.5% on the balance you maintain.
- Interest accrues on eligible balances and is tied directly to the APY shown above.

### Fees
- Monthly maintenance: $10.00 (charged only if your balance drops below $10,000 during the statement period).
- Transfer fees: Yes for this account tier.

### Withdrawals
- You can make up to 20 withdrawals per month.
- Exceeding the monthly limit may result in transaction denials or delays until the next period resets.

### Transfers
- Internal transfer fees are Yes.
- You can initiate transfers from the Transfers section in online or mobile banking and confirm details before submitting.

### Quick reference
| Item | Detail |
| --- | --- |
| APY | 5.5% |
| Minimum balance | $10,000 |
| Monthly maintenance fee (if minimum not met) | $10.00 |
| Monthly withdrawal limit | 20 |
| Transfer fees | Yes |

### doc_savings_accounts_gold_plus_account_001: Gold Plus Account specifications and requirements

### Key specifications

| Item | Value |
|---|---|
| Opening deposit minimum | $10,000 |
| Minimum balance to maintain | $25,000 |
| Interest compounding frequency | daily |
| Automatic investment sweep threshold | $50,000 |
| Monthly withdrawal limit | 25 withdrawals |

### Requirements to open and maintain

- Fund the account with at least $10,000 at opening.
- Maintain a balance of at least $25,000 to keep account benefits active.
- When your end-of-day available balance exceeds $50,000, excess funds may be moved automatically to your linked investment account according to sweep settings.
- Plan cash flows so you do not exceed 25 withdrawals in a month.
- Interest accrues daily; keeping funds on deposit helps you benefit from compounding.

### doc_savings_accounts_gold_plus_account_002: Gold Plus: Differences from Gold Account

## What is different from Gold

- APY: 6.0% percent on eligible balances in this tier.
- Automatic investment sweep: Yes and designed to move surplus funds to investments when available.
- Quarterly financial reviews: Yes with a dedicated specialist.
- Priority support tier: enhanced for faster routing and resolution.

### Practical impact

- Higher yield potential through an APY of 6.0% percent.
- Automated surplus allocation when Yes is active, reducing idle cash.
- Structured check-ins via Yes to help you fine-tune your approach.
- Elevated service experience under the enhanced support level.

### doc_savings_accounts_platinum_account_001: Platinum Savings Account: Complete Guide

### Balance requirements
- Maintain at least $50,000 to preserve Platinum benefits.
- If your balance dips below $50,000, a monthly maintenance fee of $25.00 may apply until you restore the required balance.

### Earnings
- Your account earns 6.5% APY on the balance you maintain.

### Withdrawals and transfers
- Monthly withdrawal limit: -1 (for Platinum, this indicates unlimited withdrawals).
- Domestic wire transfer fees waived: Yes.

#### Tips for smooth transfers
- For time‑sensitive disbursements, consider a domestic wire since fees are waived and settlement is typically faster than standard external transfers.
- Always confirm recipient details before sending, as wires generally cannot be reversed.

### Concierge banking
- Dedicated personal banker available: Yes.
- How to use it:
  - Request tailored support for complex transactions or financial planning within your account's secure messaging.
  - Ask for proactive account check‑ins or portfolio reviews based on your preferences.

### Day‑to‑day management
- Set balance alerts so you stay above $50,000.
- If you anticipate a large withdrawal, consider timing additional deposits to maintain your required balance and avoid the $25.00 charge.

### doc_savings_accounts_platinum_plus_account_001: Platinum Plus Account specifications and requirements

### Opening requirements
- Initial deposit to open: $50,000

### Ongoing balance and activity
- Minimum balance to maintain the account: $100,000
- Monthly withdrawal limit: -1 (no cap on the number of withdrawals)

### Interest compounding
- Interest is compounded: daily

#### Notes
- If your balance or activity changes, standard account terms apply based on these requirements.

### doc_savings_accounts_platinum_plus_account_002: Platinum Plus: Differences from Platinum Account

## What sets this tier apart
- Higher yield: 7.0% APY on balances
- Dedicated banker support: Yes
- VIP event access: Yes
- Complimentary wealth guidance: 4 hours of consultation per quarter

### Summary of enhancements
You receive elevated earnings with 7.0% APY, personalized service via Yes, invitations to select experiences with Yes, and expanded advisory time totaling 4 hours each quarter.

### doc_savings_accounts_diamond_elite_account_001: Diamond Elite Savings Account: Complete Guide

### What you earn
- Your balance accrues at 7.5%.

### Deposits
- Mobile check deposits are permitted up to $100,000 per day.

### Transfers and payments
- You can transfer out up to $500,000 per day.
- External bank transfers complete in 0 business days.
- All wire transfer fees are waived: Yes.

### Withdrawals
- Withdrawals are not capped monthly. The system reflects this as -1.

### Fees
- Monthly maintenance fee: $0.00.
- Wire transfer fees: Yes.

### Dedicated service
- Access to a dedicated private banker is available: Yes.

### Advisory and planning
- Complimentary investment advisory is included: Yes.

### Events and experiences
- Invitations to exclusive events are provided: Yes.

### Quick reference
| Category | Detail |
|---|---|
| APY | 7.5% |
| Mobile deposit daily limit | $100,000 |
| Max daily outbound transfers | $500,000 |
| Monthly maintenance fee | $0.00 |
| Monthly withdrawal limit | -1 |
| External transfer processing time | 0 business days |
| Wire transfer fees | Yes |
| Private banker access | Yes |
| Investment advisory included | Yes |
| Exclusive event access | Yes |

Shared context paths (construction metadata, not policy facts):
- `tau2/hyper/sops/banking_sop.md`
