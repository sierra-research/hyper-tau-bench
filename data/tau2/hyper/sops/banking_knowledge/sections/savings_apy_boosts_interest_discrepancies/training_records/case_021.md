# Case U
Channel: chat  
QA status: approved

**Customer:** My Silver Account stayed over $10,000 last month, but I was paid interest like it was under that. This is frustrating.

**Agent:** That concern is understandable. I’ll review the Silver Account interest after identity verification. Please provide your email address and date of birth.

**Customer:** leo.harris@yahoo.com, December 2 1981.

**Support console:** Identity verified and account ownership confirmed. get_all_user_accounts_by_user_id_3847 returned user_id USER-6671 and Silver Account savings SAV-SILV-7710. Account is confirmed as a savings account. Silver Account documentation: balance less than $10,000 earns 2.5% APY; balance at least $10,000 earns 4.0% APY. Each day's ending balance is compared to $10,000. Interest accrues on the daily balance, is compounded daily, and uses a daily periodic rate calculated from the APY. Accrued interest is credited monthly. If the balance moves between tiers during a cycle, the cycle interest is the sum of each day's accrual at that day's applicable tier.

**Agent:** The Silver Account is verified. I’m going to review the monthly interest transaction and the daily balance tier used for that cycle.

**Support console:** get_bank_account_transactions_9173 reviewed SAV-SILV-7710. Interest credit found: $27.41. Daily ending balances for the cycle were at or above $10,000 each day. Documentation review completed for base tier rate and APY components. Expected APY: 4.0%. Actual APY applied: 2.5%. Expected interest: $43.86. Actual interest: $27.41. Difference: $16.45. Eligible credit category check: credits authorized only for interest corrections, fee refunds, or goodwill credits; this qualifies as interest_correction due to an incorrect tier rate system error. apply_savings_account_credit_6831 requires account_id string, amount number greater than 0, and credit_type interest_correction, fee_refund, or goodwill_credit.

**Agent:** The account was paid using the below-$10,000 tier even though the daily ending balances qualified for the at-or-above-$10,000 tier. The correction amount is $16.45. Please reply yes if you want that interest correction credited to your Silver Account now.

**Customer:** yes

**Support console:** apply_savings_account_credit_6831 completed with account_id SAV-SILV-7710, amount 16.45, credit_type interest_correction. New balance: $10,984.45. submit_interest_discrepancy_report_7294 submitted after the credit with account_id SAV-SILV-7710, user_id USER-6671, expected_apy 4.0, actual_apy 2.5, amount_difference 16.45. Report category: incorrect tier rate.

**Agent:** Your Silver Account now includes the $16.45 interest correction credit, and the new balance is $10,984.45. I also submitted an interest calculation investigation report for the incorrect tier rate.
