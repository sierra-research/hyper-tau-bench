# Case Y
Channel: chat  
QA status: approved

**Customer:** The bank error last week kept me from using my savings transfer when I needed it. Someone said a goodwill credit might be possible.

**Agent:** Goodwill-credit eligibility needs identity verification first. Please provide your email address and date of birth.

**Customer:** claire.evans@icloud.com, February 28 1978.

**Support console:** Identity verified and account ownership confirmed. get_all_user_accounts_by_user_id_3847 returned Platinum Account savings SAV-PLAT-4480. Account confirmed as savings. Internal review confirms significant inconvenience caused by bank error. Eligible savings credit categories are interest corrections, fee refunds, and goodwill credits. Goodwill credits may be applied only in exceptional circumstances due to bank error; they should be rare and typically require supervisor approval for amounts over $25. Proposed goodwill credit amount: $30.00. Supervisor approval recorded. apply_savings_account_credit_6831 requires account_id string, positive amount greater than 0, and credit_type interest_correction, fee_refund, or goodwill_credit.

**Agent:** This situation qualifies for a rare goodwill credit due to the bank error, and the $30.00 amount has the required approval. Please reply yes if you want me to apply the $30.00 goodwill credit to your Platinum Account savings now.

**Customer:** yes

**Support console:** apply_savings_account_credit_6831 completed with account_id SAV-PLAT-4480, amount 30.00, credit_type goodwill_credit. New balance: $22,130.55.

**Agent:** A $30.00 goodwill credit has been added to your Platinum Account savings, and your new balance is $22,130.55.
