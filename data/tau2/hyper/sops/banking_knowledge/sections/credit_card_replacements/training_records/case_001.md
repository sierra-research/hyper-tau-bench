# Case A
Channel: chat
QA status: approved

**Customer:** My credit card still works sometimes, but the chip is cracked. Can I get a replacement?

**Agent:** Damaged-card replacements require identity verification first; please send your email address and date of birth.

**Customer:** maya.chen@outlook.com, March 12, 1986.

**Support console:** Identity verified with two matching factors. Credit card account lookup completed before any replacement order: customer Maya Chen, credit_card_account_id=cca_4821, card_id=card_8821, primary address 118 Cedar Avenue, Apt 4C, Boston, MA 02116.

**Agent:** Reason selection needed: choose one replacement reason from fraud suspected, lost, stolen, damaged, expired, or other.

**Customer:** Damaged. The card is cracked.

**Support console:** Replacement reason recorded exactly as damaged, one of fraud_suspected, lost, stolen, damaged, expired, other.

**Agent:** Full shipping address to confirm: 118 Cedar Avenue, Apt 4C, Boston, MA 02116.

**Customer:** Yes, that full address is correct.

**Agent:** Delivery choices are standard delivery in 7–10 business days with no fee for all cardholders, or expedited delivery in 2–3 business days with a possible fee based on card tier. Do you want expedited shipping?

**Customer:** No, standard is fine.

**Support console:** Knowledge base eligibility confirmed before tool access: damaged-card replacement is eligible; no pending replacement request is being processed; customer is within the applicable 60-day replacement limit. Replacement ordering tool was not unlocked or called before eligibility was confirmed.

**Agent:** Security impact before submission: the current card will be cancelled and will no longer work for new purchases; the new card will have a different card number and CVV; the account number will remain the same so recurring payments linked to the account continue without interruption. Please reply yes to confirm that you want the replacement order placed.

**Customer:** yes

**Support console:** unlock_discoverable_agent_tool called with tool_name=order_replacement_credit_card_7291 after eligibility confirmation.

**Support console:** call_discoverable_agent_tool called with tool_name=order_replacement_credit_card_7291; account_id=cca_4821; replacement_reason=damaged; shipping_address=118 Cedar Avenue, Apt 4C, Boston, MA 02116; shipping_speed=standard; notes=chip cracked, customer selected standard delivery.

**Support console:** Replacement order submitted successfully. Old card cancelled for new purchases. New card created with different card number and CVV. Customer record documented with interaction details and replacement order details.

**Agent:** Order result: the standard replacement order is placed. Delivery is expected in 7–10 business days, standard delivery has no fee, and you’ll receive an order email plus another email when the card ships, so watch those emails for updates.

**Customer:** Will there be instructions when it arrives?

**Agent:** Activation details arrive with the new replacement card; follow those instructions.

**Customer:** I have the old card saved on a few shopping sites.

**Agent:** Saved merchant profiles should be updated with the new card details after the replacement arrives.
