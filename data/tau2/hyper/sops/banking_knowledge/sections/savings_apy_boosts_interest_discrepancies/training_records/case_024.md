# Case X
Channel: chat  
QA status: approved

**Customer:** I was charged an excess withdrawal fee on my savings account, but I was within the limit. Can that be refunded?

**Agent:** Fee-refund review starts with identity verification. Please provide your email address and date of birth.

**Customer:** patrick.moore@gmail.com, June 10 1982.

**Support console:** Identity verified and account ownership confirmed. get_all_user_accounts_by_user_id_3847 returned Silver Account savings SAV-SILV-6205. Account confirmed as savings. get_bank_account_transactions_9173 found an excess withdrawal fee transaction of $8.00. Withdrawal count review shows customer was within limits when fee was assessed. Eligible credit categories: interest corrections, fee refunds, and goodwill credits. Fee refund is authorized because a fee was incorrectly charged while the customer was within limits. Credit amount calculated as $8.00. apply_savings_account_credit_6831 schema requires account_id string, amount number greater than 0, and credit_type string in interest_correction, fee_refund, or goodwill_credit.

**Agent:** That excess withdrawal fee was charged incorrectly, and the refund amount is $8.00. Please reply yes if you want me to apply an $8.00 fee refund credit to your Silver Account savings now.

**Customer:** yes

**Support console:** apply_savings_account_credit_6831 completed with account_id SAV-SILV-6205, amount 8.00, credit_type fee_refund. New balance: $7,418.22.

**Agent:** An $8.00 fee refund credit is now posted to your Silver Account savings, and your new balance is $7,418.22.
