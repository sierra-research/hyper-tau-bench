# Case 012

Case ID: SAV-2511-0069
Channel: Chat
Contact date: 2025-11-05
Handle time: 31m
QA status: Approved

## Transcript

[16:38] **Support console:** Chat session opened from authenticated online-banking login. Profile RB-4918306. Accounts: Platinum Account savings ····5590; Diamond Elite Card ····7741 (active).

[16:39] **Customer:** hey! two things, hopefully quick. 1) a guy on my personal finance forum swears the EcoCard is always the best card to hold for your savings rate, across the board, and I was about to apply tonight. 2) my interest deposit on the 1st looked light. are these connected?? is my rate low BECAUSE I don't have the EcoCard?

[16:42] **Agent:** Hi, Jess here. I'll take the money one first, then the forum one — the same document answers both, and I'd rather show it to you than argue with a forum. Looking at your October now.

[16:44] **Support console:** get_all_user_accounts_by_user_id_3847 executed for RB-4918306. Returned: Platinum Account savings ····5590 (open, good standing); Diamond Elite Card ····7741 (active, same profile).

[16:45] **Support console:** get_bank_account_transactions_9173 executed for account ····5590. Interest credit posted 2025-11-01: $182.73. Daily balance $33,100.00 throughout the October cycle.

[16:47] **Agent:** Here's what I see. Your balance held at $33,100 all month, and the October posting was $182.73 — your base rate of 6.5% and nothing else. Now the part your instincts caught: you hold a Diamond Elite Card, active, same profile. On the Platinum Account's product sheet that card carries a bonus on top of base, which makes your expected October rate 6.85%, and the cycle at 6.85% pays $192.57. So your rate isn't light because you lack some other card — it's light because the bonus for the card you already hold didn't make it into the run.

[16:50] **Customer:** ha! so I'm owed money and I almost applied for a credit card to fix it. what's the damage in my favor?

[16:51] **Agent:** $192.57 minus $182.73 — $9.84. Crediting that now as an interest correction, then filing a report with the backend team, because the value the run used for your card's bonus doesn't match the current sheet, and that's theirs to chase before December repeats it.

[16:53] **Support console:** apply_savings_account_credit_6831 executed: account_id ····5590, amount 9.84, credit_type interest_correction. Credit posted. New available balance $33,292.57.

[17:03] **Support console:** submit_interest_discrepancy_report_7294 executed: account_id ····5590, user_id RB-4918306, expected_apy 6.85, actual_apy 6.5, amount_difference 9.84. Report accepted; card-bonus value mismatch noted for backend review. Backend queue reference returned.

[17:04] **Agent:** Both done — sorry for the pause, I wrote the backend a proper description instead of a shrug. $9.84 shows as its own line, new balance $33,292.57. Now, the forum. Every savings product has its own sheet, and every sheet has its own card-bonus table. The tables genuinely disagree — a card that's the star of one product's table can be a zero on another's. And when you hold several eligible cards, they don't add: exactly one bonus applies, the highest on your product's table.

[17:06] **Customer:** ok but for MY account specifically. if I got the EcoCard tomorrow, what does the Platinum table say it does?

[17:07] **Agent:** Nothing — on the Platinum Account's table the EcoCard row adds zero. The top of your table is the card already in your wallet. Your forum guy isn't inventing it, for what it's worth: on some other products the EcoCard really is the biggest number on the page, and that's how "always" gets born — true somewhere, repeated everywhere. The boring fix is to read your own product's sheet before believing anything with "always" in it. Sending you the Platinum sheet now.

[17:08] **Support console:** Secure message sent: Platinum Account product sheet attached. Case notes: interest correction and discrepancy report cross-referenced; card-selection question answered from product sheet.

[17:09] **Customer:** so "is the EcoCard always best" comes out as "not even best for me, and a card I already own was quietly owed $9.84." I'm going to enjoy posting this. thanks Jess!

[17:09] **Agent:** Quote the sheet, not me — it argues better. Anything else tonight?

[17:09] **Customer:** nope, all set. have a good night!
