# Case B
Channel: chat
QA status: approved

**Customer:** I have two debit-card charges from the same store, and one other purchase my brother made without permission. I want to dispute them.

**Agent:** Before reviewing the charges and filing requirements, send your email address and date of birth for verification.

**Customer:** tessa.nguyen@icloud.com, 03/03/1992.

**Support console:** Identity verified. Internal checks remain in Support console.

**Support console:** Pre-filing requirements for debit-card transaction disputes: customer verified; transaction amount at least $1.00; transaction within 60 days old; maximum open disputes for the checking account tier not exceeded; debit card linked to an OPEN checking account; ATM disputes require determining whether the ATM was Rho-Bank or third-party.

**Support console:** Maximum open debit-card disputes are per account, not per customer: Entry Tier max 2, Mid Tier max 3, Premium Tier max 4, Elite Tier max 5. Account chk_22017 is Mid Tier with 1 open dispute, so two additional open disputes are within the limit. Account status OPEN with no holds or restrictions. Linked debit card dc_5072 is ACTIVE.

**Agent:** Here is the required liability timing before filing: if unauthorized activity is reported within 2 business days of the statement showing it, the maximum liability is $50; within 60 days, it is $500; after 60 days, liability can be unlimited and funds may not be recovered.

**Customer:** I saw both yesterday on my statement, so it’s within 2 business days.

**Support console:** get_bank_account_transactions_9173(account_id="chk_22017") reviewed transaction history. Duplicate merchant entries found: tx_6110 on 06/28/2025, "Home Goods debit purchase", amount -84.33, type debit_card_purchase, status posted; tx_6111 on 06/28/2025, "Home Goods debit purchase", amount -84.33, type debit_card_purchase, status posted. When multiple duplicate debit-card transactions exist, dispute the earliest first transaction. Unauthorized family-member transaction found: tx_6125 on 06/29/2025, "City Sports debit purchase", amount -122.18, type debit_card_purchase, status posted.

**Agent:** The two Home Goods charges match, and the earliest matching charge is the one to dispute first for a duplicate-charge claim.

**Customer:** Okay.

**Agent:** First dispute question: do you still have the physical debit card in your possession?

**Customer:** Yes, I have it.

**Agent:** Next, do you believe your PIN may have been compromised?

**Customer:** No.

**Support console:** pin_compromised value will be no. Valid pin_compromised values: yes_shared when the customer shared the PIN, yes_observed when the PIN was observed or skimmed, no when the PIN was not compromised, unknown when the customer is unsure.

**Agent:** For Home Goods, did you try to resolve the duplicate charge directly with the merchant?

**Customer:** Yes, they said to dispute it with my bank.

**Agent:** Regarding City Sports, did you try to resolve that purchase directly with the merchant?

**Customer:** Yes, they said the charge went through and I should work with the bank.

**Agent:** Can this chat serve as your written statement describing what happened?

**Customer:** Yes.

**Support console:** written_statement_provided=true because customer agreed the conversation can be used as the written statement. For non-fraud debit-card disputes, contacted_merchant is required and the customer must be asked whether they attempted to resolve directly with the merchant.

**Customer:** Do I need a police report?

**Agent:** A police report is not required for these two claims. For suspected fraud over $500, Rho-Bank asks whether a police report was filed and recommends filing one if it has not been filed.

**Support console:** Dispute category selection rules: dispute_category must be exactly one of unauthorized_transaction, atm_cash_discrepancy, atm_deposit_not_credited, duplicate_charge, incorrect_amount, goods_services_not_received, recurring_charge_after_cancellation, card_present_fraud, card_not_present_fraud. For unauthorized transactions, determine whether fraud is suspected. If fraud is suspected, use card_present_fraud for in-store or physical fraud and card_not_present_fraud for online or phone fraud. Use unauthorized_transaction only when fraud is not suspected, such as family member use without permission or customer forgetting a transaction.

**Support console:** transaction_type must be exactly one of pin_purchase, signature_purchase, online_purchase, atm_withdrawal, atm_deposit, recurring_payment, person_to_person. Person_to_person includes EveryonePay. transaction_type is determined from customer circumstances.

**Support console:** Card action mapping by dispute category: card_present_fraud=close_and_reissue; card_not_present_fraud=close_and_reissue; unauthorized_transaction=freeze_pending_investigation; atm_cash_discrepancy=keep_active; atm_deposit_not_credited=keep_active; duplicate_charge=keep_active; incorrect_amount=keep_active; goods_services_not_received=keep_active; recurring_charge_after_cancellation=keep_active. card_action records metadata only; the indicated actual card action must be performed separately after filing.

