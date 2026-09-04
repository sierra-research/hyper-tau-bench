## Business checking opening, product selection, and promotions

Bundle id: `business_checking_opening_promotions`

Construction context (guidance for transcript induction, not section
content -- do not extract as policy facts): the shared banking handbook
governs identity verification, explicit customer confirmation before
account-modifying actions, discoverable-tool wrapper behavior, schema
limits, and exact transfer wording. Express these behaviorally in
transcripts where a case exercises them; do not restate them as section
facts. The bundle id, transcript focus, losslessness risks, and shared
context paths in this file are construction metadata, not policy facts.

Transcript focus:
Opening and recommending business checking accounts, including current promotions and product-specific ATM/fee features.

Losslessness risks:
- Preserve October vs November promotion eligibility separately.
- Preserve business product eligibility and feature differences.
- Do not merge personal and business checking opening procedures.

Source documents:

### doc_bank_accounts_bank_accounts_(general)_003: Internal: Opening Business Checking Accounts

### Eligibility Requirements

To open a business checking account, ensure all of the following are true:
1. The customer is verified.
2. The customer has at least one existing personal checking account with status OPEN.
3. The customer does not exceed 6 business checking accounts.
4. The customer has no accounts with status CLOSED.
5. The customer's existing checking account has a balance of at least $500.

### Opening Procedure

1. Verify customer identity.
2. Check eligibility requirements listed above.
3. Confirm the customer's desired account_class selection.
   - Business checking account_class options include Navy Blue, Cobalt Blue, True Blue, etc.
4. Use open_bank_account_4821 to open the account.

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

### doc_bank_accounts_bank_accounts_(general)_013: Internal: Business Checking Account Promotion - November 2025

PROMOTION NOTICE - ACTIVE FROM 11/01/2025 TO 11/30/2025: When recommending business checking accounts to customers, if multiple accounts meet all of the customer's stated requirements, agents should prioritize recommending accounts in the following order: (1) Sky Blue account should be recommended first, as it is currently under promotional priority; (2) Lime Green account should be recommended second, as it is also under promotional priority; (3) All other qualifying accounts may be recommended only if neither Sky Blue nor Lime Green meet the customer's requirements. This promotion is designed to increase adoption of our startup and premium business offerings. Always ensure the recommended account still meets ALL of the customer's stated requirements - do not recommend a promotional account if it does not satisfy the customer's needs.

### doc_bank_accounts_bank_accounts_(general)_014: Internal: Business Checking Account Promotion - October 2025

PROMOTION NOTICE - ACTIVE FROM 10/12/2025 TO 11/12/2025: When recommending business checking accounts to customers, if multiple accounts meet all of the customer's stated requirements, agents should prioritize recommending accounts in the following order: (1) Lime Green account should be recommended first, as it is currently under promotional priority; (2) Hunter Green account should be recommended second, as it is also under promotional priority; (3) All other qualifying accounts may be recommended only if neither Lime Green nor Hunter Green meet the customer's requirements. This promotion is designed to increase adoption of our premium and eco-conscious business offerings. Always ensure the recommended account still meets ALL of the customer's stated requirements - do not recommend a promotional account if it does not satisfy the customer's needs.

### doc_business_checking_accounts_sky_blue_001: Getting Started with Sky Blue: Startup Account Setup

### Verify Eligibility
- Confirm your company is within 4 years of formation.
- Check whether you meet the funding requirement: 0.

### Understand Key Cost Terms Before You Apply
- Your startup receives a free period of 6 months.
- After the free period, the monthly maintenance fee is $25.00.
- If your balance goes negative, the overdraft fee is $0.00.

### Prepare Your Application
- Gather company formation documents and ownership details.
- Be ready to provide basic business information and authorized signers.
- Plan initial account settings, such as user permissions and card controls, so you can activate quickly after approval.

### Submit and Configure
- Complete the online application and upload requested documents.
- After approval, log in to set user roles, spending controls, and alerts.
- Link external accounts to enable seamless transfers.

### Startup Referral Program
Help other startups get started with Sky Blue:
- Your bonus: $150 for each successful referral
- Their bonus: $250 welcome bonus
- Annual limit: 8 referrals per year

### First-Funding and Go-Live Checklist
- Make an initial deposit from a linked account.
- Confirm your free period of 6 months is visible in your billing section.
- Review your fee settings to ensure you understand the transition to $25.00 and the overdraft policy of $0.00.

