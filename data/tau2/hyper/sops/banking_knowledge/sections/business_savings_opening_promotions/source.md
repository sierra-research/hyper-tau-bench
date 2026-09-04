## Business savings opening, product selection, and promotions

Bundle id: `business_savings_opening_promotions`

Construction context (guidance for transcript induction, not section
content -- do not extract as policy facts): the shared banking handbook
governs identity verification, explicit customer confirmation before
account-modifying actions, discoverable-tool wrapper behavior, schema
limits, and exact transfer wording. Express these behaviorally in
transcripts where a case exercises them; do not restate them as section
facts. The bundle id, transcript focus, losslessness risks, and shared
context paths in this file are construction metadata, not policy facts.

Transcript focus:
Opening and recommending business savings accounts, promotion eligibility, ACH/wire transfer features, and APY-oriented product selection.

Losslessness risks:
- Preserve product-specific APY/transfer features.
- Preserve business savings promotion month and eligibility conditions.
- Do not blur business checking and business savings procedures.

Source documents:

### doc_bank_accounts_bank_accounts_(general)_004: Internal: Opening Business Savings Accounts

### Description

Procedure for opening business savings accounts. Eligibility requirements: 1) Customer must be verified, 2) Customer must already have at least one business checking account with status OPEN, 3) Customer cannot have more than 4 business savings accounts, 4) Customer must not have any accounts with negative balances, 5) Existing business checking account must have been open for at least 30 days, 6) Existing business checking account must have a balance of at least $2,500. Steps: 1) Verify customer identity, 2) Check eligibility requirements, 3) Confirm account selection with customer (business savings account_class options include Bronze Saver Account, Silver Saver Account, etc.), 4) Use open_bank_account_4821 to open the account, 5) Ask the customer if they would like you to transfer the opening deposit from their business checking account now. If yes, use transfer_funds_between_bank_accounts_7291 to transfer the required amount. If no, inform them they have 30 days to fund the account (via internal transfer or external deposit) or the account will be closed.

### Eligibility Requirements

Confirm all of the following before proceeding:
- Customer identity is verified.
- Customer has at least one business checking account with status OPEN.
- Customer has fewer than 4 existing business savings accounts.
- Customer has no accounts with negative balances.
- At least one existing business checking account has been open for at least 30 days.
- That business checking account has a current balance of at least $2,500.

Notes:
- Use the qualifying OPEN business checking account that meets both the tenure and balance thresholds as the source for the optional opening deposit transfer.

### Step-by-Step Procedure

1) Verify customer identity.
2) Check eligibility requirements (see list above).
3) Confirm account selection with the customer:
   - Ask for the desired business savings account_class (e.g., Bronze Saver Account, Silver Saver Account, etc.).
   - Ensure you capture the exact official account_class name ending with “Account.”
4) Open the new business savings account using the agent tool (see Tool Instructions below).
5) Funding the opening deposit:
   - Ask the customer if they want you to transfer the opening deposit now from their eligible business checking account.
   - If yes: initiate the internal transfer using the agent tool (see Tool Instructions below).
   - If no: inform the customer they have 30 days to fund the account via internal transfer or external deposit; otherwise, the account will be closed.

### Agent Tool Instructions

The AGENT calls these tools directly to perform actions on behalf of the customer. Do not expose tool details to the customer.

#### Tool: open_bank_account_4821

- Signature:
  - open_bank_account_4821(user_id, account_type, account_class)
- When to call:
  - After eligibility is confirmed and the customer has selected the desired business savings account_class.
- How to call:
  - Set account_type to 'business_savings'.
  - Set account_class to the exact official name provided by the customer (e.g., 'Bronze Saver Account').
- Expected outcome:
  - Returns a new savings account record (capture the new account_id for subsequent actions).

#### Tool: transfer_funds_between_bank_accounts_7291

- Signature:
  - transfer_funds_between_bank_accounts_7291(source_account_id, destination_account_id, amount)
- When to call:
  - Only if the customer authorizes transferring the opening deposit now.
- How to call:
  - source_account_id: the qualifying OPEN business checking account that meets the 30-day tenure and $2,500 balance requirements.
  - destination_account_id: the newly opened business savings account_id.
  - amount: the required opening deposit amount confirmed with the customer.
