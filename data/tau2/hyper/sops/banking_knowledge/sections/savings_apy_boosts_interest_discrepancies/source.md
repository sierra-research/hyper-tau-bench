## Savings APY boosts, bonus selection, credits, and interest discrepancy reports

Bundle id: `savings_apy_boosts_interest_discrepancies`

Construction context (guidance for transcript induction, not section
content -- do not extract as policy facts): the shared banking handbook
governs identity verification, explicit customer confirmation before
account-modifying actions, discoverable-tool wrapper behavior, schema
limits, and exact transfer wording. Express these behaviorally in
transcripts where a case exercises them; do not restate them as section
facts. The bundle id, transcript focus, losslessness risks, and shared
context paths in this file are construction metadata, not policy facts.

Transcript focus:
Resolving suspected savings-interest errors, applying credits, deciding linked-checking APY boosts, and applying credit-card APY bonus stacking/selection rules.

Losslessness risks:
- Preserve APY boost stacking and selection order.
- Preserve when to apply a credit versus submit an interest discrepancy report.
- Preserve account-specific interest calculation and payout timing.

Source documents:

### doc_bank_accounts_bank_accounts_(general)_012: Linked Checking Account APY Boosts for Savings Accounts

Certain personal checking and savings account pairings provide bonus APY on your savings account balance. When you hold both a qualifying checking account and savings account under the same customer profile, the APY boost is automatically applied to your savings account. The following checking and savings account pairings qualify for APY boosts:

1. Green Account (checking) + Gold Account (savings)
2. Green Fee-Free Account (checking) + Bronze Account (savings)
3. Evergreen Account (checking) + Green Account (savings)
4. Blue Account (checking) + Silver Plus Account (savings)
5. Light Green Account (checking) + Diamond Elite Account (savings)
6. Dark Green Account (checking) + Bronze Account (savings)
7. Bluest Account (checking) + Silver Account (savings)
8. Purple Account (checking) + Platinum Plus Account (savings)
9. Gold Years Account (checking) + Gold Plus Account (savings)
10. Light Green Account (checking) + Platinum Account (savings)
11. Green Account (checking) + Silver Account (savings)
12. Evergreen Account (checking) + Diamond Elite Account (savings)
13. Bluest Account (checking) + Bronze Account (savings)
14. Purple Account (checking) + Gold Account (savings)
15. Gold Years Account (checking) + Silver Account (savings)
16. Blue Account (checking) + Platinum Account (savings)
17. Green Fee-Free Account (checking) + Gold Plus Account (savings)
18. Dark Green Account (checking) + Platinum Plus Account (savings)

Note: Only these specific pairings qualify for the linked checking account APY boost. All other checking and savings account combinations do not receive any APY boost from linking. The boost is additive to your savings account's base APY and any credit card APY bonuses you may already have. For the exact APY boost percentages for each pairing, please refer to the specific savings account documentation.

### doc_bank_accounts_bank_accounts_(general)_043: Internal: Applying Credits to Savings Accounts

This document describes the policy and procedure for agents to apply credits to customer savings accounts. Use the apply_savings_account_credit_6831 tool to add a credit transaction to a savings account.

Eligible Circumstances for Applying Credits:

Agents are authorized to apply credits to savings accounts ONLY in the following circumstances:

1. Interest Corrections: If a customer's interest payment was calculated incorrectly due to a system error (e.g., missing APY boost from linked checking account, incorrect tier rate applied, missing relationship bonus), the agent may apply a credit to correct the discrepancy. Before applying: Verify the customer's account details and APY components using get_all_user_accounts_by_user_id_3847, review transaction history using get_bank_account_transactions_9173 to confirm the interest amount credited, calculate the correct interest amount based on documented APY rates and bonuses, determine the difference between expected and actual interest.

2. Fee Refunds: If a fee was incorrectly charged to the savings account (e.g., excess withdrawal fee charged when customer was within limits, monthly maintenance fee charged when balance requirement was met), the agent may apply a credit to refund the incorrect fee.

