# Case 011

Case ID: SAV-2511-0412
Channel: Chat
Contact date: 2025-11-13
Handle time: 26m
QA status: Approved

## Transcript

[11:43] **Support console:** Chat session opened from authenticated online-banking login. Profile RB-6152098. Accounts: Gold Account savings ····8823; Gold Rewards Card ····3057 (active, associated with ····8823).

[11:44] **Customer:** Hi. I have your Gold Account sheet in front of me. It prints, and I'm quoting: base APY 5.5%, relationship bonus APY +0.025%, "Total APY with the bonus: 6.0%." Meanwhile my October interest works out to 5.5% flat. So the sheet promises 6.0 and I got neither the 6.0 nor the bonus. Which number is real?

[11:47] **Agent:** Hi, this is Ana. I'll answer in a specific order: components first, then that printed total. Base APY on the Gold Account: 5.5%. Relationship bonus with your Gold Rewards Card active and associated: 0.025%. Added together: 5.525%. That is the real number for an account like yours.

[11:49] **Customer:** The sheet says 6.0.

[11:50] **Agent:** That total line is a misprint. The two component lines above it are correct and match the rate documents, but 5.5 plus 0.025 does not make 6.0, and no account is paid it. A corrected copy rides the next print run. I'll send you the current documents at the end of this chat so you have the components in writing.

[11:52] **Customer:** OK, but the second half of my complaint stands. I'm not even getting the 5.525.

[11:53] **Agent:** Then let's check that properly, because if you're right, that part is money. One moment.

[11:55] **Support console:** get_all_user_accounts_by_user_id_3847 executed for RB-6152098. Gold Account savings ····8823: open, good standing. Gold Rewards Card ····3057: active, associated with ····8823. Relationship-bonus conditions met for the full October cycle.

[11:56] **Support console:** get_bank_account_transactions_9173 executed for account ····8823. Interest credit posted 2025-11-01: $407.00. Daily balance $87,130.00 throughout the October cycle.

[11:58] **Agent:** You're right. Your balance held at $87,130 all of October. At 5.5% flat that cycle pays exactly $407.00 — which is what posted. At 5.525%, with the bonus your card earns you, it should have been $408.85. The run left your bonus out. Difference: $1.85.

[12:00] **Customer:** So the sheet overpromises by half a percent and the system underpays by the bonus. Impressive in both directions. If it's your misprint, shouldn't you credit me up to the 6.0 your own paper advertises?

[12:01] **Agent:** No — and plainly, here's why. The 6.0 exists on no schedule and in no rate table; it's a wrong total printed under two right numbers. What you're owed is the components: 5.5 plus 0.025. So the correction restores your $1.85, not a rate that was never real. Posting it now.

[12:01] **Support console:** apply_savings_account_credit_6831 executed: account_id ····8823, amount 1.85, credit_type interest_correction. Credit posted. New available balance $87,538.85.

[12:02] **Support console:** submit_interest_discrepancy_report_7294 executed: account_id ····8823, user_id RB-6152098, expected_apy 5.525, actual_apy 5.5, amount_difference 1.85. Report accepted; component arithmetic attached from case. Backend queue reference returned.

[12:03] **Agent:** Two things just happened. One: $1.85 posted as an interest correction — new balance $87,538.85. Two: I filed a discrepancy report so the December run includes your bonus by itself, without you having to chat me first.

[12:05] **Customer:** And the sheet? Do I keep the wrong one as a souvenir?

[12:06] **Agent:** Sending the current rate schedule and the Gold Account sheet to your secure inbox now — trust the component lines, ignore that box's total, and the corrected copy replaces it on the next print run. I'm also tagging this case with the sheet reference; we're tracking everyone that box has confused.

[12:07] **Support console:** Secure message sent: current rate schedule and Gold Account sheet attached. Case tagged with sheet reference PDS-GLD-05 per desk instruction.

[12:08] **Customer:** Add me to the tally. Thanks, Ana — the $1.85 is already showing. It's the principle, not the dollar.

[12:09] **Agent:** The principle was on your side twice today. Anything else I can check while you're here?

[12:09] **Customer:** No, that covers it.
