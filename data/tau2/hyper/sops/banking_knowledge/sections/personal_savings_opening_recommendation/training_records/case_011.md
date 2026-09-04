# Case K
Channel: chat
QA status: approved

**Customer:** I bank here for savings only. Can you open another savings account for me?

**Agent:** Savings-only profiles still need identity verification; provide your Rho-Bank email and full birthdate.

**Customer:** liam.brooks@yahoo.com, July 27, 1990.

**Support console:** Identity verification matched for user_id U-27455. Opening-personal-savings procedure applies.

**Support console:** Calling get_all_user_accounts_by_user_id_3847 with user_id=U-27455. Returned account_type and status values used for eligibility review. Result: SAV-3007, savings, Bronze Savings Account, active, $250.00, 2023-09-14; SAV-3008, savings, Green Account, active, $600.00, 2024-06-01.

**Support console:** Eligibility item failed: no active Rho-Bank checking account found. Step 2 requires confirming that an active checking account exists and meets the tenure requirement. Account-status lookup is essential for determining opening eligibility. No collections or negative-balance blocker found.

**Agent:** Personal savings opening requires at least one active Rho-Bank checking account on your profile. Because there is no active checking account, the savings opening cannot proceed.

**Customer:** But I already have savings accounts there.

**Agent:** Existing savings accounts on the profile do not satisfy the checking-account requirement. The opening can be reviewed again after an active Rho-Bank checking account is on your profile.
