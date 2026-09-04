# Case D

Channel: chat  
QA status: approved

**Customer:** My renewed debit card came in the mail. The old one was expiring, and I need this one activated.

**Agent:** Activation depends on card type, so I’ll verify you first with your email address and date of birth.

**Customer:** elliot.green@yahoo.com, May 3 1978.

**Support console:** Customer identity verified.

**Agent:** Do you have the new card in your possession?

**Customer:** Yes.

**Support console:** get_debit_cards_by_account_id_7823(account_id=CHK-4871) used before activation to determine issue_reason. Card record: card_id=DC-5528, status=PENDING, issue_reason=expired, expiration_date=01/30, linked checking account status=OPEN. Card is not expired. Correct activation tool is activate_debit_card_8293 for a REISSUED card with issue_reason expired, damaged, upgrade, or bank_reissue. Using the wrong activation tool would result in an error.

**Agent:** Share the printed last 4 digits, expiration date in MM/YY format, and 3-digit CVV.

**Customer:** 2448, 01/30, and 790.

**Support console:** Card details match card_id=DC-5528 on the account.

**Agent:** Pick a valid 4-digit PIN; avoid sequential values like 1234 and repeating values like 1111.

**Customer:** 7240.

**Support console:** PIN format accepted.

**Agent:** The reissued card ending in 2448 can now be activated. Please reply yes to confirm activation.

**Customer:** Yes.

**Support console:** activate_debit_card_8293 submitted for card_id=DC-5528. Result: success. Reissued card activation creates a 24-hour grace period for the old card before deactivation; other previous cards linked to the same account are automatically deactivated according to the reissue grace-period rule.

**Agent:** Reissued card ending in 2448 is active now. The old card will remain active for 24 hours as a grace period.

**Customer:** Do I need to change anything for subscriptions?

**Agent:** If the card number changed, update recurring payments with the new card details.
