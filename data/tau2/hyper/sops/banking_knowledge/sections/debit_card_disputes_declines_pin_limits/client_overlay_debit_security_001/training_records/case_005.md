# Case E
Channel: chat
QA status: approved

**Customer:** My debit card was declined, and the receipt says lost card. I found the card in my desk, so can it be turned back on?

**Agent:** Let’s verify the account first with your email address and date of birth.

**Customer:** elena.rojas@yahoo.com, 02/18/1990.

**Support console:** Identity verified. Require extra caution for security-sensitive card states.

**Support console:** Decline Code 41 means Lost Card. Agent must look up debit card information to confirm the card will have issue_reason lost or a status indicating lost, then check whether the customer actually reported it lost.

**Support console:** get_debit_cards_by_account_id_7823(account_id="chk_65109") returned card dc_2200 ending 9044, status CLOSED, issue_reason lost; replacement card dc_2288 ending 1176, status PENDING, issue_reason lost.

**Agent:** The old card ending in 9044 was reported lost. Did you make that lost-card report?

**Customer:** Yes, I reported it last week and then found it today.

**Agent:** A card reported lost is not reactivated. A replacement card ending in 1176 is pending, and if no replacement had been ordered, we could help order one.

**Customer:** What if I had not reported it lost?

**Support console:** For Decline Code 41, if customer says they did not report the card lost, it is a security concern that someone else may have reported it. Agent must verify additional information, ask security questions, review recent transaction history for suspicious activity, and follow lost debit card protocol.

**Agent:** A report you did not make would be treated as a security concern, with additional security questions, recent-transaction review, and the lost-card security process.

**Customer:** I also had a different card blocked after I asked for extra security yesterday. The recent transactions were all mine.

**Support console:** Customer-initiated fraud alerts are placed when a customer reports suspicious activity or requests additional security. They can be cleared by customer service agents only after verifying identity and confirming recent transactions are legitimate. clear_debit_card_fraud_alert_4892 clears fraud alerts or velocity blocks and requires card_id and reason. reason must be customer_verified for clearing a customer-initiated fraud alert after identity verification and confirmation that recent transactions are legitimate, or velocity_clear for clearing a velocity block after identity verification and a reasonable explanation. Agent must always verify identity and document why the alert or block was cleared.

**Agent:** Review this activity: were the recent $26.14 grocery purchase and $41.80 pharmacy purchase on that card yours?

**Customer:** Yes, both were mine.

**Agent:** Say yes to clear the security alert you requested on that debit card.

**Customer:** yes

**Support console:** clear_debit_card_fraud_alert_4892(card_id="dc_3301", reason="customer_verified") succeeded. Interaction note documented: customer identity verified; customer confirmed recent transactions were legitimate.

**Agent:** The customer-requested card alert has been cleared.

**Customer:** Another card stopped after I made a bunch of purchases while traveling.

**Support console:** Velocity blocks are automatic temporary holds placed for unusual transaction patterns, including multiple rapid transactions, geographically distant transactions in a short time, sudden spending changes, and multiple declined transactions followed by successful ones. Velocity blocks automatically expire after 30 minutes but can be cleared earlier by a customer service agent only after identity verification and a reasonable explanation for the unusual activity.

**Agent:** A temporary unusual-activity block is on the card and automatically lifts after 30 minutes; to lift it early, tell me the reason for the rapid travel purchases.

**Customer:** I’m at a conference and bought train tickets, meals, and supplies within about 15 minutes.

**Support console:** Explanation is reasonable for travel and rapid purchases. Eligible to clear velocity block with reason velocity_clear.

**Agent:** Clear that temporary block by answering yes.

**Customer:** yes

**Support console:** clear_debit_card_fraud_alert_4892(card_id="dc_4417", reason="velocity_clear") succeeded. Interaction note documented: customer identity verified; travel explanation supports unusual activity.

**Agent:** The temporary block has been cleared.

**Customer:** My spouse’s card says stolen card on the receipt, but they say they never reported it stolen. What happens with that?

**Support console:** Decline Code 43 means Stolen Card and is security sensitive. Agent must use extra caution and must not immediately offer to unfreeze or reactivate. Enhanced verification requires full name, date of birth, and last 4 of SSN.

**Agent:** This security-sensitive card issue requires the cardholder to complete enhanced verification. Provide full name and date of birth.

**Customer:** I’m the cardholder too. My full name is Elena Rojas, date of birth 02/18/1990.

**Agent:** Next enhanced-verification factor: provide the last 4 digits of your SSN.

**Customer:** 4429.

**Support console:** Enhanced verification passed. After enhanced verification for Decline Code 43, agent explains card was reported stolen and stolen cards cannot be reactivated, and can order replacement with new number. If customer insists they never reported the card stolen, this is a major security flag indicating someone may have account access; agent must transfer to security team using transfer_to_human_agents and must not attempt to resolve it.

**Agent:** Enhanced verification is complete. That card was reported stolen, and stolen cards are not reactivated; a replacement with a new number can be ordered.

**Customer:** Nobody in this house made that report. The card was in the kitchen drawer the whole time.

**Agent:** A stolen-card report you say you never made needs our security team; I’ll transfer you to a human agent now.

**Support console:** transfer_to_human_agents(destination="security_team", reason="customer denies stolen-card report after enhanced verification") executed.

**Support console:** Security-sensitive decline-code handling reference: Decline Codes 04 Capture Card and 07 Pick Up Card handling per the fraud-desk script card. Decline Codes 34 and 59 indicate suspected fraud and are internal-use-only. Agent must not tell the customer the specific code or reason; customer-facing response is that a security matter affecting the card requires in-person verification at a branch with ID, and the agent must not attempt to clear or explain the code. Agents must never tell a customer over the phone that their card has been flagged for fraud.

**Support console:** Alert escalation reference: Bank-initiated fraud alerts are placed by Rho-Bank fraud detection systems for high-risk patterns, cannot be cleared by customer service agents, and require security team review. clear_debit_card_fraud_alert_4892 cannot clear bank-initiated fraud alerts; if attempting to clear one returns an error, transfer the customer to the security team. Escalate to security team when the fraud alert is bank-initiated, the customer cannot verify identity, the customer reports transactions they did not make, the agent suspects the caller may not be the account holder, or the explanation for unusual activity is suspicious or inconsistent.
