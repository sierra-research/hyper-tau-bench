# Case 012

Case ID: CLR-2511-0768
Channel: Phone
Contact date: 2025-11-12
Handle time: 3m 48s
QA status: approved

## Transcript
[00:03] **Agent:** Rho Bank card support, this is Elif. How can I help?

[00:09] **Customer:** Hello! Gold Rewards card, and I'd like a big jump — the limit's at ten thousand and I want to add six thousand. We're renovating.

[00:21] **Agent:** Renovations, the great limit-raiser. Verification first — name and phone on the profile?

[00:29] **Customer:** Constance Whitmore-Beale, 555-0129.

[00:32] **Agent:** And the street address?

[00:36] **Customer:** 4 Foxhill Crescent.

[00:39] **Agent:** Verified, thank you. Now, the six thousand — I have to stop us before anything goes in, because that's above what this card can ask for in a single request. The most I can submit for you today is a five-thousand-dollar increase. Would you like to proceed at five thousand?

[01:01] **Customer:** Hm. What happens to the other thousand? Can I ask for it next week?

[01:10] **Agent:** Not next week — an approved increase starts a waiting period for this card before the next request, so the five thousand would need to do its job for a while. My honest suggestion: take the five thousand today if it covers the renovation's spine, and revisit the rest when the window reopens.

[01:34] **Customer:** The contractor's schedule says the five thousand covers everything before spring. Fine — five thousand, do it.

[01:43] **Agent:** Confirming clean: a five-thousand-dollar increase on the Gold Rewards, to fifteen thousand total if approved. Yes?

[01:53] **Customer:** Yes.

[01:55] **Support console:** submit_credit_limit_increase_request_7392(credit_card_account_id, user_id, requested_increase_amount=5000) returned ok. Request reference CLI-119088 attached to case. Eligibility checklist recorded: all criteria met. get_payment_history_6183(credit_card_account_id, months=3) returned ok — all months on time. Requested amount re-verified within tier maximum.

[02:40] **Support console:** approve_credit_limit_increase_5847(credit_card_account_id, user_id, new_credit_limit=15000.0) returned ok. Approval recorded on request CLI-119088.

[02:50] **Agent:** Done and processed, and I can confirm the approval: your new limit is fifteen thousand dollars. It shows in your account as soon as the update completes, and the formal email follows in a few business days.

[03:07] **Customer:** Wonderful. And the waiting window for the remaining thousand — when exactly?

[03:13] **Agent:** The count starts from today's submission, and the length is a tier figure we read live — when you're ready, call and the agent will read the current table and give you the exact date. It'll be on file that today went smoothly, which never hurts.

[03:34] **Customer:** Perfectly reasonable. Thank you, Elif — the contractor thanks you too.

[03:42] **Agent:** May the renovation stay on budget. Thanks for calling Rho.
