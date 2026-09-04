## Personal checking opening and product recommendation

Bundle id: `personal_checking_opening_recommendation`

Construction context (guidance for transcript induction, not section
content -- do not extract as policy facts): the shared banking handbook
governs identity verification, explicit customer confirmation before
account-modifying actions, discoverable-tool wrapper behavior, schema
limits, and exact transfer wording. Express these behaviorally in
transcripts where a case exercises them; do not restate them as section
facts. The bundle id, transcript focus, losslessness risks, and shared
context paths in this file are construction metadata, not policy facts.

Transcript focus:
Choosing and opening a personal checking account from customer needs, existing profile data, age/travel/fee preferences, and product differences.

Losslessness risks:
- Preserve product-specific eligibility and fee/benefit differences.
- Preserve when the agent opens an account versus recommends one.
- Do not collapse the checking product catalog into generic tier advice.

Source documents:

### doc_bank_accounts_bank_accounts_(general)_001: Internal: Opening Personal Checking Accounts

### Eligibility Requirements

To open a personal checking account, ensure all of the following are true:
1. The customer is verified.
2. The customer is at least 18 years old.
3. The customer does not exceed 4 personal checking accounts.
4. The customer has no checking accounts closed for cause in the past 6 months.

### Opening Procedure

1. Verify customer identity.
2. Check eligibility requirements listed above.
3. Confirm the customer's desired account_class selection.
   - Personal checking account_class options must use the full official name ending with 'Account' (e.g., 'Blue Account', 'Green Account (checking)').
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

### doc_checking_accounts_blue_account_001: Blue Account at a glance

### Key details
- Monthly maintenance fee: $20.00
- Waiver requirement: maintain a minimum daily balance of $625
- Out-of-network ATM withdrawal: 1% of withdrawal amount (max $3.00)
- Interest earned on balances: 0.01%
- Mobile check deposit daily limit: $2,500
- Early direct deposit: 1 day(s) before payday
- No overdraft fees

#### Quick tips
- Set up alerts to keep your daily balance at or above $625 if you want the monthly fee waived.
- Use in-network ATMs to avoid the 1% out-of-network fee.
- Plan larger check deposits ahead of time if they exceed the $2,500 daily mobile deposit limit.
- With early direct deposit, your paycheck can arrive 1 day(s) early.

### doc_checking_accounts_green_account_(checking)_001: Green Account (checking) at a glance

### Highlights
- No overdraft fees and no overdraft coverage; transactions that exceed your available balance are declined
- Earn 0.11% APY on your checking balance
- Get direct deposits up to 1 day early
- Mobile check deposits up to $3,000 per day
- Boost a linked savings account's APY: Gold +0.75% or Silver +0.25%

### Fees and limits
| Item | Amount |
|---|---|
| Monthly maintenance fee | $22.50 |
| Minimum daily balance to waive fee | $1,350 |
| Paper statement fee (monthly) | $2.50 |
| Out-of-network ATM withdrawal fee | $3.00 |
| Returned deposit fee | $17.50 |
| Incoming domestic wire (receive) | $15.00 |
| APY on balance | 0.11% |
| Daily mobile check deposit limit | $3,000 |
| Early direct deposit | Up to 1 day early |

### Referral program
Refer friends and family to open a Green Account and earn rewards:
- You earn: $20 per successful referral
- They receive: $30 welcome bonus
- Maximum referrals per year: 5
- Qualifying deposit required: $500 within 60 days
- Account tenure requirement: 30 days since becoming a Rho-Bank checking customer.

### Important details
- To avoid the monthly maintenance fee, maintain a minimum daily balance of $1,350 each statement cycle
- If you opt for paper statements, a $2.50 monthly fee applies
- Using a non-network ATM incurs a $3.00 fee; the ATM owner may charge additional fees
- Deposited checks returned unpaid result in a $17.50 fee
- Receiving a domestic wire transfer costs $15.00
- Early direct deposit availability depends on when your payer submits the deposit; funds can post up to 1 day early
- Savings APY boosts apply when you link an eligible Gold or Silver Savings Account: +0.75% or +0.25% respectively

