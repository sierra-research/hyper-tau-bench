## Debit-card disputes, declines, PIN locks, temporary limits, and Regulation E

Bundle id: `debit_card_disputes_declines_pin_limits`

Construction context (guidance for transcript induction, not section
content -- do not extract as policy facts): the shared banking handbook
governs identity verification, explicit customer confirmation before
account-modifying actions, discoverable-tool wrapper behavior, schema
limits, and exact transfer wording. Express these behaviorally in
transcripts where a case exercises them; do not restate them as section
facts. The bundle id, transcript focus, losslessness risks, and shared
context paths in this file are construction metadata, not policy facts.

Transcript focus:
Filing and checking debit disputes, provisional credit, ATM and recurring-payment special cases, decline diagnostics, PIN-lock fraud-risk scoring, and temporary limit requests.

Losslessness risks:
- Preserve dispute subtype distinctions and Regulation E timing/eligibility.
- Preserve PIN-lock scoring thresholds and transfer triggers.
- Preserve temporary limit conditions and minor-account limits.

Source documents:

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

### doc_bank_accounts_bank_accounts_(general)_027: Internal: Resetting or Changing a Debit Card PIN

Procedure for when a customer wants to reset or change their debit card PIN.

### Reasons for PIN Change

- Customer forgot their current PIN
- Customer suspects someone knows their PIN
- Customer wants to change to a more memorable PIN
- Security best practice (periodic PIN change)

### Requirements

1. Customer must be verified
2. Customer must be the owner of the debit card
3. Card must be in ACTIVE status (cannot change PIN on FROZEN, PENDING, or CLOSED cards)

### PIN Reset Steps (Customer Forgot PIN)

1. Verify customer identity using standard verification procedures
2. For security, ask customer to confirm the last 4 digits of their card
3. Ask customer to provide a new 4-digit PIN
4. Validate the new PIN meets security requirements:
   - Must be exactly 4 digits
   - Cannot be sequential (e.g., 1234, 4321)
   - Cannot be all the same digit (e.g., 1111)
   - Cannot be the customer's birth year or birth month/day
5. Use reset_debit_card_pin_6284 with parameters: card_id, last_4_digits, new_pin
6. Confirm the PIN has been changed and is effective immediately

### PIN Change Steps (Customer Knows Current PIN)

1. Verify customer identity
2. Ask customer to confirm their current PIN for additional security
3. Ask customer to provide a new 4-digit PIN
4. Validate the new PIN meets security requirements (same as above)
5. Use change_debit_card_pin_6285 with parameters: card_id, current_pin, new_pin
6. Confirm the PIN has been changed

### Important Notes

- PIN changes take effect immediately
- If customer enters incorrect current PIN 3 times, the card will be temporarily locked
- Customer can also change their PIN at any Rho-Bank ATM
- For security, PINs are never displayed or read back to customers
- If customer's card is frozen, they must unfreeze it first before changing PIN

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

### doc_bank_accounts_bank_accounts_(general)_031: Internal: Filing a Debit Card Transaction Dispute

When a customer needs to file a dispute for a debit card transaction (unauthorized charges, ATM errors, merchant issues, or incorrect amounts), the agent must gather comprehensive information and follow Regulation E requirements. Before proceeding, inform the customer of their liability exposure based on when they noticed the unauthorized activity:
- Reported within 2 business days of statement: Maximum liability $50
- Reported within 60 days of statement: Maximum liability $500
- Reported after 60 days: Unlimited liability - customer may not recover funds

Dispute the earliest (first) transaction when multiple duplicates exist.

**Pre-Filing Requirements:**
1. Customer must be verified
2. Transaction must be at least $1.00
3. Transaction must be within 60 days old
4. Customer cannot exceed the maximum open disputes for their checking account tier: Entry Tier max 2, Mid Tier max 3, Premium Tier max 4, Elite Tier max 5. Dispute limits are per account, not per customer.
5. The debit card must be linked to an OPEN checking account
6. For ATM disputes, determine if it was a Rho-Bank ATM or third-party ATM (different processes apply)

**Tool: file_debit_card_transaction_dispute_6281**

**Tool Arguments:**

1. **transaction_id** (string) - ID of the transaction being disputed. Use get_bank_account_transactions_9173 to find it.

2. **account_id** (string) - The checking account ID linked to the debit card.

3. **card_id** (string) - The debit card ID. 

4. **user_id** (string) - The customer's Rho-Bank user ID.

5. **dispute_category** (string) - Must be exactly one of:
   - 'unauthorized_transaction': Transaction customer did not make or authorize (use only when fraud is NOT suspected)
   - 'atm_cash_discrepancy': ATM dispensed wrong amount or no cash
   - 'atm_deposit_not_credited': ATM deposit not reflected in account
   - 'duplicate_charge': Same transaction charged multiple times
   - 'incorrect_amount': Charged different amount than expected
   - 'goods_services_not_received': Paid but never received item/service
   - 'recurring_charge_after_cancellation': Subscription cancelled but still charging
   - 'card_present_fraud': Physical card used fraudulently (not by customer) - USE THIS when fraud suspected and card was physically present
   - 'card_not_present_fraud': Online/phone transaction customer didn't make - USE THIS when fraud suspected for online/phone transactions

 When a transaction is unauthorized, determine if fraud is suspected. If YES, use 'card_present_fraud' (for in-store/physical transactions) or 'card_not_present_fraud' (for online/phone transactions). Only use 'unauthorized_transaction' when fraud is NOT suspected (e.g., family member used card without permission, customer forgot about a transaction, etc.).

6. **transaction_date** (string, MM/DD/YYYY) - Date the disputed transaction occurred.

7. **discovery_date** (string, MM/DD/YYYY) - Date customer first noticed the issue.

8. **disputed_amount** (float) - The dollar amount being disputed.

9. **transaction_type** (string) - Determine from user circumstances. Must be exactly one of:
   - 'pin_purchase': In-store purchase with PIN
   - 'signature_purchase': In-store purchase with signature
   - 'online_purchase': Online or card-not-present transaction
   - 'atm_withdrawal': ATM cash withdrawal
   - 'atm_deposit': ATM deposit
   - 'recurring_payment': Subscription or automatic payment
   - 'person_to_person': P2P transfer (EveryonePay, etc.)

