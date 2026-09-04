# Case F

Channel: chat  
QA status: approved

**Customer:** My wallet was stolen with my debit card in it. Should I freeze it?

**Agent:** I’m sorry that happened. Since the card was stolen, closing is the safer action; a freeze is temporary and reversible, while closing is permanent. Please provide your email address and date of birth for verification.

**Customer:** dana.wilson@yahoo.com, December 4 1981.

**Support console:** Customer identity verified. Freeze, unfreeze, close, and replacement are separate debit-card actions.

**Agent:** Tell me the closure reason, choosing one of: lost, stolen, fraud_suspected for suspected fraud or unauthorized transactions, damaged when replacement is wanted, no_longer_needed, or account_closing.

**Customer:** Stolen.

**Support console:** get_debit_cards_by_account_id_7823(account_id=CHK-5412) used before closure to confirm card_id and current status. Card record: card_id=DC-3188, user_id=USR-615, owner matches verified customer, status=ACTIVE. No pending or processing transactions. No pending refunds. Reason=stolen. Minimum card-age requirement bypassed for security. Cards reported lost or stolen are closed immediately with no cooling-off period.

**Agent:** This stolen card ending in 8173 is ready for permanent closure now. Any pending transactions will still be processed, and refunds sent to the closed debit card will be credited to the linked checking account. Please reply yes to permanently close it.

**Customer:** Yes, close it now.

**Support console:** close_debit_card_4721 submitted with card_id=DC-3188, reason=stolen. Result: success.

**Agent:** The stolen debit card is permanently closed and cannot be used again. Recurring payments linked to that card need to be updated with new payment information.

**Customer:** Can I get a replacement later instead of right now?

**Agent:** Yes. A new debit card can be requested through the standard ordering flow.

**Support console:** Lost or stolen debit-card cross-product protocol: after completing standard debit-card close procedure, check whether customer has Rho-Bank credit cards on file because other cards in the wallet may also be compromised. get_credit_card_accounts_by_user(user_id=USR-615) retrieves all active and closed credit card accounts. Result: one ACTIVE credit card account and one CLOSED credit card account.

**Agent:** You also have a Rho-Bank credit card. Was that credit card in the stolen wallet too?

**Customer:** Yes, but I already locked it myself and don’t want a replacement.

**Agent:** Wallet theft often involves multiple cards, and replacing the credit card with a new card number helps protect against potential fraud. Please confirm whether you decline the replacement credit card offer.

**Customer:** I decline it.

**Support console:** Customer declined proactive credit-card replacement offer. Account note added that the offer was made.