### doc_business_checking_accounts_sky_blue_007: Mobile Banking and Deposits on Sky Blue

### Mobile Check Deposits
- Your daily mobile deposit limit is $25,000.
- Endorse the check, capture clear images, and submit through the mobile app.
- Monitor deposit status in your deposit history and retain the check until confirmation.

### Interest on Balances
- Your account earns an APY of 1.25%.
- Interest is compounded daily.

### ATM Access and Rebates
- Out-of-network ATM fees are rebated up to 15 per month.
- Keep ATM receipts and review posted rebates in your statements.

### Best Practices
- Use well-lit photos for deposits and avoid folded or damaged checks.
- Set balance and deposit alerts to track funds availability and interest accrual.

### doc_business_checking_accounts_sky_blue_010: Sky Blue Account: ATM Fees and Out-of-Network Usage

### Domestic out-of-network ATM usage (U.S.)

- When you withdraw cash at a non‑Rho (out‑of‑network) ATM in the U.S., you are charged an out‑of‑network ATM fee of $1.50 per transaction.
- ATM operators may impose their own surcharges at the terminal. These are separate from Rho’s fees and are disclosed on the ATM screen before you complete the withdrawal.

#### Ways to minimize domestic fees
- Use in‑network ATMs when possible to avoid the out‑of‑network fee of $1.50.
- If you anticipate multiple withdrawals, consider taking out cash less frequently in larger amounts to reduce the number of per‑transaction fees.

### International ATM withdrawals

- For cash withdrawals at foreign (international) ATMs, you are charged 2% of the withdrawal amount, with a minimum fee of $3.00 per withdrawal.
- Local ATM operators may assess additional surcharges. These are set by the operator and are separate from Rho’s fees.

#### Practical tips for international use
- Because a minimum fee of $3.00 applies, fewer, larger withdrawals may reduce the effective fee rate on small cash needs.
- Review the ATM’s on‑screen disclosures before confirming a withdrawal to see any operator surcharges.

### Monthly ATM fee rebates for out-of-network usage

- You are eligible for up to 15 in ATM fee rebates per month for out‑of‑network ATM usage.
- The rebate cap is monthly. If total eligible fees for out‑of‑network usage exceed 15 in a given month, any amount above the cap is your responsibility.

### Common scenarios

- Two domestic out‑of‑network withdrawals in one month:
  - You are charged $1.50 per withdrawal. If the total eligible out‑of‑network fees for the month remain within 15, they are rebated up to that monthly cap.

- International withdrawal of a small amount:
  - The fee is 2% of the withdrawal, subject to the minimum of $3.00 if the calculated percentage is lower.

### If something looks off

- Keep your ATM receipt and check your statement. If a fee or rebate does not appear as expected, contact support and include the date, location, and amount of the withdrawal so we can review it.

### doc_business_checking_accounts_lime_green_001: Lime Green Business Checking: Complete Guide

### Key account values

| Item | Value |
| --- | --- |
| Monthly maintenance fee | $25.00 |
| Annual Percentage Yield (APY) | 1.5% |
| Minimum balance requirement | $5,000 |
| Daily transaction limit | $100,000 |

### Monthly maintenance fee
- You are charged $25.00 for premium account maintenance and dedicated service.
- The fee is drawn directly from the account. If your available balance is insufficient at assessment time, the charge posts when funds are available.

### Minimum balance requirement
- Maintain at least $5,000 to preserve account benefits and avoid balance-related charges that may apply when you are below the requirement.
- Practical tips:
  - Schedule large outgoing payments after confirming that the remaining balance will stay at or above $5,000.
  - Set balance alerts so you can move funds in advance if needed.

### Interest earnings
- Your account earns interest at an APY of 1.5%.
- Interest accrual is based on your balance; keeping funds in the account consistently helps maximize earnings.

### Daily transaction limit
- You can transact up to $100,000 per day across eligible outgoing activity.
- Plan ahead for high-payment days:
  - Confirm the remaining capacity before initiating additional payments.
  - If a single payment could exceed $100,000, split payments across days or queue them to post on different business days.

### doc_business_checking_accounts_lime_green_007: Lime Green Account: ATM Access and Fee Rebates

### ATM Access

- You can use out-of-network ATMs for cash withdrawals. Each out-of-network ATM transaction is assessed a fee of $1.00.
- International (foreign) ATM withdrawals incur a fee equal to 1.5% of the withdrawal amount, with a minimum of $2.50 per withdrawal.

