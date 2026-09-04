# Case 009

Case ID: SAV-2511-0301
Channel: Phone
Contact date: 2025-11-11
Handle time: 6m 4s
QA status: Approved

## Transcript

[00:03] **Agent:** Rho Bank deposit desk, Omar speaking.

[00:07] **Customer:** Hi Omar. I'd like to talk about the eleven days I just spent waiting on a correction your bank promised me on October thirtieth. Also the three callbacks your bank promised and the zero calls it made. I have dates. Want them before or after you verify me?

[00:22] **Agent:** After, so they're official. Email on your profile and your date of birth, please.

[00:29] **Customer:** s.ferreira at brightmail dot com. July 30, 1988.

[00:37] **Support console:** Identity check passed on both factors. Profile RB-5527163. Accounts: Silver Account savings ····3349; Green Account checking ····8814. Open service history: duplicate bill-payment debit reported 2025-10-30.

[00:42] **Agent:** Thank you, Simone. I have the case history up. Give me your version anyway — I'd rather hear it than read it.

[00:50] **Customer:** October thirtieth, my utility autopay ran twice — two hundred eighteen dollars and forty cents, taken out two times. Your colleague agreed same day it was the bank's processing error, said the correction would post in a day or two and someone would call to confirm. Nothing posted, nobody called. Saturday my rent autopay bounced because the second debit ate my cushion — thirty-five dollar returned-payment fee from my landlord, my pocket. I called that Monday: escalation promised, callback promised. Silence. Called again Friday: another promised call. Silence. The reversal finally showed up last night. Eleven days, Omar, for money you agreed was mine on day one — and I only ever learned anything by dialing this number myself.

[01:41] **Agent:** Let me confirm the money, then we talk about the rest. Checking now.

[01:48] **Support console:** get_bank_account_transactions_9173 executed for account ····8814. 2025-10-30: bill-payment debit $218.40 posted twice, second instance flagged processing error same day. 2025-11-01: external autopayment returned unpaid. 2025-11-10: reversal credit $218.40 posted, eleven days after flag.

[01:54] **Agent:** Your account of it matches the record exactly, and I'm not going to dress it up. Our error, acknowledged in the first hour on October thirtieth. The correction sat unposted for eleven days. Three callback commitments — the thirtieth, the third, the seventh — none kept. And in the middle, your rent bounced and cost you thirty-five dollars. We made a mistake, then made you chase it for a week and a half.

[02:24] **Customer:** Thank you. That sentence is most of what I wanted. The fee still stings, though. Rent is not where I like surprises.

[02:33] **Agent:** So here's what I'd like to do: a forty-dollar goodwill credit on your Silver savings. Sized, not plucked — thirty-five is the fee our error cost you at your landlord's, and the rest acknowledges eleven days of chasing that should have been one call. Mechanics, honestly: my own signature stops at twenty-five, and twenty-five wouldn't even cover your landlord's fee — an insult with a bow on it. So forty goes to my supervisor with my write-up attached, recommended in the strongest wording the form allows.

[03:07] **Support console:** apply_savings_account_credit_6831 submitted: account_id ····3349, amount 40.00, credit_type goodwill_credit. Amount exceeds desk authorization threshold of $25.00 — queued pending supervisor approval, routed to C. Mercer with case summary attached. Credit not yet posted.

[03:14] **Customer:** So it's not actually on my account yet.

[03:18] **Agent:** Not yet, and I won't pretend otherwise. It's in Colin Mercer's queue as of this minute. You'll see it post once my supervisor signs off, likely tomorrow.

[03:29] **Customer:** You understand I now have callback trauma. The last three times someone said "you'll hear from us," I aged a year.

[03:37] **Agent:** Which is why I'm not promising a call — I'm promising a deposit. Check your app tomorrow morning instead of your voicemail. If it isn't there by end of day, call and reference this case, and it lands on my desk, not the queue.

[03:53] **Customer:** A deposit instead of a promise. You may be my favorite person at this bank. Low bar this week.

[04:01] **Agent:** The bar is on the floor, I know. For the record: the reversal side is closed — duplicate, flag, credit back, all documented. Open items are the forty pending approval, and a note I'm adding about the eleven days, because that gap will interest people here beyond me.

[04:19] **Customer:** Good. Do you need the landlord fee receipt?

[04:24] **Agent:** I've noted it as you described, and that's enough. Keep it in case anyone upstream asks; I don't expect them to.

[04:33] **Customer:** Then we're done, assuming tomorrow goes the way you say.

[04:39] **Agent:** It should. Thank you for giving us the chance to fix it instead of walking. Anything else, Simone?

[04:47] **Customer:** No. Just tell whoever runs the callback system that it's decorative.

[04:53] **Agent:** Going in the case, word for word. Take care.

[06:04] **Support console:** Case notes recorded: correction acknowledged 2025-10-30, posted 2025-11-10 — eleven days unposted; callback commitments 10-30, 11-03, 11-07 all missed; external returned-payment fee $35 reported. Goodwill $40.00 sized against out-of-pocket fee plus service failure; $25.00 desk limit insufficient to cover documented cost. Pending supervisor approval (C. Mercer). Case closed pending credit posting; no callback scheduled per customer preference.