10. **card_in_possession** (boolean) - Ask: "Do you still have your physical debit card in your possession?" This affects fraud classification.

11. **pin_compromised** (string) - Ask: "Do you believe your PIN may have been compromised?" Must be exactly one of:
    - 'yes_shared': Customer shared PIN with someone
    - 'yes_observed': Customer believes PIN was observed/skimmed
    - 'no': PIN not compromised
    - 'unknown': Customer unsure

12. **contacted_merchant** (boolean) - Ask: "Have you attempted to resolve this directly with the merchant?" Required for non-fraud disputes.

13. **police_report_filed** (boolean) - For fraud disputes over $500, ask if customer has filed a police report. If not, recommend they do so.

14. **written_statement_provided** (boolean) - Whether the customer has provided a written statement describing what happened. Required for Reg E provisional credit eligibility. Ask the customer: "Are you willing to provide a written statement describing what happened? We can use this conversation as your written statement if you agree." Set to true if the customer agrees.

15. **provisional_credit_eligible** (boolean) - Agent must determine based on Debit Card Provisional Credit Guidelines.

16. **card_action** (string) - Determine based on dispute category using the mapping below. Must be exactly one of:
    - 'keep_active': Keep card active
    - 'freeze_pending_investigation': Temporarily freeze card during investigation
    - 'close_and_reissue': Close card and issue replacement

**Note:** This parameter records metadata only; the agent must separately perform the indicated card action after filing the dispute.

**Card Action Mapping by Dispute Category:**
- 'card_present_fraud' → 'close_and_reissue'
- 'card_not_present_fraud' → 'close_and_reissue'
- 'unauthorized_transaction' → 'freeze_pending_investigation'
- 'atm_cash_discrepancy' → 'keep_active'
- 'atm_deposit_not_credited' → 'keep_active'
- 'duplicate_charge' → 'keep_active'
- 'incorrect_amount' → 'keep_active'
- 'goods_services_not_received' → 'keep_active'
- 'recurring_charge_after_cancellation' → 'keep_active'

**Multiple Disputes on Same Card:** When filing multiple disputes for the same card, record each dispute's card_action based on its own category mapping (do NOT change individual dispute parameters). However, when performing the actual card action after filing all disputes, use the MOST SEVERE action across all disputes. Severity order (highest to lowest): 'close_and_reissue' > 'freeze_pending_investigation' > 'keep_active'. For example, if Dispute A maps to 'keep_active' and Dispute B maps to 'freeze_pending_investigation', record 'keep_active' for Dispute A and 'freeze_pending_investigation' for Dispute B, but then call freeze_debit_card_3892 (the most severe action) once for the card.

### doc_bank_accounts_bank_accounts_(general)_032: Internal: Debit Card Provisional Credit Guidelines

Under Regulation E, Rho-Bank is REQUIRED to provide provisional credit for debit card disputes under certain conditions. 

**Timeline for Provisional Credit:**
- Standard accounts: Must issue within 10 business days of dispute filing
- New accounts (open less than 30 days): Must issue within 20 business days

**Provisional Credit is REQUIRED when ALL of these conditions are met:**

1. **Timely Reporting**: Customer reported the unauthorized transaction within 60 days of the statement date showing the transaction

2. **Dispute Category**: The dispute is for one of these categories:
   - 'unauthorized_transaction'
   - 'card_present_fraud'
   - 'card_not_present_fraud'
   - 'atm_cash_discrepancy'
   - 'duplicate_charge'

3. **Written Statement**: Customer has provided a written statement describing the unauthorized transaction

4. **Account Standing**: The checking account is in OPEN status with no holds or restrictions

**Provisional Credit is NOT REQUIRED (but may be offered at discretion) when:**

1. The dispute category is:
   - 'goods_services_not_received'
   - 'recurring_charge_after_cancellation'
   - 'atm_deposit_not_credited'
   - 'incorrect_amount'

2. Customer has not contacted merchant first (for non-fraud disputes)

3. Customer shared their PIN voluntarily (pin_compromised = 'yes_shared')

4. Account is less than 30 days old AND the dispute is for a card-not-present transaction

**Provisional Credit Amounts:**

Unlike credit cards which have tiered maximum amounts, debit card provisional credit is for the FULL disputed amount, subject to:
- Maximum: The full transaction amount
- Liability offset: If customer reported late, reduce by their liability amount ($50 or $500)

**Investigation Timeline with Provisional Credit:**

When provisional credit is issued, the bank has 45 business days to complete the investigation (extended from 10 days). For international transactions, POS transactions at merchants outside the US, or new accounts, the timeline extends to 90 days.

**If Investigation Finds Against Customer:**

If the investigation determines the transaction was authorized or the claim is invalid:
1. Provisional credit will be reversed
2. Customer will be notified in writing at least 3 business days before reversal
3. Customer has the right to request documentation supporting the finding

### doc_bank_accounts_bank_accounts_(general)_033: Internal: ATM Dispute Special Procedures

ATM-related disputes have unique requirements based on whether the ATM is Rho-Bank owned or a third-party ATM.

**Rho-Bank ATM Disputes:**

For transactions at Rho-Bank branded ATMs, we have access to internal records and can expedite investigation.

1. **Cash Discrepancy (machine dispensed wrong amount or no cash):**
   - View recent transactions on the corresponding checking accounts to pull ATM journal records for the transaction
   - Compare journal record to customer claim
   - If discrepancy confirmed, provisional credit is issued immediately (no waiting period)
   - If journal shows correct amount dispensed, inform customer the claim cannot be validated but they may still file a formal dispute

2. **Deposit Not Credited:**
   - Use get_atm_deposit_images_8473 to retrieve envelope/check images
   - Compare to expected deposit amount
   - Deposit disputes may take up to 45 days due to physical verification needs

3. **Card Retained by ATM:**
   - If Rho-Bank ATM, card can be retrieved from branch within 3 business days
   - Offer to either retrieve card OR close old card and order replacement
   - No dispute needed unless there are also unauthorized transactions

**Third-Party ATM Disputes:**

For transactions at non-Rho-Bank ATMs (Allpoint network, bank partners, or independent ATMs):

