# Case B
Channel: chat
QA status: approved

**Customer:** My wallet was stolen this morning, and my credit card was inside.

**Agent:** Wallet theft is stressful; reply with the account email address and your date of birth.

**Customer:** jordan.patel@icloud.com, November 5, 1991.

**Support console:** Identity verified with two matching factors. Credit card account lookup completed: credit_card_account_id=cca_5108, card_id=card_2304, card tier row=entry, product=Bronze Rewards Card, primary address 44 Northlake Drive, Unit 2A, Denver, CO 80202.

**Support console:** Knowledge base shipping fee row for entry tier: expedited replacement shipping costs $15.00 for Bronze Rewards, Bronze Rewards Card, EcoCard, Business Bronze, and Business Bronze Rewards Card.

**Agent:** For this stolen-card request, which one reason should be recorded: fraud suspected, lost, stolen, damaged, expired, or other?

**Customer:** Stolen.

**Support console:** Replacement reason recorded exactly as stolen.

**Agent:** To reduce exposure after a stolen card, expedited shipping is strongly recommended.

**Customer:** I want the new card as soon as possible.

**Agent:** As a safety step, review recent transactions for unauthorized activity.

**Customer:** I’ll check them now.

**Agent:** Destination check: 44 Northlake Drive, Unit 2A, Denver, CO 80202.

**Customer:** That’s correct.

**Agent:** Bronze Rewards Card shipping options are expedited delivery in 2–3 business days for $15.00, or standard delivery in 7–10 business days with no fee. Do you want expedited shipping?

**Customer:** Yes, use expedited.

**Support console:** Knowledge base eligibility confirmed before tool access: stolen-card replacement is eligible; no existing replacement request is still being processed; customer is within the applicable 60-day replacement limit. Replacement ordering tool remains locked until explicit customer confirmation.

**Agent:** Fee and card-change confirmation: this order will cancel the current card so it no longer works for new purchases, the new card will have a different card number and CVV, the account number will remain unchanged for recurring payments linked to the account, and the $15.00 expedited shipping fee will apply. Please reply yes to confirm the replacement order and the expedited fee.

**Customer:** yes

**Support console:** unlock_discoverable_agent_tool called with tool_name=order_replacement_credit_card_7291 after eligibility confirmation.

**Support console:** call_discoverable_agent_tool called with tool_name=order_replacement_credit_card_7291; account_id=cca_5108; replacement_reason=stolen; shipping_address=44 Northlake Drive, Unit 2A, Denver, CO 80202; shipping_speed=expedited; expedited_fee_acknowledgement=customer consent captured for $15.00; notes=card stolen, customer requested faster delivery to reduce exposure.

**Support console:** Replacement order submitted successfully. Customer record documented with interaction details, stolen-card reason, fee consent, shipping speed, and replacement order details.

**Agent:** Submission result: the stolen-card expedited order is submitted. Expected delivery is 2–3 business days; the $15.00 expedited fee was accepted with your confirmation, and you’ll get an order email plus a shipping email, so track those messages for updates.

**Customer:** If I find a charge I didn’t make, what should I do?

**Agent:** Transaction-list review in the app or website is the next step for checking unauthorized activity.

**Customer:** I see one that I didn’t make.

**Agent:** If that charge is unauthorized, dispute it in the app or website.

**Customer:** What do I do when the new card arrives?

**Agent:** When the replacement arrives, activate it using the instructions included with the card.

**Customer:** And my saved card details?

**Agent:** Stored payment details at merchants need the new replacement-card information after you receive it.
