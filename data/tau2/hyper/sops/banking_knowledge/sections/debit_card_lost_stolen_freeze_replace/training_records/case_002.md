# Case B

Channel: chat  
QA status: approved

**Customer:** My first debit card arrived and I want customer service to activate it.

**Agent:** Send your email address and date of birth so I can verify you before reviewing the card record.

**Customer:** noah.chen@gmail.com, October 8 1996.

**Support console:** Customer identity verified.

**Agent:** Tell me whether the physical debit card is with you now.

**Customer:** Yes, I have it here.

**Support console:** get_debit_cards_by_account_id_7823(account_id=CHK-3310) used before activation to determine issue_reason. Card record: card_id=DC-9201, status=PENDING, issue_reason=first_card, expiration_date=09/29, linked checking account status=OPEN. Card is not expired. Because issue_reason is first_card, the correct activation tool is activate_debit_card_8291 for a NEW card. Using the wrong activation tool would result in an error, so issue_reason was verified before tool selection.

**Agent:** Read back the last 4 digits printed on the card, the expiration date in MM/YY format, and the 3-digit CVV from the back.

**Customer:** Last four is 4822, expiration is 09/29, CVV is 613.

**Support console:** Provided card details match card_id=DC-9201 on the customer’s account. Card remains PENDING and linked checking account remains OPEN.

**Agent:** Choose a PIN with exactly 4 digits; it cannot be sequential like 1234 or repeating like 1111.

**Customer:** 5802.

**Support console:** PIN format accepted.

**Agent:** The new debit card ending in 4822 is ready for activation. Please reply yes to confirm activation.

**Customer:** Yes, activate it.

**Support console:** activate_debit_card_8291 submitted for card_id=DC-9201. Result: success. Previous debit cards linked to the same account are automatically deactivated when a new card is activated, except reissued cards have a 24-hour grace period; no prior active card existed for this first-card activation.

**Agent:** Card ending in 4822 can be used now.