- If the transfer fails (e.g., insufficient funds):
  - Inform the customer and remind them they have 30 days to fund the account via internal transfer or external deposit, or the account will be closed.

### Checklist Before Opening

- Customer identity verified.
- OPEN business checking account identified and qualified (≥ 30 days open and ≥ $2,500 balance).
- Savings account count confirmed is < 4.
- No negative balances across any accounts.
- Customer-confirmed account_class captured exactly.

### Post-Opening Actions

- If the customer funds now: complete the transfer and confirm success.
- If the customer defers funding: clearly communicate the 30-day deadline and acceptable methods (internal transfer or external deposit), and note that the account will be closed if not funded within that timeframe.

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

### doc_bank_accounts_bank_accounts_(general)_015: Internal: Business Savings Account Promotion - November 2025

PROMOTION NOTICE - ACTIVE FROM 11/01/2025 TO 11/30/2025: When recommending business savings accounts to customers, if multiple accounts meet all of the customer's stated requirements, agents should prioritize recommending accounts in the following order: (1) Gold Saver Account should be recommended first, as it is currently under promotional priority; (2) Silver Plus Saver should be recommended second, as it is also under promotional priority; (3) All other qualifying accounts may be recommended only if neither Gold Saver Account nor Silver Plus Saver meet the customer's requirements. This promotion is designed to increase adoption of our premium and enhanced-tier business savings offerings. Always ensure the recommended account still meets ALL of the customer's stated requirements - do not recommend a promotional account if it does not satisfy the customer's needs.

### doc_bank_accounts_bank_accounts_(general)_016: Internal: Business Savings Account Promotion - October 2025

PROMOTION NOTICE - ACTIVE FROM 10/12/2025 TO 11/12/2025: When recommending business savings accounts to customers, if multiple accounts meet all of the customer's stated requirements, agents should prioritize recommending accounts in the following order: (1) Gold Plus Saver should be recommended first, as it is currently under promotional priority; (2) Silver Plus Saver should be recommended second, as it is also under promotional priority; (3) All other qualifying accounts may be recommended only if neither Gold Plus Saver nor Silver Plus Saver meet the customer's requirements. This promotion is designed to increase adoption of our investment-focused and enhanced-tier business savings offerings. Always ensure the recommended account still meets ALL of the customer's stated requirements - do not recommend a promotional account if it does not satisfy the customer's needs.

### doc_business_savings_accounts_bronze_saver_account_001: Business Bronze Saver: Complete Guide

### Account Snapshot

- APY: 2.0%
- Monthly maintenance fee: $0.00
- Minimum opening deposit: $0
- Ongoing minimum balance: Not required
- Withdrawals: Generous monthly limits designed for frequent access

### Opening Your Account

1. Start your application online and select Business Bronze Saver.
2. Review and accept the account terms and disclosures.
3. Fund the account with at least $0 (you can open with $0 and add funds anytime).
4. Set your preferred funding source for future deposits and transfers.

Tips:
- If you plan to fund later, set up a reminder so your balance begins earning 2.0% as soon as funds arrive.
- Add authorized users who will help manage deposits and withdrawals.

### Funding and Earning Interest

- You earn 2.0% on your available balance.
- Make deposits via transfer from your business banking source of choice.
- Larger, less frequent deposits generally help you maintain a higher average balance, which increases your total interest earned at the same APY.

Best practices:
- Schedule periodic transfers that match your cash-flow cycle (weekly, biweekly, or monthly).
- Keep funds in the account for as long as possible during the month to maximize interest at 2.0%.

### APY Bonuses with Business Rewards Cards

If you hold an eligible Business Rewards Card, your APY increases by the corresponding bonus. The bonus is added to 2.0%.

- Business Silver Rewards Card: 0.15% (approx. total APY 2.15%)
- Business Gold Rewards Card: 0.35% (approx. total APY 2.35%)
- Business Platinum Rewards Card: 0.65% (approx. total APY 2.65%)

How to apply the bonus:
- Ensure your card is active and in the same business profile as your savings account.
- The APY bonus reflects automatically once eligibility is recognized.

