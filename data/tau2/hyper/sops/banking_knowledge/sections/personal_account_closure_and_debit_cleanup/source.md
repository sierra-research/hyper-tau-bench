## Personal account closure with transaction/debit-card cleanup

Bundle id: `personal_account_closure_and_debit_cleanup`

Construction context (guidance for transcript induction, not section
content -- do not extract as policy facts): the shared banking handbook
governs identity verification, explicit customer confirmation before
account-modifying actions, discoverable-tool wrapper behavior, schema
limits, and exact transfer wording. Express these behaviorally in
transcripts where a case exercises them; do not restate them as section
facts. The bundle id, transcript focus, losslessness risks, and shared
context paths in this file are construction metadata, not policy facts.

Transcript focus:
Closing checking or savings accounts only after required transaction and debit-card checks, including lost/stolen cross-product handling.

Losslessness risks:
- Preserve closure blockers and required pre-closure checks.
- Preserve debit-card cancellation/replacement consequences.
- Do not let account closure skip explicit confirmation from shared context.

Source documents:

### doc_bank_accounts_bank_accounts_(general)_005: Internal: Closing Personal Checking Accounts

### Pre-Closure Requirements

Verify all of the following before closing:
- If an early closure fee applies, the account balance must be at least the fee amount; otherwise, account balance (current_holdings) must be $0. The fee is deducted directly from the account balance and there is no alternative payment method.
- Account status is OPEN
- No pending transactions for this account

### Tier-Specific Closure Requirements

- ENTRY TIER (Light Blue Account, Light Green Account, Green Fee-Free Account)
  - Early closure fee: $15 if closed within 30 days
  - Notice period: 0 days

- MID TIER (Blue Account, Green Account (checking))
  - Early closure fee: $25 if closed within 60 days
  - Notice period: 3 days

- PREMIUM TIER (Evergreen Account)
  - Early closure fee: $50 if closed within 90 days
  - Notice period: 7 days

- ELITE TIER (Bluest Account)
  - Early closure fee: $100 if closed within 180 days
  - Notice period: 14 days

### Closure Procedure

1. Verify pre-closure requirements are met.
2. Determine the account tier and applicable fees/notice period.
3. Use close_bank_account_7392 to close the account.

### doc_bank_accounts_bank_accounts_(general)_006: Internal: Closing Personal Savings Accounts

### Pre-Closure Requirements

Verify all of the following before closing:
- If an early closure fee applies, the account balance must be at least the fee amount; otherwise, account balance (current_holdings) must be $0. The fee is deducted directly from the account balance and there is no alternative payment method.
- Account status is OPEN
- No pending transactions for this account

### Tier-Specific Closure Requirements

- ENTRY TIER (Bronze Account)
  - Early closure fee: $20 if closed within 60 days
  - Notice period: 1 days

- MID TIER (Silver Account, Silver Plus Account)
  - Early closure fee: $35 if closed within 90 days
  - Notice period: 5 days

- PREMIUM TIER (Gold Account, Gold Plus Account, Gold Years Account)
  - Early closure fee: $75 if closed within 180 days
  - Notice period: 10 days

- ELITE TIER (Platinum Account, Platinum Plus Account, Diamond Elite Account)
  - Early closure fee: $150 if closed within 270 days
  - Notice period: 21 days
  - Requires manager approval

### Closure Procedure

1. Verify pre-closure requirements are met.
2. Determine the account tier and applicable fees/notice period.
3. For ELITE tier, obtain manager approval before proceeding.
4. Use close_bank_account_7392 to close the account.

### doc_bank_accounts_bank_accounts_(general)_018: Internal: Retrieving Bank Account Transaction History

### Overview

Agents can retrieve the transaction history for a customer's bank account (checking or savings) using the get_bank_account_transactions_9173 tool. This is useful when reviewing account activity, verifying fees, checking for applied rebates, or investigating customer inquiries.

### Agent Tool Usage

- Tool: get_bank_account_transactions_9173(account_id)
  - account_id: The bank account ID to retrieve transactions for
  - Returns: A list of all transactions for the account. Transactions are returned in reverse chronological order (most recent first).

### Transaction Fields

Each transaction record contains the following fields:

