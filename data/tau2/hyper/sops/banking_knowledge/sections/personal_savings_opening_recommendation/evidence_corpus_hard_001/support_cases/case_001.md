# Case 001

Case ID: OPN-2511-0339
Channel: Phone
Contact date: 2025-11-04
Handle time: 8m 19s
QA status: Approved — kept as a training sample (2025-11-05, R. Fields)

## Transcript

[00:04] **Agent:** Rho Bank deposit desk, Ana here. What can I do for you?

[00:11] **Customer:** Hi. I'd like to open a savings account. I've had my checking with you for a while now, and I keep promising myself I'll start putting something aside. Today I'm actually doing it.

[00:29] **Agent:** Then let's not give you time to reconsider. Quick verification first — can I get the email on your profile and your date of birth?

[00:41] **Customer:** It's f.aguirre at lumenmail dot com, and June 2, 1987.

[00:46] **Support console:** Identity verified, two factors matched. Profile RB-3095471. Accounts on profile: Purple Account checking ····6120 (open, good standing, opened 2023-05-12). No savings accounts on profile.

[00:54] **Agent:** Thanks, Felix. Tell me what you're picturing — a fixed chunk you park and forget, or something you'll feed a little at a time?

[01:07] **Customer:** A little at a time. I want to start small — a couple hundred dollars from my paycheck — and build the habit before I get ambitious. And I don't want an account that punishes me while the balance is still tiny.

[01:28] **Agent:** Then the Bronze Savings Account is the one to look at — it's our starter tier, and it's built for exactly the pattern you just described. The current terms are printed on its profile sheet, and I'll send that to your secure inbox after the call, so you have the numbers in writing instead of my paraphrase. Sound right?

[01:55] **Customer:** Sounds right. Let's do the Bronze.

[01:59] **Agent:** One moment while I run the eligibility screen — standard for any new savings account.

[02:07] **Support console:** Eligibility screen run for RB-3095471: identity verification, active checking relationship, checking tenure, personal savings account count, collections, negative balances — all items pass.

[02:15] **Agent:** All items pass, no surprises. Confirming the selection back to you before I open anything: one Bronze Account, in your name, on this profile. Yes?

[02:29] **Customer:** Yes. Bronze it is.

[02:32] **Support console:** open_bank_account_4821 executed: user_id RB-3095471, account_type "savings", account_class "Bronze Account". New account ····5217 created, status open, funding_status unfunded.

[02:40] **Agent:** And it's open — your new Bronze Account ending 5217, live as of this minute. Which brings me to the question I ask everyone at exactly this moment: would you like the opening deposit transferred over from your checking account now?

[03:00] **Customer:** Ah. Can I say not yet? My paycheck lands Friday, and checking is running thin until then. I'd rather move the money once it clears than cut it close today.

[03:14] **Agent:** You can absolutely say not yet. For the record, if you'd said yes, I'd run it right here with transfer_funds_between_bank_accounts_7291 — it pulls the amount from your checking and lands it in the newly opened savings while we're still talking. Since you're deferring, the funding just happens on your schedule instead.

[03:40] **Customer:** And there's no catch to waiting?

[03:45] **Agent:** A clock, not a catch. You have 30 days to fund the account, and two ways to do it: an internal transfer from your Rho checking, or an external deposit from an account at another bank — either one counts.

[04:05] **Customer:** When does the clock start? Today, or when some paperwork settles somewhere?

[04:13] **Agent:** Today. Day one is the day the account is opened, which was about ninety seconds ago. So if you fund it this Friday, you'll be on day four of the 30 — my favorite kind of margin.

[04:30] **Customer:** Good. And the external option — how does that work if the rest of my money is at a credit union?

[04:41] **Agent:** From their side, you push the money to this account. The routing and account numbers are on your account details screen in the app, under the new Bronze. It counts exactly the same as an internal move — the money just takes the scenic route.

[05:02] **Customer:** Okay. And if life happens and I blow past the deadline anyway?

[05:09] **Agent:** Then the account doesn't linger around empty — if it isn't funded within the 30-day window, it will be closed. That part is automatic at the deadline, not a judgment call, so don't leave it for the last afternoon.

[05:28] **Customer:** Understood. Thirty days or it closes — and Friday-me has exactly one job.

[05:36] **Agent:** That sentence is going in your file, nearly word for word. When someone defers funding, I document the acknowledgment in the interaction notes — that you heard the window and what happens if it lapses. Give me two seconds.

[05:56] **Support console:** Interaction notes updated: customer acknowledged the 30-day funding window and the closure consequence; funding deferred at customer's request.

[06:02] **Customer:** You really keep notes on that?

[06:08] **Agent:** On that specifically, yes. If the account ever comes up again, the notes show you heard the deadline from a person, not a pamphlet. It protects you as much as it protects us.

[06:24] **Customer:** Fair. It's meant to be an emergency fund, mostly — my car has opinions about my savings rate.

[06:33] **Agent:** Then future-you is already grateful. Emergency money is the best first habit — boring right up until it's the only interesting thing in your month.

[06:48] **Customer:** One more thing — does this account earn anything meaningful, or is it a ceramic pig with a logo?

[06:58] **Agent:** It earns — and the exact Bronze numbers are on the profile sheet headed to your inbox, which beats me reciting figures from memory. Read it tonight; it's one page.

[07:12] **Customer:** Deal.

[07:15] **Agent:** Recap and I'll let you go. New Bronze Account ending 5217 — open, currently unfunded. You have 30 days to fund it, internal transfer or external deposit, and your acknowledgment of the window and the closure rule is on file. Friday, the app's transfer screen will do it in under a minute — or call us and one of us will run it with you.

[07:45] **Customer:** Perfect. Thanks, Ana — this was less painful than the gym.

[07:53] **Agent:** That's the bar I aim for. Anything else today?

[07:59] **Customer:** No, that's everything.

[08:02] **Agent:** Go start the habit, Felix. Take care.

[08:06] **Support console:** Secure message sent: Bronze Savings Account profile sheet attached. Case closed, no follow-up needed.
