# Case F
Channel: chat  
QA status: approved

**Customer:** My wallet was stolen, and I think there may be a fraudulent debit card charge. Please stop the card.

**Agent:** That’s concerning; I’ll secure the debit card first after verification. Please provide your email address and date of birth.

**Customer:** devon.nguyen@yahoo.com, January 19 1992.

**Support console:** Identity verified with two matching factors.

**Support console:** Lost/stolen card cross-product security protocol applies because customer reported a stolen wallet/debit card. Protocol begins by completing the standard debit card freeze/close procedure, then checking whether the customer has Rho-Bank credit cards on file. Debit card close/cancel/deactivate procedure applies. Valid closure reason enum values and meanings: lost = lost card; stolen = stolen card; fraud_suspected = suspected fraud or unauthorized transactions; damaged = damaged card when customer wants a replacement; no_longer_needed = customer no longer needs the card; account_closing = closing the linked checking account.

**Support console:** get_debit_cards_by_account_id_7823(CK-6004) run. Tool retrieves debit cards associated with a specific checking account and only for checking accounts because savings accounts do not have debit cards. Lookup may return multiple cards for account history or an empty list if no cards exist. Privacy: lookup never returns full card numbers, only last 4 digits. Lookup use cases include checking active or pending cards before ordering, checking issue_reason before activation to determine activation tool, verifying existence/status before freezing or unfreezing, confirming card_id/status before closing, and looking up card details for customer inquiries.

**Support console:** Debit card schema: card_id, account_id, user_id, card_number_last_4, status, issue_reason, expiration_date in MM/YY format, date_issued, card_design, daily_purchase_limit, daily_atm_limit. Status values: ACTIVE, PENDING, FROZEN, CLOSED. issue_reason values: new_account, first_card, lost, stolen, fraud, expired, damaged, upgrade, bank_reissue. Result: DC-9121, account_id CK-6004, user_id U-444, last4 1212, status ACTIVE, issue_reason first_card, expiration_date 08/28, date_issued 06/25/2025, card_design CLASSIC, daily_purchase_limit $4,000, daily_atm_limit $700. Customer user_id U-444 matches card owner.

**Support console:** Closure eligibility: customer verified; owner user_id matches; card status ACTIVE is eligible. No pending or processing debit card transactions. If pending or processing transactions existed, customer would need to wait for all transactions to settle before closure. No pending refunds. If pending refunds existed, customer would need to wait 3-5 business days or acknowledge in writing that refunds will be credited to the linked checking account instead. Lost, stolen, and fraud_suspected each independently bypass the 14-day minimum card age requirement for security purposes. Cards reported lost or stolen are closed immediately with no cooling-off period. For lost, stolen, or fraud_suspected closure, inform customer any pending transactions will still be processed and ask whether they want to order a replacement card immediately. For fraud_suspected, advise review of recent transactions, disputes for unauthorized charges, and online banking password change. If linked checking account is being closed, all associated debit cards must be closed first.

**Agent:** I found the active debit card ending 1212. Because the wallet was stolen and suspected fraud is involved, the 14-day card-age rule is bypassed; lost, stolen, or suspected fraud would each be enough on its own for that security bypass. Any pending transactions will still be processed. Reply yes to close card ending 1212 now for suspected fraud.

**Customer:** yes

**Support console:** close_debit_card_4721 submitted with card_id DC-9121 and reason fraud_suspected. Tool result: success; card status CLOSED. Required post-close confirmation: confirm card closed.

**Agent:** The debit card ending 1212 is now closed. It is permanently deactivated and cannot be reactivated or reopened, and recurring payments linked to that card need new payment information. Do you want to order a replacement debit card now?

**Customer:** Not right now.

**Agent:** Since you mentioned a possible unauthorized charge, please review recent debit card transactions for anything you do not recognize.

**Customer:** I see one charge I don’t recognize.

**Agent:** For that unauthorized charge, file a dispute.

**Customer:** Okay.

**Agent:** As a fraud precaution, change your online banking password.

**Customer:** I will.

**Support console:** get_credit_card_accounts_by_user run after standard debit-card close procedure. Tool returns all active and closed credit card accounts. Result: active credit card account CC-2001 and closed credit card account CC-1440. Cross-product protocol requires proactive credit card replacement offer when Rho-Bank credit cards are on file after a lost or stolen debit card report.

**Agent:** Rho-Bank noticed you also have a Rho-Bank credit card on file. Was that credit card also in the stolen wallet?

**Customer:** Yes, it was, but I’m not sure I want to replace it.

**Agent:** Wallet theft often involves multiple cards, and replacing the Rho-Bank credit card with a new card number helps protect against potential fraud. Reply yes if you want a replacement credit card ordered as a security precaution.

**Customer:** No, not now.

**Support console:** Account note added: credit card replacement offer was made after stolen-wallet debit card report; customer declined.

**Agent:** The account note now shows that the replacement credit card offer was made and declined. If the checking account is closed later, all associated debit cards must be closed first.
