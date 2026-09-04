# Case T
Channel: chat  
QA status: approved

**Customer:** My Gold savings interest did not include the checking boost. Can you fix it?

**Agent:** We can review the calculation and correct the account if there is an interest error. Please provide your email address and date of birth to verify your identity.

**Customer:** emma.clark@outlook.com, September 15 1994.

**Support console:** Identity verified and account ownership confirmed. get_all_user_accounts_by_user_id_3847 returned user_id USER-2048, Gold Account savings SAV-GOLD-4402, and active Green Account checking under the same profile. Account type confirmed as savings. KB confirms only listed checking-savings pairings qualify for linked checking APY boost; Green Account checking plus Gold Account savings is listed and qualifies. Linked checking APY boost applies automatically, adds to base APY, and can stack with credit card APY bonuses.

**Agent:** The Gold Account savings and Green Account checking are both verified on your profile. I’m going to review the interest credit on that savings account next.

**Support console:** get_bank_account_transactions_9173 reviewed SAV-GOLD-4402. Monthly interest credit posted: $50.42. Documentation reviewed for Gold Account APY components: base APY, linked checking boost, credit card bonuses, relationship bonus, and applicable account components. Expected APY: 6.25%. Actual APY applied: 5.5%. Expected interest: $57.29. Actual interest: $50.42. Difference: $6.87. Eligible credit category check: credits authorized only for interest corrections, fee refunds, or goodwill credits; this qualifies as interest_correction because a system error omitted a qualifying linked checking APY boost. Tool schema for apply_savings_account_credit_6831 requires account_id string, amount number greater than 0, and credit_type string in interest_correction, fee_refund, or goodwill_credit.

**Agent:** A missing linked checking boost made the interest payment $6.87 short. Please reply yes if you want me to apply a $6.87 interest correction credit to your Gold Account savings now.

**Customer:** yes

**Support console:** apply_savings_account_credit_6831 completed with account_id SAV-GOLD-4402, amount 6.87, credit_type interest_correction. New balance: $12,806.87. submit_interest_discrepancy_report_7294 submitted after the credit with account_id SAV-GOLD-4402, user_id USER-2048, expected_apy 6.25, actual_apy 5.5, amount_difference 6.87. Report category: missing APY boost. Backend investigation report created after customer credit.

**Agent:** A $6.87 interest correction credit is now on your Gold Account savings, bringing the balance to $12,806.87. I also submitted an interest calculation investigation report so the missing linked checking boost can be reviewed and fixed.
