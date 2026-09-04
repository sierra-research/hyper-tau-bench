# Case D
Channel: chat
QA status: approved

**Customer:** I’m trying to refer friends for personal cards. I have Silver Rewards, and I also want to understand Platinum Rewards and EcoCard. Can you generate a link and explain the status words? My account email is nina.ramirez@yahoo.com, and my date of birth is January 18, 1988.

**Support console:** Customer identity verified.

**Agent:** Which personal card should be checked first?

**Customer:** Silver Rewards Card. I think it pays 75 if my friend is approved and spends $750 within 60 days, with a 7-per-year limit.

**Support console:** Knowledge base search completed for Silver Rewards Card before referral-link guidance. Documented referral program exists. Customer-stated terms match: pays 75 for each successful referral; up to 7 referral bonuses per calendar year; referred person must be approved and spend at least $750 within 60 days of account opening. Referral activity check: no reason to expect automatic rejection. General referral access guidance: a customer needs a unique referral link tied to the customer’s account, and it can be generated through the Rho-Bank mobile app, online banking portal, or by contacting customer service.

**Agent:** Silver Rewards Card is documented, and your understanding matches: it pays 75 for each successful referral, allows up to 7 referral bonuses per calendar year, and requires the referred person to be approved and spend at least $750 within 60 days of account opening. Customers can receive at most 2 referral bonuses in any rolling 7-day window across all credit card types; exact timestamps control the window, and the third and subsequent referrals in that window are automatically denied and do not qualify for a bonus. Please run `get_referral_link(user_id: str, card_name: str)` yourself with your own user_id and exact card name `Silver Rewards Card`; the exact-card-name format is like `Gold Rewards Card`. Agents do not generate referral links on a customer’s behalf.

**Customer:** I ran it. It generated a link and shows NO_PROGRESS.

**Support console:** Customer-side `get_referral_link(user_id: str, card_name: str)` call reported successful. Referral record created with status NO_PROGRESS. Agent did not generate the referral link on the customer’s behalf.

**Agent:** NO_PROGRESS means the invitee has not applied yet and no progress has been made. The referred person can now use your generated link to apply; when a referred person uses your referral link to apply and is approved, the referral is tracked to your account. If they are approved for a new Rho-Bank credit card and meet the program requirements, you may be eligible for a referral bonus, and both parties could be rewarded.

**Customer:** How should I send the Silver Rewards referral?

**Agent:** Give friends and colleagues the Silver Rewards referral link or code.

**Customer:** Does it matter whether I send it by email or text?

**Agent:** Email, text, or social media can be used to share the link with friends and family once you have it.

**Customer:** How do I make sure it is tracked?

**Agent:** Tracking for Silver Rewards depends on the referred person applying with the referral link or code.

**Customer:** The dashboard also shows APPLIED, IN_PROGRESS, and COMPLETE on older referrals. What do those mean?

**Support console:** Referral status glossary retrieved from documented referral status guidance.

**Agent:** APPLIED means the referred person has sent in the application and is waiting for a decision, so no manual intervention is needed while the decision is awaited. IN_PROGRESS means the referred person has successfully opened a new account and is in progress toward meeting the referral bonus criteria; no action is required, and the status is monitored until the criteria are met. COMPLETE means the referred person has successfully opened a new account and met the criteria for the referral bonus, so the bonus is granted according to the applicable referral program terms.

**Customer:** What about REJECTED or ERROR? I saw those in an article and got nervous.

**Support console:** Referral status glossary includes: REJECTED means the user has too many referral processes going on; do not retry immediately and review existing referral activity before next steps. ERROR means an error occurred during the process; retry later or escalate internally if the condition persists.

**Agent:** That concern makes sense. REJECTED means the user has too many referral processes going on; the next step is to review the existing referral activity before any retry.

**Customer:** And what does ERROR mean?

**Agent:** ERROR means an error occurred during the process; retry later, and if it continues, the issue can be escalated for review.

**Customer:** How will I know when the Silver Rewards referral earns the bonus?