1. We must submit a chargeback request to the ATM owner/network
2. Investigation timeline extends to 90 days
3. Provisional credit is still required within 10 business days
4. Customer may be asked to sign an affidavit if disputed amount exceeds $200

**ATM Affidavit Requirement:**

For ATM cash discrepancy disputes exceeding $200, the customer must sign an Electronic Fund Transfer Error Resolution Affidavit. Inform the customer:
- An affidavit will be emailed to their registered email address
- They have 10 business days to sign and return it
- Failure to return the affidavit may result in denial of the claim
- Signing a false affidavit is a federal offense

### doc_bank_accounts_bank_accounts_(general)_034: Internal: Recurring Payment Disputes vs. Stop Future Payments

When a customer has issues with recurring debit card charges (subscriptions, memberships, automatic payments), there are TWO different processes depending on what they need:

**DISPUTE (Past Charges):**
Use the standard debit dispute process for charges that have ALREADY occurred. This applies when:
- Customer cancelled with merchant but was charged after cancellation
- Customer never authorized the recurring charge
- Amount charged differs from agreed amount

For recurring charge disputes, the dispute_category should be 'recurring_charge_after_cancellation'.

**BLOCK RECURRING PAYMENTS (Future Charges):**
To PREVENT future recurring charges on a debit card, use the recurring block feature. This blocks ALL recurring/subscription payments on the card - not just a specific merchant.

Blocking Process:
1. Verify customer identity
2. Explain that this will block ALL recurring payments on the card, not just one merchant
3. Use set_debit_card_recurring_block_7382 with:
   - card_id: The debit card ID
   - block_recurring: true to block, false to unblock
4. Inform customer:
   - Block takes effect within 24 hours
   - One-time purchases are NOT affected - only recurring/subscription charges
   - This does NOT cancel their subscriptions with merchants - they must still contact merchants directly
   - Block remains active until customer requests it to be removed

**When Customer Needs BOTH:**

If customer was charged after cancellation AND wants to prevent future charges:
1. First file the dispute for past charges
2. Then set up the recurring block for future protection
3. Still advise customer to confirm cancellation directly with merchant in writing

**Important Notes:**
- The recurring block affects ALL recurring payments, not just specific merchants
- If customer only wants to block one merchant, advise them to cancel directly with that merchant
- Customer can unblock recurring payments at any time by calling back

### doc_bank_accounts_bank_accounts_(general)_035: Internal: Checking Debit Card Dispute Status

To retrieve a customer's debit card dispute history and check the status of open disputes, use the get_debit_dispute_status_7483 tool.

**Tool: get_debit_dispute_status_7483(user_id: str)**

Returns a list of all debit card disputes filed by the customer, including:
- dispute_id: Unique identifier for the dispute
- transaction_id: The disputed transaction
- account_id: The checking account involved
- dispute_category: Type of dispute
- disputed_amount: Amount in dispute
- filing_date: When the dispute was filed
- status: Current status (see below)
- provisional_credit_issued: Boolean
- provisional_credit_amount: Amount of provisional credit if issued
- provisional_credit_date: Date provisional credit was applied
- expected_resolution_date: Estimated completion date
- resolution: Final outcome (if resolved)
- resolution_date: Date of resolution (if resolved)

**Dispute Statuses:**
- OPEN: Dispute filed, investigation in progress
- PENDING_DOCUMENTATION: Waiting for customer to provide additional documentation (affidavit, police report, etc.)
- UNDER_REVIEW: Investigation complete, under final review
- PROVISIONAL_CREDIT_ISSUED: Provisional credit applied, investigation ongoing
- RESOLVED_CUSTOMER_FAVOR: Dispute resolved in customer's favor, credit is permanent
- RESOLVED_BANK_FAVOR: Investigation found transaction was valid, no credit issued
- RESOLVED_PARTIAL: Partial credit issued
- PROVISIONAL_REVERSED: Provisional credit was reversed after investigation
- CLOSED_NO_RESPONSE: Closed due to customer not providing required documentation

**Timeline Monitoring:**
When checking dispute status, verify that regulatory timelines are being met:
- Provisional credit should be issued within 10 days (20 for new accounts)
- Investigation should complete within 45 days (90 for international/POS)

If a dispute appears to be exceeding timelines, escalate to a supervisor.

### doc_bank_accounts_bank_accounts_(general)_036: What To Do If You Notice an Unauthorized Debit Card Transaction

Discovering an unfamiliar charge on your debit card can be alarming, but don't worry—Rho-Bank is here to help you every step of the way. Because debit card transactions draw directly from your checking account, we take these matters very seriously and will work quickly to investigate and resolve the issue.

### Time is Important

With debit card disputes, how quickly you report the issue can affect your liability. Federal law provides strong protections, but they depend on timely reporting:

- **Report within 2 business days**: Your maximum liability is just $50
- **Report within 60 days**: Your maximum liability is $500
- **Report after 60 days**: You may not be able to recover the funds

If you notice something suspicious on your account, please contact us right away. Don't wait to see if additional charges appear.

### Types of Issues We Can Help With

You should contact us if you experience any of the following:

- **Unauthorized Transactions**: Charges you didn't make or approve
- **ATM Problems**: Cash not dispensed, wrong amount dispensed, or deposits not credited
- **Duplicate Charges**: The same transaction appearing multiple times
- **Incorrect Amounts**: Being charged more than you expected
- **Subscription Issues**: Being charged for a subscription you already cancelled
- **Missing Purchases**: You paid for something but never received it

### What Happens When You File a Dispute

When you report an issue to us, here's what you can expect:

1. **We'll gather information**: Our representative will ask you questions about the transaction and what happened
2. **Provisional credit**: For many types of disputes, we'll temporarily credit your account while we investigate, so you're not out of pocket. Provisional credit is typically issued within 10 business days.
3. **Investigation**: We'll research the transaction, which may involve contacting the merchant or ATM network
4. **Resolution**: We'll notify you of our findings, typically within 10 to 45 business days depending on the complexity

### What You'll Need

To help us process your dispute quickly, please have the following ready:

- Your account information
- Details about the transaction (date, amount, merchant name if known)
- When you first noticed the issue
- Whether you still have your physical debit card
- Any communication you've had with the merchant

