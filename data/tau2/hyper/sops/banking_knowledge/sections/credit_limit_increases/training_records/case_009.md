# Case I
Channel: chat
QA status: approved

**Customer:** I’ve only had one late card payment recently. Can I still get a limit increase?

**Agent:** To look at recent payment history for a limit review, share your email address and date of birth.

**Customer:** amina.khan@gmail.com, March 22 1987.

**Support console:** Identity verified. User ID: user_4820. Account owner for cc_mid_1852.

**Agent:** Authentication is complete. Specify the increase amount you want.

**Customer:** Current limit is $9,000. I want a $3,000 increase.

**Support console:** Requested increase $3,000 is within Mid-tier 50% per-request limit. Do not claim approval before approve action succeeds.

**Agent:** Mid-tier rules allow this $3,000 amount to move into review.

**Customer:** Okay.

**Agent:** Use yes to authorize submission for review.

**Customer:** Yes, please submit it.

**Support console:** Workflow order followed: Step 0 confirm amount within limits; Step 1 submit request; Step 2 verify basic eligibility; Step 3 verify payment history and requested amount; Step 4 process decision; Step 5 communicate decision. submit_credit_limit_increase_request_7392 called with credit_card_account_id="cc_mid_1852", user_id="user_4820", requested_increase_amount=3000. Result: submitted, reference CLI-909712. Submission creates formal record before eligibility checks; all requirements must be checked before decision.

**Agent:** Submitted reference CLI-909712 is ready for review.

**Support console:** Basic eligibility passed. Step 3 is to verify payment history and requested amount after basic eligibility and before processing the decision. Payment-history requirements: Entry-tier cards require 6 consecutive months of on-time payments; Mid-tier cards require 3 consecutive months; Premium-tier cards require 3 consecutive months. Use get_payment_history_6183 with required arguments credit_card_account_id as a string and months as an integer set to the appropriate tier value. For Mid-tier, call get_payment_history_6183 with credit_card_account_id="cc_mid_1852", months=3. Result: only 2 consecutive months on time due to one late payment in the 3-month window. Requested amount remains within limit.

**Support console:** deny_credit_limit_increase_5848 requirements: credit_card_account_id string, user_id string, denial_reason string exactly one of "insufficient_account_age", "cooldown_period_active", "pending_disputes", "pending_replacement_card", "past_due_balance", "high_utilization", "insufficient_payment_history", "requested_amount_exceeds_limit", or "other". Tool called with credit_card_account_id="cc_mid_1852", user_id="user_4820", denial_reason="insufficient_payment_history". Result: denial recorded.

**Agent:** After payment-history review, the request was not approved because the Mid-tier card does not show 3 consecutive months of on-time payments. You may be eligible to reapply after the required consecutive on-time payment history is met.
