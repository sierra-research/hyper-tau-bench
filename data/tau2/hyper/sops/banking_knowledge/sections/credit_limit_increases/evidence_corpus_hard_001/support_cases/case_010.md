# Case 010

Case ID: CLR-2511-0781
Channel: Phone
Contact date: 2025-11-12
Handle time: 3m 43s
QA status: approved

## Transcript
[00:04] **Agent:** Rho Bank card support, this is Grace. What can I do for you?

[00:11] **Customer:** Hi. I'd like a limit increase on my EcoCard. Three hundred fifty.

[00:17] **Agent:** Let's run it. Verification — name and phone number on file?

[00:24] **Customer:** Yusuf Kaya, 555-0803.

[00:26] **Agent:** And your street address?

[00:30] **Customer:** 55 Winter Garden Court.

[00:33] **Agent:** Verified. Three hundred fifty is submittable — confirming that amount?

[00:40] **Customer:** Yes.

[00:43] **Support console:** submit_credit_limit_increase_request_7392(credit_card_account_id, user_id, requested_increase_amount=350) returned ok. Request reference CLI-119130 attached to case.

[00:49] **Agent:** Submitted, reference CLI-119130. Review takes a few minutes — stay with me.

[00:57] **Support console:** Eligibility checklist recorded on request CLI-119130: all basic criteria met. get_payment_history_6183(credit_card_account_id, months=6) returned ok — late payment recorded in August; consecutive on-time streak insufficient for tier. Criterion not met.

[01:43] **Support console:** deny_credit_limit_increase_5848(credit_card_account_id, user_id, denial_reason=insufficient_payment_history) returned ok. Denial recorded on request CLI-119130.

[01:52] **Agent:** Yusuf, thanks for holding. I've processed the decision and today it's a no. The reason is payment history: your card's tier wants a run of consecutive on-time monthly payments, and there's a late payment in August that restarted your run. The months since August are spotless — they just aren't enough of them yet.

[02:15] **Customer:** August... that was the vacation where I paid it from the airport two days late. One late payment undoes everything before it?

[02:26] **Agent:** For this particular requirement, the streak is what counts, and a streak has no memory of its ancestors — the run starts over after a late month. The good news is mechanical: keep doing what you've done since September and the streak simply gets there. No waiting period from today's no; when the run is long enough, ask again.

[02:53] **Customer:** And how long is long enough for my card?

[02:59] **Agent:** The month count is a tier figure we read live — call when you're a few months further along and the agent will read the current requirement and count your streak with you. Given September, October, and the month in progress, you're closer than you probably feel.

[03:21] **Customer:** Okay. So realistically early next year. Fine. The airport payment strikes again.

[03:28] **Agent:** It usually does. Reference CLI-119130, written explanation by email. Anything else today?

[03:36] **Customer:** No, all set. Thanks Grace.

[03:40] **Agent:** Thanks for calling Rho, Yusuf.
