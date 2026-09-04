# Case H

Channel: chat  
QA status: approved

**Customer:** I see a debit-card charge I didn’t make. I want the card cancelled.

**Agent:** For suspected fraud, I need to verify you with your email address and date of birth before checking or closing the card.

**Customer:** harper.nguyen@yahoo.com, September 9 1987.

**Support console:** Customer identity verified. Freeze, unfreeze, close, and replacement are separate debit-card actions.

**Agent:** Use fraud_suspected as the closure reason for suspected fraud or unauthorized transactions; please confirm that reason.

**Customer:** Yes, fraud suspected.

**Support console:** get_debit_cards_by_account_id_7823(account_id=CHK-3198) used before closure to confirm card_id and current status. Card record: card_id=DC-1119, user_id=USR-703, owner matches verified customer, status=ACTIVE. Reason=fraud_suspected. Minimum card-age requirement bypassed for security.

**Agent:** Permanent closure is available for the debit card ending in 0426 due to suspected fraud. Any pending transactions will still be processed, and refunds sent to the closed debit card will be credited to the linked checking account. Please reply yes to close it.

**Customer:** Yes.

**Support console:** close_debit_card_4721 submitted with card_id=DC-1119, reason=fraud_suspected. Result: success.

**Agent:** Closure is complete; the debit card cannot be reactivated. Recurring payments linked to that card need to be updated with new payment information.

**Agent:** Please review your recent transactions and file disputes for any unauthorized charges.

**Customer:** I’ll do that. Should I change anything online?

**Agent:** Changing your online banking password is recommended when fraud is suspected.

**Agent:** Should I start a replacement order now?

**Customer:** Yes, but I’ll do that after filing the dispute.

**Agent:** A new card remains available through the regular debit-card ordering steps.
