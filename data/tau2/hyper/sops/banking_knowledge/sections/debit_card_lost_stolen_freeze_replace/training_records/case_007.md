# Case G

Channel: chat  
QA status: approved

**Customer:** I lost my debit card at the train station. I was thinking of freezing it, but I’m pretty sure it’s gone.

**Agent:** Because lost cards should be closed rather than only frozen, I need to verify you first with your email address and date of birth.

**Customer:** omar.bennett@gmail.com, June 16 1990.

**Support console:** Customer identity verified. Freeze, unfreeze, close, and replacement are separate debit-card actions.

**Agent:** Which closure reason applies: lost, stolen, fraud_suspected for suspected fraud or unauthorized transactions, damaged when replacement is wanted, no_longer_needed, or account_closing?

**Customer:** Lost.

**Support console:** get_debit_cards_by_account_id_7823(account_id=CHK-8801) used before closure to confirm card_id and current status. Card record: card_id=DC-4907, user_id=USR-290, owner matches verified customer, status=ACTIVE. Reason=lost. Minimum card-age requirement bypassed for security. Lost cards are closed immediately with no cooling-off period.

**Agent:** The lost debit card ending in 5529 is eligible for permanent closure. Any pending transactions will still be processed, and refunds sent to the closed debit card will be credited to the linked checking account. Please reply yes to close it.

**Customer:** Yes, close it.

**Support console:** close_debit_card_4721 submitted with card_id=DC-4907, reason=lost. Result: success.

**Agent:** That lost debit card is permanently deactivated and cannot be reactivated. Recurring payments linked to that card need to be updated with new payment information.

**Agent:** Do you want to start a replacement order now?

**Customer:** Not right now.

**Agent:** Later, a replacement request can be started through the normal debit-card order flow.

**Support console:** Lost debit-card cross-product protocol completed after debit-card closure. Customer’s wallet loss may have compromised other cards, so credit-card accounts were checked; no Rho-Bank credit card account requiring a proactive replacement offer was found.