3. Goodwill Credits: In exceptional circumstances where a customer has experienced significant inconvenience due to bank error, a goodwill credit may be applied. Goodwill credits should be rare and typically require supervisor approval for amounts over $25.

Tool: apply_savings_account_credit_6831
Parameters:
- account_id (string): The savings account ID to credit
- amount (number): The positive dollar amount to credit (must be greater than 0)
- credit_type (string): Must be one of 'interest_correction', 'fee_refund', or 'goodwill_credit'

Procedure:
1) Verify the customer's identity and account ownership
2) Confirm the account is a savings account
3) Verify the customer meets one of the eligible circumstances listed above
4) Calculate the correct credit amount based on the discrepancy or fee
5) Use apply_savings_account_credit_6831 to apply the credit
6) Inform the customer of the applied credit and new account balance

For interest corrections, after applying the credit, you should also submit an interest discrepancy report using submit_interest_discrepancy_report_7294 to ensure the backend team investigates and fixes the underlying issue.

### doc_bank_accounts_bank_accounts_(general)_044: Internal: Submitting Interest Discrepancy Reports

When a customer's savings account interest calculation is incorrect, agents must submit an interest discrepancy report to the backend team for investigation. Use the submit_interest_discrepancy_report_7294 tool to create this report.

When to Submit a Report:

1. Missing APY Boost: Customer has a qualifying checking-savings account pairing but the linked checking APY boost was not applied to their interest calculation.

2. Incorrect Tier Rate: Customer's balance qualifies for a higher APY tier but the lower tier rate was applied.

3. Missing Relationship Bonus: Customer maintains multiple Rho-Bank products but the relationship bonus was not applied.

4. System Calculation Error: Any other discrepancy between expected and actual interest credited.

Tool: submit_interest_discrepancy_report_7294
Parameters:
- account_id (string): The savings account ID with the discrepancy
- user_id (string): The customer's unique identifier
- expected_apy (number): The APY percentage the customer should have received (e.g., 2.775 for 2.775%)
- actual_apy (number): The APY percentage that was actually applied (e.g., 2.5 for 2.5%)
- amount_difference (number): The dollar amount difference between expected and actual interest credited

Procedure:
1) Verify the customer's identity and account ownership
2) Look up the customer's accounts using get_all_user_accounts_by_user_id_3847
3) Check transaction history using get_bank_account_transactions_9173 to find the interest credit
4) Review documentation for the savings account type to determine all applicable APY components (base rate, tier rate, linked checking boost, credit card bonuses, relationship bonus)
5) Calculate the expected APY by adding all applicable components
6) Calculate the discrepancy between expected and actual interest
7) If a discrepancy exists, first apply a credit using apply_savings_account_credit_6831 to correct the customer's account
8) Then submit the discrepancy report using submit_interest_discrepancy_report_7294

Important: Always apply the credit to the customer's account BEFORE submitting the report. The report is for backend investigation to fix the underlying system issue, while the credit immediately resolves the customer's concern.

### doc_bank_accounts_bank_accounts_(general)_045: Credit Card APY Bonuses: Stacking Policy

### Credit Card APY Bonus Stacking Policy

When a customer holds multiple Rho-Bank credit cards that each provide an APY bonus on their savings account, the bonuses do NOT stack. Only the highest applicable credit card APY bonus is applied to the customer's savings account.

#### How it works

1. The system identifies all active Rho-Bank credit cards linked to the customer's profile.
2. For each credit card, the corresponding APY bonus is determined.
3. Only the HIGHEST credit card APY bonus is applied to the savings account.
4. Other credit card bonuses are not added on top.

#### Example

If a customer holds:
- Gold Rewards Card: +0.025% APY bonus
- Platinum Rewards Card: +0.15% APY bonus
- EcoCard: +0.6% APY bonus

The customer receives only the EcoCard bonus of +0.6% (the highest), not the sum of all three.

#### Important distinctions

