# Case 007

Case ID: CLR-2511-0688
Channel: Phone
Contact date: 2025-11-10
Handle time: 3m 49s
QA status: approved

## Transcript
[00:04] **Agent:** Rho Bank card support, this is Nadia. How can I help?

[00:11] **Customer:** Hi. Two things, but the main one is a limit increase on my Silver Rewards. Eight hundred more, ideally.

[00:21] **Agent:** We can take that. Verify first — full name and phone on the profile?

[00:29] **Customer:** Tobias Ferreira, 555-0577.

[00:31] **Agent:** Street address?

[00:34] **Customer:** 1409 Miner Street, apartment 12.

[00:38] **Agent:** Verified, thanks. Eight hundred on this card is an amount I can submit — confirming: eight hundred dollars added, yes?

[00:48] **Customer:** Yes please.

[00:52] **Support console:** submit_credit_limit_increase_request_7392(credit_card_account_id, user_id, requested_increase_amount=800) returned ok. Request reference CLI-119029 attached to case.

[00:57] **Agent:** Submitted, reference CLI-119029. Quiet review minutes now — hold tight.

[01:04] **Support console:** get_user_dispute_history_7291(user_id) returned ok — open dispute on the account, status under_review, filed late October. Eligibility checklist recorded on request CLI-119029: active dispute on account — criterion not met. Remaining criteria checked and recorded.

[01:46] **Support console:** deny_credit_limit_increase_5848(credit_card_account_id, user_id, denial_reason=pending_disputes) returned ok. Denial recorded on request CLI-119029.

[01:55] **Agent:** Tobias, thank you for waiting. I've processed the decision and it's a no for the moment, and I suspect you can guess why: the dispute you filed on that restaurant charge last month is still open. While there's an active dispute on the account, an increase can't go through.

[02:18] **Customer:** That was actually my second thing — I was going to ask how the dispute is doing. It's blocking the increase? They're not even related amounts.

[02:31] **Agent:** Related or not, an open dispute means the account's numbers are in motion, so the increase waits for it. On the dispute itself: I can see it's under review with the investigation team. The disputes desk owns the details — I can transfer you there warm, or you can just let it run; you'll be notified when it closes either way.

[02:57] **Customer:** And once it closes, the increase — do I start over?

[03:04] **Agent:** Fresh request, ten minutes, no penalty from today's no. The moment the dispute is resolved you're clear to ask, assuming the rest of the account stays as healthy as it looked today — and it looked good.

[03:22] **Customer:** Alright. Transfer me to the disputes folks, then — may as well ask them for a timeline directly.

[03:32] **Agent:** Transferring warm with the notes attached so you don't re-explain. Your increase reference is CLI-119029, and the denial explanation follows by email. Good luck with the restaurant.

[03:45] **Customer:** Ha, thanks Nadia.