#### Quick reference

| Item | Amount |
|---|---|
| Out-of-network ATM transaction fee (domestic) | $1.00 per transaction |
| Foreign ATM withdrawal fee | 1.5% of amount; minimum $2.50 |
| Monthly ATM fee rebate cap (out-of-network usage) | Up to $25 per month |

### ATM Fee Rebates

- Your account provides monthly rebates of eligible fees from out-of-network ATM usage, up to $25 per month.
- Rebates are applied until the monthly cap is reached; any eligible fees above the cap are your responsibility.
- You do not need to take additional action for eligible rebates—fees and corresponding credits will appear as separate line items on your account activity once processed.

#### What counts toward the monthly cap

- Fees assessed for out-of-network ATM usage that are charged to your account are counted toward the $25 monthly rebate limit.

### How fees are calculated

- Domestic out-of-network usage: Each withdrawal is charged $1.00.
- Foreign ATM withdrawals: The fee is 1.5% of the withdrawal amount, with a minimum of $2.50. If the percentage-based amount is less than $2.50, the $2.50 minimum applies.

### Examples

- Domestic, multiple withdrawals:
  - If you make several out-of-network withdrawals in a month, each is charged $1.00. Eligible out-of-network ATM fees will be rebated up to a total of $25 for that month.

- Foreign withdrawal:
  - For a single international withdrawal, your fee is calculated at 1.5% of the withdrawn amount, subject to a $2.50 minimum. The applicable amount is charged at the time the transaction is processed.

### Tips to reduce fees

- Consolidate cash needs into fewer withdrawals to limit per-transaction charges of $1.00.
- Monitor your monthly total of out-of-network ATM fees to understand how close you are to the $25 rebate cap.

### doc_business_checking_accounts_hunter_green_001: Getting Started with Hunter Green Business Checking

### Quick start checklist
- Confirm your delivery preference: paperless statements are required (Yes). You will manage statements digitally from day one.
- Review pricing: the monthly maintenance fee is $25.00. You can avoid this charge by maintaining at least $5,000 in your account.
- Understand earnings: your account earns 1.0% APY on your balance.
- Know the overdraft policy: the overdraft fee is $0.00.

### Set up essentials
- Activate e-statements in your profile settings to ensure uninterrupted delivery, since Yes applies.
- Add your funding source and make an initial deposit according to your business needs.
- Confirm your balance strategy so that you consistently meet the $5,000 waiver threshold if you want to avoid the $25.00.

### Interest and statements
- Track your accrued interest at the 1.0% APY in your account activity.
- Download statements from your online documents center; statements will reflect any $25.00 assessed and interest credited.

### Tips for a smooth start
- Set internal reminders to check that your balance remains at or above $5,000 before statement cycle close to avoid $25.00.
- If your operations are sensitive to overdrafts, note that the overdraft fee is $0.00.

### Referral program

Once you're settled in, consider referring other eco-conscious businesses:

- **Referrer reward**: $175 for each successful referral
- **New member bonus**: $125 for the business you refer
- **Annual limit**: Up to 10 referral bonuses per year
- **Requirement**: Referred business must deposit $10,000 within 90 days
- **Eligibility**: A minimum relationship duration of 60 days as a checking account holder is required. 

Share the Hunter Green commitment to sustainability while growing your professional network.

### doc_business_checking_accounts_hunter_green_010: Hunter Green Account: ATM Fees and Out-of-Network Usage

### Fee Summary

- Out-of-network (non‑Rho) ATM transactions (domestic): $2.00 per transaction
- International ATM withdrawals: 2.5% of the withdrawal amount, with a minimum of $4.00 per withdrawal
- Monthly ATM fee rebates for out-of-network usage: Up to $20 per month

Note: ATM owner/operator surcharges are set by the ATM and are separate from Rho fees.

### How Fees Apply

#### Domestic out-of-network usage
- Each cash withdrawal at a non‑Rho ATM incurs a $2.00 fee.
- Any surcharge displayed by the ATM owner/operator will be charged in addition to the Rho fee.
- Eligible out-of-network ATM fees are automatically rebated until you reach the monthly cap of $20.