### How to Reach Us

To report an unauthorized transaction or file a dispute, contact us immediately:

- **Phone**: 1-800-RHO-BANK (available 24/7 for fraud reports)
- **Mobile App**: Use the "Report Issue" feature on any transaction
- **Online**: Visit rhobank.com/disputes

For suspected fraud, we recommend also filing a police report, especially for amounts over $500. This can help with the investigation and may be required for certain claims.

At Rho-Bank, protecting your money is our priority. Don't hesitate to reach out if something doesn't look right—we're here to help.

### doc_bank_accounts_bank_accounts_(general)_037: Understanding Regulation E: Your Debit Card Consumer Protections

Regulation E is a federal regulation implemented by the Consumer Financial Protection Bureau (CFPB) that governs electronic fund transfers (EFTs) and provides important consumer protections for debit card transactions. As a Rho-Bank customer, understanding these protections can help you know your rights when issues arise with your debit card.

### What Regulation E Covers

Regulation E applies to electronic fund transfers including:
- Debit card purchases (both PIN and signature transactions)
- ATM withdrawals and deposits
- Direct deposits
- Automatic bill payments
- Person-to-person (P2P) transfers
- Recurring electronic payments

### Your Key Protections Under Regulation E

#### 1. Limited Liability for Unauthorized Transactions

If someone uses your debit card without permission, your liability is limited based on how quickly you report it:
- **Within 2 business days**: Maximum $50 liability
- **Within 60 days**: Maximum $500 liability
- **After 60 days**: You may be liable for the full amount

#### 2. Right to Dispute Errors

You have the right to dispute any error on your account, including:
- Unauthorized transactions
- Incorrect transaction amounts
- Missing deposits or transfers
- Computational errors
- Transactions that weren't completed as instructed

#### 3. Investigation Requirements

When you report an error, Rho-Bank must:
- Investigate promptly (typically within 10 business days)
- Report results to you within 3 business days of completing the investigation
- Correct any confirmed errors within 1 business day of determination

#### 4. Provisional Credit

For qualifying disputes, Rho-Bank must provide provisional (temporary) credit within 10 business days if the investigation takes longer than 10 business days. This ensures you're not left without access to your funds during the investigation.

#### 5. Documentation Rights

You have the right to:
- Receive written confirmation of error resolution
- Request copies of documents used in the investigation
- Receive advance notice before provisional credit is reversed

### How to Exercise Your Regulation E Rights

To dispute an unauthorized or erroneous transaction:
1. Contact Rho-Bank customer service as soon as you notice the issue
2. Provide details about the transaction(s) in question
3. Follow up with a written statement if requested
4. Keep records of all communications

### Important Notes

- These protections apply specifically to debit card and electronic transactions, not credit cards (which are covered by different regulations)
- Business accounts may have different protections than personal accounts
- Promptly reviewing your statements helps you identify issues quickly and maximize your protections

### Decline Codes Related to Lost, Stolen, or Fraudulent Cards

When your debit card is declined due to security concerns, you may see one of the following decline codes. These codes are directly related to the protections described in this document.

#### CODE 41 - Lost Card

Card was previously reported lost. Look up the debit card information to confirm - the card will have issue_reason = 'lost' or status will indicate lost.

1. Check if customer actually reported it: 'I see this card was reported lost. Did you report it lost?'

2. If customer says YES and found the card:
   - The old card CANNOT be reactivated once reported lost.
   - Check if replacement card was ordered by looking for another card in the response. If a replacement exists with status PENDING, guide through activation with the internal protocol.
   - If no replacement ordered, offer to help order one.

3. If customer says NO (they didn't report it):
   - SECURITY CONCERN: Someone else may have reported it.
   - Say: 'For your security, I need to verify some additional information.'
   - Ask security questions. If verified, this may indicate account compromise.
   - Review recent transaction history to check for suspicious activity.
   - Follow lost debit card protocol to help the customer.

#### CODE 43 - Stolen Card (SECURITY SENSITIVE)

Card was reported stolen. This code requires EXTRA CAUTION.

1. DO NOT immediately offer to unfreeze or reactivate.

2. Verify customer identity using ENHANCED verification (not standard):
   - Full name, date of birth, AND
   - Last 4 of SSN, AND
   - Recent transaction verification - review transaction history and ask about 2-3 recent transactions

3. After enhanced verification, explain: 'This card was reported stolen. For security, stolen cards cannot be reactivated. I can order you a replacement card with a new number.' Follow protocol to order a new one.

4. If customer insists they never reported it stolen:
   - This is a MAJOR security flag. Someone may have access to their account.
   - Say: 'I understand this is frustrating. For your protection, I need to transfer you to our security team who can investigate this further.'
   - Use transfer_to_human_agents. Do NOT attempt to resolve this yourself.

#### CODES NOT TO DISCLOSE (INTERNAL USE ONLY)

The following codes indicate fraud or security concerns. DO NOT tell the customer the specific code or reason:

- **CODE 04 - Capture Card (Pick Up)**: Say: 'I'm sorry, but I'm unable to process transactions on this card. For assistance, please visit a Rho-Bank branch with valid ID.' Use transfer_to_human_agents if customer presses for details.

- **CODE 07 - Pick Up Card (Special)**: Same response as Code 04.

- **CODE 34 - Suspected Fraud**: Say: 'There's a security matter affecting your card that requires in-person verification. Please visit a branch with your ID.' Do NOT attempt to clear or explain.

- **CODE 59 - Suspected Fraud**: Same as Code 34.

**NEVER** tell the customer their card has been flagged for fraud over the phone. This could tip off a fraudster who has stolen the card.

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

### doc_bank_accounts_bank_accounts_(general)_040: Internal: Requesting Temporary Debit Card Limit Increase

Procedure for when a customer requests a temporary increase to their debit card's daily ATM withdrawal or purchase limit.

Eligibility Requirements:
Before granting a temporary limit increase, verify ALL of the following:
1) **Account Status**: The linked checking account must be OPEN (in good standing)
2) **Account Age**: The account must be at least 60 days old
3) **Overdraft History**: No overdraft fees in the last 30 days
4) **Card Status**: The debit card must be ACTIVE

