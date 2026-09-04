# Case B
Channel: chat
QA status: approved

**Customer:** My Green checking debit card showed a PIN decline. What do codes 55, 75, and 83 mean?

**Agent:** Before reviewing card-specific PIN status, please provide your email address and date of birth.

**Customer:** mina.lee@outlook.com, September 8, 1989.

**Support console:** Identity verified. PIN decline reference loaded. Code 55 means incorrect PIN; inspect pin_locked and pin_attempts_remaining. If unlocked with few attempts left, warn with the remaining count and offer PIN reset if forgotten. If locked, complete the PIN Lock Investigation Protocol - Fraud Risk Scoring using location, time, amount patterns, and other factors before any unlock; its result determines unlock, enhanced verification, or recommended closure. Code 75 uses that same locked-card path. Code 83 is a network-verification issue, not an incorrect PIN.

**Customer:** Suppose code 55 shows the card is not locked and only one attempt remains.

**Agent:** You have 1 PIN attempt remaining before your card is temporarily locked. If you have forgotten the PIN, I can help with a PIN reset.

**Customer:** What if code 55 says it is already locked, or I see code 75?

**Agent:** A locked code 55 or code 75 requires the PIN-lock fraud-risk investigation before any action. That assessment considers location, time, amount patterns, and other factors, then determines whether to unlock, require enhanced verification, or recommend card closure.

**Customer:** And code 83?

**Agent:** There was a temporary issue verifying your PIN. This wasn't because your PIN was incorrect - it was a network communication problem.

**Customer:** What should I try?

**Agent:** Retry the transaction first, because that usually resolves code 83.

**Customer:** If it keeps happening?

**Agent:** If the merchant permits it, try a signature-based transaction instead of PIN.

**Customer:** And if that is unavailable?

**Agent:** Try a different terminal or merchant.

**Customer:** What is the final retry option?

**Agent:** Wait 10-15 minutes, then retry the transaction.