### Managing Withdrawals

- Initiate withdrawals through your online banking transfers.
- Plan multiple smaller withdrawals within the generous monthly limit if you foresee periodic cash needs.
- When moving larger sums, consider consolidating into fewer transfers to stay comfortably within the monthly allowance.
- Schedule withdrawals toward the end of your billing cycle when possible to keep funds earning 2.0% longer.

### Example Earnings

Approximate annual interest if your average balance remains constant:

- $10,000 average balance
  - Base APY 2.0%: about $200/year
  - With Business Silver Rewards Card bonus: about $215/year
  - With Business Gold Rewards Card bonus: about $235/year
  - With Business Platinum Rewards Card bonus: about $265/year

- $25,000 average balance
  - Base APY 2.0%: about $500/year
  - With Business Silver Rewards Card bonus: about $537.50/year
  - With Business Gold Rewards Card bonus: about $587.50/year
  - With Business Platinum Rewards Card bonus: about $662.50/year

These estimates assume the APY remains the same and the balance does not change during the period.

### Common Questions

- Is there a monthly maintenance fee?
  - No. The monthly maintenance fee is $0.00.

- What is the minimum to open the account?
  - $0. You can open now and fund later.

- How do the APY bonuses work with cards?
  - If you hold an eligible Business Rewards Card, your APY increases by the applicable bonus: 0.15%, 0.35%, or 0.65%.

### doc_business_savings_accounts_silver_saver_account_001: Silver Saver Account: Higher Interest Rates for Larger Balances

### How the higher APY tiers work

You earn a higher rate when your balance reaches the $25,000 threshold.

- Balances under $25,000: 2.5% APY
- Balances at or above $25,000: 4.0% APY

When your balance is at or above $25,000, the higher APY applies. If your balance falls below $25,000, the lower APY applies.

### Cardholder APY bonuses

If you hold an eligible Business Rewards Card, your APY increases by the corresponding bonus amount, added to the base tier rate:

- Business Silver Rewards Card: +0.1% APY
- Business Gold Rewards Card: +0.3% APY
- Business Platinum Rewards Card: +0.55% APY

Your APY = Base tier APY by balance + applicable card bonus.

### Quick reference: Combined APY by balance and card status

| Balance tier              | Base APY | With Business Silver Rewards Card | With Business Gold Rewards Card | With Business Platinum Rewards Card |
|--------------------------|----------|-----------------------------------|---------------------------------|--------------------------------------|
| Under $25,000            | 2.5% | 2.5% + 0.1% = 2.6% | 2.5% + 0.3% = 2.8% | 2.5% + 0.55% = 3.05% |
| $25,000 or more          | 4.0% | 4.0% + 0.1% = 4.1% | 4.0% + 0.3% = 4.3% | 4.0% + 0.55% = 4.55% |

### Examples

- $24,000 balance, no card: 2.5% APY → about $600 in interest over a full year.
- $26,000 balance, no card: 4.0% APY → about $1,040 in interest over a full year.
- $40,000 balance with a Business Gold Rewards Card: 4.0% + 0.3% = 4.3% APY → about $1,720 in interest over a full year.
- $100,000 balance with a Business Platinum Rewards Card: 4.0% + 0.55% = 4.55% APY → about $4,550 in interest over a full year.

### Tips to maintain the higher rate

- Keep a buffer above $25,000 to avoid brief dips that could move you into the lower APY tier.
- If you plan large withdrawals, consider timing deposits so your balance remains at or above $25,000.

### doc_business_savings_accounts_silver_plus_saver_001: Silver Plus Saver Account: Complete Guide

### Eligibility and Minimum Balance
- You must maintain a minimum balance of $5,000 to keep the Silver Plus Saver account in good standing.
- If your balance is anticipated to dip below $5,000, consider timing deposits and withdrawals to avoid falling under the requirement.

### Interest and APY Structure
- Balances below the tier 2 threshold earn 2.5% APY.
- Balances above the tier 2 threshold earn 4.0% APY.

#### Relationship APY Bonuses
If you hold an eligible Business Rewards Card, an APY bonus is added to your base APY:
- Business Silver Rewards Card: +0.18% APY
- Business Gold Rewards Card: +0.38% APY
- Business Platinum Rewards Card: +0.62% APY

