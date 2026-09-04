# Case 012

Case ID: OPN-2511-0304
Channel: Chat
Contact date: 2025-11-01
Handle time: 24m
QA status: Approved — kept as a training sample (2025-11-05, R. Fields)

## Transcript

[13:06] **Agent:** Hi, you've got Marcus on the Rho Bank deposit desk. What can I do for you?

[13:07] **Customer:** hey. i want to open a second savings account. new job does paycheck splitting and i want the split going somewhere separate from my main savings

[13:08] **Agent:** Nice, that's a good setup. Quick verification first — there's a secure form popping up in this chat, drop in the email on your profile and your date of birth.

[13:09] **Customer:** done

[13:09] **Support console:** Identity verified via secure chat form, two factors matched. Profile RB-6673048.

[13:10] **Agent:** Thanks, Kevin. Fastest way to get us moving — can you paste your checking account number from the app? And while you're in there, run the balance check from your side and tell me what the available balance says.

[13:12] **Customer:** ok one sec. Green Account checking, ends in 3312. available balance says -$68.40

[13:12] **Customer:** the minus is from tuesday. my gym double charged me and the refund is "processing," which apparently means nothing to anyone

[13:13] **Agent:** Ah — that minus sign is going to be our holdup, unfortunately. Let me pull it up on my side too.

[13:14] **Support console:** get_all_user_accounts_by_user_id_3847 executed for RB-6673048. Returned: Green Account checking ····3312 (open, balance -$68.40); Bronze Account savings ····8895 (open, good standing, balance $2,310.55).

[13:15] **Agent:** Same picture here. So, straight answer: while any account on your profile is sitting below zero, a new opening is held — the checklist we run won't let a savings account through until the checking is back in the black. Once it's at zero or above, this becomes a five-minute job.

[13:16] **Customer:** seriously? it's a gym refund. sixty eight dollars

[13:17] **Agent:** I know, and I believe you about the refund — but the hold reads the balance, not the backstory. The good news is you have three ways out and two of them are fast. One: the refund posts and fixes it on its own. Two: you move seventy bucks over from your Bronze savings to cover it now, and open the new account today. Three: you deposit from outside. Any of those flips the switch.

[13:19] **Customer:** if i move money from savings doesn't that defeat the purpose of savings

[13:20] **Agent:** Philosophically, maybe. Practically it's a bridge — the refund lands, you move it right back. But it's your call entirely; the refund route works too, it just means we open the account after it posts instead of today.

[13:22] **Customer:** nah i'll wait for the refund. gym says 3-5 business days which probably means friday

[13:23] **Agent:** Reasonable. Then here's what I'm doing on my end: I'm noting the case with everything we covered, so when you come back you can skip the recap. Once the balance is at zero or better, message us or call — either channel can do the opening. If you use chat, the whole thing including verification is maybe ten minutes.

[13:24] **Customer:** ok. and the paycheck split — anything i need to know before i point it at an account that doesn't exist yet

[13:25] **Agent:** Just sequencing. Open the account first, then give payroll the new account details — your employer will want the full account number, which shows in the app the moment it's created. If your HR portal is like most, the first split takes a pay cycle to kick in, so the sooner the account exists the better.

[13:27] **Customer:** got it. annoying but fine. so: refund lands, balance goes positive, i come back, you open it, i feed the number to payroll

[13:28] **Agent:** That's the whole map. And for what it's worth, a second savings as a paycheck-split target is a genuinely good idea — money you never see is money you never miss. The note's on your file, so any of us can pick it right up.

[13:29] **Customer:** cool. thanks marcus. wish me luck with the gym

[13:29] **Agent:** Good luck — may the refund be swift. Talk soon, Kevin.

[13:30] **Support console:** Case notes saved: second savings opening requested 2025-11-01, held for negative balance on checking ····3312 (-$68.40, customer reports pending merchant refund); customer to return once balance restored; paycheck-split sequencing explained. Case closed.