- Credit card APY bonuses do NOT stack with each other.
- However, credit card APY bonuses DO stack with other types of bonuses, such as:
  - Checking account APY boosts (e.g., Green Account checking boost)
  - Relationship bonuses for holding multiple Rho-Bank products
  - Account tier bonuses

#### Why this policy exists

This policy ensures that customers receive a meaningful benefit for holding premium credit cards while maintaining sustainable interest rates across the product portfolio.

### doc_bank_accounts_bank_accounts_(general)_046: Linked Checking Account APY Boost: Selection Policy

### Multiple Checking Account APY Boost Selection Policy

When a customer holds multiple Rho-Bank checking accounts that each provide an APY boost on their savings account, the boosts do NOT stack. Only the highest applicable checking account APY boost is applied to the customer's savings account.

#### How it works

1. The system identifies all active Rho-Bank checking accounts linked to the customer's profile.
2. For each checking account, the corresponding APY boost for the savings account type is determined.
3. Only the HIGHEST checking account APY boost is applied to the savings account.
4. Other checking account boosts are not added on top.

#### Example

If a customer with a Gold Savings Account holds:
- Green Account (checking): +0.75% APY boost
- Purple Account (checking): +0.1% APY boost

The customer receives only the Green Account boost of +0.75% (the highest), not the sum of both.

#### Important distinctions

- Checking account APY boosts do NOT stack with each other.
- However, checking account APY boosts DO stack with other types of bonuses, such as:
  - Credit card APY bonuses (only highest credit card bonus applies)
  - Relationship bonuses for holding multiple Rho-Bank products
  - Account tier bonuses

#### Why this policy exists

This policy ensures that customers receive a meaningful benefit for holding premium checking accounts while maintaining sustainable interest rates across the product portfolio.

#### Agent Responsibility

When investigating interest discrepancies for customers with multiple checking accounts, agents must:
1. Identify all checking accounts the customer holds
2. Determine which checking account provides the highest APY boost for the savings account type
3. Verify that the system is applying the highest boost, not a lower one
4. If the system selected the wrong checking account, calculate the correct APY and apply an interest correction

### doc_savings_accounts_silver_account_002: Linking Silver Account with a Rho checking account

### What linking does
- When you link your Silver Account to a Rho-Bank checking account, your Silver APY receives an additional [[linked_checking_apy_bonus]].
- If you maintain multiple Rho-Bank products, you may also qualify for a relationship bonus of 0.025% that stacks on top of your base Silver APY.

### How to link your accounts
- From your Rho-Bank dashboard, open your Silver Account and choose the option to link a Rho checking account.
- Confirm both accounts are under the same ownership and tax ID.
- Complete the on-screen authorization to finalize the link; APY adjustments typically appear shortly after linking.

### Ongoing eligibility
- Keep both accounts open and in good standing. Unlinking the checking account can remove the [[linked_checking_apy_bonus]] and may affect your eligibility for the 0.025%.

### doc_savings_accounts_silver_account_003: Interest-rate tiers explained

### Tier structure at a glance

| Balance tier | Balance range | APY |
| --- | --- | --- |
| Below threshold | Less than $10,000 | 2.5% |
| At or above threshold | At least $10,000 | 4.0% |

### How your rate is determined
- Each day, your ending balance is compared to $10,000. If it is below that amount, the applicable APY for that day is 2.5%. If it is at or above that amount, the applicable APY for that day is 4.0%.
- Interest accrues on your daily balance and is compounded daily.

### Tips for staying in the higher tier
- Use balance alerts to help keep your balance at or above $10,000.
- Avoid large same-day transfers out that might temporarily move you below $10,000.

### doc_savings_accounts_silver_account_005: FAQ: Silver Account

## Frequently asked questions

### What APY does the Silver Account pay?
- Your APY depends on your balance tier. The lower tier pays 2.5%, and the higher tier pays 4.0%.

### What minimum balance should I keep, and what happens if I don't meet it?
- Keep at least $1,000 in your account to meet the minimum balance requirement. If you do not meet this requirement for a statement cycle, a monthly maintenance fee of $5.00 applies.