- **transaction_id**: Unique identifier for the transaction
- **account_id**: The bank account ID this transaction belongs to
- **date**: Date of the transaction (MM/DD/YYYY format)
- **description**: Description of the transaction (e.g., 'ATM WITHDRAWAL - CHASE BANK #2847 CHICAGO IL')
- **amount**: Transaction amount in USD. Positive values are credits (money in), negative values are debits (money out)
- **type**: Transaction type, one of:
  - direct_deposit
  - debit_card_purchase
  - atm_withdrawal
  - atm_balance_inquiry
  - atm_fee
  - ach_transfer_in
  - ach_transfer_out
  - wire_transfer_in
  - wire_transfer_out
  - check_deposit
  - mobile_deposit
  - bill_pay
  - everyonepay
  - monthly_fee
  - overdraft_fee
  - fee_rebate
  - interest_credit
  - rebate_credit
  - fee_refund
- **status**: Transaction status, either 'posted' or 'pending'

### doc_bank_accounts_bank_accounts_(general)_020: What to Know Before Closing Your Account

We're sorry to hear you're considering closing your Rho-Bank account, and we want to make sure you have all the information you need to make the best decision for your financial situation. While we'd love to keep you as a valued customer, we understand that circumstances change, and we're here to help make the process as smooth and straightforward as possible if you do decide to move forward with closing your account.

Before you proceed, here are some important things you should know:

### Early Closure Fees

Depending on your account type and when you opened it, there may be an early closure fee if you close your account within a certain timeframe after opening. These fees vary by account tier and are designed to offset the administrative costs of account setup. Entry-level accounts typically have lower fees and shorter early closure windows, while premium and elite accounts may have higher fees and longer windows. If you're unsure whether an early closure fee applies to your account, our customer service team can look up your specific account details and let you know exactly what to expect.

### Notice Periods

Some account types require advance notice before closure can be processed. This notice period gives us time to ensure all pending transactions have cleared and that your account is in good standing for closure. The required notice period varies by account tier, ranging from same-day processing for basic accounts to several weeks for premium business accounts.

### Pre-Closure Requirements

Before we can close your account, a few conditions must be met. Your account balance must either be zero or, if an early closure fee applies, must be at least equal to the fee amount (since the fee is deducted directly from your balance). Additionally, there cannot be any pending transactions on the account, as these need to clear first. For business savings accounts, you'll also need to ensure any linked accounts are properly addressed.

### Contact Us

If you have any questions about the closure process or would like to discuss your options, please don't hesitate to reach out to our customer service team at 1-800-RHO-BANK. We're here to help guide you through every step, and who knows—we might even be able to find a solution that makes staying with Rho-Bank the right choice for you.

### doc_bank_accounts_bank_accounts_(general)_023: Internal: Ordering a Debit Card for a Bank Account

Procedure for if the customer inquires about ordering a debit card linked to a specific checking account. Debit cards can only be ordered for checking accounts (personal or business) - savings accounts are not eligible for debit cards.

Eligibility requirements:
1) Customer must be verified
2) The account must be a checking account (account_type must be 'checking')
3) Account status must be OPEN
4) Account must have been open for at least 3 business days (excluding weekends)
5) Customer cannot have more than 1 active debit cards per checking account
6) Account must have a minimum balance of $25 (to cover potential fees)
7) Customer must be at least 18 years old (verify using date_of_birth)
8) Customer cannot have a pending debit card order for the same account (check debit_cards table for PENDING status)
9) Customer's address on file must be a valid US domestic address (international shipping is not available)
 

Delivery Options:
- STANDARD: Free shipping, arrives in 7-10 business days
- EXPEDITED: $15 fee, arrives in 3-5 business days
- RUSH: $35 fee, arrives in 1-2 business days, fees may vary based on account tier. 

Card Design Options:
- CLASSIC: Standard Rho-Bank blue design (default, no fee)
- PREMIUM: Metallic silver finish ($10 one-time fee)
- CUSTOM: Customer-uploaded image ($25 one-time fee, subject to approval), fees may vary ased on account tier. 

Steps:
1) Verify customer identity
2) Confirm which checking account the debit card should be linked to. 
3) Check eligibility requirements for the specified account
4) Ask customer for preferred delivery option (STANDARD, EXPEDITED, or RUSH) and explain fees. 
5) Ask customer for preferred card design (CLASSIC, PREMIUM, or CUSTOM) and explain fees. 
6) Confirm the address that the customer would like to mail the card to. 
7) Use order_debit_card_5739 to order the card. 
8) Inform customer of expected delivery timeframe and any applicable fees

Important Notes:
- Expedited and rush delivery fees are automatically deducted from the linked checking account
- If the account has insufficient funds for delivery or design fees, the order will fail
- Customers can track their card shipment status using the Rho-Bank mobile app
- New cards are automatically activated upon first use with PIN entry
- The customer's existing debit card (if any) will remain active until the new card is activated.

