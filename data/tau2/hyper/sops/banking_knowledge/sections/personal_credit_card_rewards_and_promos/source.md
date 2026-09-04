## Personal credit-card rewards, promos, and reward-type representation

Bundle id: `personal_credit_card_rewards_and_promos`

Construction context (guidance for transcript induction, not section
content -- do not extract as policy facts): the shared banking handbook
governs identity verification, explicit customer confirmation before
account-modifying actions, discoverable-tool wrapper behavior, schema
limits, and exact transfer wording. Express these behaviorally in
transcripts where a case exercises them; do not restate them as section
facts. The bundle id, transcript focus, losslessness risks, and shared
context paths in this file are construction metadata, not policy facts.

Transcript focus:
Explaining reward rates, promo eligibility, points-vs-cash-back representation, rounding, and product-specific reward mechanics.

Losslessness risks:
- Preserve reward rates, promo conditions, and rounding policy exactly.
- Keep cash back, sustainability points, and crypto rewards distinct.
- Do not make promo eligibility broader than the source docs.

Source documents:

### doc_credit_cards_credit_cards_(general)_006: Internal: Credit Card Rewards - Points vs Cash Back Representation

### Rewards representation
Due to a legacy backend migration that has not yet been completed, all credit card rewards in the transaction database are stored as 'points' regardless of whether the card is a cash back card or a points-based card. For cash back cards (Bronze Rewards Card, Silver Rewards Card, Gold Rewards Card, Platinum Rewards Card, Diamond Elite Card, Crypto-Cash Back, Business Bronze Rewards Card, Business Silver Rewards Card, Green Rewards Card, Silver Zoom Card, Business Gold Rewards Card, and Business Platinum Rewards Card), these 'points' should be interpreted as cash back with a conversion rate of 1 point = $0.01 when redeemed as a statement credit or as a credit to the user's Rho-Bank checking account. For example, 250 points equals $2.50 in cash back, which matches a 2.5% cash back rate on a $100 purchase. The only true points-based card is the EcoCard, which earns 'sustainability points' (5 points per dollar on green purchases, 1 point per dollar on other purchases) that also redeem at $0.01 per point when redeemed as a statement credit or checking account credit.

### doc_credit_cards_credit_cards_(general)_007: Credit Card Rewards Points Rounding Policy

### Rounding policy
All credit card rewards points are rounded down to the nearest whole number. When calculating points earned on a purchase, the system always truncates (floors) fractional points rather than rounding to the nearest integer. For example, a $126.77 purchase on a 1% cash back card earns 126 points (not 127), because 126.77 × 0.01 = 1.2677 points, which rounds down to 1 point per dollar, giving 126 points. Similarly, a $99.99 purchase at 2.5% cash back would calculate to 249.975 points but would award 249 points. This rounding policy applies consistently across all credit card types and reward categories.

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

### doc_credit_cards_platinum_rewards_card_002: Platinum Rewards Card: Earning 10% Cash Back

### How You Earn
- You earn 10.0% cash back on all eligible purchases.
- Returns or credits reduce previously earned rewards on a per-transaction basis.

### Eligible and Ineligible Transactions
- Eligible: point-of-sale and online purchases posted to your account.
- Not eligible: cash advances, balance transfers, fees, interest, and other cash-equivalent transactions.

### Posting Timeline
- Rewards accrue when transactions post to your account and typically become available after the purchase posts and clears any return window.

### Redeeming Your Rewards
- You can redeem once your available rewards balance reaches at least $15.
- Common redemption options include statement credits or other available channels in your account dashboard.

### Tips to Maximize Earnings
- Use the card for everyday spend to capture 10.0% on all categories.
- Set the card as your default payment at frequently used merchants.
- Consider your net rewards after the $200.00 annual fee when planning large purchases.

### doc_credit_cards_platinum_rewards_card_007: Platinum Rewards Card: Maximizing Your Premium Benefits and Rewards

### Everyday Earning
- Use the card for daily purchases to earn 10.0% on all categories without rotating caps.

### International Spending
- Take advantage of 0% foreign transaction fees when traveling or purchasing from foreign merchants.

### Annual Fee Rebate Strategy
- Earn a $150.00 rebate on your annual fee by meeting a monthly spend threshold of $7500.00.
- Automate large, predictable expenses on the card to help consistently meet the threshold.

### Smart Redemption
- Redeem rewards once your balance reaches at least $15 to keep value working for you.

### Purchase Protection Use
- For eligible items, keep receipts and documentation to leverage purchase protection for up to 135 days after purchase.
- The maximum coverage per claim is $17,500, subject to policy terms and exclusions.

### Putting It Together
- Channel recurring bills, travel, and major purchases through the card to earn at the flat rate, avoid foreign fees, and meet the monthly threshold for the annual fee rebate.

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

### doc_credit_cards_ecocard_009: EcoCard: New Customer Promo - Earn Bonus Sustainability Points

### Offer Window
- This promotion runs from 2025-08-01 through 2025-12-15.

### How to Qualify
- Spend at least $5,000 in eligible purchases within your first 1 month of account opening.
- You must be a new customer and the account must be open and in good standing when the bonus is awarded.

### Bonus Amount
- Earn $2,000 sustainability points once you meet the spending threshold within the qualifying period.

### Posting Timeline
- Bonus points typically post after the qualifying period closes and your transactions have cleared.

### Exclusions and Tips
- Returns, chargebacks, and disputed transactions reduce your qualifying spend.
- Balance transfers, cash equivalents, and fees do not count toward the threshold.
- Track your progress in the Rewards section to ensure you meet the $5,000 requirement on time.

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
