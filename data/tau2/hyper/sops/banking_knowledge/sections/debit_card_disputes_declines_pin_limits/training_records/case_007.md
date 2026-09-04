# Case G
Channel: chat
QA status: approved

**Customer:** I’m seeing error messages and debit-card declines. I also need account-limit details for my teen and Light Blue accounts.

**Agent:** Verification comes first for account-specific decline and limit details: send your email address and date of birth.

**Customer:** priya.shah@icloud.com, 05/29/1981.

**Support console:** Identity verified. Keep internal decline diagnostics in Support console when required.

**Customer:** The app showed Error 101 when I tried to add an external account.

**Support console:** Common error-code process: identify the error code, confirm the action the customer attempted, and follow suggested resolution. Error 101 invalid account or routing details: ask customer to verify and re-enter account and routing numbers exactly as issued by their bank. Error 202 insufficient funds: suggest depositing funds or reducing payment or transfer amount then retrying. Error 403 authentication failed: have customer reset password, confirm correct profile, and check for account security holds. Error 409 duplicate transaction request: advise waiting for initial request to settle or cancel before attempting again. Error 429 too many attempts: recommend waiting before retrying and ensuring details are correct to avoid rate limits. Error 903 account closure request blocked: instruct customer to wait 48 hours and try again. If common errors persist, capture screenshots, timestamps, exact workflow leading to the error; verify device, browser, and app version details; escalate with logs if multiple attempts produce same result.

**Agent:** Error 101 during external-account setup means the account or routing details should be verified and re-entered exactly as issued by that bank.

**Customer:** If it keeps happening, what should I collect?

**Agent:** For repeats of that error, collect screenshots, timestamps, the exact steps that led to the error, and your device, browser, and app version details.

**Customer:** My Green Account debit card was declined at a grocery store even though I had money.

**Support console:** Decline Code 51 Insufficient Funds requires first looking up checking account balance. If balance appears sufficient for the transaction, check authorization holds, pending transactions, and overdraft settings. Checking account chk_10088 balance: posted balance $512.40, available balance $318.11. Pending debits total $94.29. Authorization hold from fuel station $100.00. overdraft_pos_enabled=false.

**Support console:** Authorization hold reference: temporary hold on funds not available for use. Merchants use holds to verify card validity and sufficient funds before providing goods or services, or to secure a temporary deposit that may be adjusted when final amount is known. Holds may not show immediately in recent transactions but reduce available balance until released or finalized. If merchant finalizes charge, hold converts to posted transaction; if merchant releases or reduces hold, corresponding amount returns to available balance. Rho-Bank keeps a temporary hold on paycheck deposits that are then refunded, which can affect available balance shortly after a deposit posts.

**Support console:** Lower or negative balance causes: overdraft protections temporarily covering transactions, authorization holds reducing available balance, pending card transactions and checks decreasing available funds before posting, scheduled payments or transfers being earmarked. Review and resolution steps: check pending and posted activity, add funds or transfer money from another account, contact merchant if a hold seems higher than expected, review and adjust overdraft settings, contact support with transaction details and timestamps if something looks incorrect.

**Agent:** Available balance drove the decline, not just posted balance. Pending debits and a fuel-station hold reduced your available balance to $318.11.

**Customer:** The grocery amount was $340. What should I do?

**Agent:** Before retrying, add enough funds to cover the full authorization amount.

**Customer:** What if the balance looked sufficient?

**Agent:** A balance that looks sufficient still requires checking authorization holds, pending transactions, and whether the account is opted into debit-card overdraft coverage.

**Customer:** Am I opted in?

**Agent:** Debit-card purchase overdraft coverage is not enabled on your account, so a purchase can decline instead of overdrawing at the point of sale. The overdraft features documentation explains the opt-in choices.

**Support console:** Regulation E requires customer opt-in for POS and ATM overdraft coverage. If overdraft_pos_enabled is FALSE, explain account is not opted into overdraft coverage for debit-card purchases, offer to explain options, and reference overdraft features documentation. If balance is genuinely insufficient, inform customer of balance, offer options to transfer funds from another account or make smaller transaction, and help with transfer if customer wants.

**Customer:** Does Green Account have special decline checks?

**Support console:** Green Account declined transaction troubleshooting quick checks: verify available balance covers full amount requested, review pending authorizations reducing available balance, check decline notification message details if customer received one. Merchant-specific checks: confirm merchant did not attempt a higher amount than expected; for subscription or recurring charges ensure funds are available on charge date. Common reasons: requested amount exceeding available balance at authorization, pending card holds reducing available balance, merchant presenting final amount higher than initial estimate. Resolution: add funds and retry; contact merchant to verify attempted amount if decline persists after funding; keep records of decline notice if alerts were received. To confirm and resolve: check decline notification, review recent activity for pending holds or prior transactions using available funds, add funds and try again, ask merchant to confirm amount submitted for authorization.