**Support console:** Provisional credit guidelines: Regulation E requires provisional credit for debit-card disputes when all specified conditions are met. Required only when reported within 60 days of statement date; category is unauthorized_transaction, card_present_fraud, card_not_present_fraud, atm_cash_discrepancy, or duplicate_charge; customer provided written statement; checking account is OPEN with no holds or restrictions. Timing: within 10 business days of dispute filing for standard accounts; within 20 business days for new accounts opened less than 30 days. Provisional credit is not required but may be offered at discretion for goods_services_not_received, recurring_charge_after_cancellation, atm_deposit_not_credited, incorrect_amount; when the customer has not contacted the merchant first for a non-fraud dispute; when the customer voluntarily shared the PIN and pin_compromised=yes_shared; or when the account is less than 30 days old and the dispute is card-not-present. Debit-card provisional credit is for the full disputed amount, unlike credit cards with tiered maximums, subject to maximum of full transaction amount and reduced by any applicable $50 or $500 late-reporting liability offset. If provisional credit is issued, the bank has 45 business days to complete the investigation, extended from 10 days. For international transactions, POS transactions at merchants outside the US, or new accounts, the timeline with provisional credit extends to 90 days. If investigation finds the transaction was authorized or claim invalid, provisional credit will be reversed, customer notified in writing at least 3 business days before reversal, and customer may request supporting documentation.

**Agent:** The duplicate-charge dispute appears eligible for required provisional credit if filed with your written statement. The family-member purchase is treated as unauthorized use without suspected fraud and has a separate card-safety step.

**Customer:** File both, please.

**Agent:** Confirm by answering yes to file the duplicate-charge dispute for $84.33 and the unauthorized-transaction dispute for $122.18 on the debit card ending in 7721.

**Customer:** yes

**Support console:** file_debit_card_transaction_dispute_6281 requires transaction_id, account_id, card_id, user_id, dispute_category, transaction_date, discovery_date, disputed_amount, transaction_type, card_in_possession, pin_compromised, contacted_merchant, police_report_filed, written_statement_provided, provisional_credit_eligible, and card_action. transaction_id came from get_bank_account_transactions_9173; account_id is the checking account linked to the debit card; card_id is the debit card ID; user_id is the customer Rho-Bank user ID; transaction_date and discovery_date use MM/DD/YYYY; disputed_amount is the dollar amount being disputed.

**Support console:** file_debit_card_transaction_dispute_6281(transaction_id="tx_6110", account_id="chk_22017", card_id="dc_5072", user_id="usr_8059", dispute_category="duplicate_charge", transaction_date="06/28/2025", discovery_date="07/01/2025", disputed_amount=84.33, transaction_type="signature_purchase", card_in_possession=true, pin_compromised="no", contacted_merchant=true, police_report_filed=false, written_statement_provided=true, provisional_credit_eligible=true, card_action="keep_active") succeeded.

**Support console:** file_debit_card_transaction_dispute_6281(transaction_id="tx_6125", account_id="chk_22017", card_id="dc_5072", user_id="usr_8059", dispute_category="unauthorized_transaction", transaction_date="06/29/2025", discovery_date="07/01/2025", disputed_amount=122.18, transaction_type="signature_purchase", card_in_possession=true, pin_compromised="no", contacted_merchant=true, police_report_filed=false, written_statement_provided=true, provisional_credit_eligible=true, card_action="freeze_pending_investigation") succeeded.

**Support console:** Multiple disputes on same card: each dispute’s card_action parameter remains based on its own category and is not changed because of other disputes. Actual card action uses most severe action across all disputes: close_and_reissue greater than freeze_pending_investigation greater than keep_active. This batch has keep_active for duplicate_charge and freeze_pending_investigation for unauthorized_transaction, so freeze_debit_card_3892 is called once for card dc_5072 as the most severe actual action.

**Agent:** Both disputes have been filed. To freeze the debit card ending in 7721 while those claims are reviewed, confirm yes.

**Customer:** yes

**Support console:** freeze_debit_card_3892(card_id="dc_5072") succeeded.

**Agent:** Card ending in 7721 is frozen while the claims are reviewed. Any required provisional credit is handled under the debit-card provisional credit guidelines and may be reversed with written advance notice if the investigation finds the transaction was authorized or the claim is invalid.
