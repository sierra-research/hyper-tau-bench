# Case L
Channel: chat
QA status: approved

**Customer:** I’m trying to close my credit card account, but the review seems stuck.

**Agent:** Stalled closure reviews are frustrating; share your email address and date of birth for verification.

**Customer:** kevin.miles@icloud.com, July 19, 1987.

**Support console:** Identity verified with two matching factors.

**Agent:** Account-level reference verification is being redone before the closure precheck continues.

**Support console:** Pending replacement order checks use get_pending_replacement_orders_5765 and must be called with credit_card_account_id. Prerequisite: correct credit_card_account_id is required. Step 1 for the procedure is to locate the credit_card_account_id for the account being reviewed.

**Support console:** Account lookup shows credit_card_account_id=cca_7004 and card_id=card_7004A. Initial tool attempt used get_pending_replacement_orders_5765 with credit_card_account_id=card_7004A and returned an invalid credit_card_account_id issue.

**Support console:** Troubleshooting action completed: re-verified that the identifier must be an account-level identifier, not a card-level identifier. Confirmed identifier format and source from account lookup; correct credit_card_account_id is cca_7004.

**Customer:** Is that why it didn’t move forward?

**Agent:** Corrected account reference: the replacement-order precheck needed the account-level reference corrected before it could continue.
