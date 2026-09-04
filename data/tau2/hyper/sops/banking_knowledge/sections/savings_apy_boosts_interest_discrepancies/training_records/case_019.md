# Case S
Channel: chat  
QA status: approved

**Customer:** My Gold savings interest looks low. I have both Green checking and Purple checking, and I thought both boosts might count.

**Agent:** Interest review starts with identity verification. Please provide your email address and date of birth.

**Customer:** nadia.foster@gmail.com, May 4 1985.

**Support console:** Identity verified. get_all_user_accounts_by_user_id_3847 returned Gold Account savings SAV-GOLD-1188, active Green Account checking, active Purple Account checking, and no closed checking accounts under the profile. KB confirms Green Account checking plus Gold Account savings qualifies, and Purple Account checking plus Gold Account savings also qualifies. Multiple checking boosts do not stack. For Gold savings example: Green Account checking boost is +0.75%; Purple Account checking boost is +0.1%; only Green Account +0.75% applies, not +0.85%. Other bonus types may stack separately, including credit card APY bonuses, relationship bonuses, and account tier bonuses.

**Agent:** Two qualifying checking accounts are linked to your Gold Account savings, but checking boosts are not added together. The Green Account checking boost is higher than the Purple Account checking boost, so the Green Account boost is the one that should apply. Other bonus types, such as a credit card APY bonus, relationship bonus, or account tier bonus, can still stack separately.

**Customer:** So if the bank used the Purple one, that would be wrong?

**Support console:** Investigation step completed. Agent identified all checking accounts held, determined corresponding boosts for the Gold Account savings type, and confirmed the highest boost should be Green Account +0.75%. Transaction review shows last interest calculation used Purple Account +0.1% instead. Correct APY recalculated with the higher checking boost. Interest correction amount calculated as $21.37.

**Agent:** Using the lower Purple Account boost would be wrong for this Gold Account savings calculation. The correction amount is $21.37. Please reply yes if you want that correction credited to your Gold Account savings now.

**Customer:** yes

**Support console:** apply_savings_account_credit_6831 completed for savings account SAV-GOLD-1188 with amount 21.37 and credit_type interest_correction. New balance: $18,442.09.

**Agent:** A $21.37 interest correction has posted to your Gold Account savings. Your new balance is $18,442.09.

**Customer:** Out of curiosity, why does only one checking boost apply?

**Agent:** The selection policy exists to ensure customers receive a meaningful benefit for holding premium checking accounts while maintaining sustainable interest rates across the product portfolio.
