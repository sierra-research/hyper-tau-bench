# Case F
Channel: chat
QA status: approved

**Customer:** My debit card hit the ATM limit, and now the PIN is locked. I need help today.

**Agent:** We’ll start with verification before reviewing the limit request and PIN lock; send your email address and date of birth.

**Customer:** malik.jordan@yahoo.com, 08/06/1984.

**Support console:** Identity verified. Do not reveal internal PIN-lock risk calculations to the customer.

**Support console:** Temporary debit-card limit increase eligibility requirements: linked checking account must be OPEN and in good standing; account must be at least 60 days old; no overdraft fees in the last 30 days; debit card must be ACTIVE. Card dc_9099 is ACTIVE. Account chk_33045 is OPEN, 214 days old, good standing, no overdraft fees in last 30 days. Current daily ATM limit $500.00. No temporary increase used in last 24 hours. Only one temporary debit-card limit increase is allowed per 24-hour period per card. Temporary increase cannot exceed 150% of current limit, a 50% maximum boost. Temporary increases last 24 hours and automatically revert. Third-party ATMs may have their own limits that Rho-Bank cannot override.

**Agent:** Your card is eligible for a temporary ATM limit increase up to $750, which lasts 24 hours and then automatically reverts.

**Customer:** I want $900.

**Agent:** A $900 temporary ATM limit is above the maximum for this card. Answer yes if you want the $750 request submitted.

**Customer:** yes

**Support console:** request_temporary_debit_card_limit_increase_8374 requires card_id, limit_type of atm or purchase, and new_limit. request_temporary_debit_card_limit_increase_8374(card_id="dc_9099", limit_type="atm", new_limit=750.00) succeeded.

**Agent:** Your temporary ATM limit is now $750 for 24 hours. A non-Rho ATM may still apply its own lower limit.

**Customer:** Now what about the PIN lock?

**Support console:** Card dc_9099 has pin_locked=TRUE. Agents must perform comprehensive fraud risk assessment before unlocking and must not reveal specific calculations to users. Automatic escalation triggers must be checked before calculating fraud-risk flags; if any automatic trigger is present, follow that path, otherwise proceed to score calculation. If pin_lock_reason is security_hold, chat agents cannot unlock and should offer transfer to security team for that card. Another card on same account, dc_7780, also has pin_locked=TRUE, so all cards must be investigated before any unlock and each card must be scored individually. Card dc_7780 pin_lock_reason=security_hold. Card dc_9099 pin_lock_reason=failed_pin_attempts. Account has a card replaced in last 90 days with issue_reason stolen, so enhanced verification is required.

**Agent:** One additional verification step is required before I review the PIN lock. Provide the last 4 digits of your SSN.

**Customer:** 1180.

**Agent:** Answer your security question: what was the name of your first school?

**Customer:** Lincoln.

**Support console:** Enhanced verification passed. PIN-lock scoring uses declined transaction history with type atm_withdrawal_declined or pos_declined and card data.

