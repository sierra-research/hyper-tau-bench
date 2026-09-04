# Case A

Channel: chat  
QA status: approved

**Customer:** I opened a checking account last week and want a debit card. I also have a savings account, so I’m not sure which one the card can attach to.

**Agent:** To see which checking accounts are eligible, I need your email address and date of birth for verification.

**Customer:** maya.rivera@yahoo.com, March 12 1989.

**Support console:** Customer identity verified. Freeze, unfreeze, close or cancel, and replacement or new order are separate debit-card actions.

**Agent:** Debit cards can be ordered only for checking accounts, including personal or business checking; savings accounts are not eligible. Which checking account should the new card link to?

**Customer:** Use my personal checking, please.

**Support console:** Account selected: CHK-1044. account_type=checking, status=OPEN, opened 8 business days ago excluding weekends, balance=$82.45, customer age verified from date_of_birth as 35, address on file is a valid US domestic address. Standard debit-card ordering excludes emergency replacement while traveling; international shipping is not available for this standard order.

**Support console:** get_debit_cards_by_account_id_7823(account_id=CHK-1044) returned empty list. No ACTIVE card and no PENDING debit-card order for this checking account.

**Agent:** This checking account is eligible for a new debit card. For standard delivery, STANDARD is free and arrives in 7-10 business days; EXPEDITED arrives in 3-5 business days for a $15 fee; RUSH arrives in 1-2 business days for a $35 fee. Which delivery option would you like?

**Customer:** Rush, please.

**Agent:** Design choices are CLASSIC, the default Rho-Bank blue design with no fee; PREMIUM, metallic silver with a $10 one-time fee; and CUSTOM, a customer-uploaded image with a $25 one-time fee, subject to approval and possible tier-based fee variation. Which design would you like?

**Customer:** I’ll do the custom image.

**Agent:** Please confirm the US mailing address where the card should be sent.

**Customer:** 200 Cedar Lane, Apt 4B, Denver, CO 80203.

**Support console:** Eligibility check complete. Before order: account_type checking, account OPEN, opened at least 3 business days, no more than 1 active debit card, no PENDING debit-card order, minimum balance exceeds $25, customer at least 18, valid US domestic mailing address. Fee check: RUSH delivery $35 plus CUSTOM design $25, total $60; balance sufficient. If funds were insufficient for delivery or design fees, order_debit_card_5739 would fail.

**Agent:** The RUSH delivery fee is $35 and the CUSTOM design fee is $25, and both fees will be deducted automatically from the linked checking account. Please reply yes to place this debit-card order.

**Customer:** Yes, place the order.

**Support console:** order_debit_card_5739 submitted for account_id=CHK-1044, delivery=RUSH, delivery_fee=35, design=CUSTOM, design_fee=25, mailing_address=200 Cedar Lane, Apt 4B, Denver, CO 80203. Result: approved.

**Agent:** The debit card has been ordered. It is expected to arrive in 1-2 business days, with $60 in total fees deducted from the linked checking account.

**Customer:** Can I see shipment status somewhere? Also, how does activation work?

**Agent:** You can track the shipment in the Rho-Bank mobile app. The new card will automatically activate on first use with PIN entry.

**Customer:** Earlier I saw old card entries on another checking account. What kind of debit-card details can you see?

**Support console:** get_debit_cards_by_account_id_7823(account_id=CHK-2055) returns debit cards only for checking accounts; savings accounts do not have debit cards. The lookup may return multiple records when an account has card history. Returned fields include card_id, account_id, user_id, card_number_last_4, status, issue_reason, expiration_date in MM/YY, date_issued, card_design, daily_purchase_limit, and daily_atm_limit. Possible current statuses: ACTIVE, PENDING, FROZEN, CLOSED. Possible issue_reason values: new_account, first_card, lost, stolen, fraud, expired, damaged, upgrade, bank_reissue. Possible card_design values: CLASSIC, PREMIUM, CUSTOM. Full debit-card numbers are never returned; only last 4 digits are returned.

**Support console:** Lookup result for CHK-2055: card_id=DC-7001, account_id=CHK-2055, user_id=USR-448, card_number_last_4=3381, status=CLOSED, issue_reason=expired, expiration_date=06/24, date_issued=2020-06-10, card_design=CLASSIC, daily_purchase_limit=$2,000, daily_atm_limit=$500. Second record: card_id=DC-8119, account_id=CHK-2055, user_id=USR-448, card_number_last_4=9044, status=ACTIVE, issue_reason=bank_reissue, expiration_date=06/29, date_issued=2024-06-01, card_design=PREMIUM, daily_purchase_limit=$2,000, daily_atm_limit=$500.

**Agent:** For the other checking account, there is card history with an old closed card and a current active card. For this standard order, any existing active debit card remains active until a new card is activated; pending, frozen, closed, or otherwise blocked cards are not made usable by a new order.
