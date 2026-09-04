# Case W
Channel: chat  
QA status: approved

**Customer:** My savings interest seems off, but it doesn’t look like a tier or linked-account issue.

**Agent:** Expected-versus-actual review starts with identity verification. Please provide your email address and date of birth.

**Customer:** rachel.king@outlook.com, November 23 1990.

**Support console:** Identity verified and account ownership confirmed. get_all_user_accounts_by_user_id_3847 returned user_id USER-3309 and Green Account savings SAV-GRN-3118. Account confirmed as savings. Documentation reviewed for applicable APY components: base rate, tier rate, linked checking boost, credit card bonuses, and relationship bonus. No missing linked checking boost, incorrect tier rate, or missing relationship bonus identified.

**Agent:** The Green Account savings is verified. I’m going to review the posted interest credit and compare it with the documented APY components.

**Support console:** get_bank_account_transactions_9173 reviewed SAV-GRN-3118. Interest credit found: $31.90. Expected APY based on documentation: 4.0%. Actual APY field applied: 4.0%. Expected interest from documented calculation: $36.90. Actual credited interest: $31.90. Difference: $5.00. Eligible credit category check: credits authorized only for interest corrections, fee refunds, or goodwill credits; this qualifies as interest_correction because there is another system calculation error. apply_savings_account_credit_6831 requires account_id string, amount number greater than 0, and credit_type string in interest_correction, fee_refund, or goodwill_credit.

**Agent:** The APY components matched the documentation, but the credited dollar amount was $5.00 short. Please reply yes if you want me to apply a $5.00 interest correction credit to your Green Account savings now.

**Customer:** yes

**Support console:** apply_savings_account_credit_6831 completed with account_id SAV-GRN-3118, amount 5.00, credit_type interest_correction. New balance: $9,236.90. submit_interest_discrepancy_report_7294 submitted after the credit with account_id SAV-GRN-3118, user_id USER-3309, expected_apy 4.0, actual_apy 4.0, amount_difference 5.00. Report category: system calculation error.

**Agent:** A $5.00 interest correction is now credited to your Green Account savings, and your new balance is $9,236.90. I also submitted an investigation report for the calculation error.