**Support console:** Internal PIN-lock risk table:
- A1 Location Mismatch compares declined-transaction city to customer address city: same city 0; different city same state 1; different state 2; different country 3 with critical severity.
- A2 Location Scatter: all same location 0; 2 different locations 1; 3 or more different locations 2.
- A3 Travel Pattern Conflict checks successful transactions in last 7 days: all successful transactions in home city but declines elsewhere add 1; recent transactions in various cities indicating travel add 0.
- B1 Time of Day: 6 AM-10 PM 0; 10 PM-12 AM 1; 12 AM-2 AM 2; 2 AM-6 AM 3 with high risk.
- B2 Time Since Last Legitimate PIN Use: less than 24 hours 0; 1-7 days 0; 7-30 days 1; more than 30 days 2.
- B3 Attempt Velocity: more than 5 minutes apart 0; 2-5 minutes apart 1; 1-2 minutes apart 2; less than 1 minute apart 3 with scripted attack severity.
- C1 Amount Pattern: consistent same amounts retried 0; increasing amounts 0; decreasing amounts such as 800 to 500 to 300 is 2 with fraud pattern severity.
- C2 Round Number Testing: mixed amounts 0; all round hundreds such as 800, 500, or 300 is 1.
- C3 Amount vs Historical Average: within 2x average 0; 2-5x average 1; more than 5x average 2.
- C4 Amount vs Daily Limit: less than 50% of limit 0; 50%-80% of limit 0; 80%-100% of limit 1; multiple attempts totaling more than daily limit 2.
- D1 Lock Frequency in last 90 days: 0 prior locks 0; 1 prior lock 1; 2 prior locks 2; 3 or more prior locks 3 with automatic PIN reset required and cannot unlock.
- D2 Card Age: more than 1 year 0; 6-12 months 0; 3-6 months 0; 1-3 months 1; less than 1 month 2.
- D3 Other Card Issues: all other cards no issues 0; another card has velocity block add 1; another card has fraud alert active add 2.
- E1 Account Age: more than 2 years 0; 1-2 years 0; 6-12 months 0; 3-6 months 1; less than 3 months 2.
- E2 Overdraft History: no overdrafts 0; 1 overdraft 1; 2 or more overdrafts 2.
- E3 Low Balance Alert: more than $500 0; $100-$500 0; $50-$100 1; less than $50 2 with account may be abandoned or compromised severity.
- Total score thresholds, subject to automatic escalation triggers and the rule that any single 3-point flag requires supervisor review regardless of total score: 0-4 LOW, unlock after standard identity verification; 5-7 MEDIUM, unlock only after asking whether failed PIN attempts were the customer’s; 8-10 HIGH, ask specific location and time questions and unlock only if customer confirms with satisfactory explanation; 11-14 VERY HIGH, cannot unlock on this call and require callback verification or enhanced verification with last 4 SSN plus security question; 15 or more CRITICAL, cannot unlock, check for successful unauthorized transactions, and recommend card closure and replacement.
- For PIN-lock scores of 5 or higher, if Location Mismatch is scored, ask whether customer was at declined-attempt location; if yes, remove location flags and recalculate; if no, maintain score and proceed with caution.
- For scores of 5 or higher, if Amount Pattern is scored, ask whether customer remembers trying specific attempted amounts; if confirmed, remove amount pattern flag; if denied or confused, maintain flag.
- For scores of 5 or higher, if Time of Day is scored 2 or more, ask whether customer was trying to use the card at that time; if confirmed, remove time flag; if customer says they were asleep or similar, treat as critical and likely fraud.
- Post-unlock D1 steps: 0 prior locks, standard unlock with no additional steps; 1 prior lock, offer PIN lock notifications; 2 prior locks, ask whether customer wants PIN reset to a new number because this is the third PIN lock in 90 days; 3 or more prior locks, cannot unlock and must reset PIN.

**Support console:** Card dc_9099 score before customer challenge is HIGH due to location mismatch, time, and amount-pattern flags. No single flag equals 3, so supervisor review is not automatically required. Because score is 5 or higher and location is scored, ask location question.

**Agent:** Were you at the Midtown ATM location for the declined PIN attempts yesterday evening?

**Customer:** Yes, I was at that ATM.

**Support console:** Customer confirmed location. Removed location flags and recalculated. Amount Pattern remains scored, so ask amount question.

**Agent:** Do you remember trying the $500, $300, and $200 withdrawal amounts?

**Customer:** Yes. I tried smaller amounts after the first one failed.

**Support console:** Customer confirmed attempted amounts. Removed amount-pattern flag and recalculated. Time of Day flag was under 2 points, so no time challenge required. Final score LOW. D1 lock frequency is 1 prior lock.

**Agent:** Say yes when ready to unlock the PIN on the card ending in 9099.

**Customer:** yes

**Support console:** Eligible PIN unlock completed for card dc_9099. Post-unlock requirement for D1=1 prior lock: offer PIN lock notifications.

**Agent:** PIN access on the card ending in 9099 has been cleared. Because this is not the first PIN lock in 90 days, PIN lock notifications are available.

**Customer:** What about the other locked card?

**Support console:** Card dc_7780 pin_lock_reason=security_hold. Chat agents cannot unlock. Automatic escalation path applies before score calculation.

**Agent:** Security hold is present on the other locked card, so chat support does not unlock it. A security review transfer is available for that card; confirm yes if you want that transfer now.

**Customer:** Not right now. What if a lock cannot be cleared after review?

**Support console:** If a PIN-locked card cannot be unlocked due to score thresholds or automatic escalation triggers, first check transaction history for successful unauthorized transactions during the suspicious period. If unauthorized transactions are found, file a dispute, close the card, and order a replacement. If no unauthorized transactions are found, explain the security concern and offer card closure and replacement, transfer to the security team for investigation, or PIN reset that issues a new PIN and invalidates potential compromise; card closure and replacement is recommended if fraud is suspected.

**Agent:** When a PIN lock is not eligible to clear, the first check is whether any completed unauthorized transactions occurred during the suspicious period.