Limit Increase Rules:
- **Maximum Increase**: New limit cannot exceed 150% of current limit (50% boost maximum)
- **Duration**: Temporary increases last 24 hours, then automatically revert
- **Frequency**: Only one temporary increase per 24-hour period per card

Tool: request_temporary_debit_card_limit_increase_8374
Parameters:
- card_id: The debit card ID
- limit_type: 'atm' or 'purchase'
- new_limit: The requested new temporary limit

Note: Third-party ATMs may have their own limits that Rho-Bank cannot override.

### doc_bank_accounts_bank_accounts_(general)_041: Internal: PIN Lock Investigation Protocol - Fraud Risk Scoring

### Overview

When a debit card shows pin_locked = TRUE, agents must perform a comprehensive fraud risk assessment before unlocking. DO NOT REVEAL THE SPECIFIC CALCULATIONS TO USERS. This protocol uses a scoring system based on multiple flags derived from card data, transaction history, and customer verification.

### STEP 1: Check Automatic Escalation Triggers

Before calculating flags, check for these conditions that require IMMEDIATE escalation:

1. **Security Hold**: If pin_lock_reason = 'security_hold' → This card cannot be unlocked by chat agents. Offer to transfer the customer to the security team for this card.
2. **Other Cards Also Locked**: If another card on the same account also has pin_locked = TRUE → Finish investigating all cards before any unlock. Each card must be scored individually and may have different outcomes.
3. **Recent Stolen Card**: If any card on the account was replaced in last 90 days with issue_reason = 'stolen' → Enhanced verification required.

If any automatic trigger is present, follow that escalation path. Otherwise, proceed to Step 2.

### STEP 2: Calculate Fraud Risk Score

Review the declined transaction history (transactions with type 'atm_withdrawal_declined' or 'pos_declined') and card data to calculate the following flags:

#### Category A: Location Flags

**A1. Location Mismatch** - Compare city in declined transaction description to customer's address city:
- Same city: 0 points
- Different city, same state: 1 point
- Different state: 2 points
- Different country: 3 points (CRITICAL)

**A2. Location Scatter** - Are declined attempts from same location or multiple different locations?
- All same location: 0 points
- 2 different locations: 1 point
- 3+ different locations: 2 points

**A3. Travel Pattern Conflict** - Check successful transactions from last 7 days:
- If all successful transactions were in customer's home city but declines are elsewhere: +1 point
- If customer has recent transactions in various cities (traveling): 0 points

#### Category B: Time Flags

**B1. Time of Day** - Hour when declined transaction occurred:
- 6 AM - 10 PM: 0 points
- 10 PM - 12 AM: 1 point
- 12 AM - 2 AM: 2 points
- 2 AM - 6 AM: 3 points (HIGH RISK)

**B2. Time Since Last Legitimate PIN Use** - Compare to when the customer last successfully used their PIN:
- Less than 24 hours: 0 points
- 1-7 days: 0 points
- 7-30 days: 1 point
- More than 30 days: 2 points

**B3. Attempt Velocity** - Time between consecutive failed attempts:
- More than 5 minutes apart: 0 points
- 2-5 minutes apart: 1 point
- 1-2 minutes apart: 2 points
- Less than 1 minute apart: 3 points (SCRIPTED ATTACK)

#### Category C: Amount Flags

**C1. Amount Pattern** - Compare amounts across consecutive failed attempts:
- Consistent amounts (same amount retried): 0 points
- Increasing amounts: 0 points
- Decreasing amounts (e.g., 800→500→300): 2 points (FRAUD PATTERN)

**C2. Round Number Testing** - Are all attempted amounts suspiciously round?
- Mixed amounts: 0 points
- All round hundreds (800, 500, 300, etc.): 1 point

**C3. Amount vs Historical Average** - Calculate customer's average ATM withdrawal from recent successful transactions:
- Attempted amount within 2x average: 0 points
- Attempted amount 2-5x average: 1 point
- Attempted amount more than 5x average: 2 points

**C4. Amount vs Daily Limit** - Compare attempted amount to card's daily ATM withdrawal limit:
- Less than 50% of limit: 0 points
- 50-80% of limit: 0 points
- 80-100% of limit: 1 point
- Multiple attempts totaling more than daily limit: 2 points

#### Category D: Card History Flags

**D1. Lock Frequency** - Check how many times this card's PIN has been locked in the last 90 days:
- 0 prior locks: 0 points
- 1 prior lock: 1 point
- 2 prior locks: 2 points
- 3+ prior locks: 3 points (AUTOMATIC PIN RESET REQUIRED - cannot unlock)

**D2. Card Age** - Calculate how long the card has been active:
- More than 1 year: 0 points
- 6-12 months: 0 points
- 3-6 months: 0 points
- 1-3 months: 1 point
- Less than 1 month: 2 points

**D3. Other Card Issues** - Check if the customer's other debit cards have any security flags:
- All other cards have no issues: 0 points
- Another card has a velocity block: +1 point
- Another card has a fraud alert active: +2 points

#### Category E: Account Flags

**E1. Account Age** - Calculate how long the account has been open:
- More than 2 years: 0 points
- 1-2 years: 0 points
- 6-12 months: 0 points
- 3-6 months: 1 point
- Less than 3 months: 2 points

**E2. Overdraft History** - Check for overdraft fees in recent transaction history:
- No overdrafts: 0 points
- 1 overdraft: 1 point
- 2+ overdrafts: 2 points

**E3. Low Balance Alert** - Check the account's current balance:
- More than $500: 0 points
- $100-500: 0 points
- $50-100: 1 point
- Less than $50: 2 points (account may be abandoned/compromised)

### STEP 3: Apply Score Thresholds

After calculating total score from all applicable flags:

| Total Score | Risk Level | Required Protocol |
|-------------|------------|-------------------|
| 0-4 | LOW | Unlock after standard identity verification |
| 5-7 | MEDIUM | Unlock only after asking: 'I see failed PIN attempts on your card. Were those attempts yours?' |
| 8-10 | HIGH | Must ask specific questions about location and time. Only unlock if customer confirms AND provides satisfactory explanation. |
| 11-14 | VERY HIGH | Cannot unlock on this call. Require callback verification OR enhanced verification (last 4 SSN + security question). |
| 15+ | CRITICAL | CANNOT unlock. Check for successful unauthorized transactions. Recommend card closure and replacement. |