### Is there a cost if I make too many withdrawals?
- Yes. If you exceed the monthly withdrawal limit for your account, an excess withdrawal fee of $2.00 applies to each additional withdrawal.

### Do I get a bonus for having multiple Rho-Bank products?
- Yes. Eligible customers receive a relationship APY bonus of 0.025% added to the base Silver APY.

### Do you rebate ATM fees?
- Yes. You can receive ATM fee rebates up to 15 each month.

### doc_savings_accounts_silver_account_006: Silver Account: How is interest calculated and when is it paid?

### How interest is calculated
- Your applicable APY depends on your balance tier and may be either 2.5% or 4.0%.
- Interest accrues on your daily balance and is compounded daily. We calculate a daily periodic rate from your APY and apply it to the balance for each day of the cycle.

### When interest is paid
- Accrued interest is credited to your account monthly.

### Credit card APY bonuses
- Holding certain Rho-Bank credit cards provides bonus APY on your Silver Account:
  - Bronze Rewards Card: +0%
  - Silver Rewards Card: +0.1%
  - Gold Rewards Card: +0.5%
  - EcoCard: +2.2%
  - Green Rewards Card: +0%
  - Crypto-Cash Back Card: +0.5%

### Practical notes
- If your balance moves between tiers during a cycle, the applicable APY for each day is based on that day's balance. Interest for the cycle is the sum of each day's accrual.

### doc_savings_accounts_green_account_(savings)_003: Green Account (savings): Pairing with EcoCard for bonus APY

### Bonus APY with eligible eco cards

#### How the bonus works
- Your Green Account (savings) earns 4.0% on your balance.
- When you also hold an EcoCard, you receive an additional bonus of 0.5%.
- Your effective APY becomes 4.0% plus 0.5% while eligibility is maintained.

#### Extra rewards at eco-certified merchants
- Eligible purchases at eco-certified merchants can earn an extra cashback bonus of 2.0% when using an EcoCard.

### Credit card APY bonuses
- Other Rho-Bank credit cards also provide APY bonuses on your Green Account (savings):
  - Bronze Rewards Card: +0%
  - Silver Rewards Card: +0.45%
  - Gold Rewards Card: +0%
  - Platinum Rewards Card: +0.35%
  - Diamond Elite Card: +0.6%
  - Green Rewards Card: +0.4%
  - Crypto-Cash Back Card: +0%

#### Maintaining eligibility
- Keep your eligible card in good standing and ensure it remains linked to your Green Account (savings).
- If the card is closed or unlinked, the bonus of 0.5% and the extra cashback of 2.0% will not apply.

### doc_savings_accounts_green_account_(savings)_005: FAQ: Green Account (savings)

### Frequently asked questions

#### What APY does the Green Account (savings) earn?
- 4.0%

#### Do I need to maintain a minimum balance?
- Yes. The minimum balance requirement is $500.

#### Is there a monthly maintenance fee if I do not meet the minimum balance?
- $0.00

#### Can I boost my APY by pairing with an EcoCard or Green Rewards Card?
- Yes. You can receive a bonus of 0.5%.

#### Does Rho-Bank match donations to partner environmental charities?
- Yes. Rho-Bank matches at 50%.

#### How do I confirm my rate and benefits?
- Review your account details in online or mobile banking to see your current APY of 4.0% and any applicable bonus of 0.5%.

### doc_savings_accounts_gold_account_013: Gold Account: Gold Rewards Card holder benefits

### Overview

Gold Account holders who also have a Gold Rewards Card receive exclusive benefits that make the account more accessible. The standard minimum balance requirement of $10,000 is reduced to $5,000 for Gold Rewards Card holders. Additionally, you receive a 0.025% relationship bonus APY on top of the base 5.5% rate. Combined with the existing 30 ATM fee rebates and 20 monthly withdrawals, Gold Rewards Card holders enjoy a premium savings experience with lower balance requirements.

### Benefits summary for Gold Rewards Card holders

