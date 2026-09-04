# Case J

Channel: chat  
QA status: approved

**Customer:** I can’t find my debit card, but I think it’s somewhere at home. Can you freeze it for now?

**Agent:** A freeze is temporary and can be undone later; closing is permanent and is recommended when a card is confirmed lost or stolen. To verify your identity, please provide your email address and date of birth.

**Customer:** ethan.parker@yahoo.com, January 14 1991.

**Support console:** Customer identity verified. Freeze, unfreeze, close, and replacement are separate debit-card actions.

**Agent:** Please tell me why you want to freeze the card.

**Customer:** I misplaced it and I’m looking for it.

**Support console:** Valid freeze reasons include misplaced card being searched for, travel with extra security wanted, suspicious activity being investigated before closing, temporary spending restriction such as budgeting, and lending the card to a family member while wanting to control usage. get_debit_cards_by_account_id_7823(account_id=CHK-6420) used before freeze to verify card exists and current status. Card record: card_id=DC-2541, user_id=USR-508, owner matches verified customer, status=ACTIVE. PENDING, CLOSED, and already FROZEN cards cannot be frozen.

**Agent:** While frozen, all new transactions will be declined, including recurring payments and subscriptions, and pending transactions already authorized may still process. You can unfreeze the card at any time by calling customer service or through the mobile app. Please reply yes to freeze it.

**Customer:** Yes, freeze it.

**Support console:** freeze_debit_card_3892 submitted with card_id=DC-2541. Result: success.

**Agent:** The debit card is now frozen.

**Customer:** Does this stop ATM withdrawals too?

**Agent:** Freezing this debit card does not affect ATM access if you have your PIN. For an ATM freeze, separately enable ATM Block through the mobile app.

**Customer:** What if I forget to unfreeze it?

**Agent:** If the frozen debit card is not unfrozen within 90 days, you will receive a reminder notification.
