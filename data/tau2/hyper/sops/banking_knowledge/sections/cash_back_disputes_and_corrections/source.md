## Cash-back dispute submission and resolved-dispute correction

Bundle id: `cash_back_disputes_and_corrections`

Construction context (guidance for transcript induction, not section
content -- do not extract as policy facts): the shared banking handbook
governs identity verification, explicit customer confirmation before
account-modifying actions, discoverable-tool wrapper behavior, schema
limits, and exact transfer wording. Express these behaviorally in
transcripts where a case exercises them; do not restate them as section
facts. The bundle id, transcript focus, losslessness risks, and shared
context paths in this file are construction metadata, not policy facts.

Transcript focus:
Filing cash-back disputes, applying resolved corrections, and comparing expected rewards to source product rules.

Losslessness risks:
- Preserve which tool/action files the dispute versus the correction.
- Preserve reward-unit distinctions and rounding.
- Preserve product-specific exclusions that can make a dispute invalid.

Source documents:

### doc_credit_cards_credit_cards_(general)_003: Submitting a Cash Back Dispute (Internal)

### When to use this
Use this process when a customer believes there is a discrepancy between the cash back they received for a particular transaction and the cash back they should have received. This process applies to all credit card transactions.

### How to submit the dispute
Instead of a step-by-step workflow, instruct the customer to use the tool directly:

- Tool to provide to the user: `submit_cash_back_dispute_0589(user_id: str, transaction_id: str)`
- Tell the customer to run the tool with their own user_id and the specific transaction_id for the purchase in question.

### Agent notes
- Confirm the customer has the correct transaction_id before they submit.
- Do not collect sensitive card details; the tool uses the identifiers provided by the user.
- Advise the customer that supporting context (e.g., category or promotion expectations) may be requested later during review, but the submission itself is initiated with the tool above.

### doc_credit_cards_credit_cards_(general)_004: Applying Resolved Cash Back Dispute Corrections (Internal)

### Overview
After a cash back dispute is resolved and approved, you must update the affected transaction(s) with the correct rewards value.

### Required steps
1) Identify transactions requiring correction
- Look up the user’s resolved disputes in the cash_back_disputes database to find the transaction_id values that need rewards adjustments.

2) Unlock the internal update tool
- Use `unlock_discoverable_agent_tool` to unlock the agent tool `update_transaction_rewards_3847`.

3) Recalculate the correct rewards
- Recalculate the correct rewards for each transaction based on the card type, transaction category, and any applicable promotions.
- Important: Do not rely on any expected_rewards field in the dispute record. Independently verify rates and eligibility.

4) Apply the corrected rewards
- Use `call_discoverable_agent_tool` to invoke `update_transaction_rewards_3847` with:
  - transaction_id: the exact transaction identifier
  - new_rewards_earned: a string formatted as 'X points' where X is the correct whole-number point value

### Compliance and accuracy
- Ensure your calculation reflects the proper base rate and any active bonus category or promotion at the time of purchase.
- Confirm the update in credit_card_transaction_history after the tool call completes.
- Retain your calculation notes in the internal case record for auditability.

### doc_credit_cards_credit_cards_(general)_006: Internal: Credit Card Rewards - Points vs Cash Back Representation

### Rewards representation
Due to a legacy backend migration that has not yet been completed, all credit card rewards in the transaction database are stored as 'points' regardless of whether the card is a cash back card or a points-based card. For cash back cards (Bronze Rewards Card, Silver Rewards Card, Gold Rewards Card, Platinum Rewards Card, Diamond Elite Card, Crypto-Cash Back, Business Bronze Rewards Card, Business Silver Rewards Card, Green Rewards Card, Silver Zoom Card, Business Gold Rewards Card, and Business Platinum Rewards Card), these 'points' should be interpreted as cash back with a conversion rate of 1 point = $0.01 when redeemed as a statement credit or as a credit to the user's Rho-Bank checking account. For example, 250 points equals $2.50 in cash back, which matches a 2.5% cash back rate on a $100 purchase. The only true points-based card is the EcoCard, which earns 'sustainability points' (5 points per dollar on green purchases, 1 point per dollar on other purchases) that also redeem at $0.01 per point when redeemed as a statement credit or checking account credit.