- Reduced minimum balance: $5,000 (down from $10,000)
- Relationship bonus APY: 0.025% on top of the base 5.5%
- ATM fee rebates: Up to $30 per month
- Monthly withdrawals: Up to 20 per month

#### Quick reference

| Benefit | Gold Rewards Card holder value |
|---|---|
| Minimum balance requirement | $5,000 (standard: $10,000) |
| APY rate | 5.5% + 0.025% |
| ATM fee rebates (monthly max) | $30 |
| Monthly withdrawal limit | 20 |

### Reduced minimum balance

- If you hold a Gold Rewards Card, your required minimum balance to maintain the Gold Account is automatically reduced to $5,000.
- The standard minimum balance for the Gold Account remains $10,000, but the override applies as long as your Gold Rewards Card is active and associated with your account.

Example:
- Without the card: Minimum balance requirement is $10,000.
- With the card: Minimum balance requirement is $5,000.

### Relationship bonus APY

- Your Gold Account earns the base 5.5% APY.
- As a Gold Rewards Card holder, you receive an additional 0.025% relationship bonus APY on top of the base rate.

Example:
- Base APY: 5.5%
- Relationship bonus APY: +0.025%
- Total APY with the bonus: 6.0%

Notes:
- The relationship bonus is additive to the base rate; it is not a multiplier.
- The bonus applies while your Gold Rewards Card remains active and associated with your Gold Account.

### ATM fee rebates and monthly withdrawals

- You continue to receive up to $30 in ATM fee rebates each month.
- You are allowed up to 20 withdrawals per month.

### How to confirm your benefits are active

- Check your account details to verify:
  - The minimum balance requirement displays as $5,000.
  - The APY displays as 5.5% plus a 0.025% relationship bonus.
  - Your monthly limits show up to $30 in ATM fee rebates and up to 20 withdrawals.

### doc_savings_accounts_gold_account_014: Gold Account: Credit Card APY Bonuses

### Credit card APY bonuses for Gold Account holders

Holding certain Rho-Bank credit cards provides bonus APY on your Gold Account balance. These bonuses are automatically applied when you hold both the credit card and savings account under the same customer profile.

#### Available credit card APY bonuses

| Credit Card | APY Bonus |
|---|---|
| Bronze Rewards Card | +0.15% |
| Silver Rewards Card | +0.2% |
| Gold Rewards Card | +0.025% |
| Platinum Rewards Card | +0.15% |
| Diamond Elite Card | +0.3% |
| EcoCard | +0.6% |
| Green Rewards Card | +0.35% |
| Crypto-Cash Back Card | +0% |

#### Additional Gold Rewards Card benefits

Gold Rewards Card holders receive an additional benefit: the minimum balance requirement is reduced from $10,000 to $5,000.

#### How to qualify

1. Open or maintain a Gold Account.
2. Hold an eligible Rho-Bank credit card under the same customer profile.
3. The APY bonus is automatically applied to your Gold Account earnings.

### doc_savings_accounts_silver_plus_account_009: Silver Plus Account: Credit Card APY Bonuses

### Credit card APY bonuses for Silver Plus Account holders

Holding certain Rho-Bank credit cards provides bonus APY on your Silver Plus Account balance. These bonuses are automatically applied when you hold both the credit card and savings account under the same customer profile.

#### Available credit card APY bonuses

| Credit Card | APY Bonus |
|---|---|
| Bronze Rewards Card | +0.15% |
| Silver Rewards Card | +0.15% |
| Gold Rewards Card | +0.2% |
| Platinum Rewards Card | +0.15% |
| Diamond Elite Card | +0.4% |
| EcoCard | +0.45% |
| Green Rewards Card | +0.1% |
| Crypto-Cash Back Card | +0% |

#### How to qualify

1. Open or maintain a Silver Plus Account.
2. Hold an eligible Rho-Bank credit card under the same customer profile.
3. The APY bonus is automatically applied to your Silver Plus Account earnings.

