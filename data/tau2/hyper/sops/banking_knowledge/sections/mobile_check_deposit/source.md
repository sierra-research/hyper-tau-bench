## Mobile check deposit procedure and issue resolution

### doc_bank_accounts_bank_accounts_(general)_011: Depositing a Check Into Your Account

## Summary
Customers can deposit checks into their checking or savings accounts using mobile check deposit. To help a customer deposit a check, give them the deposit_check_3847 tool. Have the user call deposit_check_3847(account_id, check_amount) where account_id is the ID of the account they want to deposit into and check_amount is the amount of the check in USD. The customer will take a photo of the front and back of the check through their mobile banking app. Funds availability depends on the account type and deposit amount. Standard deposits are typically available within 1-2 business days. Note: The agent cannot deposit checks on behalf of the customer - this action must be performed by the customer themselves through the mobile app.

## Before you start
- Confirm the check is payable to the account owner(s) and is not altered or damaged.
- Endorse the back of the check. Include any required restrictive endorsement (for example, “For mobile deposit only”).
- Ensure the check date and numeric/written amounts match.

## Step-by-step: Mobile check deposit
1. Open the Rho-Bank mobile app and sign in.
2. Select the checking or savings account you want to deposit into.
3. Choose Mobile Check Deposit.
4. Enter the check amount exactly as printed.
5. Capture photos:
   - Front: all four corners visible, no shadows or glare.
   - Back: clear endorsement and all corners visible.
6. Review deposit details, confirm the destination account, and submit.
7. Keep the paper check in a secure place until the deposit is posted, then destroy it.

## If you are working with an agent
- To help you initiate the process, the agent will provide access to the deposit_check_3847 tool.
- You will be prompted to call deposit_check_3847(account_id, check_amount) from within the app’s flow to specify the destination account and the amount.
- The agent cannot deposit checks on your behalf. You must complete the deposit yourself in the mobile app.

## Photo and submission tips
- Place the check on a dark, flat background with good, even lighting.
- Turn off flash if it causes glare; avoid shadows and folded edges.
- Align the check within the on-screen guidelines; refocus by tapping the screen if needed.
- Confirm the amount you entered matches the printed amount before submitting.

## Funds availability
- Availability depends on your account type and the deposit amount.
- Standard deposits are typically available within 1-2 business days.
- Certain deposits may be subject to extended review. You will see the expected availability date in the app after submission.

## Common issues and how to resolve them
- Image quality error: Retake photos with better lighting and ensure all corners are visible.
- Endorsement missing: Sign the back and include the required restrictive wording, then resubmit.
- Amount mismatch: Edit the entered amount to exactly match the check and resubmit.
- Duplicate deposit detected: Do not attempt to redeposit. If you believe this is an error, contact support through the app.
- Unsupported or ineligible items: Some checks are not eligible for mobile deposit (for example, altered or incomplete checks). Deposit a different check that meets eligibility requirements.

## After you submit
- Monitor deposit status in the app’s transaction history for updates and availability.
- Retain the paper check until the deposit shows as posted and available, then securely destroy it.

Shared context paths (construction metadata, not policy facts):
- `tau2/hyper/sops/banking_sop.md`