#### Single Flag Escalation

If ANY single flag equals 3 points, escalate to supervisor review regardless of total score.

### STEP 4: Customer Verification Questions

For scores of 5 or higher, ask these questions based on flags present:

**If Location Mismatch flag is scored:**
'I see your card was locked after failed PIN attempts at [location from transaction]. Were you at that location?'
- If customer says YES: Remove location flags, recalculate score.
- If customer says NO: Maintain score, proceed with caution.

**If Amount Pattern flag is scored:**
'The attempts were for [amount 1], then [amount 2], then [amount 3]. Do you remember trying those specific amounts?'
- If customer confirms: Remove amount pattern flag.
- If customer denies or seems confused: Maintain flag.

**If Time of Day flag is scored (2+ points):**
'These attempts occurred at [time]. Were you trying to use your card at that time?'
- If customer confirms: Remove time flag.
- If customer says 'I was asleep' or similar: CRITICAL - likely fraud.

### STEP 5: Post-Unlock Requirements

After unlocking (for eligible cases), complete these steps based on D1 Lock Frequency:

- **0 prior locks**: Standard unlock, no additional steps.
- **1 prior lock**: After unlock, MUST offer: 'Would you like me to enable PIN lock notifications so you're alerted if this happens again?'
- **2 prior locks**: After unlock, MUST ask: 'This is your third PIN lock in 90 days. Would you like me to reset your PIN to a new number? Frequent locks sometimes indicate the current PIN is difficult to remember.'
- **3+ prior locks**: Cannot unlock. Must reset PIN.

### STEP 6: If Cannot Unlock

For scores above thresholds or automatic escalation triggers:

1. Check transaction history for any successful unauthorized transactions during the suspicious period.
2. If unauthorized transactions found: File dispute, close card, order replacement.
3. If no unauthorized transactions: Explain the security concern and offer options:
   - Card closure and replacement (recommended if fraud suspected)
   - Transfer to security team for investigation
   - PIN reset (issues new PIN, invalidates potential compromise)

### doc_checking_accounts_checking_accounts_(general)_003: FAQ: Common Error Codes

### How to use this reference
Identify the error code, confirm the action the customer attempted, and follow the suggested resolution.

#### Error reference
- Error 101 — Invalid account or routing details
  - Ask the customer to verify and re-enter account and routing numbers exactly as issued by their bank.
- Error 202 — Insufficient funds
  - Suggest depositing funds or reducing the payment or transfer amount, then retrying.
- Error 403 — Authentication failed
  - Have the customer reset their password and confirm they are signing in with the correct profile. Check for account security holds.
- Error 409 — Duplicate transaction request
  - Advise the customer to wait for the initial request to settle or cancel before attempting again.
- Error 429 — Too many attempts
  - Recommend waiting before retrying and ensuring details are correct to avoid rate limits.
- Error 903 — Account closure request blocked
  - This can occur when attempting to close an account. Instruct the customer to wait 48 hours and try again.

### If errors persist
- Capture screenshots, timestamps, and the exact workflow leading to the error.
- Verify device, browser, and app version details.
- Escalate with logs if multiple attempts produce the same result.

### Debit Card Decline Codes - Card Status and Validity Issues

The following decline codes indicate issues with the card's status or validity:

#### CODE 05 - Do Not Honor (Generic Decline)

This is a catch-all code that requires investigation. Check the following IN ORDER:

1. **Card Status**: Look up the debit card information and check the card's status field.
   - If status is FROZEN → Ask customer if they want to unfreeze. If yes, follow the freezing/unfreezing card protocol.
   - If status is CLOSED → Inform customer this card is no longer active. Check if they have another active card or offer to order a replacement.
   - If status is PENDING → Card not yet activated. Follow protocol to activate it.
   - If status is ACTIVE → Continue to step 2.

2. **Account Status**: Look up the customer's accounts to check the linked checking account.
   - If account status is not OPEN → Inform customer their account has a restriction. DO NOT provide specific details if status is SUSPENDED or RESTRICTED. Say: 'Your account has a restriction that is preventing transactions. Please visit a branch or call our dedicated account services line at 1-800-RHO-ACCT for assistance.'

3. **Fraud Alert**: Check the card's fraud_alert_active field from the debit card lookup response.
   - If fraud_alert_active is TRUE and alert_source is 'customer_initiated' → Ask customer to verify recent transactions. If they confirm all transactions are legitimate, clear the alert.
   - IMPORTANT: If fraud_alert_active is TRUE and alert_source is 'bank_initiated' → Do NOT clear it. Say: 'I see there's a security flag on your account that requires additional review. I'm transferring you to our security team.' Then transfer to human agents.

4. **Velocity Block**: Check the card's velocity_blocked field from the debit card lookup response.
   - If velocity_blocked is TRUE, inform customer: 'Your card was temporarily blocked because our security system detected unusual activity patterns. This block automatically lifts after 30 minutes. Would you like me to verify your identity and lift it now?'
   - To lift early: Verify customer identity, then clear the velocity block.

#### CODE 14 - Invalid Card Number

The card number entered doesn't match records. Possible causes:

1. **Typo**: Customer or merchant may have entered card number incorrectly. Ask customer to verify they're using the correct card.

2. **Card Replaced**: Customer may be using old card number after replacement.
   - Look up all debit cards for the account.
   - If there's a newer card with status ACTIVE and an older card with status CLOSED, inform customer: 'I see you received a new card on [date_issued]. The old card number is no longer valid. Please use your new card ending in [card_number_last_4].'
   - If new card is PENDING (not activated), help the user activate the card.

3. **Online Transaction with Old Saved Card**: Customer may have old card saved with merchant.
   - Advise: 'If you have card details saved with this merchant, you may need to update them with your new card information.'

#### CODE 54 - Expired Card

The card has passed its expiration date.

1. Verify expiration: Look up the debit card information and check expiration_date field.

