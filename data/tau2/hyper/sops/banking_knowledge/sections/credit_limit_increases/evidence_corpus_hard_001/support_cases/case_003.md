# Case 003

Case ID: CLR-2511-0158
Channel: Phone
Contact date: 2025-11-04
Handle time: 4m 58s
QA status: approved

## Transcript
[00:03] **Agent:** Thanks for calling Rho Bank card support, this is Grace. What can I do for you?

[00:12] **Customer:** Hi Grace. I'd like a limit increase on my Silver Zoom card. It's at four thousand and I want to add three thousand — I've got tuition and a laptop for my kid landing in the same month.

[00:30] **Agent:** Congratulations and condolences on the same invoice. Let me verify you first — full name and phone number on the profile?

[00:41] **Customer:** Sam Bouchard, 555-0339.

[00:44] **Agent:** And the street address on file?

[00:48] **Customer:** 1120 Wren Street.

[00:51] **Agent:** Verified. And this is your own account — you're the owner?

[00:57] **Customer:** Yep, mine.

[01:00] **Agent:** Then let's talk numbers, because I have to be straight with you before anything gets submitted. Three thousand is more than I can put through on this card right now — the maximum amount you're eligible for on this card today is a two-thousand-dollar increase. Would you like to proceed with that amount instead?

[01:24] **Customer:** Huh. Where does the two thousand come from? Is that about me, or about the card?

[01:32] **Agent:** It's about the card's tier — every tier has a per-request maximum, and the current figures come off a table on my side. It isn't a judgment of you, and it isn't permanent: it's the most any single request on this card can ask for. And to be clear, I can't submit the three thousand just to see what happens — a request above the maximum doesn't go in at all. What I can submit is two thousand.

[02:06] **Customer:** Okay. Two thousand still covers the laptop and most of the tuition gap. Do it at two.

[02:15] **Agent:** Confirming back so it's clean: you're requesting a two-thousand-dollar increase on the Silver Zoom card, taking the limit to six thousand if approved. Yes?

[02:27] **Customer:** Yes.

[02:30] **Support console:** submit_credit_limit_increase_request_7392(credit_card_account_id, user_id, requested_increase_amount=2000) returned ok. Request reference CLI-118231 attached to case.

[02:37] **Agent:** Submitted — your reference confirmation is CLI-118231. Give me a few quiet minutes to complete the review.

[02:45] **Customer:** Go for it.

[02:48] **Support console:** get_credit_limit_increase_history_4829(credit_card_account_id) returned ok — no prior requests within the card-tier cooldown window. Eligibility checklist recorded on request CLI-118231: all criteria met. get_payment_history_6183(credit_card_account_id, months=3) returned ok — all months on time. Requested amount re-verified within tier maximum.

[03:31] **Agent:** Sam, thanks for holding. Review's done, processing the decision now.

[03:38] **Support console:** approve_credit_limit_increase_5847(credit_card_account_id, user_id, new_credit_limit=6000.0) returned ok. Approval recorded on request CLI-118231.

[03:48] **Agent:** Done and approved. Your new limit is six thousand dollars — you'll see it on the account as soon as the update completes, and the formal notification follows by email in a few business days.

[04:05] **Customer:** Great. And if I find out the tuition bill is worse than advertised — when can I come back for the rest?

[04:17] **Agent:** Ask us when you're ready and we'll look at the account as it stands then — I won't quote you a waiting period off the top of my head, because the timing rules come off the same live table and depend on what's happened on the account. The honest answer is: call, and we'll read the current rules together.

[04:44] **Customer:** Fair enough. Thanks, Grace, that was less painful than the tuition.

[04:51] **Agent:** Low bar, but I'll take it. Thanks for calling Rho, Sam.
