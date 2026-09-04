# Case 002

Case ID: SAV-2511-0114
Channel: Phone
Contact date: 2025-11-06
Handle time: 14m 21s
QA status: Approved — kept as a training sample (2025-11-10, R. Fields)

## Transcript

[00:04] **Agent:** Rho Bank deposit desk, Jess speaking. How can I help?

[00:09] **Customer:** Hi Jess. I've been staring at my savings statement since Saturday and I think the interest is wrong. Not by a lot, but wrong. I did the math three times.

[00:22] **Agent:** Then let's do it a fourth time together, properly. First I need to verify you — the email on your profile and your date of birth, please?

[00:33] **Customer:** t.vasquez at corvidmail dot com. September 3, 1971.

[00:43] **Support console:** Identity verified, two factors matched. Profile RB-2216034.

[00:47] **Agent:** Thank you, Teresa. Tell me what you're seeing.

[00:52] **Customer:** The November first interest posting on my Gold savings. I have the Green checking too, and I have your Gold Rewards Card, and the numbers I get when I add everything up are a little higher than what you paid me. It's maybe ten, twelve dollars. It's not the money, it's that I can't make it reconcile.

[01:15] **Agent:** That's exactly the kind of thing we want to hear about, and there's a proper way we run it down. For context: an interest correction credit is authorized when the customer's interest payment was calculated incorrectly due to a system error, such as a missing APY boost from a linked checking account, an incorrect tier rate, or a missing relationship bonus. So the first question is whether one of your components went missing — and we check that with the account data, not by guessing.

[01:44] **Customer:** Okay. What do you need from me?

[01:48] **Agent:** Nothing but patience for about ten minutes. There are four checks I have to run before I can touch the account, and I'll narrate as I go. First: before applying any interest correction credit, I verify the customer's account details and APY components using get_all_user_accounts_by_user_id_3847 — that shows me everything on your profile that can move the rate.

[02:14] **Support console:** get_all_user_accounts_by_user_id_3847 executed for RB-2216034. Returned: Gold Account savings ····5310 (open, good standing); Green Account checking ····0092 (open, good standing, linked to ····5310); Gold Rewards Card ····7714 (active, associated with Gold Account).

[02:22] **Agent:** Good news at the profile level: the Gold savings, the Green checking with the link intact, and the Gold Rewards Card active and associated. Nothing is missing from the profile itself.

[02:36] **Customer:** So the parts are all there. Then why is the number off?

[02:42] **Agent:** That's what check two is for. Next, I review the transaction history using get_bank_account_transactions_9173 to confirm the interest amount credited — I want the exact figure the platform paid, not the rounded one on the statement summary.

[03:01] **Support console:** get_bank_account_transactions_9173 executed for account ····5310. Interest credit posted 2025-11-01: $2,916.67. Prior cycle interest credit posted 2025-10-01: $2,928.11.

[03:09] **Agent:** So the platform credited $2,916.67 for the October cycle. And interesting — your September cycle credit was actually a touch higher. Balances move, so that alone proves nothing, but it fits your suspicion.

[03:26] **Customer:** That's the number I couldn't hit. My spreadsheet says it should be more like twenty-nine twenty-eight.

[03:35] **Agent:** Let's build it from the documents rather than the spreadsheet. Check three: I calculate the correct interest amount based on documented APY rates and bonuses — the current rate schedule and your product's sheet, nothing from memory. Give me a moment to pull both.

[03:54] **Support console:** Reference pulled: Personal Deposit Rate & Fee Schedule, current issue, and Gold Account disclosure sheet. Component worksheet opened on case.

[04:02] **Customer:** Can I ask something while you're pulling those? When I built my spreadsheet I used the rate off the website, the one on the savings page. Is that not the right number?

[04:14] **Agent:** It's the right number for the day you looked at it — that's the catch. The site shows the rate as of the current day, straight from the pricing system, and deposit rates are variable. For reconciling a whole cycle, we work from the rate schedule and the product sheets, because those are the controlled documents the desk quotes from. If your spreadsheet grabbed the page rate on a Tuesday, it can drift from what the cycle actually paid.

[04:41] **Customer:** So the website is a snapshot and the schedule is the record.

[04:46] **Agent:** Well put — I may steal that. Now, here's your stack, Teresa, straight from those documents. Base rate on the Gold Account, from the schedule's rate table. On top of that, the linked checking boost for your Green checking and Gold savings pairing — the pairing itself is listed in the schedule, and the exact percentage is printed in the product documentation. And on top of both, because your Gold Rewards Card is active and associated with the Gold Account, the relationship bonus from the Gold sheet. Three components, all additive.

[05:21] **Customer:** That's how I built mine. Base, plus the boost, plus the little card bonus.

[05:29] **Agent:** And when I add the documented numbers, your expected rate comes out at 6.275 for the cycle. The platform paid you at 6.25. The difference is exactly the relationship bonus — 0.025 — which means the system dropped that one component when it ran the October interest.

[05:50] **Customer:** So my card bonus fell off.

[05:54] **Agent:** The relationship bonus tied to the card association, yes — the account data says the card is there, but the interest run didn't include its component. Which brings me to check four: I determine the difference between expected interest and actual interest, in dollars. At your expected rate the October credit should have been $2,928.40. You received $2,916.67.

[06:20] **Customer:** So eleven dollars and... seventy-three cents.

