# Case J
Channel: chat
QA status: approved

**Customer:** I want to open a Green savings account today, but my checking may be slightly overdrawn.

**Agent:** Overdraft status can be reviewed after verification; share the email on file and your birth date.

**Customer:** priya.shah@icloud.com, November 11, 1987.

**Support console:** Identity verification matched for user_id U-90318. Opening-personal-savings procedure applies.

**Support console:** Calling get_all_user_accounts_by_user_id_3847 with user_id=U-90318. Returned balance values used for eligibility review. Result: CHK-6208, checking, Everyday Checking Account, active, -$42.15, 2019-12-04; SAV-5121, savings, Bronze Savings Account, active, $150.00, 2023-03-18.

**Support console:** Eligibility item failed: account has a negative balance. Balance lookup is essential for determining eligibility for opening new accounts. No collections status or savings-count blocker found.

**Agent:** Your checking balance is negative by $42.15, so the new personal savings account opening cannot proceed today. Please bring the account balance back to at least $0.

**Customer:** Once I cover the $42.15, can I open it?

**Agent:** Once the negative balance is resolved, the account can be reviewed again; all accounts must be in good standing before a personal savings opening may proceed.
