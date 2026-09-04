# Case 008

Case ID: SAV-2511-0157
Channel: Phone
Contact date: 2025-11-07
Handle time: 5m 12s
QA status: approved

## Transcript

[00:04] **Agent:** Rho Bank deposit desk, Omar here. How can I help?

[00:09] **Customer:** Morning. Marcus Doyle. I've got a meeting in ten minutes so I'll be quick: my savings interest came in a dollar light this month and I'd like it looked at. It's not about the dollar, it's that I don't like drift.

[00:24] **Agent:** Quick works for me. Verification first — the email on the profile and your date of birth — and then I'm straight into the ledger.

[00:33] **Customer:** m.doyle at averline dot com, October 12, 1969. Go.

[00:42] **Support console:** Identity verified, two factors matched. Profile RB-1147206.

[00:46] **Agent:** Pulling your profile and the interest lines side by side. Tell me what you saw while I read.

[00:53] **Customer:** Simple. I reconcile the house accounts on the first of every month, and I keep that savings parked at 48 even — the interest gets swept out to checking mid-month, the balance itself never moves. October first you paid me $221 flat. November first, $220 flat. Same money in the account. The dollar went somewhere.

[01:15] **Support console:** get_all_user_accounts_by_user_id_3847 executed for RB-1147206. Returned: Gold Account savings ····3327 (open, good standing); Gold Rewards Card ····8265 (active, associated with Gold Account).

[01:21] **Support console:** get_bank_account_transactions_9173 executed for account ····3327. Interest credit posted 2025-11-01: $220.00. Interest credit posted 2025-10-01: $221.00. Standing monthly sweep to checking confirmed.

[01:27] **Agent:** Your ledger agrees with you to the penny: $221.00 on October first, $220.00 on November first. And your profile tells me where the dollar lives. You hold the Gold savings and a Gold Rewards Card, active and tied to it — and while that card stays active and associated, the savings account gets a small extra rate component on top of its base.

[01:50] **Customer:** The point-oh-two-five thing. It's in the brochure.

[01:54] **Agent:** That's the one, and I've got the Gold sheet open here rather than trusting either of our memories: 5.5 base, plus the 0.025 relationship bonus, 5.525 together. Now the arithmetic, and on your account it's unusually tidy. The monthly payment is one-twelfth of the yearly rate on the balance — so month length never comes into it. A twelfth of 5.525% on your $48,000 is exactly $221.00. A twelfth of the bare 5.5 is $220.00. October included the bonus. November didn't. Your card didn't change — I'm looking at it, it's active — so the November run dropped a component it should have kept.

[02:36] **Customer:** So put the dollar back and tell me it won't drift again.

[02:42] **Agent:** Both, in that order. Dollar first.

[02:47] **Support console:** apply_savings_account_credit_6831 executed: account_id ····3327, amount 1.00, credit_type interest_correction. Credit posted. New available balance $48,221.00.

[02:53] **Agent:** Credited — it shows as an interest correction line dated today, so your reconciliation has something to tie to. Second: this doesn't get to become a monthly ritual, so I'm filing a report with the team that owns the calculation. It goes in under missing relationship bonus, with the rate you should be getting and the rate you got, and they trace why the November run left it out.

[03:16] **Support console:** submit_interest_discrepancy_report_7294 executed: account_id ····3327, user_id RB-1147206, expected_apy 5.525, actual_apy 5.5, amount_difference 1.00. Report accepted, backend queue reference returned.

[03:24] **Customer:** Good. December first — do I check it myself or does somebody do that for me?

[03:31] **Agent:** Check it — it'll take you ten seconds, since your balance never moves. It should read $221.00 again. If it comes in at $220.00, call and give this case number, and it escalates with the open report attached instead of starting over from a fresh ticket.

[03:48] **Customer:** What's the case number?

[03:51] **Agent:** SAV-2511-0157. It'll also be in the secure message I'm sending you now, along with the Gold sheet, so you've got the components in writing: 5.5 base, 0.025 bonus, 5.525 together, $221.00 a month at your balance.

[04:06] **Customer:** Fine. Wait — one more. Was October itself right? And September? If November drifted, maybe it wasn't the first time.

[04:16] **Agent:** Asked and already checked while we talked: every posting from September back is $221.00 on the nose. November first is the only light one, and it's now corrected. You're square.

[04:29] **Customer:** Then we're done. That was faster than my coffee order this morning.

[04:35] **Agent:** We aim to beat the coffee. The message with the sheet and the case number is in your inbox. Anything else in your last five minutes?

[04:44] **Customer:** No. Appreciated. Bye.

[04:48] **Support console:** Secure message sent: Gold Account disclosure sheet attached, case reference included. Case notes: correction and discrepancy report cross-referenced. Case closed.
