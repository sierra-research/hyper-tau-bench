## Debit-card lost/stolen, freeze/unfreeze, replacement, and security alerts

Bundle id: `debit_card_lost_stolen_freeze_replace`

Construction context (guidance for transcript induction, not section
content -- do not extract as policy facts): the shared banking handbook
governs identity verification, explicit customer confirmation before
account-modifying actions, discoverable-tool wrapper behavior, schema
limits, and exact transfer wording. Express these behaviorally in
transcripts where a case exercises them; do not restate them as section
facts. The bundle id, transcript focus, losslessness risks, and shared
context paths in this file are construction metadata, not policy facts.

Transcript focus:
Handling lost or stolen debit cards, freezes/unfreezes, replacements by account tier, travel/emergency replacement, and security alert blocks.

Losslessness risks:
- Preserve freeze/unfreeze, cancel, and replacement as separate actions.
- Preserve account-tier replacement options and fees.
- Preserve cross-product lost/stolen protocol ordering.

Source documents:

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

### doc_bank_accounts_bank_accounts_(general)_024: Internal: Activating a Debit Card

Procedure for when a customer has received their new debit card and wants to activate it with Rho-Bank customer service.

### IMPORTANT: Activation Tool Selection

There are THREE different activation tools depending on WHY the card was issued. You MUST use the correct tool based on the card's issue reason. Check the debit_cards table for the 'issue_reason' field or debit_card_orders table for the order reason.

- activate_debit_card_8291: Use for NEW cards (first-time card for this checking account, issue_reason = 'new_account' or 'first_card')
- activate_debit_card_8292: Use for REPLACEMENT cards (replacing lost/stolen/fraud cards, issue_reason = 'lost', 'stolen', or 'fraud')
- activate_debit_card_8293: Use for REISSUED cards (expiration renewal, damaged card, design upgrade, or bank-initiated, issue_reason = 'expired', 'damaged', 'upgrade', or 'bank_reissue')

Using the wrong activation tool will result in an error. Always verify the issue reason before selecting the tool.

### Activation Requirements

1. Customer must be verified
2. Customer must have the physical card in their possession
3. The debit card must be in PENDING status (not already ACTIVE)
4. The linked checking account must still be OPEN
5. Card must not be expired (check expiration_date)

### Required Information from Customer

- Last 4 digits of the debit card number (printed on the card)
- Card expiration date (MM/YY format)
- The 3-digit CVV on the back of the card

### Activation Steps

1. Verify customer identity using standard verification procedures
2. Look up the card in the debit_cards table and check the 'issue_reason' field to determine which activation tool to use
3. Ask customer for the last 4 digits of the card number
4. Ask customer for the card expiration date
5. Ask customer for the 3-digit CVV on the back
6. Verify the card details match the customer's account
7. Ask customer to set a 4-digit PIN for the card (must be exactly 4 digits, cannot be sequential like 1234 or repeating like 1111)
8. Use the CORRECT activation tool based on issue_reason:
   - For new cards: activate_debit_card_8291
   - For replacement cards (lost/stolen/fraud): activate_debit_card_8292
   - For reissued cards (expired/damaged/upgrade): activate_debit_card_8293
9. Confirm activation was successful

### Additional Steps for REPLACEMENT Cards (8292)

- After activation, remind customer to review recent transactions for any unauthorized charges
- Ask if they have noticed any suspicious activity on their account
- Recommend changing their online banking password if fraud was suspected

### Additional Steps for REISSUED Cards (8293)

- Inform customer that their old card will remain active for 24 hours as a grace period
- Remind them to update any recurring payments with the new card details if the card number changed

### Important Notes

- If the customer provides incorrect card details 2 times, the card will be locked for security and they must visit a branch in person
- Previous debit cards linked to the same account will be automatically deactivated when the new card is activated (except for reissued cards which have a 24-hour grace period)

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

### doc_bank_accounts_bank_accounts_(general)_026: Internal: Freezing and Unfreezing a Debit Card

Procedure for when a customer wants to temporarily freeze or unfreeze their debit card.

### Freezing vs. Closing

- FREEZE: Temporary lock - card can be unfrozen later. Use when customer misplaced the card or wants temporary security.
- CLOSE: Permanent deactivation - cannot be reversed. Use when card is confirmed lost/stolen or customer wants to cancel.

### Reasons for Freezing

- Customer misplaced the card and is looking for it
- Traveling and wants extra security
- Suspicious activity noticed, wants to investigate before closing
- Temporarily restricting spending (e.g., budgeting purposes)
- Lending card to family member and wants to control usage

### Freezing Requirements

1. Customer must be verified
2. Customer must be the owner of the debit card
3. Card must currently be in ACTIVE status (cannot freeze PENDING, CLOSED, or already FROZEN cards)

### Freezing Steps

1. Verify customer identity
2. Ask customer why they want to freeze the card
3. Inform customer of the following:
   - All new transactions will be declined while frozen
   - Recurring payments/subscriptions will also be declined
   - Pending transactions already authorized may still process
   - They can unfreeze at any time by calling customer service or through the mobile app
4. Use freeze_debit_card_3892 with the card_id
5. Confirm the freeze was successful

### Unfreezing Requirements

1. Customer must be verified
2. Customer must be the owner of the debit card
3. Card must currently be in FROZEN status
4. The linked checking account must still be OPEN

### Unfreezing Steps

1. Verify customer identity
2. Use unfreeze_debit_card_3893 with the card_id
3. Confirm the card is now active and ready to use immediately

