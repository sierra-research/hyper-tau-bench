## Credit-card referral status, restrictions, and link generation

Bundle id: `credit_card_referrals`

Construction context (guidance for transcript induction, not section
content -- do not extract as policy facts): the shared banking handbook
governs identity verification, explicit customer confirmation before
account-modifying actions, discoverable-tool wrapper behavior, schema
limits, and exact transfer wording. Express these behaviorally in
transcripts where a case exercises them; do not restate them as section
facts. The bundle id, transcript focus, losslessness risks, and shared
context paths in this file are construction metadata, not policy facts.

Transcript focus:
Checking referral statuses, applying referral restrictions, generating links, and distinguishing personal from business referral programs.

Losslessness risks:
- Preserve every referral status and its customer-facing implication.
- Preserve product-specific restrictions and reward timing.
- Do not imply a referral reward is guaranteed before status criteria are met.

Source documents:

### doc_credit_cards_credit_cards_(general)_001: Internal: Understanding Credit Card Referral Statuses.

### Referral status meanings

- COMPLETE — the referred person has successfully opened a new account and met the criteria to get the referral bonus
- IN_PROGRESS — the referred person has successfully opened a new account and is in progress to meet the criteria for the referral bonus
- NO_PROGRESS — the referred person has not applied yet, no progress has been made
- APPLIED — the referred person has sent in the application and is waiting for a decision
- REJECTED — the user has too many referral processes going on
- ERROR — an error has occurred throughout the process

#### How to interpret and act
- COMPLETE: The bonus will be granted per the applicable referral program terms.
- IN_PROGRESS: No action required; monitor until criteria are met.
- NO_PROGRESS: You may remind the referrer that the invitee has not started an application.
- APPLIED: Await the application decision; no manual intervention is needed.
- REJECTED: Do not retry immediately; review the user’s existing referral activity before advising next steps.
- ERROR: Retry later or escalate internally if the condition persists.

### doc_credit_cards_credit_cards_(general)_002: Credit Card Referral Offers and Restrictions

### Program scope
- Each credit card type has its own referral bonus and eligibility requirements that are not detailed here.

### Weekly referral limit
- You can receive at most 2 referral bonuses in any rolling 7-day window.
- If you attempt to receive more than 2 referrals in a single week, the third referral (and any subsequent referrals that week) will be automatically denied.
- This limit applies across all credit card types; referrals from different cards still count toward the same weekly cap.

### Practical guidance
- Track the timing of your last two successful referral bonuses before sending additional referrals.
- A rolling 7-day window means the count is evaluated based on the exact timestamps of your most recent referral bonuses, not calendar weeks.
- Auto-denied referrals due to the limit cannot be reinstated within the same 7-day window.
- If a referral is denied for hitting the limit, wait until enough time has passed to drop under the cap before attempting another.

### doc_credit_cards_credit_cards_(general)_009: Generating a Credit Card Referral Link (Internal)

### Pre-check before providing the referral tool
- Search the knowledge base to confirm the specific card has a documented referral program.
- Verify the customer’s understanding of referral terms. If the customer cites terms that do not match any documented program, clarify the discrepancy.
- If no referral program is documented for the requested card, or if the user’s claimed terms are incorrect, or if there is reason to believe the referral will be automatically rejected, explain why and do not provide a referral link tool. Do not transfer to a human in these cases.

### How the user generates their referral link
- Provide the customer with this tool and instruct them to run it themselves:
  - `get_referral_link(user_id: str, card_name: str)`
- Tell the customer to pass their own user_id and the exact card name (for example, 'Gold Rewards Card').
- When the tool is called successfully, a referral record is created with status 'NO_PROGRESS'. The referred person can then use the generated link to apply.

### Important reminders
- Weekly limit: Customers can receive at most 2 referral bonuses in any rolling 7-day window; the third and subsequent referrals in that window are automatically denied.
- Agents must not generate the link on the customer’s behalf.
- Reiterate the correct referral terms as documented to prevent confusion and complaints.

### doc_credit_cards_credit_cards_(general)_020: Refer a Friend to Rho-Bank and Earn Rewards

Do you love your Rho-Bank credit card? Share the love with friends and family, and you could both earn rewards! Our referral program makes it easy to invite the people you care about to join Rho-Bank, and when they're approved for a new card and meet the program requirements, you'll both be rewarded.

### How It Works

Participating in our referral program is simple. When you refer someone to apply for a Rho-Bank credit card and they're approved, you may be eligible to receive a referral bonus. The specific bonus amount and requirements vary depending on which credit card you're referring them to—some cards offer cash back bonuses, while others may offer bonus points or statement credits.

### Getting Your Referral Link

To refer a friend, you'll need to generate a unique referral link that's tied to your account. You can do this through the Rho-Bank mobile app, online banking portal, or by contacting our customer service team. Once you have your link, simply share it with friends and family via email, text, or social media. When they use your link to apply and are approved, the referral will be tracked to your account.

### Important Things to Know

To ensure the referral program remains fair for all participants, there are a few guidelines to keep in mind:

- **Weekly Limit**: You can earn referral bonuses for up to 2 successful referrals per week. This is calculated on a rolling 7-day basis, so if you've already had 2 referrals complete in the past week, any additional referrals during that time won't qualify for a bonus.
- **Eligibility**: Not all credit cards participate in the referral program. Before sharing your link, make sure the card you're referring has an active referral offer.
- **Bonus Requirements**: Each referral program has specific requirements that your friend must meet to trigger the bonus, such as making a certain amount of purchases within a specified timeframe after account opening.

### Check Your Referral Status

You can track the status of your referrals at any time through the Rho-Bank mobile app or by contacting customer service. We'll also send you notifications when your referrals are approved and when you earn your bonus.

If you have any questions about the referral program or want to confirm the current offer for your card, please reach out to our customer service team at 1-800-RHO-BANK. We're always happy to help!

### doc_credit_cards_silver_rewards_card_011: Silver Rewards Card: Referral Program - Earn Rewards for Referring Friends

### What You Earn
- Receive 75 for each successful referral
- You can earn up to 7 referral bonuses per calendar year

### What Your Referral Must Do
- The referred person must be approved and spend at least $750 within 60 days of account opening

### How to Refer
1. Share your referral link or code with friends and colleagues
2. Ensure they apply using your link or code so the referral is tracked
3. You’ll be notified when the referral meets the qualifying spend requirement

### Payout Timing
- Your bonus typically posts within one to two billing cycles after the referred account meets the $750 requirement

### Program Tips
- Remind your referral to activate their card promptly and add recurring bills to help them meet $750 within 60 days
- Track your annual count to stay within the 7 limit

### doc_credit_cards_platinum_rewards_card_008: Platinum Rewards Card: Referral Program - Earn Rewards for Referring Friends

### How It Works
- Share your referral through your account to invite friends to apply.
- For each friend who is approved and meets the qualifying spend, you earn a referral bonus of $100.

### Qualifying Spend Requirement
- The referred friend must spend at least $1,500 within 90 days of account opening to qualify you for the bonus.

### Annual Limits
- You can earn up to 7 referral bonuses per calendar year.

### Steps to Refer
1. Open the referrals section in your account.
2. Send your referral using the available sharing options.
3. Track the status of pending referrals in your dashboard.

### Payout Timing and Eligibility
- Bonuses are typically credited after the referred applicant is approved and meets the $1,500 spend requirement within 90 days.
- Self-referrals or duplicate applications do not qualify.

### Tips
- Share with friends who are likely to benefit from the card's features.
- Remind your referral to meet the $1,500 spend threshold within 90 days.
- Ensure your account is in good standing to receive bonuses promptly.

### doc_credit_cards_ecocard_011: EcoCard: Referral Program - Earn Rewards for Referring Friends

### What You Earn
- Receive 50 for each successful referral
- You can earn up to 7 referral bonuses per calendar year

### What Your Referral Must Do
- The referred person must be approved and spend at least $500 within 60 days of account opening

### How to Refer
1. Share your referral link or code with friends and family
2. Ensure they apply using your link or code so the referral is tracked
3. You'll be notified when the referral meets the qualifying spend requirement

### Payout Timing
- Your bonus typically posts within one to two billing cycles after the referred account meets the $500 requirement

### Program Tips
- Remind your referral to activate their card promptly and add recurring bills to help them meet $500 within 60 days
- Track your annual count to stay within the 7 limit

### doc_business_credit_cards_business_gold_rewards_card_010: Business Gold Rewards Card: Referral Program - Earn Rewards for Referring Businesses

### How the Referral Bonus Works
- Earn $200 for each successful referral who is approved and meets the qualifying spend.
- You can earn up to 8 referral bonuses per calendar year.

### Qualifying Spend Requirement
- The referred business must spend $7,500 within 90 from account opening to qualify your bonus.

### Program Timeline
- The referral program accepts new referrals until 2025-09-15. Referrals submitted after this date are not eligible.

### How to Refer
- Generate your unique referral link from your account’s referral center.
- Share the link directly with businesses that consent to receive it.
- Track application status and eligibility in the referral dashboard.

### Payouts
- Once the referred account is approved and completes $7,500 within 90, your $200 is queued for issuance to your account.

### Rules and Best Practices
- Self-referrals are not permitted.
- Share referral invitations only with contacts who have given permission to receive them.
- If a referral applies without your link, the referral may not be attributed.
- Program terms, eligible industries, and promotional availability may change without notice prior to 2025-09-15.

### doc_business_credit_cards_silver_zoom_card_011: Silver Zoom Card: Referral Program - Earn Rewards for Referring Logistics Businesses

### How the referral program works
- Earn a referral bonus of $150 for each referred logistics business that is approved and meets the qualifying spend requirement
- Bonuses are capped at 10 per calendar year

### Qualifying activity for your referral
- The referred business must complete purchases totaling $7,500 within 90 days of account opening
- Only one referrer is credited per approved account

### Program timing
- No new referrals are accepted after 2025-10-01

### How to refer
- Share your referral link or submit the referral through your account portal before the referred business applies
- Ensure the referred business uses your link or is otherwise properly attributed during application
- Track referral status within your account until the qualifying spend threshold of $7,500 is met

### Payout details
- Bonuses are typically issued to the referrer after the referred business satisfies the $7,500 requirement within 90 days
- If the referred business returns purchases or does not meet the requirement, no bonus is issued

Shared context paths (construction metadata, not policy facts):
- `tau2/hyper/sops/banking_sop.md`
