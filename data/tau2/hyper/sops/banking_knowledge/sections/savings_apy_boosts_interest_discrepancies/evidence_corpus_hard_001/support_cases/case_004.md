# Case 004

Case ID: SAV-2510-0352
Channel: Phone
Contact date: 2025-10-27
Handle time: 6m 4s
QA status: Approved — kept as a training sample (2025-11-06, R. Fields)

## Transcript

[00:04] **Agent:** Thanks for calling Rho Bank, this is Ana on the deposit desk. How can I help you today?

[00:11] **Customer:** Oh good, a person. Hello, Ana. It's nothing urgent — I have a savings account and two checking accounts with you, and I opened the second checking account back in September because my granddaughter said it would bump my savings rate up. But the rate never moved. I've been watching it since, and it just sits there.

[00:35] **Agent:** Then let's find out together whether something is stuck. I need to verify you first — could you give me the email address on the profile, and your date of birth?

[00:47] **Customer:** It's r.delgado at quiltbox dot net. And June 2, 1954.

[00:57] **Support console:** Identity verified, two factors matched. Profile RB-5583927.

[01:02] **Agent:** Perfect, thank you, Ruth. Give me a moment to lay out everything you hold with us, so neither of us is guessing.

[01:11] **Support console:** get_all_user_accounts_by_user_id_3847 executed for RB-5583927. Returned: Gold Account savings ····7302 (open, good standing); Green Account checking ····1148 (open, good standing, linked); Purple Account checking ····6613 (open, good standing, linked).

[01:19] **Agent:** So the first bit of good news: your setup is exactly right. The Gold savings is there, your Green checking is linked to it, and the Purple checking you opened in September is open and linked too. Nothing is stuck or half-finished.

[01:36] **Customer:** Then why didn't my rate move when the Purple one came in? I was promised a bump.

[01:44] **Agent:** That's the right question, and I want to answer it with the actual numbers rather than from memory, so I'm opening the rate schedule now. One second... here we are. For a Gold savings account, your Green checking carries a lift of 0.75, and the Purple carries 0.1. Both of your pairings are on the list, both accounts linked — so with the Green adding 0.75 and the Purple adding 0.1, you should be earning an extra 0.85 over your base rate.

[02:19] **Customer:** And am I?

[02:22] **Agent:** Let me check what was actually paid instead of assuming. I'm pulling the interest line from your transaction history now.

[02:32] **Support console:** get_bank_account_transactions_9173 executed for account ····7302. Interest credit posted 2025-10-01: $968.75.

[02:38] **Agent:** Here it is. On the first of October you were credited $968.75. When I work that backwards it matches a rate of 6.25 — which is your 5.5 base plus the Green account's 0.75, and nothing else. Ruth, I think you've caught something real. The Purple account's 0.1 isn't in your number. At the full 6.35 your October interest should have been $984.25, so you're $15.50 short.

[03:08] **Customer:** Well. My granddaughter is going to be unbearable about this.

[03:14] **Agent:** As she's earned. Here's what I'm doing about it, in order. First, the $15.50 goes back on your account right now — you shouldn't wait on anyone's investigation to be made whole.

[03:28] **Support console:** apply_savings_account_credit_6831 executed: account_id ····7302, amount 15.50, credit_type interest_correction. Credit posted. New available balance $186,984.25.

[03:35] **Agent:** That's done — you'll see it as its own line, dated today. Second, I'm sending a report to the team that runs the interest calculation, with your numbers in it, so they can fix whatever kept the Purple account's lift out of the math. The credit puts October right; the report is so November comes out right on its own.

[03:57] **Support console:** submit_interest_discrepancy_report_7294 executed: account_id ····7302, user_id RB-5583927, expected_apy 6.35, actual_apy 6.25, amount_difference 15.50. Report accepted, backend queue reference returned.

[04:05] **Customer:** You're very quick. At my last bank this would have been three phone calls and a letter.

[04:13] **Agent:** We do try to finish things on the first call. While I have you in here — anything else that's been nagging at you?

[04:22] **Customer:** One small thing. The Purple account — I only keep a little in it, a few hundred dollars for birthday presents. Does the lift care how much money sits in the checking account?

[04:36] **Agent:** No — what matters is that the account is open, in good standing, and linked to the savings, and yours is all three. The lift applies to your savings balance, not the checking balance, so a quiet Purple account is pulling its weight just fine.

[04:53] **Customer:** Good. It buys the birthday presents and now it earns its keep too. And will I see the correction on my paper statement as well?

[05:00] **Agent:** You will — the next statement shows today's $15.50 as an interest correction, its own labeled line, and from November the interest line should carry the full rate on its own. If next month's number still looks flat to you, call us and mention this case, and whoever answers can pick it straight up without you re-explaining anything.

[05:19] **Customer:** I'll make a note on the calendar. You've been lovely, Ana.

[05:25] **Agent:** It was genuinely a pleasure, Ruth. And credit where it's due — you watched your rate for a month and then did something about it. Most people never check. Anything else today?

[05:38] **Customer:** No, that's everything. Tell your manager you were wonderful.

[05:44] **Agent:** I'll let the recording do that for me. Take care, Ruth.

[05:50] **Support console:** Case notes: interest shortfall corrected and discrepancy report filed; customer advised to monitor next cycle. Case closed.