### doc_bank_accounts_bank_accounts_(general)_025: Internal: Closing/Cancelling a Debit Card

Procedure for when a customer wants to close, cancel, or deactivate their debit card.

### Reasons for Closing a Debit Card

- Lost card
- Stolen card
- Suspected fraud/unauthorized transactions
- Damaged card (customer wants replacement)
- Customer no longer needs the card
- Closing the linked checking account

### Requirements

1. Customer must be verified
2. Customer must be the owner of the debit card (verify user_id matches)
3. The debit card must currently be in ACTIVE or PENDING status
4. No pending transactions: The card must not have any pending or processing transactions. If pending transactions exist, inform the customer they must wait for all transactions to settle before the card can be closed.
5. No pending refunds: The card must not have any pending refunds. If pending refunds exist, inform the customer they must wait for the refunds to process (typically 3-5 business days) or acknowledge in writing that the refunds will be credited to the linked checking account instead.
6. Minimum card age: The debit card must have been active for at least 14 days. Calculate this from the date_issued field. If the card is newer than this, inform the customer they cannot close the card yet and provide the earliest eligible closure date.

### Closing Steps

1. Verify customer identity using standard verification procedures
2. Ask customer for the reason they want to close the card (select from: lost, stolen, fraud_suspected, damaged, no_longer_needed, account_closing)
3. Check eligibility requirements. If any requirement is not met, inform the customer what needs to be resolved and do not proceed with closure.
4. If reason is 'lost', 'stolen', or 'fraud_suspected':
   - These reasons bypass the minimum card age requirement (requirement 6) for security purposes
   - Inform customer that any pending transactions will still be processed
   - Ask if they want to order a replacement card immediately
   - If fraud is suspected, advise customer to review recent transactions and file disputes for any unauthorized charges
5. Use close_debit_card_4721 to close the card with parameters: card_id, reason
6. Confirm the card has been closed and provide the following information:
   - The card is now permanently deactivated and cannot be reactivated
   - Any recurring payments linked to this card will need to be updated with new payment information
   - If they need a new card, they can order one through the standard ordering process

### Important Notes

- Cards reported as lost or stolen are closed immediately with no cooling-off period
- For fraud_suspected closures, recommend the customer also change their online banking password
- If the linked checking account is being closed, all associated debit cards must be closed first
- Closed cards cannot be reopened - customer must order a new card if needed
- Refunds to a closed card will be credited to the linked checking account

### doc_bank_accounts_bank_accounts_(general)_028: Internal: Retrieving Debit Card Information

Tool for retrieving debit card information for a customer's checking account. Use get_debit_cards_by_account_id_7823 to look up all debit cards associated with a specific checking account.

### Tool Usage

get_debit_cards_by_account_id_7823(account_id) - account_id is the checking account ID to retrieve debit cards for.

### Debit Card Fields Returned

- card_id: Unique identifier for the debit card
- account_id: The checking account ID the card is linked to
- user_id: The user ID of the cardholder
- card_number_last_4: Last 4 digits of the card number
- status: Current status of the card (ACTIVE, PENDING, FROZEN, CLOSED)
- issue_reason: Why the card was issued (new_account, first_card, lost, stolen, fraud, expired, damaged, upgrade, bank_reissue)
- expiration_date: Card expiration date (MM/YY format)
- date_issued: Date the card was issued
- card_design: Design type (CLASSIC, PREMIUM, CUSTOM)
- daily_purchase_limit: Maximum daily purchase amount
- daily_atm_limit: Maximum daily ATM withdrawal amount

### Common Use Cases

1. Before ordering a new debit card: Check if customer already has an active or pending card for the account
2. Before activating a card: Look up the issue_reason to determine which activation tool to use
3. Before freezing/unfreezing: Verify the card exists and check its current status
4. Before closing a card: Confirm the card_id and current status
5. Customer inquiries: Look up card details when customer asks about their debit card

### Important Notes

- This tool only returns debit cards for checking accounts (savings accounts do not have debit cards)
- Multiple cards may be returned if the account has card history (e.g., old closed cards plus current active card)
- For privacy, full card numbers are never returned - only the last 4 digits
- If no cards exist for the account, an empty list is returned

### doc_bank_accounts_bank_accounts_(general)_029: Internal: Debit Card Replacement Options by Account Tier

When a customer requests a replacement debit card (due to lost, stolen, damaged, or other reasons), the replacement policies vary based on the customer's checking account tier.

