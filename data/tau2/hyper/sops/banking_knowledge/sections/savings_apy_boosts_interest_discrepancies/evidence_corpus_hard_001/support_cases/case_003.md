# Case 003

Case ID: SAV-2510-0331
Channel: Phone
Contact date: 2025-10-24
Handle time: 7m 44s
QA status: Approved — kept as a training sample (2025-11-06, R. Fields)

## Transcript

[00:04] **Agent:** Rho Bank deposit desk, Omar speaking. How can I help?

[00:11] **Customer:** Hi. I'm calling about my savings interest, and fair warning, I've done my homework. The payment on the first is short, and I know why.

[00:26] **Agent:** Homework makes my job easier. Hold the theory while I verify you — the email on your profile and your date of birth?

[00:37] **Customer:** e.kowalski at lindenpost dot com, March 14, 1978.

[00:46] **Support console:** Identity verified, two factors matched. Profile RB-3390517.

[00:51] **Agent:** Thank you, Elaine. Now — the theory.

[00:56] **Customer:** The Purple checking account. I opened it in April, it's supposed to give my Gold savings a lift, and I don't think it ever got hooked in. I sat down Sunday with all my paperwork. Base 5.5, plus 0.75 for my Green checking, plus 0.1 for the Purple, plus the 0.025 for my card — that's 6.375. You paid me $1,288.02 on the first. My number is $1,313.78.

[01:29] **Agent:** That's a precise theory, and I'm going to test it rather than agree with it on the spot. First I'm pulling everything on your profile — not just the Purple account — because I want the whole picture before I commit to a story.

[01:47] **Support console:** get_all_user_accounts_by_user_id_3847 executed for RB-3390517. Returned: Gold Account savings ····8841 (open, good standing); Green Account checking ····2276 (open, good standing, linked); Purple Account checking ····9034 (open, good standing, linked); Gold Rewards Card ····5512 (active, associated with Gold Account).

[01:55] **Agent:** Good news first: everything you named is there. Gold savings, both checking accounts open and linked, card active. Nothing fell off your profile. Next I'm bringing the rate schedule and the Gold sheet up on my second screen — the numbers should come off the page, not out of my head.

[02:17] **Customer:** I have the same pages printed in front of me, so we can race.

[02:23] **Agent:** Then you know what I'm looking at. Both pairings are listed — Green with Gold, Purple with Gold — and the printed lifts are 0.75 for the Green and 0.1 for the Purple. Which is where I have to adjust your arithmetic. When two linked checking accounts both qualify, the schedule applies whichever one gives the savings the bigger lift, and it stops there. The second doesn't pile on. So the right expectation is the 0.75, full stop — the 0.1 never joins it.

[03:01] **Customer:** Huh. So the Purple account does nothing for me?

[03:06] **Agent:** For the savings rate it's the runner-up, and runners-up don't score. What I still owe you is proof the system actually picked the winner — that it's paying the 0.75 and not the 0.1. There's a selection record on my side that shows that choice, account by account. Keep talking while I read it — the accounts, how you use them, anything. I can read and listen at the same time.

[03:34] **Customer:** Alright. The Green account is our household one, that's where the paychecks land. The Purple I opened in April mostly for the travel debit card — we took the kids to Lisbon in June and the no-fee thing paid for itself in a week. Since then it mostly sits, there's maybe nine hundred dollars in it. My husband keeps saying close it, and I keep saying it's free to keep, and lately I've been telling him it's also helping the savings rate, which apparently was never true.

[04:08] **Customer:** I'll also say the Sunday spreadsheet session was his idea of a joke about me. Two checking accounts and one card, and I built a whole workbook with tabs. Omar? Did I lose you?

[04:22] **Agent:** Not for a second — I was reading while you talked. Here's what the record shows. Both accounts were considered for the October payment: Green at 0.75, Purple at 0.1, and the marker is on the Green. The system took the bigger lift, which matches the pages we're both holding. Your Lisbon account is officially innocent.

[04:48] **Customer:** Then why is my interest still wrong? Twenty-five dollars is twenty-five dollars.

[04:56] **Agent:** Because your total wasn't wrong by twenty-five — it was wrong by five. Walk the components with me. With the 0.75 selected, your rate should be the base 5.5, plus 0.75, plus the 0.025 relationship bonus for the card — 6.275. What you were actually paid works out to 6.25 exactly. The gap is precisely the 0.025. Your card is active and associated, but the October payment didn't include its component.

[05:29] **Customer:** So my theory had the wrong suspect.

[05:33] **Agent:** Wrong suspect, real crime. In dollars: at 6.275, the first-of-October payment should have been $1,293.17. You received $1,288.02. That's $5.15 owed to you. The Purple's 0.1 would have been another $20.61 a month, but that was never yours to expect. I'm putting the $5.15 back now.

[05:56] **Support console:** apply_savings_account_credit_6831 executed: account_id ····8841, amount 5.15, credit_type interest_correction. Credit posted. New available balance $248,593.17.

[06:03] **Agent:** Done — it shows as its own line, dated today. Second half of the fix: I'm filing a report so the team behind the calculation finds out why your card's component was dropped and repairs it. The credit squares October; the report is about November.

[06:22] **Support console:** submit_interest_discrepancy_report_7294 executed: account_id ····8841, user_id RB-3390517, expected_apy 6.275, actual_apy 6.25, amount_difference 5.15. Report accepted, backend queue reference returned.

[06:30] **Customer:** And I don't have to chase that myself?

[06:34] **Agent:** No — if the team needs anything, it comes through us. If the November payment still looks off, call and reference this case, but check it against 6.275, not 6.375. Want me to send the schedule and the Gold sheet so the workbook gets rebuilt on the right rate?

[06:53] **Customer:** Please. My husband will never let me hear the end of this.

[07:01] **Agent:** It caught a real $5.15 the system missed — that's a win for the spreadsheet. Anything else today, Elaine?

[07:11] **Customer:** No, that's everything. Thank you for actually checking instead of just agreeing with me.

[07:18] **Agent:** That's the job. Have a good one.

[07:22] **Support console:** Secure message sent: current rate schedule and Gold Account disclosure sheet attached. Case notes: selection record reviewed against the schedule; correction and discrepancy report cross-referenced. Case closed.