#### International ATM withdrawals
- Each withdrawal outside the U.S. incurs a fee of 2.5% of the withdrawal amount, with a minimum charge of $4.00 per withdrawal.
- If the international withdrawal is made at a non‑Rho ATM, the $2.00 out-of-network fee also applies.
- ATM owner/operator surcharges at foreign ATMs may also be charged.
- Eligible out-of-network ATM fees are rebated up to the monthly maximum of $20.

### Calculating Your Total Cost

For each ATM withdrawal:
1. Add any ATM owner/operator surcharge shown at the terminal.
2. If the ATM is non‑Rho, add $2.00.
3. If the withdrawal is international, add 2.5% of the withdrawal amount (minimum $4.00).
4. Subtract any applicable rebates, up to a total of $20 per month.

### Examples

- Domestic, non‑Rho ATM, $100 withdrawal:
  - Rho out-of-network fee: $2.00
  - Plus any ATM owner surcharge
  - Rebated up to your remaining monthly $20 cap

- International ATM, $100 withdrawal:
  - International fee: 2.5% of $100 = $2.50, but minimum applies → $4.00
  - Out-of-network fee (if the ATM is non‑Rho): $2.00
  - Plus any ATM owner surcharge
  - Rebated up to your remaining monthly $20 cap

- International ATM, $400 withdrawal:
  - International fee: 2.5% of $400 = $10.00
  - Out-of-network fee (if the ATM is non‑Rho): $2.00
  - Plus any ATM owner surcharge
  - Rebated up to your remaining monthly $20 cap

### Posting and Visibility

- Fees and any related rebates appear as separate line items on your account activity and statements.
- You can track how much of the $20 monthly rebate you have used by reviewing your statement or recent transactions.

### doc_business_checking_accounts_navy_blue_001: Navy Blue Business Checking: Complete Guide

### Key Account Costs and Limits

- Monthly maintenance fee: $0.00
- Annual Percentage Yield (APY) on balances: 0.5%
- Daily digital transfer limit: $25,000

#### What you can expect day to day
- No minimum balance requirement, so you can use the account flexibly.
- Unlimited digital transfers within the daily limit of $25,000.
- Optional overdraft settings are available if you want coverage on eligible transactions.
- E-statements are included at no additional cost.

#### Practical tips for managing your account
- Use e-statements to keep records organized and accessible.
- Plan larger transfers with the daily limit of $25,000 in mind; schedule across days if needed.
- Keep an eye on your balance to maximize earnings at 0.5%.

#### Quick reference
| Item | Amount |
| --- | --- |
| Monthly maintenance fee | $0.00 |
| APY | 0.5% |
| Daily digital transfer limit | $25,000 |

### Business Referral Program

Grow your network and earn rewards by referring other businesses to Navy Blue:

| Referral Detail | Value |
| --- | --- |
| Your referral bonus | $100 |
| New business welcome bonus | $75 |
| Maximum referrals per year | 10 |
| Required qualifying deposit | $5,000 |
| Deposit must be made within | 90 days |
| Your account age requirement | 60 days |

To qualify: The referred business must open a Navy Blue account and deposit at least $5,000 within 90 days of account opening. Referrer eligibility requires having been a Rho-Bank checking customer for 60 days or more.

### doc_business_checking_accounts_true_blue_001: True Blue Business Checking: Complete Guide

### What you pay
- Monthly maintenance fee: $75.00

### Balance requirements
- Maintain at least $25,000 to keep the account in good standing and access premium features.

### Transactions included
- Transactions included per month: -1 (unlimited)

### Interest on balances
- Annual Percentage Yield (APY): 2.0%
- Interest accrues on your collected balance and is credited according to the account terms.

### Practical guidance
- Keep your end-of-day balance at or above $25,000 to avoid interruptions to premium capabilities.
- Use the account for high-volume activity without worrying about transaction limits, as the included transactions per month are -1.

### doc_business_checking_accounts_world_blue_001: Getting Started with World Blue International Checking

### Quick checklist before you begin
- Confirm you can maintain at least $10,000 across currencies to keep the account in good standing
- Be aware of the monthly maintenance fee of $50.00
- Decide which of the up to 35 supported currencies you plan to hold and transact in
- Verify that your intended counterparties and destinations are within the $140 supported regions for sending and receiving payments

### Initial setup steps
- Fund your account so you can meet ongoing balance needs
- Add the currency wallets you will use for operations and settlements
- Set a primary operating currency for reporting and reconciliation
- Configure payee profiles for your frequent counterparties within the supported regions
- Review user access and prepare to assign permissions based on roles and responsibilities

