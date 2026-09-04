## Checking-account ATM fees, rebates, and fee credits

Bundle id: `checking_atm_fee_rebates_and_credits`

Construction context (guidance for transcript induction, not section
content -- do not extract as policy facts): the shared banking handbook
governs identity verification, explicit customer confirmation before
account-modifying actions, discoverable-tool wrapper behavior, schema
limits, and exact transfer wording. Express these behaviorally in
transcripts where a case exercises them; do not restate them as section
facts. The bundle id, transcript focus, losslessness risks, and shared
context paths in this file are construction metadata, not policy facts.

Transcript focus:
Investigating ATM-fee complaints, checking product-specific fee/rebate rules, and applying credits or explaining ineligibility.

Losslessness risks:
- Preserve product-specific domestic, international, foreign, and out-of-network fee rules.
- Preserve when a fee credit is allowed versus when the customer is ineligible.
- Do not collapse all ATM-fee handling into a generic refund policy.

Source documents:

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

### doc_bank_accounts_bank_accounts_(general)_017: Internal: Applying Credits and Rebates to Checking Accounts

### Overview

This document describes the policy and procedure for agents to apply credits to customer checking accounts. Credits may only be applied to checking accounts (not savings accounts or other account types). The apply_checking_account_credit_5829 tool is used to add a credit transaction to a checking account.

### Eligible Circumstances for Applying Credits

Agents are authorized to apply credits to checking accounts ONLY in the following circumstances:

#### 1. Missing Rebates

If a rebate that should have been applied to the customer's account has not yet been applied, and the customer meets all eligibility requirements for that rebate, the agent may apply the credit. Before applying:
- Verify the customer is eligible for the rebate based on documented rebate policies
- Confirm the rebate has not already been applied by checking the account's transaction history
- Ensure the rebate amount matches what is specified in the applicable rebate policy

#### 2. Fee mischarges

If any fees on the customer's account do not match the correct amounts per the documented fee schedule, the agent must identify all fee discrepancies and apply a credit for the net correction. Before applying:
- Review the account terms and documented fee structures to identify all fees that differ from what should have been charged
- Check the transaction history to confirm each fee discrepancy
- Ensure the credit amount reflects the net correction across all identified fee discrepancies

### Credit Types

When applying a credit, use the appropriate credit_type:
- `rebate_credit`: For rebates that should have been applied but were missing
- `fee_refund`: For refunding fees that were incorrectly charged

### Procedure

1. Verify the customer's identity and account ownership
2. Confirm the account is a checking account (credits cannot be applied to savings or other account types)
3. Verify the customer meets one of the eligible circumstances listed above
4. Calculate the correct credit amount based on the rebate policy or fee that was overcharged
5. Use the apply_checking_account_credit_5829 tool to apply the credit
6. Inform the customer of the applied credit and new account balance

### Agent Tool Usage (Internal Only)

- Tool: apply_checking_account_credit_5829(account_id, amount, credit_type)
  - When to call: After confirming the customer meets one of the eligible circumstances above
  - How to set parameters:
    - account_id: The checking account ID to credit
    - amount: The positive dollar amount to credit (must be greater than 0)
    - credit_type: Must be one of 'rebate_credit' or 'fee_refund'
  - Expected outcome: Adds a credit transaction to the checking account and updates the account balance

The apply_checking_account_credit_5829 tool may only be called ONCE per checking account per customer interaction. After a credit is applied to a checking account, the system enforces a 14-day cooldown period before another credit can be applied to that same account. Because only one credit call is allowed per account, if multiple corrections are needed for the same account (e.g., both fee refunds and missing rebates), combine them into a single credit with the total amount and use the credit_type that applies to the majority of the corrections.

### Important Restrictions

- Credits may ONLY be applied to checking accounts. Savings accounts and other account types are not eligible.
- Credits may only be applied for the two circumstances listed above. Do not apply credits for any other reason without supervisor approval.
- Always document the reason for the credit by selecting the appropriate credit_type. 
- The credit amount must match the exact rebate or fee amount - do not round or estimate.

### doc_checking_accounts_blue_account_012: International ATM withdrawals for Blue Account

### Fee for international ATM withdrawals

- For ATM withdrawals made in a foreign currency, you are charged 3% of the withdrawal amount, with a minimum fee of $5.00 per withdrawal.
- The fee is calculated on the U.S. dollar equivalent of the cash dispensed and is applied per transaction.