[06:25] **Agent:** $11.73, exactly. And now — only now — I'm authorized to fix it, because your situation fits the first circumstance I read you: interest calculated incorrectly due to a system error, in your case a missing relationship bonus.

[06:43] **Support console:** apply_savings_account_credit_6831 executed: account_id ····5310, amount 11.73, credit_type interest_correction. Credit posted. New available balance $561,204.02.

[06:52] **Agent:** Done. There's a credit of $11.73 on your Gold savings as of right now, categorized as an interest correction, and your new balance is $561,204.02. You'll see it as a separate line, not a revised interest posting.

[07:10] **Customer:** I see it in the app already. Okay. But — and I don't mean to be difficult — what stops it from happening again on December first?

[07:21] **Agent:** The right question, and it's the other half of my job on this call. For interest corrections, after applying the credit, the agent should also submit an interest discrepancy report using submit_interest_discrepancy_report_7294 so the backend team investigates and fixes the underlying issue. The credit makes you whole today; the report is what makes December run correctly.

[07:46] **Customer:** So there's an actual engineering ticket behind it, not just my refund.

[07:52] **Agent:** Exactly. I file it with your account, your expected rate, the rate that was actually applied, and the dollar difference, and the backend team picks it up from there. Filing it now.

[08:06] **Support console:** submit_interest_discrepancy_report_7294 executed: account_id ····5310, user_id RB-2216034, expected_apy 6.275, actual_apy 6.25, amount_difference 11.73. Report accepted, backend queue reference returned.

[08:14] **Agent:** Filed. If the backend needs anything from you, they come through us, not to you directly.

[08:22] **Customer:** Great. While I have you — my husband has one of the eco cards, the green one with the tree. Would his card have added anything to my rate? Because if we're stacking bonuses I want them all.

[08:37] **Agent:** Only cards under the same customer profile count. His card sits on his profile, so it doesn't touch your Gold Account. And even on one profile, when several cards are eligible, only the highest single card bonus applies — they don't add together. The per-card numbers for each savings product are on that product's sheet, and honestly they differ more between products than people expect.

[09:04] **Customer:** So no card-collecting strategy.

[09:08] **Agent:** Not for the savings rate, no. The combination that matters is the one you already have, and now every component of it is actually paying.

[09:19] **Customer:** Alright. Since you clearly enjoy this — sanity-check two more lines in my spreadsheet? Quick ones.

[09:27] **Agent:** Go ahead.

[09:30] **Customer:** One. If I moved say forty thousand out of the Gold account mid-month, does the whole month earn less, or just the days after the money leaves?

[09:41] **Agent:** Interest on these accounts accrues on the daily balance, so each day earns on what's actually there that day. Moving money out mid-cycle only affects the days after it leaves. Your statement's interest line is the sum of all those daily accruals, which is why hand math on a moving balance gets fiddly.

[10:02] **Customer:** That explains a lot about my spreadsheet, honestly. Two. The card thing — if my Gold Rewards Card ever gets replaced, like after fraud, does the bonus fall off while the new card ships?

[10:15] **Agent:** A straight replacement keeps the same card account, so the association with your Gold Account carries over and the bonus continues. What matters is that the card account stays active and associated — a replacement plastic doesn't change that. If a card is actually closed and reopened, that's different, and worth a call like this one.

[10:37] **Customer:** Okay. I officially have no complaints left.

[10:42] **Agent:** Then let me wrap up so you have it in one piece. Your interest was calculated incorrectly because the relationship bonus component was dropped by the system. I verified your accounts and components, confirmed the credited amount from the transaction history, recalculated from the documented rates, and took the difference. You've been credited $11.73 as an interest correction, and I submitted the discrepancy report so the backend team investigates and fixes the underlying issue before your next cycle.

[11:14] **Customer:** And if December first is wrong anyway?

[11:18] **Agent:** Then you call us, reference this case, and it gets escalated with the open report attached — you wouldn't be starting over. But watch your account details screen over the next few days; once the backend closes the fix, the components all show correctly there.

[11:36] **Customer:** Will do. One more thing — I spent my whole Sunday afternoon on this. On principle, is that worth some kind of... goodwill gesture? My neighbor said you gave her a credit once when her card got double-charged.

[11:52] **Agent:** I understand the impulse, and we do have goodwill credits — but they're for exceptional circumstances, where a bank error caused significant inconvenience beyond the money itself, and they're deliberately rare. What happened here is a calculation error that we've now corrected to the penny, plus a report to stop it recurring. I wouldn't be able to justify goodwill on top of that, and I'd rather be straight with you than promise something a supervisor would reverse.

[12:23] **Customer:** Fair enough. Honestly the eleven dollars was never the point.

[12:29] **Agent:** For what it's worth, your three-times-checked spreadsheet was right, and that's what made this fast. Anything else while I have you, Teresa?

[12:39] **Customer:** Yes, actually. Can you send me whatever document has my product's numbers in it? If I'm going to keep a spreadsheet, I want it fed from the real thing.

[12:50] **Agent:** Sending the Gold Account sheet and the current rate schedule to your secure inbox now. Between those two, every component of your rate is in writing — and if the two ever look different to you, call us rather than picking one.

[13:07] **Customer:** Perfect. That's everything.

[13:11] **Agent:** Thanks for your patience with the checks, Teresa. Have a good afternoon.

[13:18] **Support console:** Secure message sent: Gold Account disclosure sheet and current rate schedule attached. Case notes: component worksheet attached; credit and discrepancy report cross-referenced. Case closed.