### Key thresholds and limits at a glance

| Item | Value |
|---|---|
| Monthly maintenance fee | $50.00 |
| Minimum balance requirement | $10,000 |
| Supported currencies | 35 |
| Supported regions for payments | $140 |

### First-week best practices
- Keep an operating buffer above $10,000 to avoid service interruptions
- Start with a small set of currency wallets and expand as your payment flows stabilize
- Validate a test payment to a known counterparty in one of the supported regions and confirm posting and reconciliation
- Set alerts and reports aligned to your treasury cadence to monitor balances and activity

### Referring other businesses to World Blue

As a Rho-Bank checking account holder, you can refer other businesses to World Blue. To be eligible to refer:
- You must have maintained checking account status with Rho-Bank for at least 90 days

For a referral to qualify:
- The referred business must open a World Blue account
- They must deposit at least $25,000 within 90 days of account opening

### doc_business_checking_accounts_beige_001: Implementing Beige: Enterprise Treasury Onboarding

### Onboarding timeline and responsibilities
- Confirm executive sponsorship and authorized signers before initiating onboarding.
- Prepare onboarding documentation, treasury policy, and internal approval matrix.
- Identify primary funding sources for initial deposits and recurring cash flows.

### Funding and balance setup
- Maintain at least $250,000 to keep your enterprise-level treasury account in good standing.
- The monthly maintenance fee is $200.00. This fee is waived when your average balance meets or exceeds $500,000.
- If you anticipate balance variability during early implementation, align funding schedules to preserve eligibility for the fee waiver threshold.

### Dedicated support structure
- You are assigned 2 dedicated account managers who coordinate onboarding milestones, entitlements, and operational readiness.
- Establish a recurring operating cadence with your account team for progress tracking and rapid issue resolution.

### Overdraft settings during go-live
- Overdrafts incur a fee of $0.00.
- If you plan to stagger incoming funds across multiple institutions, configure conservative payment windows and internal approvals to avoid negative balances.

### Operational readiness checklist
- Set signer roles and entitlements consistent with your treasury policy.
- Add internal approval rules for payments and administrative changes in line with your governance model.
- Validate statement delivery preferences, reporting formats, and reconciliation identifiers prior to first close.
- Confirm that funding sources are scheduled to achieve at least $250,000 and, if desired, the waiver threshold of $500,000.

### Reference values for onboarding
| Item | Value |
| --- | --- |
| Monthly maintenance fee | $200.00 |
| Minimum balance requirement | $250,000 |
| Fee waiver balance threshold | $500,000 |
| Dedicated account managers | 2 |
| Overdraft fee | $0.00 |

### doc_business_checking_accounts_cobalt_blue_001: Getting Started with Cobalt Blue Business Checking

### Set up your account
Follow these steps to start using your account immediately:

- Fund your account to begin transacting and to work toward waiving the monthly fee
- Enroll in online and mobile banking to monitor balances, interest, and transaction activity
- Set account alerts for balance thresholds and transaction activity so you can stay on top of usage
- Add authorized users and establish permissions as needed for your business operations

### Know your core costs and how to avoid them
- Monthly maintenance fee: $20.00
- How to waive it: maintain a daily balance at or above $2,500

Tip: Use balance alerts to help you remain above $2,500 throughout the statement cycle.

### Start earning interest
- Your balance earns an APY of 0.5%
- Interest begins accruing once your initial deposit is received and available

### Manage your monthly activity
- You get $175 free transactions per month (deposits, withdrawals, and transfers)
- After you use your included allotment, additional transactions may incur a fee

### Grow your network with referrals
Once you're established, refer other businesses to Cobalt Blue:
- You earn: $150 per successful referral
- They receive: $100 as a welcome bonus
- Maximum referrals: 10 per calendar year

### First-week checklist
- Make your initial deposit and confirm it has posted
- Set a balance alert at or slightly above $2,500
- Review your current month's usage against the $175 limit
- Verify interest is accruing at 0.5% on your available balance

### Where to find these details
- Account summary: shows current balance against the $2,500 waiver requirement
- Activity tracker: displays monthly usage versus the $175 limit
- Interest section: displays the current APY of 0.5% and accrued interest to date

Shared context paths (construction metadata, not policy facts):
- `tau2/hyper/sops/banking_sop.md`