### doc_checking_accounts_green_fee-free_account_001: Green Fee-Free Account: Complete Guide and Table of Contents

### Table of Contents
- Key Figures
- Receiving Domestic Wires
- Returned Deposits
- EveryonePay Daily Limit
- Common Scenarios and Tips

### Key Figures
| Item | Amount |
|---|---|
| Returned deposit fee | $15.00 per returned item |
| Incoming domestic wire fee | $12.50 per incoming wire |
| EveryonePay daily send limit | $2,000 per day |

### Receiving Domestic Wires
- Fee: $12.50 per incoming domestic wire.
- What to expect:
  - The fee is assessed when the wire posts to your account.
  - The sender’s bank may also charge the sender; that is separate from the amount you receive.
- Tips to ensure smooth delivery:
  - Provide your full account name exactly as it appears on your account.
  - Share your account and routing details only through trusted, secure channels.
  - Ask the sender to include your name in the wire memo to help identify funds.

### Returned Deposits
- Fee: $15.00 when a deposited check is returned unpaid by the issuing bank.
- When this can happen:
  - Insufficient funds or a stop payment placed by the issuer.
  - Altered, stale-dated, or otherwise invalid checks.
- How to reduce risk:
  - Accept checks only from trusted parties.
  - Verify funds with the issuer before depositing when possible.
  - Keep deposit receipts and any correspondence with the issuer.

### EveryonePay Daily Limit
- Daily send cap: $2,000 via EveryonePay.
- What counts toward the cap:
  - All successful send transactions created within the same day count against the daily total.
  - Canceled or failed sends generally do not reduce your available daily amount once reversed.
- Managing your daily usage:
  - Plan larger transfers ahead and split them across multiple days if needed.
  - If you reach the cap, you can resume sending when your daily limit refreshes.

### Common Scenarios and Tips
- Combining a wire receipt and a returned check on the same day can result in both the $12.50 and $15.00 applying if each event occurs.
- If you plan to send via EveryonePay and also expect an incoming wire the same day, account for the $12.50 and your $2,000 to avoid interruptions.
- Keep payees informed: if a check you deposited is returned and you incur the $15.00, you may wish to request an alternative payment method, such as a wire or EveryonePay within your $2,000.

### doc_checking_accounts_green_fee-free_account_003: Green Fee-Free Account at a glance

## Snapshot
| Feature | Value |
|---|---|
| Overdraft fee | $0.00 |
| Out-of-network ATM fee (Rho Bank) | $0.00 |
| APY on balances | 0% |
| Mobile check deposit daily limit | $2,500 |
| Early direct deposit | 0 day(s) before payday |

## Notes
- Rho Bank does not charge for non-network ATM withdrawals: $0.00; ATM owners may set a separate surcharge.
- No interest is paid on balances: 0%.
- Mobile check deposits are limited to $2,500 per day.
- You won't incur an overdraft fee: $0.00.
- This account offers 0 day(s) early access to direct deposits.

### doc_checking_accounts_purple_account_001: Purple Account at a glance

### Key numbers

| Item | Value |
|---|---|
| Foreign transaction fee | 0% |
| Foreign ATM withdrawal fee | $0.00 |
| Global ATM fee rebates | Up to $30 per month |
| Currency conversion markup | 0.5% above interbank rate |
| Multi-currency wallet | Yes |
| Supported wallet currencies | 30 |
| Complimentary airport lounge visits | 6 per year |
| Incoming domestic wire fee | $0.00 |
| Mobile check deposit limit (daily) | $5,000 |
| Early direct deposit | 2 days early |
| APY boost with Platinum Plus Savings | +0.3% |
| APY boost with Gold Savings | +0.1% |

### Travel-friendly highlights

- No foreign transaction fees: 0%
- No foreign ATM withdrawal fees: $0.00 per withdrawal (third-party ATM operator fees may still apply)
- Global ATM fee rebates: up to $30 monthly worldwide
- Real-time currency conversion with a markup of 0.5% over the interbank rate
- Multi-currency wallet: Yes with up to 30 supported foreign currencies
- Complimentary airport lounge access: 6 visits per year
- Travel insurance benefits included

