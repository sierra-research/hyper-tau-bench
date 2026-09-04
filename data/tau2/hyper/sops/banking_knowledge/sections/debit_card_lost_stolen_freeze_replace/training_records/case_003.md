# Case C

Channel: chat  
QA status: approved

**Customer:** I got my replacement debit card after my old one was stolen. Can you activate it?

**Agent:** Before I review the replacement-card status, provide your email address and date of birth for verification.

**Customer:** priya.shah@icloud.com, February 21 1984.

**Support console:** Customer identity verified.

**Agent:** Confirm the replacement card is physically with you.

**Customer:** Yes, I’m holding it.

**Support console:** get_debit_cards_by_account_id_7823(account_id=CHK-6022) used before activation to determine issue_reason. Card record: card_id=DC-7740, status=PENDING, issue_reason=stolen, expiration_date=11/29, linked checking account status=OPEN. Card is not expired. Correct activation tool is activate_debit_card_8292 for a REPLACEMENT card with issue_reason lost, stolen, or fraud. Using the wrong activation tool would result in an error.

**Agent:** Enter the last 4 digits on the card, the expiration date in MM/YY format, and the 3-digit CVV.

**Customer:** 6190, 11/29, and 442.

**Support console:** Card details match customer account and card_id=DC-7740.

**Agent:** Select a 4-digit PIN that is not sequential or repeating.

**Customer:** 3907.

**Support console:** PIN format accepted.

**Agent:** Replacement debit card ending in 6190 is ready to activate. Please reply yes to confirm activation.

**Customer:** Yes, go ahead.

**Support console:** activate_debit_card_8292 submitted for card_id=DC-7740. Result: success. Previous debit cards linked to the same account were automatically deactivated when the replacement card was activated.

**Agent:** Replacement card ending in 6190 has been activated. Please review your recent transactions for unauthorized charges.

**Customer:** I was worried because the old card was stolen from my bag.

**Agent:** That worry makes sense after a stolen card. Have you noticed any suspicious activity on the account?

**Customer:** Not so far.

**Agent:** Since fraud was a concern with the stolen card, changing your online banking password is recommended.
