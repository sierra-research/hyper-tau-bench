# Case A
Channel: chat
QA status: approved

**Agent:** Tell me which rewards transaction you want reviewed.

**Customer:** My Silver Rewards Card gave me regular cash back on a software subscription. I thought it should be 4%, so I want to dispute the rewards.

**Agent:** To verify your identity, please provide your email address and date of birth.

**Customer:** maya.chen@outlook.com, March 12, 1987.

**Support console:** Identity verified with two matching factors.

**Support console:** Account lookup: user_id U-48219. Card: Silver Rewards Card. Transaction history: transaction_id TXN-SR-77341, posted, merchant CloudLedger SaaS, submitted merchant category software/SaaS, amount $220.50, rewards earned 220 points. No card number or sensitive card details requested.

**Agent:** TXN-SR-77341 is posted, and the merchant submitted it under a software/SaaS category. The Silver Rewards Card earns 4.0% cash back on eligible travel and software transactions when paid with the card, and rewards are calculated after transactions post rather than at authorization.

**Customer:** So this one looks eligible?

**Agent:** This transaction’s merchant category supports a rewards review. Please confirm that TXN-SR-77341 is the purchase you want to dispute.

**Customer:** Yes, that is the one.

**Agent:** For the dispute submission, run submit_cash_back_dispute_0589 directly with your own user_id U-48219 and transaction_id TXN-SR-77341.

**Customer:** Do you need my card number or a screenshot?

**Agent:** Card details are not needed for this submission. The dispute uses your user_id and the specific transaction_id, and supporting context such as category expectations or promotion expectations may be requested later during review.

**Customer:** Is this dispute tool only for Silver Rewards, or can it be used for other credit cards too?

**Agent:** That process applies to credit card transactions when the concern is a difference between received cash back and expected cash back, and the submission is initiated with submit_cash_back_dispute_0589 rather than a step-by-step workflow.

**Customer:** I used my phone wallet for a different travel booking last month. Could that affect the rate?

**Agent:** With future Silver Rewards Card travel or software purchases, use the card directly with the merchant because third-party wallets and processors may alter the merchant classification.

**Customer:** What exactly does the bank look at for the 4% rate?

**Agent:** Rewards for the Silver Rewards Card are based on the merchant’s submitted category, so the merchant should be categorized in a travel or software/SaaS merchant category.

**Customer:** Should I keep anything from the merchant?

**Agent:** Receipts and invoices are worth keeping for purchases you believe should qualify, because documentation may be requested during a rewards review if a purchase is misclassified.

**Customer:** Are there purchases that look travel or software but usually do not get 4%?

**Agent:** Certain transaction types typically do not qualify for the Silver Rewards Card 4.0% travel and software rate, including gift cards, person-to-person payments, fees, interest, and insurance premiums charged by the bank.

**Customer:** What if I return part of a software purchase later?

**Agent:** A returned or refunded purchase typically does not qualify, and rewards are reversed when credits post.

**Customer:** I saw pending rewards before. Are those final?

**Agent:** Pending earnings can appear soon after posting, and final reward amounts may adjust if the merchant updates the transaction or issues a credit.