### Everyday banking essentials

- $0.00 fee for receiving domestic wire transfers
- Mobile check deposit up to $5,000 per day
- Get paid up to 2 days early with eligible direct deposits
- Earn boosted yields when linked:
  - Platinum Plus Savings: +0.3% APY
  - Gold Savings: +0.1% APY

### doc_checking_accounts_light_blue_account_001: Light Blue Account — summary

### Key costs
- Monthly maintenance fee: $0.00
- Overdraft fee: $0.00
- Cashier’s check (per check): $10

### What this means for you
- You will not incur an overdraft fee when your balance goes negative: the fee is $0.00.
- You pay $0.00 in monthly maintenance fees, so your balance isn’t reduced by a recurring service charge.
- When you need certified funds, each cashier’s check is issued for $10.

### Practical tips
- Use electronic statements and alerts to help you avoid going negative, even though the overdraft fee is $0.00.
- Request a cashier’s check only when necessary to keep your total costs to $10 per check.

### doc_checking_accounts_light_green_account_001: Light Green Account at a glance

### Key details

| Item | Detail |
|---|---|
| Monthly maintenance fee | $0.00 |
| APY on balances | 0.05% |
| Daily spending limit | $300 |
| Daily ATM withdrawal limit | $150 |
| Free out-of-network ATM withdrawals per month | 4 |
| Out-of-network ATM withdrawal fee (after free) | $1.50 |
| Mobile check deposit daily limit | $500 |
| Early direct deposit | 0 day(s) before payday |

#### Notes
- No overdraft fees apply to this account.

#### Quick planning tips
- Plan purchases to stay within the daily cap of $300.
- If you need cash, withdraw up to $150 per day. You get 4 free out-of-network ATM withdrawals per month before the $1.50 fee applies.
- Use mobile check deposit for up to $500 each day.
- Keep funds growing with an APY of 0.05%.
- Direct deposits arrive 0 day(s) before your scheduled payday.

### Refer a friend
Share the Light Green Account with friends and earn rewards:
- You earn: $15 for each successful referral
- They receive: $25 as a welcome bonus
- Maximum referrals: 3 per calendar year

### doc_checking_accounts_dark_green_account_001: Dark Green Account at a glance

### Snapshot

Quick reference to core details you will use most often.

#### Eligibility
- Minimum primary holder age: 17
- Maximum primary holder age: 26

#### Fees and rates
- Monthly maintenance fee: $10.00
- Overdraft protection transfer fee: 0
- Out-of-network ATM withdrawal fee: 1% (min $1.50)
- Annual percentage yield (APY): 1.5%

#### Rewards and perks
- Student loan payment cashback: 1.25%
- Annual academic standing bonus: $62.50
- Partner textbook retailer discount: 10.0%
- Graduation transition bonus: $100.00

#### Limits
- Mobile check deposit daily limit: $1,500

#### Direct deposit
- Early direct deposit: 1 day(s) before payday

#### Quick tables

##### Eligibility and costs
| Item | Value |
| --- | --- |
| Minimum age | 17 |
| Maximum age | 26 |
| Monthly maintenance fee | $10.00 |
| Overdraft protection transfer fee | 0 |
| Out-of-network ATM withdrawal fee | 1% (min $1.50) |

##### Rewards and limits
| Item | Value |
| --- | --- |
| APY | 1.5% |
| Student loan payment cashback | 1.25% |
| Annual academic standing bonus | $62.50 |
| Partner textbook discount | 10.0% |
| Graduation transition bonus | $100.00 |
| Mobile deposit daily limit | $1,500 |
| Early direct deposit | 1 day(s) before payday |

#### Notes
- Rewards and limits apply when eligibility conditions are met and verification is provided where required.
- Fees and rates may change with required notice.
- Get paid 1 day(s) early with direct deposit.

### doc_checking_accounts_gold_years_account_001: Gold Years Account at a glance

### Snapshot

