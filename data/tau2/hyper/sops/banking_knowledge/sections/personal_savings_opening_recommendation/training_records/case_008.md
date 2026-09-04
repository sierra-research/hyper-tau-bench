# Case H
Channel: chat
QA status: approved

**Customer:** I opened checking recently and now want a savings account. Can you open one today?

**Agent:** This new-account request needs verification: provide the email tied to your profile and your birth date.

**Customer:** elise.grant@icloud.com, April 16, 1995.

**Support console:** Identity verification matched for user_id U-46017. Opening-personal-savings procedure applies.

**Support console:** Calling get_all_user_accounts_by_user_id_3847 with required user_id=U-46017. Returned date_opened values used for tenure review. Result: CHK-5570, checking, Everyday Checking Account, active, $1,400.00, date_opened 2025-06-19; no personal savings accounts; no collections; no negative balances.

**Support console:** Current processing date 2025-06-27. Active Rho-Bank checking exists, but tenure is 8 days, fewer than the required 14 days. Tenure lookup is essential for determining eligibility for opening new accounts. Other checklist items passed.

**Agent:** The active checking account has been open for 8 days. A personal savings account opening can proceed once the checking account reaches 14 days of tenure, which is July 3, 2025.

**Customer:** So there’s no way to open it today?

**Agent:** Today’s opening is blocked by the 14-day checking tenure requirement, which is not met yet.
