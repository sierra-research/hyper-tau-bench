# Case 002

Case ID: OPN-2511-0361
Channel: Phone
Contact date: 2025-11-06
Handle time: 9m 47s
QA status: Approved — kept as a training sample (2025-11-10, R. Fields)

## Transcript

[00:04] **Agent:** Rho Bank new-accounts desk, Omar speaking. How can I help you today?

[00:11] **Customer:** Hi Omar. Two things. I opened a Platinum savings account with you last week, and the welcome packet says someone should walk me through it. And I have a genuinely time-sensitive question about getting a large payment out of it.

[00:32] **Agent:** A walkthrough and a deadline — my whole job in one call. Verification first: the email on your profile and your date of birth, please.

[00:42] **Customer:** p.raman at oakfieldpost dot com. March 14, 1972.

[00:48] **Support console:** Identity verified, two factors matched. Profile RB-5580216.

[00:56] **Agent:** Thank you, Priya. Let me pull up the full picture before either of us says anything clever.

[01:05] **Support console:** get_all_user_accounts_by_user_id_3847 executed for RB-5580216. Returned: Platinum Account savings ····9042 (open, good standing); Green Account checking ····7731 (open, good standing).

[01:12] **Agent:** There you are — the new Platinum Account and your Green checking, both in good standing. And the savings itself —

[01:24] **Support console:** get_bank_account_transactions_9173 executed for account ····9042. Opening deposit posted 2025-10-30: $120,000.00. No further activity. Current balance $120,000.00.

[01:30] **Agent:** — funded on day one with $120,000 and untouched since. You've done the easy parts already. Tell me about the time-sensitive thing.

[01:41] **Customer:** We're closing on a house at the end of the month. When escrow calls for it, the title company needs $95,000, and they need it the same day. My realtor keeps chanting "wire, wire, wire." Is she right, or is there something smarter from a savings account?

[02:03] **Agent:** For a time-sensitive disbursement like a closing, she's right: a domestic wire is worth considering, and on your Platinum account it's an easy call — the wire fees are waived, and settlement is typically faster than a standard external transfer. Standard transfers are fine for money that can wait. Escrow money usually can't.

[02:29] **Customer:** Good. What do I need to be careful about? My realtor also forwarded me a horror story about wire fraud.

[02:39] **Agent:** Then she's earned her commission twice. Here's the rule I will say twice because it matters: always confirm the recipient details before the wire goes — the exact account name, account number, and routing number, straight from the title company's written instructions — because wires generally cannot be reversed. Once it settles, there is no quiet undo on my side.

[03:08] **Customer:** And the horror-story scenario — instructions changing by email at the last minute?

[03:15] **Agent:** Treat changed instructions as false until proven otherwise. Verify by calling the title company at a number you already trust, never one printed in the surprise email. And when the real instructions arrive, call us and we'll go through every digit together before anything moves.

[03:35] **Customer:** Okay. Now the part I'm actually losing sleep over. After $95,000 walks out the door, what happens to the account it leaves behind?

[03:49] **Agent:** Let's do that arithmetic out loud. You're at $120,000 today. The wire takes $95,000, which leaves $25,000 — and that's well below the balance this account is built to sit at, so it deserves a plan rather than a shrug.

[04:06] **Customer:** I might have a plan. There's a certificate of deposit at my old bank — about $45,000 — maturing right around the closing. Honestly, I was going to leave it there out of inertia.

[04:23] **Agent:** Inertia is expensive this month. This is the textbook case: when you know a large withdrawal is coming, timing an additional deposit around it keeps the required balance intact and avoids the $25.00 charge entirely. Land the $45,000 here before the wire goes out — or as close behind it as you can manage — and instead of sitting at $25,000 you're at $70,000, and the fee conversation never happens.

[04:55] **Customer:** And if the timing slips? Escrow dates wander. CDs mature when they mature.

[05:01] **Agent:** Then don't guess — let the account watch itself. Setting balance alerts is the cheap insurance here: an alert pings you the day the balance dips, and it helps you stay above $50,000 without checking the app every morning.

[05:21] **Customer:** Can you set that up while we're on the phone?

[05:28] **Agent:** You'll have it live before we hang up — it's yours to set, in the app under Alerts, then balance threshold. Open it and I'll navigate with you. Pick the amount you want to be warned at, confirm, and that's the whole ceremony.

[05:49] **Customer:** Done. It says the alert is active.

[05:53] **Support console:** Customer self-service action observed: balance alert created on Platinum Account savings ····9042, threshold set by customer. No agent-side account changes.

[06:01] **Agent:** Confirmed on my side too. That's your backstop — the deposit timing is still the actual plan.

[06:10] **Customer:** The welcome letter kept mentioning a "dedicated personal banker." Is that a person, or a chatbot with a nice name?

[06:20] **Agent:** A person. A dedicated personal banker comes with the Platinum Savings Account — yours is already assigned, and the introduction is sitting in your secure messaging inbox with the welcome materials.

[06:36] **Customer:** What would I actually use them for that you can't do right now?

[06:44] **Agent:** Continuity, mostly. Within secure messaging you can request tailored support for complex transactions or financial planning — and a closing, a same-week deposit from a maturing CD, and a keep-the-balance-up constraint is exactly the kind of braided problem you hand to one person instead of re-explaining to whoever answers the phone.

[07:07] **Customer:** Will they check in on me, or do I have to remember they exist?

[07:16] **Agent:** Your call. You can ask for proactive account check-ins or portfolio reviews, tuned to your preferences — quarterly, annually, or never — and they run at whatever rhythm you set. Some Platinum customers want a standing review; some want radio silence and one fast answer a year.

[07:36] **Customer:** Quarterly sounds civilized. Last thing — the rate. The welcome letter has a number in it. Do I memorize it, frame it, what?

[07:48] **Agent:** Neither — never trust a rate from memory, including mine. The Platinum profile sheet carries the current terms, and I'll send it to your secure inbox after this call. Your account details screen shows what the account is actually earning on any given day — paper for planning, screen for truth.

[08:12] **Customer:** Alright. Recap me, Omar. I want to hear the plan back in one piece.

[08:19] **Agent:** The plan: when escrow calls for it, the $95,000 goes by domestic wire — the right tool for time-sensitive money on this account. Before it goes, we confirm the recipient details together, digit by digit, against the title company's written instructions. The $45,000 from your maturing CD lands here around the same time, ideally first, so the balance stays where it belongs and the timing does the work. Your new alert is the backstop. And the whole plan goes into your secure-messaging thread with your banker today, so it lives somewhere better than both our memories.

[09:05] **Customer:** You've talked me off the ledge. Thank you.

[09:11] **Agent:** That's the job. Anything else while I have you, Priya?

[09:17] **Customer:** No — I'll write to the banker this afternoon.

[09:22] **Agent:** Perfect. Congratulations on the house, and call us before that wire moves.

[09:30] **Support console:** Secure message sent: Platinum Savings Account profile sheet attached; call summary shared to the customer's personal-banker thread in secure messaging. Case notes: wire guidance, deposit-timing plan, and alert setup documented. Case closed.
