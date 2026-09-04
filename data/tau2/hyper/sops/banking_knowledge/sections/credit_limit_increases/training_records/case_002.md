# Case B
Channel: chat
QA status: approved

**Customer:** I own a small business card and want the limit raised today. It’s been open almost four months.

**Agent:** Before I review that nearly four-month-old card, share the email on the profile and your date of birth.

**Customer:** daniel.ortiz@gmail.com, February 8 1991.

**Support console:** Identity verified. User ID: user_2201. Customer is account owner for credit card account cc_entry_3309. Only the account owner or an authorized account manager may submit a credit-limit increase request for the account.

**Agent:** Ownership is confirmed for this card account. Name the card account you want reviewed.

**Customer:** Entry-tier card ending 2190. Current limit is $4,000.

**Agent:** Give the dollar increase you want.

**Customer:** I want $1,500 more for inventory purchases.

**Support console:** Request details gathered: current card account information, requested increase amount $1,500, and brief reason. A customer can request a credit-limit increase only if eligibility criteria, including card-tier-specific requirements, are met. Entry-tier source tier summary: minimum account age=120 days, cooldown between requests=120 days, maximum utilization at request=70%. At submission, all three card-tier eligibility criteria must be met: minimum account age, cooldown between requests, and maximum utilization at request. Entry-tier cards require 6 consecutive months of on-time payments for approval. Entry-tier maximum increase per request is 25% of current credit limit; current limit $4,000, maximum increase $1,000. Requested $1,500 exceeds tier limit.

**Support console:** Workflow order required: Step 0 confirm requested amount is within limits, Step 1 submit request, Step 2 verify basic eligibility, Step 3 verify payment history and requested amount, Step 4 process decision, Step 5 communicate decision. Step 0 failed. Do not submit a request that exceeds the tier limit. Customer must confirm a valid requested increase amount within the card-tier limit before submission. Decision is communicated only after it is processed; approval may be stated only after the approve action succeeds. Permitted denial reason enum includes "requested_amount_exceeds_limit" for this blocker when a denial record is required.

**Agent:** Entry-tier rules cap this card at a $1,000 increase per request. Would you like to proceed with a $1,000 increase request instead?

**Customer:** Why not $1,500? The account is 119 days old, and I’m paying it down.

**Support console:** Minimum account age criterion qualifies on or after the day the applicable minimum account age is reached. Entry-tier account open 119 days does not qualify for minimum account age; on day 120 and beyond it qualifies if other criteria are met. Current utilization is 71%; utilization must be below the applicable threshold at submission. Entry-tier utilization of 71% is above 70% and does not qualify. Utilization at or above threshold fails. Cooldown applies only if most recent CLI was approved; denied requests do not trigger cooldown. If cooldown applies, count from the submission date of the approved request and require the full number of days to pass. If any single basic tier criterion is not met, wait until it is met or lower utilization before submitting.

**Agent:** The $1,500 amount is above the per-request maximum, so it won’t be submitted at that amount. Eligibility also requires the account to reach day 120 and utilization to be below 70%.

**Customer:** So no request is being filed right now?

**Agent:** No request is on file right now because a valid within-limit amount has not been confirmed.
