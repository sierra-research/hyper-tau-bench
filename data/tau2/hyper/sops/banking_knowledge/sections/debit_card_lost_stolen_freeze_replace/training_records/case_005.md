# Case E

Channel: chat  
QA status: approved

**Customer:** I’m trying to activate a debit card that just arrived, but the app keeps rejecting it.

**Agent:** Please provide your email address and date of birth; after verification I can check the activation requirements.

**Customer:** lucas.martin@yahoo.com, July 19 1992.

**Support console:** Customer identity verified.

**Agent:** Is the physical card with you now?

**Customer:** Yes, it’s right here.

**Support console:** get_debit_cards_by_account_id_7823(account_id=CHK-7180) used before activation to determine issue_reason. Card record: card_id=DC-6632, status=PENDING, issue_reason=new_account, expiration_date=08/29, linked checking account status=OPEN. Card is not expired. Correct activation tool would be activate_debit_card_8291 for a NEW card. Issue_reason was verified before tool selection because using the wrong activation tool would result in an error.

**Agent:** Use the card as printed and provide its last 4 digits, expiration date in MM/YY format, and 3-digit CVV.

**Customer:** 4412, 08/29, CVV 201.

**Support console:** Activation detail check failed. Provided details do not match card_id=DC-6632. Incorrect detail attempt count: 1 of 2.

**Agent:** The card details did not match. Please re-enter the last 4 digits, expiration date in MM/YY format, and 3-digit CVV exactly as printed.

**Customer:** Sorry, 4412, 08/29, CVV 210.

**Support console:** Activation detail check failed again. Incorrect detail attempt count: 2 of 2. Card locked for security; branch visit required. Activation not performed.

**Agent:** The card is now locked for security after two incorrect detail attempts. The next step is to visit a branch in person for assistance with this card.
