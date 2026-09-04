# Case C
Channel: chat
QA status: approved

**Customer:** I got an alert for a charge I don’t recognize, so I think my credit card may be compromised.

**Agent:** Unrecognized-charge alerts need secure review; share the email address on the account and your date of birth.

**Customer:** priya.singh@gmail.com, January 22, 1984.

**Support console:** Identity verified with two matching factors. Credit card account lookup completed: credit_card_account_id=cca_6720, card_id=card_7740, product=Green Rewards Card, tier row=mid, primary address 901 Market Street, Suite 1206, San Francisco, CA 94103.

**Support console:** Knowledge base shipping fee row for mid tier: expedited replacement shipping costs $10.00 for Silver Rewards, Silver Rewards Card, Business Silver, Business Silver Rewards Card, Green Rewards, Green Rewards Card, Silver Zoom, and Silver Zoom Card.

**Agent:** Fraud-risk replacement setup needs one reason from this list: fraud suspected, lost, stolen, damaged, expired, or other.

**Customer:** Fraud suspected.

**Support console:** Replacement reason recorded exactly as fraud_suspected.

**Agent:** Expedited shipping is strongly recommended for suspected fraud to minimize exposure.

**Customer:** Yes, I’d rather reduce the risk.

**Agent:** Recent-transaction check: look for unauthorized activity.

**Customer:** I checked and see one I don’t recognize.

**Agent:** Ship-to address for confirmation: 901 Market Street, Suite 1206, San Francisco, CA 94103.

**Customer:** Yes, send it there.

**Agent:** Green Rewards Card shipping options are expedited delivery in 2–3 business days for $10.00, or standard delivery in 7–10 business days with no fee. Do you want expedited shipping?

**Customer:** Yes, expedited please.

**Support console:** Knowledge base eligibility confirmed before tool access: fraud_suspected replacement is eligible; no existing replacement request is still being processed; customer is within the applicable 60-day replacement limit. Replacement ordering tool was not unlocked or called before eligibility confirmation.

**Agent:** Replacement authorization summary: submitting this expedited order will cancel the current card so it no longer works for new purchases; the new card will have a different card number and CVV; the account number will stay the same so recurring payments linked to the account continue without interruption; and the $10.00 expedited shipping fee will apply. Please reply yes to confirm the replacement order and the expedited fee.

**Customer:** yes

**Support console:** unlock_discoverable_agent_tool called with tool_name=order_replacement_credit_card_7291 after eligibility confirmation.

**Support console:** call_discoverable_agent_tool called with tool_name=order_replacement_credit_card_7291; account_id=cca_6720; replacement_reason=fraud_suspected; shipping_address=901 Market Street, Suite 1206, San Francisco, CA 94103; shipping_speed=expedited; expedited_fee_acknowledgement=customer consent captured for $10.00; notes=fraud_suspected after customer reported an unrecognized transaction.

**Support console:** Replacement order submitted successfully. Customer record documented with interaction details, fraud_suspected reason, fee consent, shipping speed, and replacement order details.

**Agent:** Suspected-fraud order status: the expedited replacement is ordered. Delivery is expected in 2–3 business days; the $10.00 expedited fee was accepted, and you’ll receive an order email plus another email when the card ships, so watch those messages for updates.

**Customer:** How do I handle the suspicious charge?

**Agent:** Rho-Bank transaction review is available in the app or website for checking recent unauthorized activity.

**Customer:** The one I saw still looks unauthorized.

**Agent:** Unauthorized charges should be reported or disputed in the Rho-Bank app or website.

**Customer:** Do I need to activate the card?

**Agent:** Your replacement-card packet includes the instructions for activating the new card.

**Customer:** I have this card saved with ride share and utilities.

**Agent:** Ride share, utilities, and other saved merchants should be updated with the new card details after arrival.