2. If card IS expired:
   - Check if replacement was already sent. Look for another card with issue_reason = 'expired' and status PENDING or ACTIVE.
   - If replacement exists and is PENDING: Guide through the appropriate activation protocol article.
   - If replacement exists and is ACTIVE: Customer may be using old card. Direct them to new card.
   - If NO replacement exists: 'It looks like your replacement card wasn't automatically sent. Let me order one for you now.' and call the appropriate tools to do so.

#### CODE 56 - No Card Record

The card number format is valid but no record exists in Rho-Bank's system at all. This is different from Code 14 (invalid number) - here the number is valid but completely unknown.

1. **Possible Causes**:
   - Card was reported lost/stolen AND fully purged from the system (rare)
   - Customer is using a card from a different bank
   - Data entry error at merchant

2. Ask customer to verify they are using a Rho-Bank debit card (check for Rho-Bank logo).

3. Look up the debit cards for the account to see what cards exist.
   - If the card_number_last_4 from customer doesn't match any cards on file, the card may have been fully removed.
   - Offer to order a new card.

### doc_checking_accounts_checking_accounts_(general)_004: What is an authorization hold?

### Overview
An authorization hold is a temporary hold on funds in your account that are not available for use. Merchants commonly place these holds to confirm sufficient funds or to secure deposits for services such as lodging, fuel, and rentals.

### Why merchants use holds
- To verify the card is valid and has sufficient funds before providing goods or services.
- To secure a temporary deposit that may be adjusted once the final amount is known.

### Visibility in your account
- Authorization holds may not show up in your recent transactions list immediately.
- Even if you do not see a line item, the hold reduces your available balance until it is released or finalized.

### Paycheck deposit holds
Rho-Bank will keep a temporary hold on paycheck deposits that are then refunded. This can affect your available balance shortly after a deposit posts.

### When a hold is released
- If the merchant finalizes the charge, the hold converts to a posted transaction.
- If the merchant releases or reduces the hold, the corresponding amount returns to your available balance.
- Timing depends on the merchant’s processing and settlement practices.

### doc_checking_accounts_checking_accounts_(general)_006: Why does my account have a lower balance than I expected or have a negative balance?

### What can cause a lower or negative balance
- Overdraft protections may temporarily cover transactions, which can display a negative balance until incoming funds post or adjustments complete.
- Authorization holds reduce your available balance while a merchant finalizes a purchase or security deposit.
- Pending card transactions and checks can decrease available funds before they appear as posted.
- Scheduled payments or transfers may be earmarked, lowering your available balance in advance.

### How to review and resolve
- Check both pending and posted activity to understand current holds and recent payments.
- Add funds or transfer money from another account to restore a positive available balance.
- If a hold seems higher than expected, contact the merchant to request a release or adjustment.
- Review and adjust overdraft settings to align with your preferences for coverage and fees.
- If something looks incorrect, contact support with transaction details and timestamps.

### Decline Codes Related to Balance Issues

If your debit card was declined due to balance-related reasons, you may have encountered one of these codes:

#### CODE 51 - Insufficient Funds

The account doesn't have enough funds for the transaction. This is the most common decline but requires careful diagnosis.

1. **Check Current Balance**: Look up the customer's accounts to get the checking account balance.

2. **If balance APPEARS sufficient** for the transaction amount:
   
   a. **Check Authorization Holds**: Ask the customer if they have any recent authorization holds that might be reducing their available balance.
      - Authorization holds reduce available balance but don't show as posted transactions.
      - Common sources: gas stations (often $75-$150 pre-auth), hotels, car rentals, restaurants (tip buffer).
      - If holds exist, explain: 'Your posted balance is $[balance], but you may have pending authorization holds reducing your available balance. These holds typically release in 1-3 business days.'

   b. **Check Pending Transactions**: Review recent transaction history and look for transactions with status 'pending'.
      - Pending debits reduce available balance.
      - Explain: 'You have pending transactions totaling $[amount] that haven't posted yet.'

   c. **Check Overdraft Settings**: The account's overdraft_pos_enabled field from the account lookup shows if overdraft is enabled for POS.
      - Regulation E requires customer opt-in for POS/ATM overdraft coverage.
      - If overdraft_pos_enabled is FALSE: 'Your account isn't opted into overdraft coverage for debit card purchases. Would you like me to explain your options?' Then reference the overdraft features documentation.

3. **If balance is genuinely insufficient**:
   - Inform customer of their balance.
   - Offer options: 'Would you like to transfer funds from another account, or would you prefer to make a smaller transaction?'
   - If they want to transfer, help them do so.

#### CODE 52 - No Checking Account

The PIN was accepted but the underlying checking account has issues.

1. Look up the customer's accounts to check the account status.

2. If account status is CLOSED: 'The checking account linked to this debit card has been closed. This card can no longer be used for transactions.'
   - If customer wants to continue banking with Rho-Bank, discuss opening a new checking account.

3. If account exists and is OPEN but still getting this code: This may be a system synchronization issue. Advise waiting 10-15 minutes and retrying.

### doc_checking_accounts_green_account_(checking)_007: Green Account (checking): Troubleshooting: declined transactions

### Quick checks
- Verify your available balance covers the full amount requested.
- Review any pending authorizations that may be reducing your available balance.
- If you received a decline notification, check the message details: Yes.

### Merchant-specific considerations
- Confirm that the merchant did not attempt a higher amount than expected.
- For subscription or recurring charges, ensure funds are available on the charge date.

### What to do next
- Add funds and retry the transaction.
- If the decline persists after funding, contact the merchant to verify the amount they are attempting.
- Keep records of the decline notice if you receive alerts: Yes.

### doc_checking_accounts_green_account_(checking)_008: Why was my Green Account (checking) transaction declined?

### Common reasons
- The requested amount exceeded your available balance at the time of authorization.
- Pending card holds temporarily reduced your available balance.
- The final amount presented by the merchant was higher than the initial estimate.

### How to confirm
- Check your decline notification if you receive alerts: Yes.
- Review your recent activity for pending holds or prior transactions that used available funds.

### How to resolve
- Add funds and attempt the transaction again.
- Ask the merchant to confirm the amount they are submitting for authorization.

### doc_checking_accounts_light_green_account_002: Light Green Account specifications and requirements

