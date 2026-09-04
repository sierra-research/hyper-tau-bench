# Case B
Channel: chat
QA status: approved

**Agent:** Share what changed on the approved rewards dispute.

**Customer:** My Business Silver Rewards Card dispute was approved, but the transaction still shows the old rewards amount.

**Agent:** Account review starts with identity verification. Please provide your email address and date of birth.

**Customer:** jordan.patel@icloud.com, August 5, 1982.

**Support console:** Identity verified with two matching factors.

**Support console:** cash_back_disputes database lookup for user_id U-77502: dispute CBD-9104 status resolved and approved. Affected transaction_id TXN-BSR-4412 requires rewards adjustment. Dispute record includes expected_rewards "3000 points"; do not rely on that field for correction.

**Support console:** Transaction TXN-BSR-4412: Business Silver Rewards Card, posted 2025-03-20, amount $126.77, merchant Coastline Suites, billed by lodging provider, merchant category travel, current rewards 126 points. Account opened 2025-01-15.

**Support console:** Business Silver Rewards Card rules verified independently: earns 10.0% cash back on eligible travel and software purchases; earns 1.0% on purchases other than eligible travel and software. To qualify for 10.0%, the merchant must process under a travel or software-related merchant category. Online purchases should be billed by the service provider itself or an authorized platform categorized as travel or software. If a merchant sells multiple categories, the charge must be coded under a qualifying category for 10.0%.

**Support console:** Business Silver Rewards Card best practices: use the card for airfare, lodging, car rentals, transit, and other travel booked directly with providers or recognized travel agencies; use it for recurring SaaS subscriptions and cloud-based software billed by software providers; keep receipts and confirmations in case merchant category coding needs review.

**Support console:** Double-cash-back promotion verified: promo start date 2024-11-14, end date 2025-11-14. Customer opened the account during the promotional period. The six-month window begins on the account opening date, not the promotional start date, so this account’s window is 2025-01-15 through 2025-07-15. No separate enrollment required. Merchant category exclusions continue to apply during the promotion. Cash back is credited to the account at the end of each billing cycle consistent with program rules.

**Support console:** Correction calculation: card type Business Silver Rewards Card; category travel; applicable promotion active at time of purchase. Base eligible travel rate 10.0%; double-cash-back promo multiplies travel/software purchases that normally earn 10.0% by 2, producing 20.0%. Other purchases that normally earn 1.0% would be multiplied by 2 during the qualifying promo window, producing 2.0%.

**Support console:** Legacy backend migration note: credit card transaction database stores all credit card rewards as "points" regardless of cash-back or points-based card. Stored "points" should be interpreted as cash back for Bronze Rewards Card, Silver Rewards Card, Gold Rewards Card, Platinum Rewards Card, Diamond Elite Card, Crypto-Cash Back, Business Bronze Rewards Card, Business Silver Rewards Card, Green Rewards Card, Silver Zoom Card, Business Gold Rewards Card, and Business Platinum Rewards Card. For cash-back cards, 1 point equals $0.01 when redeemed as a statement credit or as a credit to the user's Rho-Bank checking account. Example evidence: 250 points equals $2.50 in cash back and matches a 2.5% cash-back rate on a $100 purchase.

**Support console:** Rounding verification: all credit card rewards points are rounded down to the nearest whole number; fractional points are truncated or floored rather than rounded to the nearest integer. Examples retained: a $126.77 purchase on a 1% cash-back card earns 126 points, not 127; source calculation note says 126.77 × 0.01 = 1.2677 points, rounded down to 1 point per dollar, giving 126 points. A $99.99 purchase at 2.5% calculates to 249.975 points but awards 249 points. Rounding-down applies consistently across all credit card types and reward categories.

**Support console:** New rewards calculation for TXN-BSR-4412: $126.77 × 20.0% = $25.354 cash back = 2535.4 stored points; floor to 2535 points.

**Support console:** unlock_discoverable_agent_tool requested for update_transaction_rewards_3847. Tool unlocked.

**Agent:** Dispute CBD-9104 is resolved and approved, and TXN-BSR-4412 needs the corrected rewards value. I calculated the corrected amount as 2535 points; please reply yes if you want me to update that transaction’s rewards now.

**Customer:** yes

**Support console:** call_discoverable_agent_tool invoked: update_transaction_rewards_3847(transaction_id: "TXN-BSR-4412", new_rewards_earned: "2535 points"). Result: success.

**Support console:** credit_card_transaction_history lookup confirms TXN-BSR-4412 rewards_earned now "2535 points". Internal case record retained calculation notes: card type, transaction category, merchant billing/category eligibility, promo window, rounding method, ignored expected_rewards field, and final value.

**Agent:** Update confirmed: TXN-BSR-4412 now shows 2535 points in the transaction history, which represents $25.35 in cash back on this cash-back card.
