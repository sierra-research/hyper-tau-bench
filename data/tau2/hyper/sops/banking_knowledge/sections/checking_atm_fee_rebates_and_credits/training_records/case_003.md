# Case C
Channel: chat
QA status: approved

**Customer:** I was charged three Purple Account out-of-network ATM fees at $3.50 each. I thought they were supposed to be $2.50.

**Agent:** I’ll compare those ATM fees to the Purple Account schedule after verification. Please provide your email address and date of birth.

**Customer:** marisol.rivera@outlook.com, January 19 1982.

**Support console:** Customer identity and ownership verified.

**Support console:** Account reviewed: account_id="chk_3190", account_type="checking", account_class="Purple Account", status="active", balance="$684.25". Credit eligibility limited to checking accounts; savings accounts and other account types are not eligible for these credits.

**Support console:** Purple Account fee structure reviewed. A $2.50 fee is charged per cash withdrawal made at an out-of-network ATM. The fee applies to withdrawals made at ATMs not in Rho-Bank's ATM network. The fee is assessed per withdrawal, and multiple withdrawals in the same day each incur a separate $2.50 fee. Three separate cash withdrawals at out-of-network ATMs in one day result in total Rho-Bank fees of 3 x $2.50. The $2.50 out-of-network ATM fee is separate from any surcharge charged by the ATM owner or operator. The out-of-network ATM fee posts as a separate line item associated with the withdrawal, and the posting date may differ from the ATM-use date depending on settlement.

**Support console:** Transaction history checked. Three Rho-Bank out-of-network ATM fee line items posted after settlement: "$3.50", "$3.50", "$3.50". Correct charge should have been "$2.50" each. Fee discrepancies identified: three overcharges of "$1.00" each. Net correction across all fee discrepancies: "$3.00". Operator surcharges were separate and are not part of this fee-mischarge correction.

**Support console:** Eligible credit circumstance verified: documented fee mischarge. Account terms and fee structure reviewed; transaction history confirms each discrepancy; credit amount reflects net correction and is exact, not rounded or estimated. Credits are limited to missing rebates or fee mischarges unless supervisor approval is involved.

**Agent:** The correct Rho-Bank fee was $2.50 for each of the three out-of-network withdrawals, so the net correction is $3.00. This credit can be applied only to your Purple checking account and will be documented as a fee refund. Please reply yes to apply the $3.00 credit to checking account ending 3190.

**Customer:** yes

**Support console:** Required credit checks complete: identity and account ownership verified; account is checking; eligible fee-mischarge circumstance verified; amount is a positive dollar amount greater than $0; amount matches the exact overcharged fee total. If multiple corrections were needed for this same checking account, including both fee refunds and missing rebates, they would be combined into one credit with the credit_type that applies to the majority of corrections. Only fee-refund corrections are present, so credit_type="fee_refund".

**Support console:** apply_checking_account_credit_5829 is the tool used to add a credit transaction to a checking account. Internal parameters: account_id, amount, credit_type. account_id must be the checking account ID to credit. Tool may only be called once per checking account per customer interaction. No credit applied to account_id="chk_3190" in the prior 14 days.

**Support console:** Calling apply_checking_account_credit_5829(account_id="chk_3190", amount="$3.00", credit_type="fee_refund"). Result: credit transaction added to checking account; balance updated from "$684.25" to "$687.25". A 14-day cooldown period now applies before another credit can be applied to this same account.

**Agent:** The $3.00 fee-refund credit has been applied to your Purple checking account. Your new account balance is $687.25. A 14-day cooldown now applies before another credit can be applied to this same account.