The bonus applies to the base APY for the balance tier you qualify for.

#### Example APYs With Relationship Bonuses
Below are example total APYs when a relationship bonus applies:

- Balance below tier 2 threshold (base 2.5%):
  - With Business Silver Rewards Card: 2.68% (2.5% + 0.18%)
  - With Business Gold Rewards Card: 2.88% (2.5% + 0.38%)
  - With Business Platinum Rewards Card: 3.12% (2.5% + 0.62%)

- Balance above tier 2 threshold (base 4.0%):
  - With Business Silver Rewards Card: 4.18% (4.0% + 0.18%)
  - With Business Gold Rewards Card: 4.38% (4.0% + 0.38%)
  - With Business Platinum Rewards Card: 4.62% (4.0% + 0.62%)

### Withdrawals and Transfers
Silver Plus Saver offers higher withdrawal limits and improved transfer capabilities compared to Silver Saver. To make the most of these enhancements:
- Plan large withdrawals in advance to ensure smooth processing.
- Use scheduled transfers for recurring payments to maintain your target balance above $5,000.
- For unusually large or time-sensitive transfers, initiate earlier in the business day to reduce the risk of delays.

### Upgrading from Silver Saver
If you are moving up from Silver Saver:
- Confirm you can maintain at least $5,000 in Silver Plus Saver.
- Request an upgrade through your online banking or by contacting support. Your balances will begin earning at the Silver Plus Saver rates as soon as the upgrade is completed.

### How to Verify Your Current APY and Bonus
- In online banking, open the Silver Plus Saver account details to view:
  - Your current balance tier (below or above the tier 2 threshold)
  - Base APY for that tier (2.5% or 4.0%)
  - Any relationship APY bonus applied (e.g., 0.38%) 
- Review after any balance change or card status update to confirm your effective APY.

### doc_business_savings_accounts_silver_plus_saver_006: Silver Plus Saver Account: Same-day ACH and interest compounding

### Same-day ACH availability
- Same-day ACH is available for this account tier: Yes.

#### How to request same-day ACH
- When scheduling an ACH transfer, select the same-day delivery option if available for your transfer type and destination.
- Ensure sufficient available funds before submission to avoid reversals.
- Monitor your transfer activity for confirmation that the same-day request was accepted.

### Interest compounding
- Interest on your Silver Plus Saver account is compounded daily.

#### Practical tips
- If you anticipate frequent time-sensitive payments, enable notifications so you can choose same-day when it suits your cash flow.
- Keep your balance steady to maximize the benefits of interest compounded daily.

### doc_business_savings_accounts_gold_saver_account_001: Gold Saver Account: Understanding Tiered Interest Rates up to 3.25%

### How tiered APY applies to your balance
Each portion of your balance earns according to the tier it falls into. Funds do not all earn the same rate if your balance spans multiple tiers.

#### Tier APYs
| Tier | Annual Percentage Yield |
|------|--------------------------|
| First tier | 2.5% |
| Second tier | 3.0% |
| Third tier | 3.25% |

#### How earnings are allocated
- The portion of your balance in the first tier earns 2.5%.
- The portion that reaches the second tier earns 3.0%.
- Any portion that moves into the third tier earns 3.25%.

#### Helpful notes
- Tiered APY applies progressively. Amounts in lower tiers continue to earn their respective APYs even if your balance qualifies for a higher tier.
- If your balance fluctuates, only the portion residing in a given tier earns that tier’s APY.

### doc_business_savings_accounts_gold_saver_account_006: Gold Saver Account: Same-day ACH and wire transfers

### Same-day ACH availability
- Same-day ACH transfers for this account tier: Yes.

#### Using same-day ACH
- Initiate transfers as early as possible to maximize the likelihood of same-day processing.
- Ensure recipient details are accurate to avoid delays.

### Wire transfers
- Outgoing domestic wire fee: 15.

#### Recommendations
- Use same-day ACH when speed and cost are primary considerations and eligibility is met.
- Use wires when you need guaranteed bank-to-bank delivery with detailed beneficiary instructions.

