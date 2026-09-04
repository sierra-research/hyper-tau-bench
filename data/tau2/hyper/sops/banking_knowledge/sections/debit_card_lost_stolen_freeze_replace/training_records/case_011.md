# Case K

Channel: chat  
QA status: approved

**Customer:** I found the card I froze yesterday. Please turn it back on.

**Agent:** To check unfreeze eligibility, please provide your email address and date of birth for verification.

**Customer:** ava.patel@gmail.com, November 2 1988.

**Support console:** Customer identity verified. Freeze, unfreeze, close, and replacement are separate debit-card actions.

**Support console:** get_debit_cards_by_account_id_7823(account_id=CHK-5590) used before unfreeze to verify card exists and current status. Card record: card_id=DC-7302, user_id=USR-211, owner matches verified customer, status=FROZEN. Linked checking account status=OPEN. Only a card currently in FROZEN status with an OPEN linked checking account is eligible to unfreeze.

**Agent:** The frozen debit card ending in 9002 is eligible to be unfrozen. Please reply yes to unfreeze it.

**Customer:** Yes.

**Support console:** unfreeze_debit_card_3893 submitted with card_id=DC-7302. Result: success.

**Agent:** The unfreeze is complete, and the debit card is ready to use immediately.
