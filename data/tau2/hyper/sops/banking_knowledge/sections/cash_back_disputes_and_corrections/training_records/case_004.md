# Case D
Channel: chat
QA status: approved

**Agent:** Which EcoCard transaction should we review first?

**Customer:** I have a few. EV charging earned a lot, a regular store earned less, a mixed online order earned the low rate, and a refunded transit pass reversed points. One public transit charge looks wrong and I want to dispute it.

**Agent:** Account-specific EcoCard details require verification. Please provide your email address and date of birth.

**Customer:** devon.rivera@yahoo.com, June 9, 1991.

**Support console:** Identity verified with two matching factors.

**Support console:** Account lookup: user_id U-66318. Card: EcoCard. Legacy backend migration note: transaction database stores all credit card rewards as "points" regardless of card type. The EcoCard is the only true points-based card. EcoCard sustainability points redeem at $0.01 per point when redeemed as a statement credit or checking account credit.

**Support console:** EcoCard earning rules: green purchases at qualifying green merchants and categories earn 5.00 sustainability points per dollar spent; source labels this as "$5.00 sustainability points per dollar." Other purchases earn 1.00 sustainability point per dollar; source labels this as "$1.00 sustainability points per dollar." General rewards reference also states EcoCard earns 5 points per dollar on green purchases and 1 point per dollar on other purchases.

**Support console:** EcoCard guidance: higher green earn rate applies at certified green partners and eco-friendly categories such as public transit, EV charging, and renewable energy subscriptions. For online purchases, customer should check that the merchant is listed as a qualifying green merchant before checkout. If a cart mixes green and non-green items at a non-partner merchant, the entire purchase may earn at the non-green rate. Customers should save receipts for purchases they believe should qualify as green. Returned or refunded EcoCard transactions reverse corresponding points at the original earn rate.

**Support console:** Transaction comparison: TXN-ECO-1001, $100.00, certified EV charging partner, rewards 500 points, correct by example 100 × 5.00 points. TXN-ECO-1002, $100.00, non-green merchant, rewards 100 points, correct by example 100 × 1.00 points. TXN-ECO-1003, $99.99, mixed cart at non-partner online merchant, rewards 99 points after floor, non-green rate applied. TXN-ECO-1004, public transit pass refunded, original 250 points reversed at original earn rate when credit posted. TXN-ECO-2044, $46.20 public transit, posted rewards 46 points; customer claims qualifying green rate should apply.

**Support console:** Rounding evidence: all credit card rewards points are rounded down to nearest whole number; fractional points are truncated or floored rather than rounded to nearest integer. Example retained: a $99.99 purchase at 2.5% cash back calculates to 249.975 points but awards 249 points. Rounding-down applies consistently across all credit card types and reward categories.

**Agent:** The EcoCard transaction comparison shows the $100 EV charging purchase earned 500 sustainability points, the $100 non-green merchant purchase earned 100 points, the mixed cart at a non-partner merchant earned at the non-green rate, and the refunded transit pass had its points reversed at the original earn rate.

**Customer:** The public transit one is the one that seems wrong. It only got 46 points.

**Agent:** Public transit can be a green category for the EcoCard when it is processed as a qualifying green merchant or category. Please confirm that TXN-ECO-2044 is the transaction you want to dispute.

**Customer:** Yes, TXN-ECO-2044.

**Agent:** Submit TXN-ECO-2044 by running submit_cash_back_dispute_0589 directly with your own user_id U-66318 and transaction_id TXN-ECO-2044.

**Customer:** Is it weird that it says cash-back dispute for EcoCard points?

**Agent:** EcoCard reward disputes use the same credit-card rewards dispute process when the reward amount received differs from what you believe should have been earned, and the submission itself is initiated with submit_cash_back_dispute_0589.

**Customer:** Do you need the full card number for the dispute?

**Agent:** Sensitive card details are not needed for this dispute. The tool uses your user_id and the specific transaction_id, and receipts or green-merchant context may be requested later during review.

**Customer:** For online green purchases, what should I check before buying?

**Agent:** For an online green purchase, check that the merchant is listed as a qualifying green merchant before checkout.

**Customer:** And if I buy green and non-green items together?

**Agent:** Separating mixed purchases is best when possible, because a mixed cart at a non-partner merchant may cause the entire EcoCard purchase to earn at the non-green rate.

**Customer:** Should I save receipts for EcoCard purchases?

**Agent:** Saved receipts can help resolve earn-rate disputes for purchases you believe should qualify as green.