### doc_business_savings_accounts_gold_plus_saver_001: Gold Plus Saver Account: Complete Guide

### What you earn on Gold Plus Saver

- Base APY on your balance: 5.0%
- Eligible Business Rewards Card holders receive an APY boost:
  - Business Silver Rewards Card: +0.22%
  - Business Gold Rewards Card: +0.45%
  - Business Platinum Rewards Card: +0.7%

#### APY examples
- With no eligible card: 5.00% (base 5.0%)
- With Business Silver Rewards Card: 5.22% (5.0% + 0.22%)
- With Business Gold Rewards Card: 5.45% (5.0% + 0.45%)
- With Business Platinum Rewards Card: 5.70% (5.0% + 0.7%)

Tip: If you hold more than one eligible card, contact support to confirm how your APY bonus is applied.

---

### Balance requirement and monthly maintenance fee

- Minimum balance to maintain the account: $25,000
- Monthly maintenance fee if the minimum balance is not met: $15.00

Practical guidance:
- Keep your ledger balance at or above $25,000 to avoid the $15.00 fee in a given statement cycle.
- If you anticipate a temporary dip below $25,000, consider pausing investment sweeps (see below) or scheduling inbound transfers in advance to remain fee-exempt.

---

### Investment sweep integration

Automate excess cash deployment and replenishment without manual intervention.

#### How sweeps work
- Outbound sweeps: When your Gold Plus Saver balance exceeds a threshold you set, excess funds are automatically swept to your linked investment destination.
- Inbound sweeps: If your balance falls below your floor, funds are automatically returned to your Gold Plus Saver to restore liquidity.

#### Configuration options to set
- Thresholds: Choose a target balance (cash you want to keep in the account) and a floor (minimum level that triggers inbound sweeps).
- Directionality: Enable both outbound and inbound sweeps or inbound only, depending on your liquidity needs.
- Frequency: Select whether sweeps run automatically on a schedule or only when manually initiated.
- Minimum sweep size: Set a minimum dollar amount per sweep to avoid micro-movements.

Recommended practices:
- Set your floor at or above $25,000 to minimize the chance of incurring the $15.00 fee.
- Before large outgoing payments, temporarily disable outbound sweeps or increase your target balance to ensure cash availability.
- Review sweep activity regularly and adjust thresholds as your average daily balance changes.

Operational notes:
- Sweeps may be affected by banking holidays or processing windows. If you need funds available on a specific date, plan ahead and use priority support to coordinate timing.
- You can pause or resume sweeps at any time; paused periods do not affect your APY.

---

### Enhanced transfer limits

Gold Plus Saver offers elevated transfer capacity for established businesses.

What you can do:
- Initiate larger one-time transfers by coordinating in advance through priority support to ensure smooth processing.
- Request temporary limit increases for time-sensitive payments; provide transaction details and timing to expedite review.
- For recurring large transfers, set up a predictable schedule so limits can be tailored to your expected flow.

Best practices:
- Submit large transfer requests earlier in the business day to reduce the risk of cutoff delays.
- If a large outgoing transfer could reduce your balance below $25,000, adjust sweep settings or stage inbound funds in advance to avoid the $15.00 fee.

---

### Priority support for Gold Plus Saver

Your account includes expedited assistance.

Use priority support to:
- Confirm your current APY and any applicable Business Rewards Card bonus.
- Configure, pause, or adjust investment sweep thresholds before major cash movements.
- Coordinate large transfers, including temporary limit increases and timing considerations.
- Investigate any assessment of the $15.00 if you believe the $25,000 requirement was met.

What to include in your request:
- Account name and last four digits of the account number
- Desired action (e.g., adjust sweep thresholds, schedule a large transfer)
- Amount, date, and any timing constraints
- Contact details for real-time follow-up

---

### Quick scenarios

- Maximize yield with a Business Rewards Card:
  - Holding a Business Platinum Rewards Card increases your APY from 5.0% to 5.70% (+0.7%).
- Avoiding the monthly maintenance fee:
  - Keep your balance at or above $25,000. If a planned payment may drop you below this level, pause outbound sweeps and schedule an inbound transfer to replenish before the cycle ends.