**Agent:** Rho-Bank sends notifications when referrals are approved and when referral bonuses are earned. For Silver Rewards, you are notified when the referral meets the qualifying spend requirement, and the bonus typically posts within one to two billing cycles after the referred account meets the $750 requirement.

**Customer:** Any tip to help my friend qualify?

**Agent:** One helpful Silver Rewards reminder is for the referral to activate the card promptly and add recurring bills to help meet $750 within 60 days.

**Customer:** And for my annual Silver Rewards count?

**Agent:** Monitor the Silver Rewards annual referral count to stay within the 7 limit.

**Customer:** If another friend asks this week, should I just send another link?

**Agent:** Check the timing of your last two successful referral bonuses before sending another referral. If a referral is denied for hitting the rolling 7-day limit, it cannot be reinstated within that same 7-day window; those timestamps show when enough time has passed to drop under the cap.

**Customer:** Can I confirm active offers or status later without starting a new chat?

**Support console:** General referral service guidance retrieved: customers can track referral status at any time through the Rho-Bank mobile app or by contacting customer service; Rho-Bank sends notifications when referrals are approved and when referral bonuses are earned; customers may reach customer service at 1-800-RHO-BANK for referral program questions or to confirm the current offer for a card.

**Agent:** Active referral offers are not available for every credit card, so confirm that the card has an active referral offer before sharing a referral link. Participating offers can vary by credit card type, including bonus amount, eligibility requirements, and reward types such as cash back bonuses, bonus points, or statement credits.

**Customer:** Where can I track status?

**Agent:** Status tracking is available at any time through the Rho-Bank mobile app or by contacting customer service.

**Customer:** What number confirms current offers?

**Agent:** Referral program questions and current-offer confirmations can be handled at 1-800-RHO-BANK.

**Customer:** Can I generate referral links outside this chat?

**Agent:** Referral-link generation outside this chat is available through the Rho-Bank mobile app, online banking portal, or customer service.

**Customer:** Please summarize Platinum Rewards too.

**Support console:** Knowledge base search completed for Platinum Rewards Card. Documented referral program exists.

**Agent:** Platinum Rewards Card referrals are shared through your account to invite friends to apply. The referrer earns $100 for each friend who is approved and meets the qualifying spend, and the friend must spend at least $1,500 within 90 days of account opening; the program allows up to 7 referral bonuses per calendar year. Bonuses are typically credited after the referred applicant is approved and meets the $1,500 spend requirement within 90 days. Self-referrals and duplicate applications do not qualify.

**Customer:** What are the Platinum steps?

**Agent:** Open the Platinum referrals section in the account.

**Customer:** Then what?

**Agent:** Choose the available Platinum sharing options to send the referral.

**Customer:** After I send it?

**Agent:** After that, track the status of pending Platinum referrals in the dashboard.

**Customer:** Any Platinum tips?

**Agent:** A useful Platinum sharing tip is to choose friends who are likely to benefit from the card’s features.

**Customer:** What should I remind the referral about?

**Agent:** Ask the Platinum referral to meet the $1,500 spend threshold within 90 days.

**Customer:** Anything about my own account?

**Agent:** Keeping your referrer account in good standing helps Platinum bonuses be received promptly.

**Customer:** And EcoCard?

**Support console:** Knowledge base search completed for EcoCard. Documented referral program exists.

**Agent:** EcoCard pays 50 for each successful referral, allows up to 7 referral bonuses per calendar year, and requires the referred person to be approved and spend at least $500 within 60 days of account opening. For EcoCard, the referrer is notified when the referral meets the qualifying spend requirement, and the bonus typically posts within one to two billing cycles after the referred account meets the $500 requirement.

**Customer:** How should I share EcoCard referrals?

**Agent:** Share EcoCard referrals by giving the referral link or code to friends and family.

**Customer:** How do I keep EcoCard tracked?

**Agent:** Proper EcoCard tracking requires the referred person to apply using the link or code.

**Customer:** Any EcoCard tip for the referral?

**Agent:** Help an EcoCard referral by reminding them to activate their card promptly and add recurring bills to help meet $500 within 60 days.

**Customer:** What about the annual EcoCard limit?

**Agent:** Track EcoCard annual referral count to stay within the 7 limit.
