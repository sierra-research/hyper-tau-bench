# Case 013

Case ID: SAV-2511-0190
Channel: Email
Contact date: 2025-11-08
Handle time: 8h 2m (same-day email resolution)
QA status: Approved

## Transcript

[Nov 8, 09:14] **Customer (email):** Good morning. I am writing about the interest posted to my Silver Plus Account on November 1. For months, each posting has reflected the card bonus for the EcoCard I hold with you; I reconcile my statements monthly and the figures have always agreed with mine. This month's does not. Working backwards from the amount, the November 1 interest appears to have been calculated at the base rate alone, with no card bonus whatsoever. I would appreciate a written explanation and, if my reading is correct, a correction. Please handle this by email — I prefer numbers I can reread to numbers said quickly on a phone. Margaret Holloway.

[Nov 8, 10:39] **Support console:** get_all_user_accounts_by_user_id_3847 executed for RB-2765981. Returned: Silver Plus Account savings ····6634 (open, good standing); EcoCard ····2219 (active, same profile). get_bank_account_transactions_9173 executed for account ····6634: interest credit posted 2025-11-01 at base rate only; card bonus component absent all cycle.

[Nov 8, 10:47] **Case note:** Ana B. — Identity: message received from the email of record on profile RB-2765981; date of birth confirmed via the secure-message form attached to her request. Account pull and cycle history above; card active and in good standing all cycle. Components: Silver Plus base today 4.5; EcoCard bonus per the card program terms the Silver Plus sheet's card table routes to; expected 4.95. The October cycle paid 4.5 flat — her card bonus came across at zero, which matches a different product's table, not hers. Her reading is correct; the cycle difference is $7.42. Plan: file the discrepancy report first and let backend confirm the component values before the credit goes on — if their number differs from mine, I'd rather not claw anything back from her account.

[Nov 8, 13:36] **Case note:** C. Mercer (supervisor) — Ana, your components and your $7.42 are right; your sequence isn't. Before you send anything, look at the current revision of the report board: RATE-OPS-102 rev C, dated October 8. The ordering you're describing is the September draft of that board, and the draft never went live. Your numbers are already confirmed against the current records — that's the confirmation the desk acts on. The credit goes on today; the report follows it, same day.

[Nov 8, 15:41] **Case note:** Ana B. — Understood, and glad you caught it before it reached her inbox with the wrong promise in it. Rev C is now pinned over my monitor. Proceeding: credit now, report right behind it, written explanation to follow.

[Nov 8, 15:58] **Support console:** apply_savings_account_credit_6831 executed: account_id ····6634, amount 7.42, credit_type interest_correction. Credit posted.

[Nov 8, 16:05] **Support console:** submit_interest_discrepancy_report_7294 executed: account_id ····6634, user_id RB-2765981, expected_apy 4.95, actual_apy 4.5, amount_difference 7.42. Report accepted; backend queue reference returned.

[Nov 8, 16:18] **Agent (email):** Dear Ms. Holloway, thank you for the precise write-up — it made this quick. Your reading is correct, and here is the arithmetic in writing, as requested. Your rate has two components: the Silver Plus base rate, currently 4.5%, which online banking displays as of the current day, and the EcoCard bonus per the card program terms the current Silver Plus Account sheet routes to — 4.95% together. The November 1 posting was calculated at 4.5% alone, although your card was active and eligible the entire cycle. The difference for the October cycle is $7.42, credited to your account today as an interest correction — its own line item, dated November 8. I have also filed a discrepancy report with our backend team so the cause is fixed at the source; the December 1 posting should arrive with both components and no action from you. The current Silver Plus sheet is attached so your records and ours reconcile from the same page. If December disagrees with it, reply to this thread and reference this case. Kind regards, Ana, Rho Bank deposit desk.

[Nov 8, 17:16] **Customer (email):** Received, and the credit is already showing. The attachment is exactly what I wanted — my previous copy evidently predates this one. I appreciate a bank that will put arithmetic in writing. Consider the matter closed on my end. M.H.
