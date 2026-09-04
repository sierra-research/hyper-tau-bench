# Case E
Channel: chat  
QA status: approved

**Customer:** I want to cancel one of my debit cards because I don’t use it anymore. I might close the checking account later too.

**Agent:** Card closure requires verification first. Please provide your email address and date of birth.

**Customer:** tanya.morales@gmail.com, April 6 1989.

**Support console:** Identity verified with two matching factors.

**Support console:** Debit card closing/cancelling procedure applies when a customer wants to close, cancel, or deactivate a debit card. Valid closure reason enum values and meanings: lost = lost card; stolen = stolen card; fraud_suspected = suspected fraud or unauthorized transactions; damaged = damaged card when the customer wants a replacement; no_longer_needed = customer no longer needs the card; account_closing = closing the linked checking account. Gating procedure: verify identity, ask the reason from the allowed list, check eligibility, apply source exceptions or resolution paths where available, and if any applicable requirement remains unmet or unresolved, inform the customer what must be resolved and do not proceed with closure.

**Support console:** get_debit_cards_by_account_id_7823(CK-5500) run. Tool retrieves debit cards for checking accounts only because savings accounts do not have debit cards. Lookup may return multiple cards when there is card history and returns an empty list if no cards exist. Privacy: full card numbers are never returned, only last 4 digits. Lookup should be used before ordering a new debit card to check active or pending cards, before activation to check issue_reason and determine the activation tool, before freezing or unfreezing to verify existence and status, before closing to confirm card_id and status, and for customer debit card inquiries.

**Support console:** Returned debit card records include card_id, account_id, user_id, card_number_last_4, status, issue_reason, expiration_date in MM/YY format, date_issued, card_design, daily_purchase_limit, and daily_atm_limit. Status values are ACTIVE, PENDING, FROZEN, CLOSED. issue_reason values are new_account, first_card, lost, stolen, fraud, expired, damaged, upgrade, bank_reissue. Results: DC-7788, CK-5500, user_id U-778, last4 5588, status ACTIVE, issue_reason first_card, expiration_date 09/28, date_issued 05/21/2025, card_design CLASSIC, daily_purchase_limit $3,000, daily_atm_limit $500. DC-7799, CK-5500, user_id U-778, last4 7744, status ACTIVE, issue_reason damaged, expiration_date 10/28, date_issued 06/15/2025, card_design PREMIUM, daily_purchase_limit $3,000, daily_atm_limit $500. DC-7800, CK-5500, user_id U-778, last4 3399, status ACTIVE, issue_reason bank_reissue, expiration_date 11/28, date_issued 04/02/2025, card_design CLASSIC, daily_purchase_limit $3,000, daily_atm_limit $500.

**Support console:** Ownership and eligibility: customer user_id U-778 matches card owner user_id for requested card DC-7788. To close a debit card, customer must be verified, must be the owner verified by user_id, and card must currently be ACTIVE or PENDING. DC-7788 has no pending or processing card transactions. DC-7788 has pending refund RF-221 for $18.40. Pending refund rule: card must have no pending refunds unless customer acknowledges in writing that refunds will be credited to the linked checking account instead. If pending debit card refunds exist, customer must wait for refunds to process, typically 3-5 business days, or acknowledge in writing that refunds will be credited to the linked checking account instead. Refunds to a closed debit card will be credited to the linked checking account.

**Support console:** Additional blockers found for other cards: DC-7800 has a pending card transaction, so it cannot be closed until all pending or processing transactions settle. DC-7799 is newer than 14 days for a non-security closure reason; for reasons other than lost, stolen, or fraud_suspected, the card must have been active at least 14 days calculated from date_issued. Earliest eligible closure date for DC-7799 is 06/29/2025. If the linked checking account is being closed, all associated debit cards must be closed first.

**Agent:** Card ending 5588 can be closed for no longer needed, but it has a pending refund. Please type this acknowledgment if you want to proceed without waiting 3-5 business days: I acknowledge that pending refunds will be credited to my linked checking account instead.

**Customer:** I acknowledge that pending refunds will be credited to my linked checking account instead.

**Agent:** Also, card ending 3399 has a pending card transaction, so that card must wait for settlement; card ending 7744 is too new for a non-security closure and is eligible on 06/29/2025. To close card ending 5588 now, reply yes.

**Customer:** yes

**Support console:** close_debit_card_4721 submitted with card_id DC-7788 and reason no_longer_needed. Tool result: success; card status CLOSED. Closure confirmation required after tool success.

**Agent:** Card 5588 is now closed. It is permanently deactivated and cannot be reactivated or reopened, recurring payments linked to that card need new payment information, and any refund to the closed card will be credited to the linked checking account. If you need a new card, it can be ordered through the standard ordering process.