**Agent:** Green Account declines usually start with checking whether available balance covered the full authorization amount and whether pending holds reduced available funds.

**Customer:** I also got a generic Do Not Honor decline yesterday.

**Support console:** Decline Code 05 Do Not Honor is a catch-all generic decline requiring investigation in order: card status, account status, fraud alert, then velocity block. Card status checks: FROZEN, ask whether customer wants to unfreeze and follow freezing/unfreezing protocol if yes; CLOSED, inform card is no longer active and check for another active card or offer replacement; PENDING, follow activation protocol; ACTIVE, continue to account status. Account status checks: look up linked checking account status; if status is not OPEN, inform customer account has a restriction preventing transactions, do not provide specific details if SUSPENDED or RESTRICTED, direct to branch or 1-800-RHO-ACCT. Fraud alert checks: if fraud_alert_active TRUE and alert_source customer_initiated, verify identity, ask customer to verify recent transactions, clear only if all legitimate; if alert_source bank_initiated, do not clear, tell customer additional security review is required, and transfer to human agents. Velocity block checks: if velocity_blocked TRUE, inform customer card was temporarily blocked due to unusual activity patterns and automatically lifts after 30 minutes; to lift early, verify identity, obtain reasonable explanation, and clear only if satisfactory.

**Agent:** Generic Do Not Honor diagnostics follow this order: card status first, then linked account status, then customer-requested alerts, then temporary unusual-activity blocks.

**Customer:** What about invalid card number, expired card, and no card record?

**Support console:** Decline Code 14 Invalid Card Number means entered card number does not match records. Possible causes and resolutions: typo, ask customer to verify correct card; replaced card, look up all debit cards and if newer ACTIVE card and older CLOSED card exist, tell customer to use new card ending in returned last 4, or if new card is PENDING help activate it; old saved card online, advise updating saved merchant card details. Decline Code 54 Expired Card requires debit-card lookup and checking expiration_date; if expired, check for replacement with issue_reason expired and status PENDING or ACTIVE, guide activation if PENDING, direct customer to new card if ACTIVE, order replacement if none exists. Decline Code 56 No Card Record means card number format is valid but no record exists in Rho-Bank system, unlike Code 14. Possible causes: lost or stolen card fully purged, customer using different bank card, merchant data entry error. Ask customer to verify Rho-Bank logo, look up cards for account, and if last 4 does not match any card on file, offer to order a new card.

**Agent:** Invalid-card-number declines usually mean the entered number does not match the card record; start by checking the card number on the physical or saved card.

**Customer:** My old closed checking account card gave No Checking Account once.

**Support console:** Decline Code 52 No Checking Account means PIN was accepted but underlying checking account has issues. Look up accounts. If account status CLOSED, tell customer linked checking account has been closed and card can no longer be used, and discuss opening a new checking account if customer wants to continue banking with Rho-Bank. If account exists and is OPEN but customer still receives code, treat as possible system synchronization issue and advise waiting 10 to 15 minutes and retrying.

**Agent:** Closed linked checking accounts make the debit card unusable with that account.

**Customer:** What if the account is actually open?

**Agent:** An open checking account with that message may indicate a synchronization issue, so wait 10 to 15 minutes and retry.

**Customer:** I also saw transaction not permitted.

**Support console:** Decline Code 57 Transaction Not Permitted to Cardholder means restrictions block the transaction type; agent must check restrictions from debit-card lookup. MCC blocks: check restricted_mccs. Common blocks are gambling MCC 7995, adult content MCC 5967, cryptocurrency MCC 6051. For gambling or adult content, do not remove MCC blocks over the phone; tell customer these restrictions can only be modified through mobile app or by visiting a branch in person. International transactions: if international_enabled=false and transaction was international, inform international transactions are blocked and ask whether customer wants enabled. Online transactions: if online_enabled=false, inform online or card-not-present transactions are blocked and ask whether customer wants enabled. Teen or Light Green Account restrictions: if account_class is Light Green Account, parental controls may restrict certain transaction types; primary account holder can modify settings; agent must not modify parental controls without guardian authorization.

**Agent:** Transaction-not-permitted declines come from card restrictions, such as merchant category, international, online, or parental-control settings.

**Customer:** The decline was at an international online merchant.

**Agent:** International and online permissions should be checked on the card before that purchase can be retried.

**Customer:** Another store said terminal not permitted.

**Support console:** Decline Code 58 Transaction Not Permitted to Terminal means the specific merchant terminal is blocked, typically because it is flagged. Customer or agent cannot resolve the terminal flag; customer should try a different register at the same store or a different merchant. If issue occurs at multiple unrelated terminals, it may indicate a card issue and agent should follow Code 05 diagnostic steps.

**Agent:** At one terminal, try a different register at the same store.

**Customer:** If it happens at several stores?

**Agent:** Multiple unrelated terminals point back to a card review using the generic decline checks.

