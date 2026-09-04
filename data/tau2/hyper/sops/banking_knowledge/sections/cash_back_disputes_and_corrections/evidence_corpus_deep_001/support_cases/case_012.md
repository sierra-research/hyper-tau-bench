# Case 012

Case ID: CB-2510-0521
Channel: Live chat
Contact date: 2025-10-24
Handle time: 17m 12s
QA status: approved

## Transcript
[13:22] **Customer:** $57.89 purchase on my crypto card. 2% of 57.89 is 1.1578, so I should have 115.78 cents of rewards. app shows 115 points. where did my .78 go

[13:24] **Agent:** Hi — Bea here. Let me verify the account first: the email on file plus your date of birth?

[13:25] **Customer:** therrera@voltaicpress.com, 12/08/1979

[13:26] **Support console:** Identity confirmed. RB-4917206, Crypto-Cash Back. TX-2209-8841C: $57.89, eligible purchase at 2.0%, posted rewards 115 points. Rounding treatment cross-checked against the Q4 QA calibration session notes (2025-10-16): fractional points are floored, across all card types and reward categories.

[13:28] **Agent:** Your math is right up until the last step — the calculation does come out to 115.78 points, and then the fraction is dropped rather than rounded to the nearest whole point. So the posted 115 is the expected value for that charge.

[13:29] **Customer:** dropped?? .78 rounds UP everywhere else in the world

[13:30] **Agent:** Here the fraction doesn't carry, no matter how large it is — and that's the same handling on every card we issue, not something specific to yours.

[13:31] **Customer:** ok hold on. I keep a spreadsheet. pulling it up

[13:33] **Customer:** last month: 21.18 coffee run, thats 42.36 cents at 2%, you posted 42. the month before: 24.50 lunch, 49 even, you posted 49. so when it divides clean I get it all and when it doesnt you keep the crumbs

[13:35] **Agent:** That's an accurate description of the two charges, and honestly a tidy pair of examples. The $24.50 charge computes to exactly 49 points, so there's no fraction to drop. The $21.18 charge computes to 42.36 and posts as 42. Whole points post; fractions don't, in either direction — we don't round up at .99 and we don't hold the .36 anywhere.

[13:36] **Customer:** thats the part that gets me. if you HELD it my spreadsheet would balance eventually. 78 + 36 is more than a whole point you've kept just from two charges

[13:38] **Agent:** I follow the logic, but there's no carried balance to accumulate — each charge is its own calculation and the fraction ends with that charge. Your spreadsheet and the app will always differ by the sum of the fractions, and that difference doesn't convert to points later.

[13:39] **Customer:** who decided this? genuinely asking. is there a document I can read or is it vibes

[13:41] **Agent:** It's documented — the rewards program terms cover how points calculate, and the handling I've described is the program-wide rule, not my interpretation. I can send the terms link to your secure messages if you want the paper version.

[13:42] **Customer:** send it. also does anyone ever win this argument

[13:44] **Agent:** Sending now. And no — not because we're stubborn, but because an exception for one charge would contradict the next customer's statement. The one thing I can tell you that helps: the handling is identical everywhere, so your spreadsheet can model it with one FLOOR function.

[13:45] **Customer:** ...that is actually useful. fine. FLOOR() it is

[13:46] **Customer:** for the record I still think the bank should sweep the crumbs into like a charity jar

[13:47] **Agent:** For the record, I've written your charity-jar idea into the case notes as feedback — that's real, it goes to the rewards product team in the monthly digest.

[13:48] **Customer:** ok. noted for my spreadsheet. every fraction dies alone

[13:49] **Support console:** No adjustment. Floor handling explained per current guidance; no exception path exists. Program terms link sent to secure messages. Customer suggestion (fraction sweep to charity) logged as product feedback.
