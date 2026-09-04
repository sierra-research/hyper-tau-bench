# Case L

Channel: chat  
QA status: approved

**Customer:** I closed my damaged debit card two days ago. I have an Entry checking account and need a replacement, maybe rush if possible.

**Agent:** Replacement limits depend on the checking account tier. Please provide your email address and date of birth for verification.

**Customer:** benjamin.kim@yahoo.com, August 30 1985.

**Support console:** Customer identity verified.

**Support console:** Account tier=ENTRY, account_type=checking. Debit cards are available only for checking accounts, not savings accounts. Replacement policies vary by checking-account tier. To check replacement history, retrieve all cards for the account, look for issue_reason lost, stolen, fraud, or damaged, check date_issued, and count cards issued within the last 12 months. Cards with issue_reason new_account, first_card, expired, upgrade, or bank_reissue do not count toward the replacement limit.

**Support console:** Replacement history for CHK-4107: damaged card issued 2025-02-16 and lost card issued 2025-05-05 count within rolling 12-month period. bank_reissue card issued 2025-01-11 does not count. ENTRY maximum is 2 replacement debit cards per rolling 12-month period. Customer is requesting another replacement before the oldest replacement ages out; customer may wait until oldest ages out or pay $25 excess replacement fee. Closed damaged card closure timestamp is 50 hours ago; ENTRY 48-hour waiting period after closure is satisfied.

**Agent:** Entry accounts allow up to 2 replacement debit cards in a rolling 12-month period. You have reached that limit, so you can either wait until the oldest replacement ages out of the 12-month window or pay a $25 excess replacement fee. Which option do you choose?

**Customer:** I’ll pay the $25 fee.

**Agent:** Entry replacements can only ship by STANDARD delivery, and that delivery option has a $0 fee. EXPEDITED and RUSH shipping are not available. Please confirm STANDARD shipping.

**Customer:** Standard is fine.

**Agent:** Design pricing for Entry replacements is CLASSIC at $0, PREMIUM metallic silver at $10, and CUSTOM uploaded image at $25. Which design would you like?

**Customer:** Premium.

**Support console:** order_debit_card_5739 requires exact delivery_fee and design_fee for replacement orders. ENTRY tier values: delivery_fee=0 for STANDARD, design_fee=10 for PREMIUM, excess_replacement_fee=25. All applicable replacement fees, including shipping, design, and excess replacement fees, are automatically charged to the linked checking account and must be disclosed before order.

**Agent:** The replacement order will deduct a $25 excess replacement fee and a $10 PREMIUM design fee from the linked checking account; STANDARD shipping is $0. Please reply yes to order the replacement card.

**Customer:** Yes.

**Support console:** order_debit_card_5739 submitted for account_id=CHK-4107, replacement=true, delivery=STANDARD, delivery_fee=0, design=PREMIUM, design_fee=10, excess_replacement_fee=25. Result: approved.

**Agent:** The Entry replacement debit card has been ordered with STANDARD shipping. The total fee deducted from the linked checking account is $35.
