# Case B
Channel: chat
QA status: approved

**Customer:** There’s a charge I didn’t make on my credit card. I’m worried the card number was stolen.

**Agent:** That concern makes sense; because this involves a specific transaction, please provide your registered email address and date of birth.

**Customer:** jordan.lee@outlook.com, 11/02/1982.

**Support console:** Identity verified.

**Agent:** To identify the charge, provide the transaction ID shown for it.

**Customer:** txn_847201.

**Support console:** Credit card account lookup completed. User: Jordan Lee. user_id=user_11984. Registered phone=415-555-0198. Registered email=jordan.lee@outlook.com. Registered home address=210 Market St, Unit 8B, San Francisco, CA 94105. Card account_id=cc_44820. Card last4=9081. Product=Gold Rewards Card. Account open 420 days. Transaction txn_847201: merchant_name=MetroCamera Online, amount=$1,246.19, currency=USD, transaction_date=05/29/2025. Formal credit card transaction dispute may be needed for unauthorized charges, merchant issues, or billing errors.

**Agent:** The transaction is on your card; for card security, choose whether to keep using the current card or cancel it and have a replacement issued.

**Customer:** Cancel it and send a replacement.

**Support console:** Dispute card_action mapping available: keep_active is used when the user wants to continue using the current card; cancel_and_reissue is used when the card is being cancelled and a replacement issued, whether already ordered through order_replacement_credit_card_7291 or cancelled as part of the dispute.

**Agent:** Replacement delivery requires the full shipping address, including any unit or suite.

**Customer:** 210 Market St, Unit 8B, San Francisco, CA 94105.

**Agent:** Record the replacement reason as exactly one of these: fraud_suspected, lost, stolen, damaged, expired, or other.

**Customer:** fraud_suspected.

**Agent:** Shipping options are: standard delivery takes 7-10 business days with no fee; expedited shipping takes 2-3 business days; Entry-tier cards have a $15.00 expedited fee and include Bronze Rewards, EcoCard, and Business Bronze; Mid-tier cards have a $10.00 expedited fee and include Silver Rewards, Business Silver, Green Rewards, and Silver Zoom; Premium-tier and above cards have a $0.00 complimentary expedited fee and include Gold, Platinum, and Diamond Elite. Because the reason is fraud_suspected, expedited shipping is strongly recommended to minimize exposure. Choose standard or expedited.

**Customer:** Expedited.

**Support console:** Replacement eligibility checked in knowledge base before proceeding. Customer is eligible for replacement. If customer were not eligible, the replacement-card tool would not be unlocked or called, and next steps would be explained per the knowledge base. Gold Rewards Card qualifies for complimentary expedited shipping; no fee consent required.

**Agent:** Submission will automatically cancel the old card for security, and it will no longer work for new purchases. Reply yes if you want the replacement submitted with expedited shipping to 210 Market St, Unit 8B, San Francisco, CA 94105.

**Customer:** yes

**Support console:** unlock_discoverable_agent_tool called with tool_name=order_replacement_credit_card_7291. Unlock succeeded.

**Support console:** call_discoverable_agent_tool called with tool_name=order_replacement_credit_card_7291 and arguments_json="{\"account_id\":\"cc_44820\",\"replacement_reason\":\"fraud_suspected\",\"shipping_address\":\"210 Market St, Unit 8B, San Francisco, CA 94105\",\"shipping_speed\":\"expedited\",\"expedited_fee_acknowledgement\":\"no fee applies for Gold Rewards Card\",\"notes\":\"Customer reported unauthorized transaction txn_847201; replacement requested due to suspected card compromise.\"}". Replacement order submitted.

**Agent:** The replacement order is submitted. The old card is cancelled for security and will no longer work for new purchases. Expedited delivery is 2-3 business days.

**Customer:** Okay.

**Agent:** Email notifications will be sent when the order is placed and when the card ships.

**Customer:** I will watch for them.

**Agent:** Because the reason was fraud_suspected, review recent transactions for unauthorized activity.

**Customer:** This MetroCamera charge is the one I need to dispute.

**Agent:** A formal dispute can be filed for that unauthorized charge. Did you try to resolve the issue with the merchant first?

**Customer:** No, I didn’t authorize it at all.