#### Quick formula
Fee = the greater of:
- 3% of the withdrawal amount, or
- $5.00

### Daily ATM withdrawal limit

Your Blue Account debit card has a daily ATM withdrawal limit of $500. This limit applies to all ATM withdrawals combined (domestic and international) within a 24-hour period.

### Examples

The following examples assume the ATM dispenses local currency and the final transaction amount is converted to the U.S. dollar equivalent for fee calculation.

| Withdrawal (USD equivalent) | Percentage fee at 3% | Minimum applies? | Fee charged |
|---|---:|:--:|---:|
| $40 | $1.20 | Yes | $5.00 |
| $200 | $6.00 | No | $6.00 |
| $1,000 | $30.00 | No | $30.00 |

Tip: Because a $5.00 minimum applies to each transaction, making fewer, larger withdrawals can reduce total fees compared with multiple small withdrawals.

### How the fee appears

- The fee posts when the withdrawal settles and appears as a separate line item on your account history and statement.
- The ATM owner or network may charge its own fee at the machine. Those third‑party fees are separate and in addition to the amounts described above.

### Using international ATMs effectively

- At the ATM, choose to be charged in the local currency rather than converting at the terminal. This generally helps you avoid extra conversion costs set by the ATM provider.
- Verify the total amount before confirming the withdrawal and save the receipt.
- If an ATM displays a message about an additional operator fee, you can cancel and try another nearby bank-operated machine to potentially avoid or reduce those charges.
- If a transaction is declined after cash is not dispensed, do not retry repeatedly at the same machine; locate a different ATM.

### doc_checking_accounts_green_account_(checking)_012: Foreign ATM fees for Green Account (checking)

### When the fee applies
- You are charged a foreign ATM withdrawal fee for each successful cash withdrawal made in a foreign currency using your Green Account (checking).
- The fee is assessed per transaction.

### Daily ATM withdrawal limit

Your Green Account (checking) debit card has a daily ATM withdrawal limit of $600. This limit applies to all ATM withdrawals combined (domestic and foreign) within a 24-hour period.

### How the fee is calculated
- The fee is the greater of:
  - 3% of the withdrawal amount (calculated on the U.S. dollar equivalent), or
  - $5.00
- The fee is determined using the U.S. dollar value of the cash dispensed at settlement and posts as a separate line item.

#### Quick way to estimate your fee
1. Convert the withdrawal amount to its U.S. dollar equivalent (the amount that will post).
2. Multiply that amount by 3%.
3. Compare the result to $5.00. The higher amount is your fee.

### Examples
The table below shows typical outcomes based on the U.S. dollar equivalent of the cash dispensed:

| USD-equivalent cash withdrawn | 3% of amount | Fee charged |
|---:|---:|---:|
| $20 | $0.60 | $5.00 (minimum applies) |
| $100 | $3.00 | $5.00 (minimum applies) |
| $150 | $4.50 | $5.00 (minimum applies) |
| $200 | $6.00 | $6.00 |
| $400 | $12.00 | $12.00 |

Note: When the percentage calculation is less than $5.00, the minimum fee applies.

### Posting and visibility
- The fee posts when the ATM transaction settles and appears as a separate line on your account activity and statement.

### Other potential charges
- ATM owners or operators may impose their own fees. These are separate from the foreign ATM withdrawal fee described above and may appear as additional line items.

### doc_checking_accounts_bluest_account_007: ATM fee rebates for Bluest

### Daily ATM withdrawal limit
- Your Bluest Account debit card has a daily ATM withdrawal limit of $1,500. This applies to all ATM withdrawals within a 24-hour period.

### Monthly rebate cap
- You are eligible for ATM fee rebates up to $50 per month.

#### How rebates are applied
- Rebates are credited until you reach the monthly maximum of $50.
- If your aggregate ATM fees exceed $50 in a given month, the excess will not be rebated.

#### Tips for maximizing rebates
- Keep track of your cumulative ATM fees during the month to stay within the $50 cap.
- Consider using fee-free ATMs once you approach the monthly cap.

### doc_checking_accounts_bluest_account_010: Bluest Account: Out-of-network ATM fees

### When this fee applies
- You are charged an out-of-network ATM fee when you withdraw cash from an ATM that is not part of Rho-Bank’s network.
- The fee is assessed per withdrawal. Multiple withdrawals will each incur a separate fee.
- Any surcharge displayed by the ATM operator is in addition to Rho-Bank’s fee and is not controlled by Rho-Bank.

