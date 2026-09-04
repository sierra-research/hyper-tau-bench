# Case G
Channel: chat
QA status: approved

**Customer:** I want to open another personal savings account. It should just take a minute, right?

**Agent:** Opening eligibility starts with verification; reply with your account email and date of birth.

**Customer:** devon.miles@outlook.com, January 8, 1982.

**Support console:** Identity verification matched for user_id U-77126. Opening-personal-savings procedure applies. Customer must be verified before proceeding.

**Support console:** Calling get_all_user_accounts_by_user_id_3847 with user_id=U-77126. Returned fields include account_id, account_type, account_class, status, balance, date_opened. Result: CHK-9012, checking, Everyday Checking Account, active, $9,120.00, 2020-05-14; SAV-1001, savings, Bronze Savings Account, active, $600.00, 2021-01-15; SAV-1002, savings, Silver Account, active, $1,800.00, 2021-08-03; SAV-1003, savings, Green Account, active, $900.00, 2022-04-22; SAV-1004, savings, Gold Account, active, $12,000.00, 2023-07-10; SAV-1005, savings, Silver Plus Account, active, $3,200.00, 2024-02-19.

**Support console:** Eligibility item failed: customer already holds 5 personal savings accounts. Account count lookup is essential for determining eligibility for opening new accounts. Other reviewed items do not create an additional blocker.

**Agent:** The profile already has the maximum of 5 personal savings accounts, so a new personal savings account cannot be opened.

**Customer:** Even if I pick Bronze with no deposit?

**Agent:** $0 opening funding does not override the account-count limit. Because the limit is already reached, the opening cannot proceed.