**Agent:** Purchase date confirmation is needed for the disputed transaction: 05/29/2025.

**Customer:** Yes, that’s the date.

**Agent:** Issue-noticed date is required in MM/DD/YYYY format.

**Customer:** 06/25/2025.

**Agent:** Dispute reason must be one of these exact values: unauthorized_fraudulent_charge for a charge that was not authorized or is fraudulent; duplicate_charge for the same charge appearing multiple times; incorrect_amount for an amount that differs from expected; goods_services_not_received for never receiving what was paid for; goods_services_not_as_described for receiving something that differs from description; canceled_subscription_still_charging for a cancelled subscription that keeps charging; or refund_never_processed for a promised refund that was never applied.

**Customer:** unauthorized_fraudulent_charge.

**Agent:** Requested resolution must be exactly full_refund, partial_refund, or reversal_of_charge.

**Customer:** reversal_of_charge.

**Agent:** Since the replacement was already ordered, confirm that the dispute should use cancel_and_reissue for the card action.

**Customer:** Yes, use cancel_and_reissue.

**Support console:** Provisional Credit Eligibility Guidelines checked. Provisional credit means the disputed amount is temporarily credited back to the customer’s account while the investigation is ongoing. All eligibility criteria are required: account open at least 60 days; eligible reason category is unauthorized_fraudulent_charge, duplicate_charge, or goods_services_not_received when purchase was made more than 30 days ago; amount is at least $25.00 and does not exceed the card tier maximum; customer has not filed more than 2 disputes in the past 12 months; for non-fraud disputes, the customer must have contacted the merchant first. Tier maximums: Entry Tier $2500.00 includes Bronze Rewards Card, EcoCard, Business Bronze Rewards Card, Crypto-Cash Back Card; Mid Tier $5000.00 includes Silver Rewards Card, Business Silver Rewards Card, Green Rewards Card, Silver Zoom Card; Premium Tier $10000.00 includes Gold Rewards Card and Business Gold Rewards Card; Elite Tier $15000.00 includes Platinum Rewards Card and Business Platinum Rewards Card; Invitation Tier $25000.00 includes Diamond Elite Card. Eligibility result for txn_847201: true. Account open 420 days; reason unauthorized_fraudulent_charge; amount $1,246.19 within Premium Tier $10000.00 maximum; dispute count in past 12 months is 1; merchant-contact criterion not required for fraud reason.

**Agent:** All required dispute details are ready from your verified profile and the transaction record, including the transaction ID, card ending 9081, merchant-contact answer, purchase date, noticed date, dispute reason, requested resolution, card action, and provisional-credit eligibility. Reply yes to file the dispute.

**Customer:** yes

**Support console:** unlock_discoverable_agent_tool called with tool_name=file_credit_card_transaction_dispute_4829. Unlock succeeded.

**Support console:** partial_refund_amount omitted because resolution_requested is reversal_of_charge; partial_refund_amount is required only when resolution_requested is partial_refund and must contain the dollar amount for the partial refund.

**Support console:** call_discoverable_agent_tool called with tool_name=file_credit_card_transaction_dispute_4829 and arguments_json="{\"transaction_id\":\"txn_847201\",\"card_action\":\"cancel_and_reissue\",\"card_last_4_digits\":\"9081\",\"full_name\":\"Jordan Lee\",\"user_id\":\"user_11984\",\"phone\":\"415-555-0198\",\"email\":\"jordan.lee@outlook.com\",\"address\":\"210 Market St, Unit 8B, San Francisco, CA 94105\",\"contacted_merchant\":false,\"purchase_date\":\"05/29/2025\",\"issue_noticed_date\":\"06/25/2025\",\"dispute_reason\":\"unauthorized_fraudulent_charge\",\"resolution_requested\":\"reversal_of_charge\",\"eligible_for_provisional_credit\":true}". Dispute filed.

**Agent:** The formal dispute is filed. You are eligible for provisional credit, which means the disputed amount is temporarily credited back to your account while the investigation is ongoing.

**Customer:** If I find another bad charge, what should I do?

**Agent:** For any additional unauthorized charge, file that dispute in the Rho-Bank app or website.

**Support console:** Interaction documented in customer record with replacement order details, fraud_suspected reason, shipping speed, shipping address, dispute transaction ID, and provisional-credit decision.
