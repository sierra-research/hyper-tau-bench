# Case 012

Case ID: ATM-2510-0640
Channel: Live chat
Contact date: 2025-10-31
Handle time: 16m 33s
QA status: approved

## Transcript
[11:47] **Customer:** hi. Purple account. I sat down with my October statement and I have a small list. 1) the ATM fee from 10/18 is on there twice, one withdrawal two fees. 2) 10/21 I used the machine IN your Ledyard branch lobby and still got charged the out-of-network fee. 3) an operator fee from 10/12 ($3.00) never got the rebate. three separate problems or one big one, you tell me

[11:49] **Agent:** Hi, this is Keisha — that's an admirably organized list. Verification first: email on the account and your date of birth?

[11:50] **Customer:** wes.kandel@kandelbrew.com, August 16, 1988

[11:51] **Support console:** Identity confirmed. RB-5218873, Purple Account checking.

[11:52] **Agent:** Thanks, Wes. Give me a few minutes to confirm each line in the history before I say anything rash.

[11:58] **Support console:** Transaction history review, October 2025. TXN-P7L2290A 10/18: one out-of-network withdrawal, two $2.50 fee lines — duplicate confirmed. TXN-P7L2308F 10/21: withdrawal at in-network terminal (Ledyard branch lobby), $2.50 out-of-network fee posted in error. Operator fee $3.00 posted 10/12, coded ATM operator fee, eligible, no rebate credited; October rebate total $12.00 against $30 monthly cap.

[11:59] **Agent:** All three check out exactly as you described. So: two fees that were charged and shouldn't have been (the duplicate $2.50 and the in-network $2.50), and one rebate that should have applied and didn't (the $3.00).

[12:00] **Customer:** so three refunds incoming?

[12:02] **Agent:** One credit incoming, and here's why. When one checking account needs several corrections — fee refunds and a missing rebate together — they go out as a single credit for the total, and the credit_type follows the majority of the corrections. Your total is $2.50 + $2.50 + $3.00 = $8.00.

[12:03] **Customer:** what's a credit_type

[12:05] **Agent:** It's how the reason gets documented — every credit carries one, and picking it is the documentation. There are two: fee_refund is the type for fees that were charged and shouldn't have been, and rebate_credit is the type for a rebate that should have applied and didn't. Yours is two fee corrections against one rebate correction, so the majority rules it: the $8.00 goes on as fee_refund.

[12:06] **Customer:** the $3 rebate part just rides along under the wrong label? not fighting it, just curious

[12:07] **Agent:** It rides along under the majority label, right — the case record underneath still lists all three corrections separately, so nothing about your $3.00 gets lost. The label is about the credit as a whole.

[12:08] **Support console:** Credit applied via apply_checking_account_credit_5829: account CHK-77120945, amount $8.00, credit_type fee_refund. New balance $941.16.

[12:09] **Agent:** Done — $8.00 posted just now, new balance $941.16. You'll see it as one line dated today.

[12:10] **Customer:** list fully crossed off. excellent. thanks Keisha

[12:11] **Agent:** Thanks for bringing the list — you made it easy. Anything else?

[12:11] **Customer:** nope, that was everything

[12:12] **Support console:** Chat ended. Credit posted; case notes list all three corrections against TXN references above.
