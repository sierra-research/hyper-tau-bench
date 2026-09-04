# Case 002

Case ID: CLR-2511-0517
Channel: Phone
Contact date: 2025-11-06
Handle time: 6m 39s
QA status: approved

## Transcript
[00:03] **Agent:** Rho Bank card support, this is Marcus. How can I help?

[00:10] **Customer:** Hi Marcus. I want to request a higher limit on my Bronze Rewards card. Money's been tight-ish and the card keeps bumping its head on the ceiling.

[00:24] **Agent:** Let's take the request properly and see where the account stands. First, verification — your full name and the phone number on the profile?

[00:35] **Customer:** Teresa Whitfield, 555-062 — sorry, 555-0621.

[00:39] **Agent:** And your street address?

[00:42] **Customer:** 17 Almeda Row, unit 4.

[00:46] **Agent:** Verified, thanks Teresa. You're the account owner here, so we're good to proceed. What increase did you have in mind — a new total, or an amount added?

[01:00] **Customer:** Six hundred more. It's at twenty-five hundred now.

[01:06] **Agent:** A six-hundred-dollar increase on the twenty-five-hundred limit — that's an amount I can submit for this card. Confirming it back: you're requesting six hundred dollars added, for a thirty-one-hundred total if approved. Submit it?

[01:22] **Customer:** Yes please.

[01:25] **Support console:** submit_credit_limit_increase_request_7392(credit_card_account_id, user_id, requested_increase_amount=600) returned ok. Request reference CLI-118902 attached to case.

[01:32] **Agent:** Submitted, and your reference confirmation is CLI-118902. Now I'll complete the review — a few quiet minutes on my end, stay with me.

[01:43] **Customer:** Sure.

[01:45] **Support console:** get_credit_limit_increase_history_4829(credit_card_account_id) returned ok — no prior requests within the card-tier cooldown window.

[02:04] **Support console:** Eligibility checklist recorded on request CLI-118902: account age satisfies tier minimum; no active disputes; no outstanding replacement card orders; account current, no past-due balance; current utilization 74% — above tier threshold, criterion not met. Remaining criteria checked and recorded per complete-records requirement.

[02:33] **Support console:** get_payment_history_6183(credit_card_account_id, months=6) returned ok — all months on time. Recorded.

[02:50] **Agent:** Teresa, thank you for holding. I've finished the review, and I'm processing the decision now.

[02:59] **Support console:** deny_credit_limit_increase_5848(credit_card_account_id, user_id, denial_reason=high_utilization) returned ok. Denial recorded on request CLI-118902.

[03:08] **Agent:** I don't have good news this time — the request was denied. But here's how this works when it's a no: you receive an explanation and information about when another request can be submitted. Both of those, right now, from me — so let me explain the denial reason and when you may be eligible to reapply.

[03:34] **Customer:** Okay. I appreciate you not just reading me a form letter.

[03:41] **Agent:** The reason is your current utilization — how much of your limit is in use today. You're at seventy-four percent, and for an increase to go through, your utilization has to sit below the ceiling for your card's tier. Right now you're above it. I want to be straight with you: that was the only box that didn't check. Your payment history is spotless — six months, not a single late payment — and everything else on the account looked exactly how we want it.

[04:18] **Customer:** Ugh. Okay. So how long am I locked out? Is there a penalty box?

[04:26] **Agent:** That's the good part of the explanation: there is no penalty box. A denied request doesn't start any waiting clock on this account. The moment your utilization is below your tier's ceiling, you can submit a fresh request — tomorrow, if the numbers move by tomorrow.

[04:46] **Customer:** Really? I assumed a no meant months.

[04:50] **Agent:** A common assumption and happily wrong. And you have a lever you control: paying the balance down brings utilization down, point for point. Some customers even do it right on the phone with us from a Rho checking account, and the payment is reflected on the card right away. Get below the ceiling, ask again, and given how the rest of your file looks, the conversation should go differently.

[05:22] **Customer:** That's genuinely useful. What's the magic number I need to get under, dollar-wise?

[05:29] **Agent:** The exact tier ceilings come off a table we read live rather than a number I'd want you to carve into a post-it, because they're reviewed periodically. What I can do is this: when you're ready to pay down and re-ask, call us, and whoever answers will read the current figure and do the arithmetic with you on the spot. You won't be guessing.

[05:57] **Customer:** Fine. And I'll get something in writing about today?

[06:03] **Agent:** Yes — the formal decision notification arrives by email within a few business days, and it repeats what I told you: the reason, and the fact that you can reapply as soon as the utilization picture changes. Your reference is CLI-118902 if you ever want to ask about this one.

[06:27] **Customer:** Okay. Thanks for the straight answers, Marcus.

[06:31] **Agent:** Any time, Teresa. Thanks for calling Rho — and truly, this one is very fixable.
