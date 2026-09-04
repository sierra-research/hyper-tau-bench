# Case J
Channel: chat
QA status: approved

**Customer:** I sent a request to raise my Silver card from $12,000 to $20,000. Why was it declined?

**Agent:** To explain a declined request, enter the profile email and date of birth.

**Customer:** victor.huang@outlook.com, December 2 1980.

**Support console:** Identity verified. User ID: user_3177. Account owner for cc_mid_4402.

**Support console:** Existing formal CLI request found for cc_mid_4402. Current limit $12,000. Requested new limit $20,000; requested increase $8,000. Before submitting any new CLI, agents must verify requested increase amount is within tier maximum. If requested amount exceeds tier limit, inform customer of maximum allowed, ask customer to adjust request, and do not submit a request that exceeds tier limit. Do not claim approval before approval action succeeds.

**Support console:** Per-request maximums: Entry-tier cards 25% of current credit limit; Mid-tier cards 50%; Premium-tier cards 50%. Mid-tier maximum for current limit $12,000 is $6,000. Existing request exceeded the Mid-tier limit. deny_credit_limit_increase_5848 requirements: credit_card_account_id string, user_id string, denial_reason string exactly one of "insufficient_account_age", "cooldown_period_active", "pending_disputes", "pending_replacement_card", "past_due_balance", "high_utilization", "insufficient_payment_history", "requested_amount_exceeds_limit", or "other". Tool called with credit_card_account_id="cc_mid_4402", user_id="user_3177", denial_reason="requested_amount_exceeds_limit". Result: denial recorded.

**Agent:** After review, the request was not approved because the $8,000 increase exceeded the Mid-tier per-request maximum of $6,000.

**Customer:** What could I request instead?

**Agent:** For this Mid-tier card, the maximum increase available per request is $6,000. Would you like to proceed with a new $6,000 increase request instead?

**Customer:** Are the other tiers different?

**Agent:** Across tiers, Entry-tier cards allow up to 25% of the current credit limit per request, while Mid-tier and Premium-tier cards allow up to 50%.