IMPORTANT - Fee Charging: All applicable fees (shipping, design, excess replacement) are AUTOMATICALLY CHARGED to the linked checking account when the card is ordered. Always inform the customer that the fee will be deducted from their checking account balance before placing the order. When using order_debit_card_5739, you must provide the exact delivery_fee and design_fee amounts based on the tier rules below.

Replacement Limits and Shipping Fees by Tier:

ENTRY TIER:
- Maximum 2 replacement cards per rolling 12-month period
- 48-hour waiting period after card closure before a replacement can be ordered
- Standard shipping only (no expedited option available) - delivery_fee: $0
- If customer has exceeded the 2-card limit, they must wait until oldest replacement ages out of the 12-month window, OR pay a $25 excess replacement fee

MID TIER:
- Maximum 3 replacement cards per rolling 12-month period
- No waiting period - can order immediately after closure
- Standard (delivery_fee: $0) or expedited shipping available (delivery_fee: $15)
- If customer has exceeded the 3-card limit, they must wait until oldest replacement ages out, OR pay a $15 excess replacement fee

PREMIUM TIER:
- Maximum 5 replacement cards per rolling 12-month period
- No waiting period - can order immediately after closure
- Free expedited shipping on all replacements (delivery_fee: $0 for both STANDARD and EXPEDITED)
- Rush shipping available (delivery_fee: $35)
- If customer has exceeded the 5-card limit, they must wait until oldest replacement ages out (no fee option - must wait)

ELITE TIER:
- Unlimited replacement cards
- No waiting period - can order immediately after closure
- Complimentary shipping on all replacements (delivery_fee: $0 for STANDARD, EXPEDITED, and RUSH)
- Priority processing - cards ship same business day if ordered before 2pm EST

Card Design Fees by Tier:

ENTRY TIER:
- CLASSIC design: design_fee $0
- PREMIUM design (metallic silver): design_fee $10
- CUSTOM design (uploaded image): design_fee $25

MID TIER:
- CLASSIC design: design_fee $0
- PREMIUM design (metallic silver): design_fee $10
- CUSTOM design (uploaded image): design_fee $25

PREMIUM TIER:
- CLASSIC design: design_fee $0
- PREMIUM design (metallic silver): design_fee $0 (complimentary)
- CUSTOM design (uploaded image): design_fee $15 (discounted from $25)

ELITE TIER:
- CLASSIC design: design_fee $0
- PREMIUM design (metallic silver): design_fee $0 (complimentary)
- CUSTOM design (uploaded image): design_fee $0 (complimentary)

How to Check Replacement History:
1) Retrieve all cards for the account
2) Look for cards with issue_reason of 'lost', 'stolen', 'fraud', or 'damaged'
3) Check the date_issued field and count cards issued within the last 12 months
4) Cards with issue_reason of 'new_account', 'first_card', 'expired', 'upgrade', or 'bank_reissue' do NOT count toward the replacement limit.

### doc_bank_accounts_bank_accounts_(general)_030: Internal: Lost/Stolen Card - Cross-Product Security Protocol

When a customer reports a lost or stolen debit card, there is a risk that other cards in their wallet were also compromised. Agents must follow this cross-product security protocol to protect the customer's full relationship with Rho-Bank.

### Required Security Check

When a customer reports a lost or stolen debit card:
1) Complete the standard debit card freeze/close procedure
2) Check if the customer has any Rho-Bank credit cards on file
3) If yes, proactively offer to order a replacement credit card as a security precaution
4) Explain that wallet theft often involves multiple cards and this protects against potential fraud

### How to Check for Credit Cards

Use get_credit_card_accounts_by_user to retrieve any credit card accounts for the customer. This will return all active and closed credit card accounts.

### Offering Credit Card Protection

If the customer has one or more credit cards:
- Inform them that you noticed they also have a credit card with Rho-Bank
- Ask if their credit card was also in the lost/stolen wallet
- Offer to order a replacement credit card with a new card number to prevent any unauthorized charges
- If they decline, note in the account that the offer was made

### Why This Matters

Customers who lose their wallet often focus on their debit card and forget about credit cards until fraudulent charges appear. Proactively offering this protection demonstrates excellent customer service and reduces fraud losses for the bank.

### Agent Script Example

"I see that you also have a [Card Type] credit card with us. Was that card also in your lost wallet? If so, I can order a replacement card with a new card number to protect you from any potential fraud. Would you like me to do that for you?"

Shared context paths (construction metadata, not policy facts):
- `tau2/hyper/sops/banking_sop.md`