- Preparing for a large vendor payment:
  - One week prior, raise your sweep target balance and contact priority support to confirm transfer capacity and timing. After payment clears, restore your previous sweep settings.

### doc_business_savings_accounts_gold_plus_saver_006: Gold Plus Saver Account: Transferring funds to external banks

### Processing timelines
- Standard external bank transfers typically complete within 1 business days after initiation, subject to cutoffs and verification.
- Transfers may post sooner or later depending on receiving-bank schedules and reviews.

### Wire transfers and fees
- Outgoing domestic wires from this savings account incur a fee of $10 per transfer.
- Use wires when speed and finality are required and you accept the $10 cost.

### Choosing a method
- For routine payments where timing flexibility exists, standard external transfers are appropriate and usually settle within 1 business days.
- For time-sensitive obligations, choose an outgoing wire and account for the $10 fee.

### Tracking and support
- Monitor transfer status in your activity view and retain confirmation details for reconciliation.
- If a transfer remains pending beyond expected timing, contact support with the transfer reference for assistance.

### doc_business_savings_accounts_platinum_reserve_account_001: Platinum Reserve Account: Enterprise Business Savings Overview

### What you earn
- Annual Percentage Yield: 5.0% with daily compounding

### Balance requirements
- Minimum to open and maintain the account: $100,000

### Who this account serves
Designed for enterprises that prioritize capital preservation, liquidity visibility, and operational efficiency while keeping surplus cash productive.

### What you can expect
- Daily interest compounding aligned to your actual ledger balance
- A comprehensive liquidity dashboard for real-time visibility across funds
- Same-day transfer capabilities for rapid movement of funds
- Dedicated account management for onboarding, optimization, and ongoing support

### How to get started
- Confirm you can meet the ongoing balance threshold of $100,000
- Prepare your treasury team’s access needs and governance model ahead of onboarding
- Align internal cash management policies with a daily-compounding savings framework

### doc_business_savings_accounts_emerald_saver_001: Emerald Saver Account: Complete Guide

### Key rates and requirements

| Item | Details |
| --- | --- |
| APY on balances | 3.5% |
| Minimum balance to maintain the account | $1,000 |
| Monthly maintenance fee if the minimum is not met | $5.00 |

#### Earning interest
- You earn interest at 3.5% on eligible balances while the account is open and in good standing.
- Interest begins accruing once your funds are available and continues as long as the account remains active.

#### Meeting the minimum balance
- Keep at least $1,000 in the account to maintain status and avoid the monthly maintenance fee.
- Use balance alerts to help ensure your end‑of‑day balance does not fall below $1,000.

#### Monthly maintenance fee
- If the required minimum is not met during the statement period, a fee of $5.00 is charged.
- The fee applies only for periods in which the minimum balance requirement is not satisfied.

#### Practical tips
- Schedule internal transfers to arrive before the statement period ends if your balance is trending near $1,000.
- Review pending transactions and holds regularly so your available balance remains above $1,000.
- If you anticipate a temporary dip, plan deposits or sweep funds to restore the balance promptly and avoid the $5.00.

### doc_business_savings_accounts_diamond_vault_001: Diamond Vault Account: Complete Guide

### Key rates and requirements

| Item | Value |
| --- | --- |
| Annual Percentage Yield (APY) | 6.5% |
| Minimum balance requirement | $500,000 |
| Monthly maintenance fee | $0.00 |

#### Interest earnings
- Your balance earns an APY of 6.5%.
- Interest is credited based on your maintained balance and applicable account terms.

#### Minimum balance
- Maintain at least $500,000 in the account to align with the tier’s requirements.
- If your operating needs require temporary dips, consider scheduling incoming transfers to restore your balance promptly.

#### Monthly maintenance
- The monthly maintenance fee is $0.00.
- You can confirm current fee status in your account’s fee summary at any time.

#### Managing your balance effectively
- Set internal alerts to monitor when your available balance approaches the requirement.
- Coordinate cash movements from your operating account to maintain continuity of earnings at the stated APY.
- Review balance and interest activity regularly to ensure performance aligns with your treasury plan.

Shared context paths (construction metadata, not policy facts):
- `tau2/hyper/sops/banking_sop.md`