### Fee amount
| Transaction | Rho-Bank fee |
| --- | --- |
| Cash withdrawal at an out-of-network ATM | $2.00 per withdrawal |

### How the fee is assessed and displayed
- The fee is added to the total cost of your withdrawal and posts as a separate line item on your account activity.
- The description typically references “ATM” or “Out-of-network ATM” along with the fee amount of $2.00.
- If the ATM operator adds a surcharge, it will usually appear as part of the withdrawal amount on the receipt and may appear as a separate charge or be included in the withdrawal total, depending on the operator’s processing.

### Tips to minimize out-of-network ATM costs
- Use in-network ATMs whenever possible to avoid the $2.00 fee.
- If you must use an out-of-network ATM, consolidate cash needs into a single withdrawal to avoid paying the fee multiple times.
- Review the ATM screen for any additional operator surcharges before confirming your withdrawal; cancel and try a different ATM if the surcharge is high.

### Examples
- Single withdrawal: Withdrawing cash once from an out-of-network ATM will incur a fee of $2.00, plus any ATM operator surcharge.
- Multiple withdrawals: Making two separate withdrawals at out-of-network ATMs will result in two fees of $2.00 (one per withdrawal), in addition to any operator surcharges.

### doc_checking_accounts_purple_account_004: Using ATMs worldwide

### Daily ATM withdrawal limit
- Your Purple Account debit card has a daily ATM withdrawal limit of $1,000. This limit applies to all ATM withdrawals worldwide within a 24-hour period.

### How ATM rebates work
- You are eligible for refunds of ATM operator fees up to a monthly cap of $30.
- Rebates apply after eligible ATM fees post to your account and are credited up to the monthly cap.

### Best practices when withdrawing cash abroad
- Choose the checking account option on the ATM when prompted.
- Retain the ATM receipt if it shows a surcharge to help with any rebate review.
- Avoid optional dynamic currency conversion at the ATM if you prefer to be billed in the local currency.

### Troubleshooting
- If you believe a rebate is missing, verify whether your monthly total rebates have reached $30 and confirm that the charge was coded as an ATM operator fee.

### doc_checking_accounts_purple_account_010: Why was my ATM fee not rebated?

### Common reasons
- You reached the monthly rebate cap of $30. Additional ATM operator fees in the same month are not rebated.
- The charge was not coded as an ATM operator fee by the merchant or network.
- The transaction posted outside the eligible rebate window.
- The withdrawal occurred at a location or terminal type not eligible for rebates.

### What to do next
- Review your statement to total rebates already received this month and compare to $30.
- Confirm that the charge is labeled as an ATM operator fee and keep the receipt.
- If you still believe a rebate is due, contact support and include the date, location, and a copy of the receipt showing the surcharge.

### doc_checking_accounts_purple_account_012: Out-of-network ATM fees for Purple Account

### Fee amount
- You are charged $2.50 per cash withdrawal made at an out-of-network ATM.

### When the fee applies
- Applies to withdrawals made at ATMs that are not in Rho‑Bank's ATM network.
- Assessed per withdrawal. Multiple withdrawals in the same day will each incur a separate $2.50 fee.
- This fee is separate from any surcharge the ATM owner/operator may charge at the terminal.

### How it appears on your account
- The fee posts as a separate line item associated with the out-of-network ATM withdrawal.
- The posting date may differ from the date you used the ATM, depending on when the transaction settles.

### Example
- If you make three separate cash withdrawals at out-of-network ATMs in one day, your total Rho‑Bank fees would be 3 × $2.50.

### Additional ATM operator fees
- The ATM owner/operator may display and charge its own surcharge before you complete the transaction. You can cancel at that prompt to avoid the operator's surcharge.
- Operator surcharges are set by the ATM owner and are in addition to Rho‑Bank's $2.50 fee.

### Tips to minimize fees
- Use in-network ATMs whenever possible.
- If you must use an out-of-network ATM, consider making a single larger withdrawal rather than multiple smaller ones to reduce the number of per‑withdrawal fees.
- Review on-screen disclosures before confirming the transaction to see any operator surcharge.

### doc_checking_accounts_light_blue_account_006: Foreign ATM withdrawal fees for Light Blue Account

### Monthly free foreign ATM withdrawal allowance