### Important Notes

- Freezing does not affect ATM access if the customer has their PIN
- For ATM freeze, customer must also enable 'ATM Block' separately through mobile app
- If a frozen card is not unfrozen within 90 days, the customer will receive a reminder notification
- If customer confirms the card is lost/stolen, recommend closing instead of freezing

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

### doc_bank_accounts_bank_accounts_(general)_039: Internal: Managing Debit Card Security Alerts and Blocks

This document covers the procedures for managing security alerts and temporary blocks on debit cards. These protections are designed to prevent fraudulent transactions but may occasionally affect legitimate customers.

### Types of Security Protections

#### Fraud Alerts

Fraud alerts are flags placed on debit cards when suspicious activity is detected or reported. There are two types:

1. **Customer-Initiated Alerts**: Placed when a customer reports suspicious activity or requests additional security. These can be cleared by customer service agents after verifying the customer's identity.

2. **Bank-Initiated Alerts**: Placed by Rho-Bank's fraud detection systems when high-risk patterns are identified. These CANNOT be cleared by customer service agents and require review by the security team.

#### Velocity Blocks

Velocity blocks are automatic, temporary holds placed on cards when unusual transaction patterns are detected. Common triggers include:
- Multiple transactions in rapid succession
- Transactions in geographically distant locations within a short time
- Sudden changes in spending patterns
- Multiple declined transactions followed by successful ones

Velocity blocks automatically expire after 30 minutes, but can be cleared earlier by a customer service agent after identity verification.

### Clearing Security Protections

#### Tool: clear_debit_card_fraud_alert_4892

Use this tool to clear fraud alerts or velocity blocks on a customer's debit card.

**Parameters:**
- `card_id` (required): The debit card ID to clear the alert/block for
- `reason` (required): The reason for clearing. Must be one of:
  - `'customer_verified'`: Use when clearing a customer-initiated fraud alert after the customer has verified their identity and confirmed their transactions are legitimate
  - `'velocity_clear'`: Use when clearing a velocity block after verifying the customer's identity

**Important Restrictions:**
- This tool CANNOT clear bank-initiated fraud alerts. If you attempt to clear a bank-initiated alert, you will receive an error. In this case, you must transfer the customer to the security team.
- Always verify the customer's identity before using this tool.
- Document why the alert/block was cleared in the interaction notes.

**Example Usage:**

To clear a velocity block:
```
clear_debit_card_fraud_alert_4892(card_id="dbc_12345", reason="velocity_clear")
```

To clear a customer-initiated fraud alert:
```
clear_debit_card_fraud_alert_4892(card_id="dbc_12345", reason="customer_verified")
```

### When to Clear vs. When to Escalate

**Clear the alert/block when:**
- Customer's identity is verified
- For fraud alerts: The alert was customer-initiated AND customer confirms their recent transactions are legitimate
- For velocity blocks: Customer provides a reasonable explanation for the unusual activity (e.g., shopping spree, travel)

**Escalate to security team when:**
- The fraud alert is bank-initiated (you'll receive an error if you try to clear it)
- Customer cannot verify their identity
- Customer reports transactions they did not make
- You suspect the person calling may not be the actual account holder
- The customer's explanation for unusual activity is suspicious or inconsistent

### doc_checking_accounts_purple_account_007: Emergency card replacement while traveling

### Timeline
- If your card is lost or stolen while abroad, an emergency replacement can typically reach you within 2 days, subject to local courier availability and your exact location.

### How to request
- Contact us immediately to report the card as lost or stolen.
- Confirm a secure delivery address where you can receive the replacement card.
- Monitor delivery updates provided after your request is processed.

### Accessing funds while you wait
- If you need a bank‑issued instrument, a cashier's check can be provided for a fee of $8. Availability may depend on your location and delivery options.

#### Security reminders
- As soon as you report your card, it will be blocked to prevent further use.
- Update any recurring payments once your replacement card arrives.

### Debit Card Decline Codes - Card Damage and Physical Issues

The following decline codes may indicate physical card problems requiring replacement:

#### CODE 82 - Negative CAM/CVV Results (Chip or CVV Mismatch)

The card's chip data or CVV code doesn't match what's on file. This could indicate card damage or potential fraud.

1. Ask: 'Has your card been damaged recently? Have you noticed any issues with the chip or magnetic stripe?'

2. **If card is physically damaged**:
   - Explain: 'It sounds like the chip or magnetic stripe on your card may be damaged, which is causing the mismatch.'
   - Offer / help them to order a replacement.

3. **If card appears undamaged**:
   - SECURITY CONCERN: This could indicate a cloned or counterfeit card was used.
   - Say: 'For your security, I'd like to review some recent transactions with you.'
   - Review recent transaction history to check for suspicious activity.
   - If suspicious transactions found: Follow stolen card protocol to assist the customer.
   - Recommend freezing the card until a replacement arrives.

#### CODE 87 - Purchase Amount Only, No Cash Back

The transaction was declined because it included a cash back request that isn't permitted.

1. Explain: 'Your transaction included a cash back request, but cash back isn't available for this transaction. This could be due to the merchant type, the transaction amount, or your account settings.'

2. Advise: 'Please try the transaction again without requesting cash back. The purchase portion should go through.'

3. If customer needs cash: 'For cash withdrawals, you can use any Rho-Bank ATM for free, or use a partner ATM. I can help you locate the nearest one if you'd like.'

Shared context paths (construction metadata, not policy facts):
- `tau2/hyper/sops/banking_sop.md`