### Eligibility requirements
- You must be the primary account holder and be between 13 and 24 years old to open the account.
- You must remain within the 13–24 age range to maintain the account.

#### Age verification and ongoing eligibility
- Your eligibility is determined using your date of birth at account opening and on an ongoing basis.
- Once you are no longer within the 13–24 range, you are no longer eligible to maintain the Light Green Account.

### Key specifications
- Overdraft fees: None (no overdraft fee is charged on this account)

### Rates
- Interest earned: 0.05% APY on the account balance

### Fees and limits
| Item | Amount/Limit |
|---|---|
| Monthly maintenance fee | $0.00 |
| Returned deposit fee (per returned item) | $12.50 |
| Incoming domestic wire transfer fee (per incoming wire) | $10.00 |
| Debit card daily purchase limit | $250 per day |

### Linked savings APY boosts
- If you link a Platinum Savings Account, you receive a 0.65% APY boost on that savings account.
- If you link a Diamond Elite Savings Account, you receive a 0.2% APY boost on that savings account.

### Referral program requirements
To participate in the Light Green Account referral program:
- The person you refer must deposit at least $100 within 90 days of opening their account.
- Referrer eligibility is based on account tenure: you must have opened your first Rho-Bank checking account at least 14 days ago.

### doc_checking_accounts_light_green_account_005: Spending limits and safety features for minors

### Daily spending limit
- Card-based purchases are capped at $300 per day. Attempts above this threshold are declined to help prevent overspending.

### ATM cash access
- Cash withdrawals are limited to $150 per day at ATMs. This helps manage cash use while limiting exposure if a card is lost or stolen.

### EveryonePay transfers
- Person-to-person payments via EveryonePay are limited to $250 per day.

### Alerts for higher-value transactions
- Parent or guardian notifications are triggered for transactions at or above 62. Adjust your monitoring approach by aligning the alert threshold with typical spending patterns.

### Debit Card Decline Codes - Transaction Limits and Restrictions

The following decline codes indicate that a transaction was blocked due to limits or restrictions on the card:

#### CODE 57 - Transaction Not Permitted to Cardholder

The card has restrictions that block this type of transaction. Check the card's restrictions from the debit card lookup:

1. **Merchant Category Code (MCC) Block** (check restricted_mccs field):
   - Common blocks: gambling (MCC 7995), adult content (MCC 5967), cryptocurrency (MCC 6051)
   - For gambling/adult: 'Your card has category restrictions that block this type of merchant. These restrictions can be modified through your account settings or by visiting a branch.'
   - IMPORTANT: Do NOT remove MCC blocks over the phone for gambling or adult content. Customer must do this themselves via app or in-branch. Say: 'For your protection, these specific restrictions can only be modified through our mobile app or by visiting a branch in person.'

2. **International Transactions Blocked** (check international_enabled field):
   - If international_enabled is FALSE and transaction was international:
   - 'International transactions are currently blocked on your card. Would you like me to enable them?'

3. **Online Transactions Blocked** (check online_enabled field):
   - If online_enabled is FALSE:
   - 'Online/card-not-present transactions are blocked on your card. Would you like to enable them?'

4. **Teen/Light Green Account Restrictions**:
   - If account_class is 'Light Green Account', there may be parental controls.
   - 'This account has parental controls that restrict certain transaction types. The primary account holder can modify these settings.'
   - Do NOT modify parental controls without the guardian's authorization.

#### CODE 58 - Transaction Not Permitted to Terminal

Similar to Code 57, but the specific merchant TERMINAL is blocked rather than the merchant category. This typically indicates a flagged terminal.

1. This is NOT something the customer or agent can resolve - the terminal itself has been flagged.

2. Explain: 'This particular payment terminal has been flagged in our system. Your card should work at other terminals or merchants.'

3. Advise customer to try a different register at the same store, or a different merchant entirely.

4. If customer reports this happening at multiple unrelated terminals: This may indicate an issue with their card. Follow Code 05 diagnostic steps.

#### CODE 61 - Exceeds Withdrawal Amount Limit

Transaction exceeds the card's daily purchase or ATM limit. Check limits from the debit card lookup:
- daily_purchase_limit: Maximum daily purchase amount
- daily_atm_limit: Maximum daily ATM withdrawal
- daily_purchase_used: Amount already used today
- daily_atm_used: ATM amount already used today

1. Calculate remaining: 'Your daily [purchase/ATM] limit is $[limit]. You've used $[used] today, leaving $[remaining] available.'

2. If customer needs higher limit:
   - **Temporary Increase**: Temporary increases last 24 hours.
   - **Permanent Increase**: Depends on account tier. Elite tier can request permanent increases. Tell customer: 'I can request a temporary increase that lasts 24 hours. Would you like me to do that?'

3. IMPORTANT: For ATM limits at non-Rho ATMs, the other bank's ATM may have its own lower limit that we cannot override.

#### CODE 62 - Restricted Card

Card has geographic restrictions. Check allowed_regions and blocked_regions from the debit card lookup.

1. **Geographic Restriction**: Card may be region-locked.
   - If customer is traveling: 'Your card is currently restricted to [regions]. Since you're traveling to [location], I can add that region.'

2. **New Card Restriction**: If card was issued within last 24 hours (check date_issued):
   - 'New cards have a brief security hold while they're being set up in all systems. This should clear within 24 hours of activation.'

#### CODE 65 - Activity Count Exceeded

Too many transactions in the current period. Check daily_transaction_count and daily_transaction_limit from the debit card lookup.

1. Explain: 'Your card allows [limit] transactions per day. You've made [count] transactions today.'

2. Transaction count limits are typically fixed and cannot be increased. Customer must wait until midnight for reset.

3. Alternative: If customer has multiple Rho-Bank accounts, they could use a different card.

### doc_checking_accounts_light_blue_account_002: Light Blue Account at a glance

### Quick facts
- APY on your balance: 0%
- Daily mobile check deposit limit: $2,000
- Early direct deposit: 0 day(s) before payday

### Notes
- If you plan to deposit multiple checks in one day, track your total to stay within the $2,000 daily limit.
- This account offers 0 day(s) early access to direct deposits.

Shared context paths (construction metadata, not policy facts):
- `tau2/hyper/sops/banking_sop.md`