### doc_savings_accounts_gold_plus_account_009: Gold Plus Account: Credit Card APY Bonuses

### Credit card APY bonuses for Gold Plus Account holders

Holding certain Rho-Bank credit cards provides bonus APY on your Gold Plus Account balance. These bonuses are automatically applied when you hold both the credit card and savings account under the same customer profile.

#### Available credit card APY bonuses

| Credit Card | APY Bonus |
|---|---|
| Bronze Rewards Card | +0.15% |
| Silver Rewards Card | +0.1% |
| Gold Rewards Card | +0.35% |
| Platinum Rewards Card | +0.2% |
| Diamond Elite Card | +0.25% |
| EcoCard | +0.1% |
| Green Rewards Card | +0.05% |
| Crypto-Cash Back Card | +0.3% |

#### How to qualify

1. Open or maintain a Gold Plus Account.
2. Hold an eligible Rho-Bank credit card under the same customer profile.
3. The APY bonus is automatically applied to your Gold Plus Account earnings.

### doc_savings_accounts_platinum_plus_account_009: Platinum Plus Account: Credit Card APY Bonuses

## Credit card APY bonuses for Platinum Plus Account holders

Holding certain Rho-Bank credit cards provides bonus APY on your Platinum Plus Account balance. These bonuses are automatically applied when you hold both the credit card and savings account under the same customer profile.

### Available credit card APY bonuses

| Credit Card | APY Bonus |
|---|---|
| Bronze Rewards Card | +0% |
| Silver Rewards Card | +0% |
| Gold Rewards Card | +0.1% |
| Platinum Rewards Card | +0.4% |
| Diamond Elite Card | +0.6% |
| EcoCard | +0.05% |
| Green Rewards Card | +0% |
| Crypto-Cash Back Card | +0.25% |

### How to qualify

1. Open or maintain a Platinum Plus Account.
2. Hold an eligible Rho-Bank credit card under the same customer profile.
3. The APY bonus is automatically applied to your Platinum Plus Account earnings.

### doc_savings_accounts_platinum_account_010: Platinum Account: Credit Card APY Bonuses

### Credit card APY bonuses for Platinum Account holders

Holding certain Rho-Bank credit cards provides bonus APY on your Platinum Account balance. These bonuses are automatically applied when you hold both the credit card and savings account under the same customer profile.

#### Available credit card APY bonuses

| Credit Card | APY Bonus |
|---|---|
| Bronze Rewards Card | +0% |
| Silver Rewards Card | +0% |
| Gold Rewards Card | +0.15% |
| Platinum Rewards Card | +0.25% |
| Diamond Elite Card | +0.35% |
| EcoCard | +0% |
| Green Rewards Card | +0% |
| Crypto-Cash Back Card | +0% |

#### How to qualify

1. Open or maintain a Platinum Account.
2. Hold an eligible Rho-Bank credit card under the same customer profile.
3. The APY bonus is automatically applied to your Platinum Account earnings.

### doc_savings_accounts_diamond_elite_account_011: Diamond Elite Account: Credit Card APY Bonuses

### Credit card APY bonuses for Diamond Elite Account holders

Holding certain Rho-Bank credit cards provides bonus APY on your Diamond Elite Account balance. These bonuses are automatically applied when you hold both the credit card and savings account under the same customer profile.

#### Available credit card APY bonuses

| Credit Card | APY Bonus |
|---|---|
| Bronze Rewards Card | +0% |
| Silver Rewards Card | +0% |
| Gold Rewards Card | +0% |
| Platinum Rewards Card | +0.1% |
| Diamond Elite Card | +0.5% |
| EcoCard | +0% |
| Green Rewards Card | +0% |
| Crypto-Cash Back Card | +0.15% |

#### How to qualify

1. Open or maintain a Diamond Elite Account.
2. Hold an eligible Rho-Bank credit card under the same customer profile.
3. The APY bonus is automatically applied to your Diamond Elite Account earnings.

Shared context paths (construction metadata, not policy facts):
- `tau2/hyper/sops/banking_sop.md`