**Customer:** My ATM also said I exceeded the withdrawal amount limit.

**Support console:** Decline Code 61 Exceeds Withdrawal Amount Limit means transaction exceeds card daily purchase or ATM limit. Check daily_purchase_limit, daily_atm_limit, daily_purchase_used, daily_atm_used; calculate relevant daily limit, amount used, remaining available amount. If customer needs higher limit, temporary increase lasts 24 hours, permanent increases depend on account tier, Elite tier can request permanent increases, and agent can offer temporary increase lasting 24 hours. For ATM limits at non-Rho ATMs, the other bank’s ATM may have its own lower limit that Rho-Bank cannot override.

**Support console:** Card dc_7002 daily_atm_limit $500.00, daily_atm_used $420.00, remaining ATM amount $80.00. daily_purchase_limit $1,500.00, daily_purchase_used $232.00.

**Agent:** ATM withdrawal availability today is $80: the daily ATM limit is $500, and $420 has already been used.

**Customer:** Can that limit be raised permanently?

**Agent:** Permanent limit increases depend on account tier, and Elite tier can request permanent increases; a temporary increase can be requested for 24 hours.

**Customer:** I also got restricted card while traveling.

**Support console:** Decline Code 62 Restricted Card can be caused by geographic restrictions; check allowed_regions and blocked_regions. If customer traveling, explain card is restricted to current regions and agent can add travel region. If card was issued within last 24 hours based on date_issued, a new-card security hold may be present while systems are being set up and should clear within 24 hours of activation.

**Agent:** Travel-related restricted-card declines can happen when the card is limited to current regions, and a travel region can be added after confirming the trip.

**Customer:** My card is brand new too.

**Agent:** New-card security holds may clear within 24 hours of activation when the card was issued within the last 24 hours.

**Customer:** One decline said activity count exceeded.

**Support console:** Decline Code 65 Activity Count Exceeded means too many transactions in current period. Check daily_transaction_count and daily_transaction_limit and explain card allows daily limit and customer has made current count. Transaction count limits are typically fixed and cannot be increased, so customer must wait until midnight for reset; if customer has multiple Rho-Bank accounts, they could use a different card.

**Agent:** Activity-count declines reset at midnight, and those count limits are typically fixed rather than increased.

**Customer:** I’m thinking of opening a Light Green Account for my teen. What are the requirements?

**Support console:** Light Green Account eligibility: customer must be primary account holder and be between 13 and 24 years old; must remain within 13 to 24 age range to maintain account. Eligibility determined by date of birth at opening and ongoing; once outside the range, customer is no longer eligible to maintain it. Key specs: no overdraft fees; 0.05% APY on account balance; $0.00 monthly maintenance fee; $12.50 returned deposit fee per returned item; $10.00 incoming domestic wire transfer fee per incoming wire; debit card daily purchase limit $250 per day. Linked savings APY boosts: 0.65% APY boost for linked Platinum Savings Account; 0.2% APY boost for linked Diamond Elite Savings Account. Referral program: referred person must deposit at least $100 within 90 days of opening; referrer must have opened first Rho-Bank checking account at least 14 days ago. Minor spending limits and safety features: card-based purchases capped at $300 per day; ATM cash withdrawals limited to $150 per day; EveryonePay person-to-person payments limited to $250 per day; parent or guardian notifications triggered for transactions at or above $62; monitoring should align alert threshold with typical spending patterns.

**Agent:** Light Green eligibility requires the primary account holder to be age 13 through 24, and the customer must remain in that age range to maintain the account.

**Customer:** What are the main fees and rates?

**Agent:** Main Light Green fees and rates are no overdraft fees, 0.05% APY, a $0 monthly maintenance fee, a $12.50 returned deposit fee per returned item, and a $10 incoming domestic wire fee per incoming wire.

**Customer:** Does it have linked savings boosts?

**Agent:** Linked-savings boosts are 0.65% APY with a linked Platinum Savings Account and 0.2% APY with a linked Diamond Elite Savings Account.

**Customer:** How does the referral work?

**Agent:** The Light Green referral program requires the referred person to deposit at least $100 within 90 days of opening, and the referrer must have opened their first Rho-Bank checking account at least 14 days ago.

**Customer:** What safety limits apply for minors?

**Agent:** Minor safety features include card-based purchases capped at $300 per day, daily ATM withdrawals limited to $150, EveryonePay payments limited to $250 per day, and guardian notifications for transactions at or above $62.

**Customer:** And what are Light Blue quick facts?

**Support console:** Light Blue Account quick facts: 0% APY on balance, $2,000 daily mobile check deposit limit, and 0 days early direct deposit before payday. If customer plans to deposit multiple checks in one day, they should track the total to stay within $2,000 daily limit, and account offers 0 days early access to direct deposits.

**Agent:** Light Blue quick facts are 0% APY, a $2,000 daily mobile check deposit limit, and 0 days early direct deposit access before payday.
