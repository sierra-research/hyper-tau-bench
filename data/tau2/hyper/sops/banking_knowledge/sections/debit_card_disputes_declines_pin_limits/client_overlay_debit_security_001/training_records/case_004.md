# Case D
Channel: chat
QA status: approved

**Customer:** I filed a debit-card dispute weeks ago and haven’t heard anything. Can you check the status and explain my rights?

**Agent:** To check the dispute record, send your email address and date of birth for verification.

**Customer:** omar.patel@outlook.com, 12/09/1979.

**Support console:** Identity verified. Use customer-facing plain-language outcomes. Escalate when timelines appear exceeded.

**Support console:** get_debit_dispute_status_7483(user_id: str) retrieves debit-card dispute history and open-dispute status. It returns a list of all debit-card disputes filed by the customer, including dispute_id, transaction_id, account_id, dispute_category, disputed_amount, filing_date, status, provisional_credit_issued, provisional_credit_amount, provisional_credit_date, expected_resolution_date, resolution if resolved, and resolution_date if resolved.

**Support console:** get_debit_dispute_status_7483(user_id="usr_4402") returned: dispute_id dsp_7001, transaction_id tx_4007, account_id chk_88740, dispute_category card_not_present_fraud, disputed_amount 233.19, filing_date 05/03/2025, status OPEN, provisional_credit_issued false, provisional_credit_amount 0.00, provisional_credit_date null, expected_resolution_date 06/17/2025, resolution null, resolution_date null.

**Support console:** Debit-card dispute status meanings: OPEN=filed and investigation in progress; PENDING_DOCUMENTATION=waiting on customer documentation; UNDER_REVIEW=investigation complete and final review; PROVISIONAL_CREDIT_ISSUED=provisional credit applied with investigation ongoing; RESOLVED_CUSTOMER_FAVOR=credit permanent; RESOLVED_BANK_FAVOR=valid transaction and no credit issued; RESOLVED_PARTIAL=partial credit issued; PROVISIONAL_REVERSED=provisional credit reversed after investigation; CLOSED_NO_RESPONSE=closure due to missing required documentation.

**Support console:** Regulatory timeline check required when checking dispute status. For disputes qualifying for provisional credit, provisional credit should be issued within 10 business days, or 20 business days for new accounts. Investigation should complete within 45 days, or 90 days for international transactions, POS transactions at merchants outside the US, or new accounts. Dispute dsp_7001 appears to exceed expected provisional-credit and resolution timelines for a standard account. Supervisor escalation required.

**Support console:** Supervisor escalation opened for dispute dsp_7001 due to apparent regulatory timeline overrun.

**Agent:** Your dispute is still open, and a supervisor escalation has been opened because the expected timing appears to have been exceeded.

**Customer:** What should have happened by now?

**Agent:** Standard qualifying disputes generally receive provisional credit within 10 business days if the investigation takes longer, and the investigation is generally completed within 45 days unless a 90-day timeline applies.

**Customer:** What kinds of problems should people report as debit disputes?

**Agent:** Report unauthorized transactions, ATM cash not dispensed, wrong ATM amount dispensed, ATM deposits not credited, duplicate charges, incorrect amounts, subscription issues after cancellation, or paid-for goods or services not received.

**Customer:** What information helps when reporting one?

**Agent:** Helpful reporting details include your account information, transaction date, amount, merchant if known, when you first noticed the issue, whether you still have the physical debit card, and any merchant communications.

**Customer:** Where can I file if it happens again?

**Agent:** Filing channels are 1-800-RHO-BANK, the Mobile App Report Issue feature on a transaction, and rhobank.com/disputes.

**Customer:** Is the phone line always open for fraud?

**Agent:** Fraud reports can be made at 1-800-RHO-BANK 24/7.

**Customer:** Should I file a police report too?

**Agent:** Rho-Bank recommends a police report for suspected fraud, especially for amounts over $500, because it can help the investigation and may be required for certain claims.

**Customer:** Can you explain Regulation E in plain English?

**Support console:** Regulation E applies to electronic fund transfers including debit card purchases by PIN and signature, ATM withdrawals and deposits, direct deposits, automatic bill payments, person-to-person transfers, and recurring electronic payments. It covers rights to dispute errors including unauthorized transactions, incorrect transaction amounts, missing deposits or transfers, computational errors, and transactions not completed as instructed. It applies specifically to debit card and electronic transactions, not credit cards. Business accounts may have different protections than personal accounts. Prompt statement review helps identify issues quickly and maximize protections.

**Agent:** Regulation E covers many debit-card and electronic transactions, including PIN and signature debit purchases, ATM withdrawals and deposits, direct deposits, automatic bill payments, person-to-person transfers, and recurring electronic payments.

**Customer:** What are the liability limits?

**Agent:** Liability for unauthorized debit-card use depends on how quickly it is reported after the statement first shows it; the caps for each reporting window are kept on the Reg E desk card.

**Customer:** What does the bank have to do after I report an error?

**Agent:** After an error report, Rho-Bank must investigate promptly, typically within 10 business days, report results within 3 business days after completing the investigation, and correct any confirmed error within 1 business day of the determination.

**Customer:** And if they need more time?

**Agent:** Extra investigation time triggers temporary provisional credit for qualifying disputes within 10 business days for standard accounts or within 20 business days for accounts open less than 30 days.

**Customer:** Do I get documents?

**Agent:** Documentation rights include written confirmation of error resolution, the ability to request copies of documents used in the investigation, and advance notice before provisional credit is reversed.

**Customer:** What should I do to protect those rights?

**Agent:** Protect those rights by contacting Rho-Bank as soon as you notice an unauthorized or erroneous transaction, providing the transaction details, following up with a written statement if requested, and keeping records of your communications.

**Customer:** Does this apply to my credit card too?

**Agent:** These protections apply to debit-card and electronic transactions, not credit cards; business accounts may have different protections than personal accounts.

**Customer:** Remind me—what exactly is Regulation E?

**Agent:** Regulation E is a federal regulation implemented by the Consumer Financial Protection Bureau, or CFPB. It governs electronic fund transfers and provides important consumer protections for debit card transactions.