- Designed for customers aged 62 and older
- $0.00 monthly maintenance fee
- Earn 1.0% APY on your checking balance
- 3 complimentary personal check orders per year
- Paper statements: $0.00/month
- Out-of-network ATM withdrawal fee: $0.00
- Early direct deposit: up to 2 days early
- Mobile check deposit limit: $5,000 per day
- Prescription savings: 12.5% at partner pharmacies when you pay with your debit card
- Dedicated senior support line access: Yes
- One-time Social Security direct deposit bonus: $50.00
- Estate planning consultation discount through partner firms: 17.5%
- APY boosts on linked savings: Gold Plus +0.5%, Silver +0.6%

### Quick reference

| Item | Details |
|---|---|
| Monthly maintenance fee | $0.00 |
| APY on checking | 1.0% |
| Free personal check orders | 3 per year |
| Paper statement fee | $0.00 per month |
| Out-of-network ATM withdrawal fee | $0.00 |
| Early direct deposit | Up to 2 days early |
| Mobile check deposit limit | $5,000 per day |
| Prescription discount | 12.5% at partner pharmacies (debit card required) |
| Dedicated senior support line | Yes |
| Social Security direct deposit bonus | $50.00 (one-time) |
| Estate planning consultation discount | 17.5% |
| Linked savings APY boosts | Gold Plus: +0.5%; Silver: +0.6% |

### doc_checking_accounts_bluest_account_001: Bluest Account at a glance

### Key figures

| Item | Value |
|---|---|
| Minimum opening deposit | $75,000 |
| Minimum daily balance to maintain benefits | $112,500 |
| Annual Percentage Yield (APY) | 2.25% APY |
| Complimentary domestic wire transfers per month | 10 |
| International wire fee (outbound) | $12.50 per transfer |
| Complimentary personal check orders per year | 3 |
| ATM fee rebates cap per month | Up to $50 |
| Safe deposit box rental discount | 75.0% |
| Incoming domestic wire fee | $0.00 |
| Mobile check deposit limit (daily) | $10,000 |
| Early direct deposit | 2 day(s) before payday |

#### How to use this summary
- Use the APY and balance details to plan how you keep funds in the account.
- Track monthly caps for ATM rebates and complimentary wires so you can maximize value.
- Remember that incoming domestic wires are credited without an incoming fee.
- If you need higher-volume check usage, note your complimentary orders per year.
- Get paid 2 day(s) early with direct deposit.

### doc_checking_accounts_evergreen_account_001: Evergreen Account at a glance

### Key highlights
- One tree planted for every $750 you spend with your debit card
- Automatic carbon offset on purchases: $1.25 g CO2 per $1 spent
- Earn 0.05% APY on your checking balance
- Extra rewards at partner eco-friendly brands: +1.75% cashback
- Early direct deposit: get your paycheck up to 2 days early
- Mobile check deposit daily limit: $3,500

#### Linked savings boosts
- Link a Green Account (savings): +0.55% APY boost
- Link a Diamond Elite Savings Account: +0.15% APY boost

#### How tree planting works (at a glance)
- For every $750 in eligible spending, we plant one tree on your behalf.
- Example: Spend $750 → 1 tree planted; spend 5× that amount → 5 trees planted.

#### Foreign ATM withdrawals
- Foreign ATM withdrawal fee: 2% of the withdrawal amount, with a minimum of $3.00 per transaction.
- Third-party ATM operator fees may also apply.

#### Refer and grow the green community
- Refer others to join Evergreen and earn $35 per successful referral
- New members receive $25 as a welcome bonus
- Earn up to 6 referral bonuses per calendar year

### Quick reference
| Feature | Amount |
|---|---|
| Tree planting threshold | $750 per tree |
| Carbon offset rate | $1.25 g per $1 |
| Checking APY | 0.05% |
| Eco brand cashback bonus | +1.75% |
| Early direct deposit | Up to 2 days early |
| Mobile deposit daily limit | $3,500 |
| Foreign ATM withdrawal fee | 2% (min $3.00) |
| Green Savings APY boost | +0.55% |
| Diamond Elite Savings APY boost | +0.15% |
| Referral bonus (you earn) | $35 |
| Referral bonus (they receive) | $25 |
| Max referrals per year | 6 |

Shared context paths (construction metadata, not policy facts):
- `tau2/hyper/sops/banking_sop.md`
