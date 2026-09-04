# Case A
Channel: chat
QA status: approved

**Customer:** Can you deposit this $840 check into my savings account for me?

**Agent:** Mobile check deposits must be completed by you through the Rho-Bank app. Before starting, confirm that the check is payable to the account owner, is not altered or damaged, has a valid date with matching written and numeric amounts, and is endorsed on the back with any required wording such as "For mobile deposit only."

**Customer:** It passes those checks. What do I do first?

**Support console:** Customer-owned action boundary: provide deposit_check_3847. Customer must call deposit_check_3847(account_id, check_amount); account_id is the destination checking or savings account ID, and check_amount is the USD amount. Agent must not call the tool.

**Agent:** First, open the Rho-Bank mobile app. Tell me when it is open.

**Customer:** The app is open.

**Agent:** Sign in to the app. Tell me when you are signed in.

**Customer:** I'm signed in.

**Agent:** Select the savings account that should receive the deposit. Tell me when it is selected.

**Customer:** The destination savings account is selected.

**Agent:** Choose Mobile Check Deposit in the app.

**Customer:** I selected Mobile Check Deposit.

**Agent:** Enter $840 exactly as printed on the check.

**Customer:** The amount is entered.

**Agent:** I'm providing access to deposit_check_3847. Call deposit_check_3847 with the selected savings account's account_id and check_amount 840.

**Customer:** I called it with that account ID and check amount.

**Support console:** Customer called deposit_check_3847 with the selected savings account ID and check_amount 840. The customer remains responsible for photo capture, review, and submission in the app.

**Customer:** How should I photograph the front?

**Agent:** Place the check on a dark, flat surface with even lighting, align it within the on-screen guide, and photograph the front with all four corners visible and no shadows or glare. Turn off flash if it causes glare, avoid folded edges, and tap to refocus if needed.

**Customer:** The front photo is complete. What about the back?

**Agent:** Photograph the back with the endorsement clear and all four corners visible, using the same even lighting and on-screen alignment.

**Customer:** Both photos are complete. What should I check before submitting?

**Agent:** Review the deposit details and confirm that the entered amount matches the printed amount and that the selected savings account is the intended destination. Tell me when the review is complete.

**Customer:** The amount and destination are correct.

**Agent:** Submit the deposit in the app.

**Customer:** It is submitted.

**Support console:** Front and back capture and submission completed in the app. Availability depends on account type and amount; standard deposits are typically available in 1-2 business days, and the transaction history shows posting and availability updates.

**Agent:** Keep the paper check secure while the deposit is pending.

**Customer:** I'll keep it secure. How will I know when the deposit is ready?

**Agent:** Monitor the transaction history for posting and availability.

**Customer:** It now shows as posted and available. What should I do with the check?

**Agent:** Securely destroy the paper check now that the deposit is posted and available.
