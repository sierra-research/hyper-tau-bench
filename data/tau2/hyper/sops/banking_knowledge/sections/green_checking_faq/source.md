## Green Account checking fees, transfers, and PIN-decline FAQ

### doc_checking_accounts_green_account_(checking)_010: FAQ: Green Account (checking)

## Frequently asked questions

### Do I pay for paper statements?
- Yes, paper statements delivered by mail cost $2.50 per month.

### Does this account earn interest?
- Yes. Your balance earns 0.11% APY.

### What is the fee for using a non-network ATM?
- The fee for out-of-network withdrawals is $3.00 per withdrawal.

### How long do transfers to another bank take?
- Transfers to external banks generally complete in 3 business days.

### What happens if a check I deposit is returned unpaid?
- A returned deposit incurs a fee of $17.50.

### Is there a fee to receive a domestic wire?
- Yes. Incoming domestic wires cost $15.00.

## Debit Card Decline Codes - PIN-Related Issues

If your debit card is declined due to PIN problems, you may see one of the following codes:

### CODE 55 - Incorrect PIN

Wrong PIN was entered. The card's pin_locked and pin_attempts_remaining fields from the debit card lookup show the status.

1. If pin_locked is FALSE but pin_attempts_remaining is low:
   - Warn customer: 'You have [X] PIN attempts remaining before your card is temporarily locked.'
   - If they've forgotten: Offer/help them PIN reset.

2. If pin_locked is TRUE:
   - **IMPORTANT**: Before unlocking, you MUST follow the 'Internal: PIN Lock Investigation Protocol - Fraud Risk Scoring' document.
   - This protocol requires calculating a fraud risk score based on location, time, amount patterns, and other factors.
   - Do NOT simply unlock the card without completing the fraud risk assessment.
   - The protocol will guide you on whether to unlock, require enhanced verification, or recommend card closure.

### CODE 75 - PIN Tries Exceeded

Same as Code 55 when pin_locked is TRUE. Follow the PIN Lock Investigation Protocol before taking any action.

### CODE 83 - Unable to Verify PIN

The network couldn't verify the PIN due to a technical issue - this does NOT mean the PIN was wrong.

1. Explain: 'There was a temporary issue verifying your PIN. This wasn't because your PIN was incorrect - it was a network communication problem.'

2. Advise customer to try the transaction again. This usually resolves on retry.

3. If it keeps happening:
   - Try a signature-based transaction instead of PIN if the merchant allows.
   - Try a different terminal or merchant.
   - If persistent, wait 10-15 minutes and retry.

Shared context paths (construction metadata, not policy facts):
- `tau2/hyper/sops/banking_sop.md`
