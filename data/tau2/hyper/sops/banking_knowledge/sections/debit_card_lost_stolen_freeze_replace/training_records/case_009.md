# Case I

Channel: chat  
QA status: approved

**Customer:** I’m closing my checking account and want the debit card cancelled today.

**Agent:** To evaluate closure eligibility, please provide your email address and date of birth for verification.

**Customer:** sienna.lopez@yahoo.com, April 27 1995.

**Support console:** Customer identity verified. Freeze, unfreeze, close, and replacement are separate debit-card actions.

**Agent:** Choose the closure reason for this debit card: lost, stolen, fraud_suspected, damaged, no_longer_needed, or account_closing.

**Customer:** Account closing.

**Support console:** get_debit_cards_by_account_id_7823(account_id=CHK-7704) used before closure to confirm card_id and current status. Card record: card_id=DC-8862, user_id=USR-912, owner matches verified customer, status=ACTIVE, date_issued=2025-06-21. Today=2025-06-28. Closure reason=account_closing. Non-security closure reasons require card active at least 14 days; earliest eligible closure date=2025-07-05. Pending card transaction present. Pending refund present. If linked checking account is being closed, all associated debit cards must be closed first.

**Agent:** This card cannot be closed today. A pending transaction must settle first, the pending refund must process, typically in 3-5 business days, or you must acknowledge in writing that the refund will credit to the linked checking account instead, and the earliest eligible closure date is July 5, 2025.

**Customer:** So the checking account can’t close until the card is closed?

**Agent:** Correct. When a linked checking account is being closed, all associated debit cards must be closed first.

**Customer:** What about my subscriptions?

**Agent:** Once the card closure is completed, recurring payments linked to the card need to be updated with new payment information.

**Customer:** If a refund arrives after closure, where does it go?

**Agent:** Refunds sent to a closed debit card are credited to the linked checking account.
