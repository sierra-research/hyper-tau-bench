# Case C
Channel: chat
QA status: approved

**Customer:** I was charged twice by the same merchant. I want to dispute one of the charges but keep my card active.

**Agent:** A secure check comes first; provide your registered phone number and date of birth.

**Customer:** 646-555-0144, 08/09/1990.

**Support console:** Identity verified.

**Agent:** Transaction lookup needs the transaction ID for the charge you want to dispute.

**Customer:** txn_502778.

**Support console:** Account lookup completed. User: Priya Nair. user_id=user_28810. Registered phone=646-555-0144. Registered email=priya.nair@gmail.com. Registered address=88 Hudson Ave, Apt 14C, New York, NY 10013. Credit card account_id=cc_31008. Card product=Business Silver Rewards Card. Card last4=3349. Account open 210 days. Transaction txn_502778: merchant_name=Northstar Office Supply, amount=$179.80, currency=USD, transaction_date=06/21/2025. A duplicate charge is a billing error and may require a formal credit card transaction dispute.

**Agent:** Prior dispute history affects provisional-credit review, so I’m checking the credit card dispute history for your verified user profile.

**Support console:** First procedure step completed: obtained user_id for the user whose dispute history needs review. Required input is user_id, the user’s canonical internal identifier. Confirmed user_id user_28810 is correct and current before calling get_user_dispute_history_7291.

**Support console:** get_user_dispute_history_7291 is used when a consolidated list of all credit card disputes filed by a specific user is needed, when reviewing current status or historical progression, and when transaction-level context for each dispute is needed. Tool call: get_user_dispute_history_7291(user_id="user_28810").

**Support console:** Returned list of dispute records for specified user_id user_28810 only. Record 1: dispute_id=disp_70122, dispute_date=09/13/2024, status=closed, last_updated_at=10/21/2024, transaction_id=txn_194400, transaction_date=09/10/2024, merchant_name=BookTrail, amount=42.10, currency=USD, card_last4=3349, reason_code=refund_never_processed, outcome=merchant_refund_confirmed, notes/internal comments="Merchant proof received; dispute closed." Reviewed returned list and associated transaction details. Verified list is complete for user_id user_28810. Used dispute_date and last_updated_at to understand timeline and recency; used status to determine no current action needed on closed prior dispute; reviewed transaction details to confirm the prior dispute context.

**Agent:** The history review shows one closed credit card dispute in the past 12 months, so I can continue gathering details for this duplicate charge.

**Customer:** The merchant said they see both charges but told me to dispute one with the bank.

**Agent:** Merchant-contact answer is required for this non-fraud dispute: did you try to resolve this issue with the merchant first?

**Customer:** Yes.

**Agent:** Use MM/DD/YYYY for the purchase date of the disputed transaction.

**Customer:** 06/21/2025.

**Agent:** Duplicate-charge timing also needs when you first noticed the issue, in MM/DD/YYYY format.

**Customer:** 06/22/2025.

**Agent:** Reason code selection must be exactly one of these values: unauthorized_fraudulent_charge for a charge that was not authorized or is fraudulent; duplicate_charge for the same charge appearing multiple times; incorrect_amount for an amount that differs from expected; goods_services_not_received for never receiving what was paid for; goods_services_not_as_described for receiving something that differs from description; canceled_subscription_still_charging for a cancelled subscription that keeps charging; or refund_never_processed for a promised refund that was never applied.

**Customer:** duplicate_charge.

**Agent:** Resolution selection must be full_refund, partial_refund, or reversal_of_charge.

**Customer:** partial_refund.

**Agent:** Partial-refund amount is required for that choice; provide the dollar amount requested.

**Customer:** 179.80.

**Agent:** Card action must be keep_active or cancel_and_reissue; choose keep_active if you want to continue using the current card or cancel_and_reissue if the card is being cancelled and a replacement issued.

**Customer:** keep_active.

**Support console:** card_action must be exactly keep_active or cancel_and_reissue. keep_active selected because the customer wants to continue using the current card. cancel_and_reissue would be used when the card is cancelled and a replacement issued, whether the replacement was already ordered through order_replacement_credit_card_7291 or cancellation occurs as part of the dispute.

**Support console:** Provisional Credit Eligibility Guidelines checked. Provisional credit means the disputed amount is temporarily credited back while the investigation is ongoing. All eligibility criteria are required: account open at least 60 days; eligible reason category is unauthorized_fraudulent_charge, duplicate_charge, or goods_services_not_received when the purchase was made more than 30 days ago; amount is at least $25.00 and within card-tier maximum; customer has not filed more than 2 disputes in the past 12 months; non-fraud disputes require attempted merchant resolution. Tier maximums: Entry Tier $2500.00 includes Bronze Rewards Card, EcoCard, Business Bronze Rewards Card, Crypto-Cash Back Card; Mid Tier $5000.00 includes Silver Rewards Card, Business Silver Rewards Card, Green Rewards Card, Silver Zoom Card; Premium Tier $10000.00 includes Gold Rewards Card and Business Gold Rewards Card; Elite Tier $15000.00 includes Platinum Rewards Card and Business Platinum Rewards Card; Invitation Tier $25000.00 includes Diamond Elite Card. Eligibility result: true. Account open 210 days; duplicate_charge is eligible; amount $179.80 is at least $25.00 and below Mid Tier $5000.00 maximum; prior disputes in past 12 months=1; merchant contacted=true.

**Agent:** Ready-to-submit details include the transaction ID, keep_active card action, card ending 3349, verified profile information, merchant-contact answer, purchase date, noticed date, duplicate-charge reason, partial-refund request, partial-refund amount, and provisional-credit eligibility. Reply yes to submit the dispute.

**Customer:** yes

**Support console:** unlock_discoverable_agent_tool called with tool_name=file_credit_card_transaction_dispute_4829. Unlock succeeded.

**Support console:** call_discoverable_agent_tool called with tool_name=file_credit_card_transaction_dispute_4829 and arguments_json="{\"transaction_id\":\"txn_502778\",\"card_action\":\"keep_active\",\"card_last_4_digits\":\"3349\",\"full_name\":\"Priya Nair\",\"user_id\":\"user_28810\",\"phone\":\"646-555-0144\",\"email\":\"priya.nair@gmail.com\",\"address\":\"88 Hudson Ave, Apt 14C, New York, NY 10013\",\"contacted_merchant\":true,\"purchase_date\":\"06/21/2025\",\"issue_noticed_date\":\"06/22/2025\",\"dispute_reason\":\"duplicate_charge\",\"resolution_requested\":\"partial_refund\",\"partial_refund_amount\":179.80,\"eligible_for_provisional_credit\":true}". Dispute filed.

**Agent:** Your dispute is filed with the card kept active. The partial refund amount requested is $179.80, and provisional credit applies while the investigation is ongoing.
