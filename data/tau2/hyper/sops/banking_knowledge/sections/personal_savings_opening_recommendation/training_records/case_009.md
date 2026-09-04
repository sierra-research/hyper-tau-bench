# Case I
Channel: chat
QA status: approved

**Customer:** I need a new savings account, but one of my older accounts might have a problem. Can you check?

**Agent:** Secure account review needs two details: your profile email and date of birth.

**Customer:** marcus.reed@outlook.com, September 5, 1979.

**Support console:** Identity verification matched for user_id U-18593. Opening-personal-savings procedure applies.

**Support console:** Calling get_all_user_accounts_by_user_id_3847 with user_id=U-18593. Returned status values used for eligibility review. Result: CHK-3304, checking, Everyday Checking Account, active, $2,250.00, 2021-03-12; SAV-7710, savings, Bronze Savings Account, active, $300.00, 2022-10-01; LOAN-4430, account_type loan, Personal Loan Account, collections, $780.00, 2020-06-08.

**Support console:** Eligibility item failed: account status shows collections activity. Account-status lookup is essential for determining eligibility for opening new accounts. No separate negative-balance or savings-count blocker found.

**Agent:** A collections status appears on one account, so a new personal savings account cannot be opened right now. The collections issue must be resolved first, and opening can proceed only after all accounts are in good standing.

**Customer:** If I choose a small account, does that change it?

**Agent:** A smaller savings product does not change this eligibility requirement. The opening cannot proceed until the collections issue is resolved and all accounts are in good standing.
