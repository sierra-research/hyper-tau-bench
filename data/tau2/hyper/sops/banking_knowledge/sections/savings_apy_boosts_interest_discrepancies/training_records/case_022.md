# Case V
Channel: chat  
QA status: approved

**Customer:** I have a Gold Account and an active Gold Rewards Card, but I don’t think the relationship bonus was paid.

**Agent:** A relationship-bonus review requires identity verification first. Please provide your email address and date of birth.

**Customer:** jasmine.wu@gmail.com, July 8 1986.

**Support console:** Identity verified and account ownership confirmed. get_all_user_accounts_by_user_id_3847 returned user_id USER-5120, Gold Account savings SAV-GOLD-9021, and active Gold Rewards Card associated with the Gold Account. Account confirmed as savings. Documentation review: Gold Account holders whose Gold Rewards Card remains active and associated receive a 0.025% relationship bonus APY on top of the base rate; the relationship bonus is additive, not a multiplier, and applies while the Gold Rewards Card remains active and associated. Silver Account documentation also states a Silver Account customer who maintains multiple Rho-Bank products may qualify for a 0.025% relationship bonus that stacks on top of the base Silver APY.

**Agent:** Your Gold Account and associated Gold Rewards Card are verified. I’m going to compare the interest paid with the relationship bonus that should have been included.

**Support console:** get_bank_account_transactions_9173 reviewed SAV-GOLD-9021. Monthly interest credit posted: $68.75. Documentation reviewed for all applicable APY components: base rate, tier rate, linked checking boost, credit card bonuses, and relationship bonus. Expected APY: 5.525%. Actual APY applied: 5.5%. Expected interest: $69.06. Actual interest: $68.75. Difference: $0.31. Eligible credit category check: credits authorized only for interest corrections, fee refunds, or goodwill credits; this qualifies as interest_correction because a system error omitted the relationship bonus. apply_savings_account_credit_6831 requires account_id string, positive amount greater than 0, and credit_type in interest_correction, fee_refund, or goodwill_credit.

**Agent:** The relationship bonus was missing from the Gold Account interest payment. The correction amount is $0.31. Please reply yes if you want me to credit that correction to your Gold Account savings now.

**Customer:** yes

**Support console:** apply_savings_account_credit_6831 completed with account_id SAV-GOLD-9021, amount 0.31, credit_type interest_correction. New balance: $15,069.06. submit_interest_discrepancy_report_7294 submitted after the credit with account_id SAV-GOLD-9021, user_id USER-5120, expected_apy 5.525, actual_apy 5.5, amount_difference 0.31. Report category: missing relationship bonus.

**Agent:** A $0.31 correction has posted to your Gold Account savings, and your new balance is $15,069.06. I also submitted an investigation report for the missing relationship bonus.
