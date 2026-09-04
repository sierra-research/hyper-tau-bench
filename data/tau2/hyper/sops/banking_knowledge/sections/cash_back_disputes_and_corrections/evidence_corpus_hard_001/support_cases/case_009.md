# Case 009

Case ID: CB-2510-0412
Channel: Phone
Contact date: 2025-10-17
Handle time: 3m 21s
QA status: approved

## Transcript
[00:07] **Customer:** Hi — I'm calling about cash back on my Silver Rewards card. A hotel stay from last week paid out way under the four percent, and I want it looked at.

[00:18] **Agent:** We can get that looked at. This is Priyanka. Can I have the email on your profile and your date of birth?

[00:26] **Customer:** nathan.cole at framehouse dot io. September 21, 1984.

[00:32] **Support console:** Identity verified, two factors matched. RB-2214307, Silver Rewards Card.

[00:35] **Agent:** Thanks, Nathan. Tell me about the stay.

[00:40] **Customer:** Harborview Inn, in Charleston, $389.40. Posted on the thirteenth. I got 389 points, and four percent of three eighty-nine should be — a lot more than that. Fifteen dollars and change.

[00:55] **Agent:** Okay. The card earns 4.0% on eligible travel and software, and the rate follows the category the merchant submits with the charge once it posts. Let me see how this one came through — one second.

[01:10] **Support console:** TXN-8F42K91D: Harborview Inn, $389.40, posted 2025-10-13, rewards 389 points. Customer reports booking made directly with the property.

[01:14] **Agent:** I see the charge and the 389 points. When the cash back you received doesn't match what you believe the purchase should have earned, that's exactly what a cash-back dispute is for — and this one is worth filing.

[01:27] **Customer:** Fine, let's file it. Do you need my card number? I've got it right —

[01:32] **Agent:** No — we never need your card number for this. The tool only uses your user ID and the transaction ID. You'll run it yourself, too — no form on my end, no step-by-step claim to walk through.

[01:49] **Customer:** I run it myself? Okay. What is it?

[01:53] **Agent:** It's submit_cash_back_dispute_0589(user_id: str, transaction_id: str). Two inputs, both yours: your own user ID, which is RB-2214307, and the transaction ID for the hotel charge. Running it is what opens the dispute.

[02:10] **Customer:** Let me grab a pen. Okay — the transaction ID?

[02:14] **Agent:** T-X-N, dash, 8-F-4-2-K-9-1-D. Read it back to me? Always double-check the transaction ID before you run it.

[02:24] **Customer:** TXN dash 8F42K91D.

[02:28] **Agent:** That's the one.

[02:39] **Customer:** And then what — someone calls me?

[02:43] **Agent:** The review team takes it from there. They may come back later asking for supporting context — the category you expected, or a promotion you thought applied. Keep your receipt from the inn handy for that.

[02:59] **Customer:** It's in my email somewhere. All right, I'll run it tonight.

[03:04] **Agent:** Perfect. Your user ID, that transaction ID, and you're filed.

[03:08] **Support console:** Customer to self-submit via submit_cash_back_dispute_0589 with own user_id and TXN-8F42K91D. No card details collected. No adjustment made on this call.