### doc_credit_cards_credit_cards_(general)_007: Credit Card Rewards Points Rounding Policy

### Rounding policy
All credit card rewards points are rounded down to the nearest whole number. When calculating points earned on a purchase, the system always truncates (floors) fractional points rather than rounding to the nearest integer. For example, a $126.77 purchase on a 1% cash back card earns 126 points (not 127), because 126.77 × 0.01 = 1.2677 points, which rounds down to 1 point per dollar, giving 126 points. Similarly, a $99.99 purchase at 2.5% cash back would calculate to 249.975 points but would award 249 points. This rounding policy applies consistently across all credit card types and reward categories.

### doc_business_credit_cards_business_silver_rewards_card_002: Business Silver Rewards Card: How to Earn 10% Back on Travel and Software Purchases

### Earning rates
- Earn 10.0% cash back on eligible travel and software purchases
- Earn 1.0% cash back on all other purchases

### Making sure your purchase qualifies
- The merchant must process the transaction under a travel or software-related merchant category
- Online purchases should be billed by the service provider itself or an authorized platform categorized as travel or software
- If a merchant sells multiple categories of goods or services, your charge must be coded under a qualifying category to receive 10.0%

### Best practices
- Use this card for airfare, lodging, car rentals, transit, and other travel booked directly with providers or recognized travel agencies
- Use this card to pay recurring SaaS subscriptions and cloud-based software billed by software providers
- Keep receipts and confirmations in case a merchant’s category coding needs review

### doc_business_credit_cards_business_silver_rewards_card_005: Business Silver Rewards Card: Exceptions and Exclusions

### Important exclusions
The following specific merchants do NOT earn the 10.0% bonus rate and instead earn the standard 1.0% rate:

**Corporate Expense Platform Merchants (Travel Exclusion):**
- Concur
- SAP Concur
- Expensify
- Navan

**Hardware/Electronics Merchants (Software Exclusion):**
- Apple
- Microsoft
- Dell

**Gaming Subscription Merchants (Software Exclusion):**
- Xbox Game Pass
- PlayStation Plus
- Nintendo Switch Online

**Online Learning Platform Merchants (Software Exclusion):**
- Coursera
- Udemy
- LinkedIn Learning
- Skillshare
- Pluralsight

### doc_business_credit_cards_business_silver_rewards_card_012: Business Silver Rewards Card: Double Cash Back Promo

### Limited-time offer: double your cash back
New Business Silver Rewards Card customers can earn 2x cash back on all purchases for the first 6 months after opening their account.

### How it works
- Travel and software purchases that normally earn 10.0% are multiplied by 2 during the promotional period
- Other purchases that normally earn 1.0% are multiplied by 2 during the promotional period
- The increased rewards rate is automatically applied to qualifying transactions; no separate enrollment is required

### Promo period
- Start date: 2024-11-14
- End date: 2025-11-14

### Important details
- The 6-month window begins on your account opening date, not the promotional start date
- You must open your account during the promotional period to qualify
- Merchant category exclusions continue to apply (see Exceptions and Exclusions)
- Cash back is credited to your account at the end of each billing cycle consistent with program rules

### doc_credit_cards_silver_rewards_card_002: Silver Rewards Card: How to Earn 4% Cash Back on Travel and Software Purchases

### Earning at the Enhanced Rate
- Pay with your card for eligible travel and software transactions to earn 4.0% back

### Steps to Ensure You Earn Properly
1. Use your card directly with the merchant; third-party wallets and processors may alter merchant classification
2. Check that the merchant is categorized in a travel or software/SaaS merchant category; rewards are based on the merchant’s submitted category
3. Allow transactions to post; rewards are calculated after posting, not at authorization
4. Keep receipts and invoices; if a purchase is misclassified, you may be asked to provide documentation during a rewards review