- Each month, you receive 2 free foreign ATM cash withdrawals.
- The free allowance applies on a per-withdrawal basis. Each foreign ATM cash withdrawal counts as one use of the allowance.
- Unused free withdrawals do not roll over to future months.

### Fees after the allowance is used

- After you use all 2 free foreign ATM withdrawals in a month, each additional foreign ATM withdrawal is charged a fee of $4.00.
- The fee is charged per additional foreign ATM withdrawal for the remainder of that month.

#### Summary

| Usage in a single month | Rho-Bank fee per foreign ATM withdrawal |
| --- | --- |
| Up to 2 withdrawals | $0 |
| Each withdrawal beyond 2 | $4.00 |

### Examples

- 1 foreign ATM withdrawal in a month: no fee.
- 2 foreign ATM withdrawals in a month: no fee.
- 5 foreign ATM withdrawals in a month: the first 2 are free; the remaining 3 are charged at $4.00 each (total bank fees: 3 × $4.00).

### Notes

- ATM owners or operators may impose their own fees. Those third-party fees are separate and may be charged in addition to any Rho-Bank fee described above.
- The fee applies regardless of the amount withdrawn in each transaction.

### doc_checking_accounts_light_green_account_013: Understanding foreign ATM fees for teens

### What you pay for a foreign ATM withdrawal (Light Green)

Foreign ATM withdrawal fees on Light Green accounts are flat per withdrawal and depend on the amount you take out in a single transaction.

| Withdrawal amount (single transaction) | Fee per withdrawal |
| --- | --- |
| Up to and including $100 | $2.00 |
| More than $100 and up to and including $300 | $3.50 |
| Above $300 | $5.00 |

Notes:
- The fee is determined by the amount dispensed in each single withdrawal.
- The fee is charged by Rho-Bank and is separate from any fee an ATM operator may charge.

### How the fee is determined

- Each successful foreign ATM cash withdrawal is assessed one fee based on the amount withdrawn in that transaction.
- Amounts exactly at a threshold are charged the lower tier’s fee.
  - Example: A withdrawal of exactly $100 is charged $2.00.
  - Example: A withdrawal of exactly $300 is charged $3.50.
- Multiple withdrawals in the same day each incur their own fee based on their individual amounts.

### Quick examples

- You withdraw $60: Fee = $2.00.
- You withdraw $150: Fee = $3.50.
- You withdraw $350: Fee = $5.00.

### Tips to manage fees

- Combine withdrawals when possible:
  - Two withdrawals of $90 each would cost 2 × $2.00; one withdrawal of $180 would cost $3.50.
  - Two withdrawals of $200 each would cost 2 × $3.50; one withdrawal of $400 would cost $5.00.
- Plan your cash needs ahead so you can make fewer, larger withdrawals instead of several smaller ones that add multiple fees.

### doc_checking_accounts_evergreen_account_008: Out-of-network ATM fees for Evergreen Account

### When the fee applies
- You are charged an out-of-network ATM fee when you withdraw cash from an ATM that is not in Rho’s network.
- The fee is assessed per withdrawal transaction.

### Fee structure
- Percentage: 1% of the withdrawal amount
- Maximum per withdrawal: $2.50
- The percentage is applied to the cash dispensed amount. If the percentage-based fee exceeds $2.50, the fee is capped at $2.50.

### Calculation examples
| Cash withdrawal | Percentage fee at 1% | Applied cap | Total out-of-network fee |
|---|---:|---:|---:|
| $40 | $0.40 | Not reached | $0.40 |
| $250 | $2.50 | Equals cap | $2.50 |
| $600 | $6.00 | Capped at $2.50 | $2.50 |

### How the fee is charged and displayed
- The fee is deducted from your account in addition to the cash withdrawn.
- You will see a separate line item for the out-of-network ATM fee on your transaction history, reflecting the amount calculated using 1% and the $2.50 cap.

### Important notes
- The ATM operator may charge its own surcharge. That surcharge is separate from Rho’s out-of-network fee and is not subject to the $2.50 cap.
- Multiple withdrawals in the same day each incur a separate fee, calculated individually using 1% and capped at $2.50 per withdrawal.

### Tips to reduce or avoid the fee
- Use in-network ATMs to avoid out-of-network charges.
- If you need a larger amount of cash, consider a single withdrawal rather than multiple smaller withdrawals to avoid multiple per-withdrawal fees.

Shared context paths (construction metadata, not policy facts):
- `tau2/hyper/sops/banking_sop.md`