### Transactions That Typically Do Not Qualify
- Gift cards, person-to-person payments, fees, interest, and insurance premiums charged by the bank
- Returned or refunded purchases (rewards are reversed when credits post)

### Visibility of Rewards
- You will see pending earnings soon after posting; final amounts may adjust if the merchant updates the transaction or issues a credit

### doc_credit_cards_ecocard_002: EcoCard: How to Earn Sustainability Points on Green Purchases

### Earning Rates
- Green purchases: Earn $5.00 sustainability points per dollar spent at qualifying green merchants and categories.
- Other purchases: Earn $1.00 sustainability points per dollar.

### How to Maximize Green Earnings
- Use your card at certified green partners and eco-friendly categories (e.g., public transit, EV charging, renewable energy subscriptions) to receive the higher earn rate.
- When shopping online, check that the merchant is listed as a qualifying green merchant before checkout.

### Examples
- A $100 purchase at a qualifying green merchant earns 100 × $5.00 points.
- A $100 purchase at a non-green merchant earns 100 × $1.00 points.

### Tips to Ensure You Earn Correctly
- Keep transactions separate: If a cart mixes green and non-green items at a non-partner merchant, the entire purchase may earn at the non-green rate.
- Save receipts for any purchases you believe should qualify as green; this helps in resolving any earn-rate disputes.
- If a transaction is returned or refunded, the corresponding points will be reversed at the original earn rate.

### doc_credit_cards_crypto-cash_back_001: Crypto-Cash Back: Getting Started with Crypto Rewards

### Before You Begin
- Confirm that crypto redemptions are available on your account: Yes.
- Note that purchase protection on this card is No.

### How to Start Earning Rewards You Can Redeem in Crypto
1. Make eligible purchases with your card. You earn rewards at 2.0% on those transactions.
2. Track your reward balance in the app. You can prepare for crypto redemption once your balance reaches at least 30 dollars.
3. If you prefer to segregate spending for specific projects or merchants, use virtual cards (when available) to organize and monitor reward accrual. Virtual card management availability: Yes.

### Tips for a Smooth Start
- Set a personal target for your first crypto redemption that meets or exceeds 30.
- Plan larger purchases strategically to accelerate reaching the threshold while staying within your budget.
- Review merchant processing categories in your statements to confirm which transactions earned rewards at the 2.0% rate.

### When You’re Ready to Redeem
- Verify your reward balance has met the 30 requirement.
- Proceed to the crypto redemption flow in the app to choose your cryptocurrency and destination wallet.

### Common Questions at Setup
- How much do I earn per purchase? You earn 2.0%.
- What is the minimum balance to redeem to crypto? 30 dollars.
- Can I organize spending with virtual cards? Yes.

### doc_credit_cards_crypto-cash_back_002: Crypto-Cash Back: How to Redeem Rewards in Your Crypto Wallet

### Prerequisites
- Crypto redemption availability on your account: Yes.
- Minimum reward balance to redeem: 30 dollars.

### Step-by-Step Redemption
1. Open Rewards in your app and choose Redeem to Crypto.
2. Confirm your current reward balance meets the 30 threshold.
3. Select a cryptocurrency from the available list (up to 12 options).
4. Choose your transfer method:
   - If direct wallet integration is available: Yes
   - Otherwise, use manual wallet address entry.
5. Review the estimated conversion. A conversion fee of 1.25% applies to the rewards you convert.
6. Confirm your wallet address and submit the redemption request.

### Timing and Fees
- Conversion fee: 1.25% (applied at the time of conversion).
- The number of available cryptocurrencies can be up to 12.

### Troubleshooting
- Can’t proceed? Ensure your redemption is enabled: Yes.
- Threshold not met? Accumulate more rewards until you reach 30.
- Integration unavailable? If Yes is False, enter your wallet address manually and confirm accuracy before submitting.

Shared context paths (construction metadata, not policy facts):
- `tau2/hyper/sops/banking_sop.md`
