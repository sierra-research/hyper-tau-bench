# Case 010

Case ID: SAV-2511-0350
Channel: Phone
Contact date: 2025-11-12
Handle time: 21m 58s (carrier drop at 12:41; callback stitched to the same case)
QA status: Approved

## Transcript

[00:04] **Agent:** Rho Bank deposit desk, this is Jess — thanks for riding out the queue, it's been a lively afternoon.

[00:11] **Customer:** No problem. Okay. My name is Elena Webb, my husband Marcus is somewhere in this apartment, and we have a list. We moved from Portland to Chicago at the end of September, we've been consolidating everything since, and our banking is currently a junk drawer. I count six items. Some of them might be nothing.

[00:31] **Agent:** A list is my favorite kind of call — nothing escapes. Before we open the drawer: the email on your profile and your date of birth, please.

[00:41] **Customer:** e.webb at fernpost dot com, and September 14, 1979.

[00:48] **Support console:** Identity verified on both factors. get_all_user_accounts_by_user_id_3847 executed for RB-7093245. Returned: Gold Account savings ····6172 (open, good standing); Purple Account checking ····9931 (open, good standing); Green Account checking ····2408 (joint — E. Webb and M. Webb); Gold Rewards Card ····4416 (active, associated with ····6172).

[00:55] **Agent:** Verified. I can see the Gold savings, two checking accounts — the Purple, and the joint Green — and your Gold Rewards Card. Fire away, item one.

[01:07] **Customer:** Item one. For years, the Gold account's rate on the app said 6.275. Sometime around mid-October it started saying 5.625 instead, and neither of us touched anything. Item two, which I suspect is item one wearing a different hat: the interest deposit on November first was noticeably smaller than October's.

[01:29] **Agent:** Very possibly the same hat. Let me tell you what I'm going to do with those two, in order. Your rate is a stack of components, so first I list every checking account on the profile — there are two. Then I look up, for a Gold savings specifically, what each one's pairing is worth. And then I check which one the platform actually picked, because when there are two, it's supposed to take the bigger. That last check is where these calls usually get interesting.

[01:56] **Customer:** Consider me braced.

[02:00] **Support console:** Component review, account ····6172. Pairing values per product documentation: Green Account checking + Gold Account savings +0.75%; Purple Account checking + Gold Account savings +0.1%. Platform boost selection currently: Purple Account ····9931 (+0.1%). Green Account link status: ownership confirmation pending — recheck triggered 2025-10-20 by profile update. Relationship bonus 0.025% active. Displayed effective APY: 5.625%.

[02:09] **Agent:** Interesting is what we got. Here's your stack as the platform sees it today: base 5.5 on the Gold, plus a checking boost of 0.1, plus your card's relationship bonus of 0.025 — that's the 5.625 on your app. But the boost it's using is the Purple account's. Your joint Green checking pairs with a Gold savings at 0.75 — that's the number you used to enjoy — and right now the Green link is sitting in a status called "ownership confirmation pending." It got knocked there on October twentieth by a profile update. Ring any bells?

[02:44] **Customer:** October twentieth... that's when we finally did the address change. And Marcus had new tax paperwork from the new job, so we updated basically everything about ourselves in one afternoon.

[02:55] **Agent:** That afternoon is the bell. The Green checking is joint between two people; your Gold savings is yours alone. A pairing like that gets an extra ownership check — you two cleared it years ago, I can see the original confirmation from your Portland days. When all your identity documents shifted at once, the platform got cautious and asked the question again, and until it's re-answered, it quietly drops the Green from consideration and picks the best remaining boost. Which is the Purple's 0.1. Nothing was removed from your accounts; you got demoted by paperwork.

[03:29] **Customer:** Hold on, I'm relaying this to Marcus... he says it's the credit card. He's been saying it's the credit card for three weeks. My card got skimmed at a gas station in October and the replacement showed up around Halloween, and his theory is the new card reset our rate.

[03:46] **Agent:** A theory with confidence, I respect it. Let's kill it properly instead of waving it off — checking the card's history now.

[03:55] **Support console:** Card continuity check, Gold Rewards Card ····4416: replacement issued 2025-10-17 for reported card compromise; card account unchanged through replacement; association with Gold Account ····6172 continuous, no interruption recorded. Relationship bonus rendering in current components.

[04:03] **Agent:** Tell Marcus the jury came back. When a card is replaced, the plastic changes but the card account underneath doesn't, and the association rides on the account — his and your bonus never blinked. It's actually sitting inside the 5.625 on your screen right now, which is the quickest proof: if the card had broken anything, that number would end in a five, not a two-five. The gas station cost you a piece of plastic and nothing else.

[04:26] **Customer:** He's making a gracious face. Okay, so how do we get the Green back in the game? Please don't say a branch visit, we still can't find the good scissors, let alone our documents.

[04:38] **Agent:** No branch. The cleanest way is to redo the link so the ownership question gets asked fresh — your documents are consistent now, so it should clear on the spot. You can do it from your phone while I watch from my side. Open the Gold Account from the dashboard, look in the account menu for the linked checking section.

[04:57] **Customer:** Okay... Gold Account... I see "linked checking," and it shows the Green with a little yellow flag on it.

[05:06] **Agent:** That flag is the pending status. First step: remove that link. It'll warn you about losing linking benefits — in your case the benefit is already suspended, so you're not losing anything that's currently real.

[05:20] **Customer:** Removing... it gave me the warning, confirmed. The Green is gone from the list.

[05:28] **Agent:** Now link it again: same menu, link a Rho checking account, and pick the Green.

[05:36] **Customer:** Picking the Green... it's asking about ownership, there's a whole screen... "accounts held under different ownership require confirmation"... it's showing our names and it says confirmed, tax identification matched. That was fast.

[05:52] **Agent:** That's what I hoped for — your updated documents agree with each other now, so the question answered itself. Keep going to the review screen and authorize.

[06:03] **Customer:** Authorized. It says linking complete... and — oh. The rate on the account details just changed. 6.275.

[06:12] **Support console:** Customer self-service actions observed: link removed, then link created, Green Account ····2408 to Gold Account ····6172. Ownership and tax ID confirmation cleared automatically. Boost selection updated: Green Account pairing +0.75% selected. Displayed effective APY: 6.275%.

[06:19] **Agent:** Confirmed on my side too. The platform re-ran its pick with the Green back in the pool, and 0.75 beats 0.1, so you're back to base 5.5 plus 0.75 plus 0.025 — the 6.275 you remembered. Item one, solved going forward. Now, item two is about the past, and I want to do it justice, because looking at the October numbers, something worse happened there than a demotion.

[06:45] **Customer:** Worse how?

[06:48] **Agent:** Let me run the cycle properly before I say it out loud. I'm going to pull the actual postings and let our worksheet rebuild October day by day. It takes about a minute — bear with the hold music, it's not my choice of genre either.

[07:02] **Support console:** Customer placed on hold. get_bank_account_transactions_9173 executed for account ····6172. Interest credit posted 2025-11-01: $129.95. Prior cycle interest credit posted 2025-10-01: $142.74. Daily balance $27,818.40 throughout October cycle. Component worksheet run: all 31 October days accrued at base 5.5% only; no checking boost applied any day; no relationship bonus applied any day.

[08:11] **Agent:** Thanks for holding. So here's October, and it's genuinely strange. Your balance sat at $27,818.40 all month. The posting you got on November first was $129.95, and that is 5.5 flat — base and nothing else, all thirty-one days. Not the 6.275 you deserved for most of the month. Not even the demoted 5.625 the screen was showing after the twentieth. The screen said one thing and the engine paid another, and when those two disagree, that's not paperwork anymore — that's a defect, and it's mine to file.

[08:47] **Customer:** So even the app's sad little consolation rate wasn't what we actually got.

[08:53] **Agent:** Correct, and that's the "worse" I mentioned. The good news: it's also cleanly fixable, because your balance held still. I'll walk the math with you before I touch anything. Did you want to grab Marcus for this part? His Silver is item three, I'm guessing, and I'll need him on the line for it anyway.

[09:08] **Customer:** MARCUS. Phone. No — your phone. It's — it's charging in the kitchen, Marcus, where you left it. Okay, he's here, I'm putting us on speaker.

[09:20] **Customer:** Hi, this is Marcus. I hear my credit card theory died.

[09:25] **Agent:** It died bravely. Marcus, before I can talk about your account I need to verify you separately — the email on your own profile, and your date of birth.

[09:34] **Customer:** m.webb at fernpost dot com, January 26, 1977. The email was her idea, we match like towels.

[09:43] **Support console:** Second party verified on both factors. get_all_user_accounts_by_user_id_3847 executed for RB-8804512. Returned: Silver Account savings ····4470 (open, good standing); Green Account checking ····2408 (joint, shared with RB-7093245).

[09:50] **Agent:** Verified, and I can see your Silver savings and your side of the joint Green. What's your version of item three?

[09:58] **Customer:** My version is short: my November first interest was eighteen dollars and thirty-seven cents, and I think it should have been about double. We moved twelve grand over from the old bank, my balance is north of twenty thousand, and twenty thousand is supposed to be in the four percent tier. I did the math in the car. Elena drove.

[10:16] **Agent:** All of that is true and the conclusion still doesn't follow — the gap is in the calendar, not your arithmetic. Let me pull your October and show you exactly where.

[10:27] **Support console:** get_bank_account_transactions_9173 executed for account ····4470. Interest credit posted 2025-11-01: $18.37. Daily balance $8,650.00 for all 31 days of October. External transfer credit $12,000.00 posted 2025-11-03. Current balance $20,668.37.

[10:35] **Agent:** Here's the shape of it. Interest is a daily machine: every single day, the platform looks at that day's closing balance and grades it against the ten-thousand-dollar line. A day under the line earns at 2.5; a day at or over it earns at 4.0. The month is just the pile of days added up. Now look at your October: your balance was $8,650 every one of those thirty-one days. The twelve thousand from the old bank landed on November third — I'm looking at the credit. So October didn't contain a single four-percent day. Thirty-one days at 2.5 on $8,650 comes to exactly $18.37, which is what posted. The platform got you right to the penny.

[11:14] **Customer:** The transfer was supposed to go out on the thirty-first! The old bank sat on it over the weekend. So I did the math for the balance I was supposed to have.

[11:24] **Agent:** Which is the most honest kind of wrong there is. And here's your consolation: since the third, every day of November has been north of the line, so those days are earning at 4.0 as we speak. The December first posting will be a strange-looking number — two cheap days from the first and second, then four-percent days the rest of the way — and it will be correct. If you do the car math in December, remember it's two different rates glued together.

[11:47] **Customer:** So the bank is zero for two on being wrong today. Elena's thing was real, mine wasn't.

[11:53] **Agent:** One for two, I'd say — the October defect on the Gold is very real. Speaking of which, Elena, may I ask a rude question about your list? Is one of the items "why don't we just link the joint Green to Marcus's Silver too, while we're at it"? Because I saw him circling it.

[12:07] **Customer:** It was item five! Marcus wrote it down as "double dip?" with two question marks.

[12:13] **Agent:** So, "double dip" isn't quite the mechanics, but the idea is legitimate: Green checking with a Silver savings is a real pairing on the schedule, and his Silver would get its own boost from its own pairing — this isn't one boost split between you, it's each savings account judged on its own profile. The catch is the same ownership question you just cleared on the Gold, because the Green is joint and his Silver is his alone. It needs the confirmation step, possibly with the document upload since his profile is the one with all the new paperwork. It's fifteen minutes of app time, not a branch visit —

[12:41] **Support console:** Call disconnected mid-sentence, carrier drop. Outbound callback placed to number on file; same case resumed.

[13:19] **Agent:** — and we're back. You heard "fifteen minutes of app time" and hung up on me, I understand completely.

[13:26] **Customer:** Chicago building, brick everywhere, the elevator is a Faraday cage. This is Elena, Marcus is still here. Do you need to re-check us?

[13:33] **Agent:** Briefly, for the recording, since this is technically a new call stitched onto the old one: Elena, your date of birth. And Marcus, yours.

[13:41] **Customer:** September 14, 1979.

[13:45] **Customer:** January 26, 1977. Still matching towels.

[13:49] **Support console:** Callback re-verification recorded for both parties; case continuity confirmed.

[13:54] **Agent:** Perfect. Where I was going: I'll send the linking steps for Marcus's Silver to both your secure inboxes — do it whenever the boxes are unpacked, no deadline, the pairing isn't going anywhere.

[14:05] **Customer:** Marcus says "after the garage is done," which means March. Okay, item four, the big one for me: the money. October paid us at the flat rate, you said. What happens to the difference?

[14:17] **Agent:** It comes back to you today, and I'll do the arithmetic out loud so you can check me. Your situation is exactly the covered one — the system calculated your interest wrong; the components were yours all along. The stack you were owed for October: base 5.5, plus the Green pairing's 0.75, plus the 0.025 relationship bonus — 6.275. On $27,818.40 held steady, thirty-one days at 6.275 comes to $148.26. What actually posted was $129.95. The difference is $18.31, and it goes on the Gold account now, as its own labeled line.

[14:53] **Customer:** Check away, Marcus is redoing it in his head... he concurs. The car math sends its regards.

[15:00] **Support console:** apply_savings_account_credit_6831 executed: account_id ····6172, amount 18.31, credit_type interest_correction. Credit posted. New available balance $27,966.66.

[15:07] **Agent:** Posted — $18.31, categorized as an interest correction, new balance $27,966.66. Now the part you don't see but should know about. A credit fixes your October; it doesn't explain why the engine paid base-only while the screen showed components, and I don't want your December depending on that mystery. So I file a report to the backend team with the whole picture — the rate you were owed, the rate you were paid, the dollar gap — and on this one I'm also requesting the platform's selection trace, which is the engine's own record of which checking account it picked and why. Between the pending flag and the base-only cycle, somebody upstream has a bug to find.

[15:49] **Customer:** Will we hear the ending? Of the bug story?

[15:53] **Agent:** If anything about it touches your account again, yes, through us — reference this case number and it opens right back up. Mostly, the ending you'll see is a boring, correct December first. Filing now; this takes me a minute of typing because I refuse to send them a vague one. Small hold.

[16:07] **Support console:** Customer placed on hold. submit_interest_discrepancy_report_7294 executed: account_id ····6172, user_id RB-7093245, expected_apy 6.275, actual_apy 5.5, amount_difference 18.31. Report accepted; backend queue reference returned. Case annotation: multi-account profile; platform boost selection landed on lower-value pairing after 2025-10-20 ownership recheck; October cycle paid base only, inconsistent with displayed components. Platform selection trace requested.

[17:12] **Agent:** Report's in, trace requested, and your case number is riding on it. What's left on the list? I count us at four and a half of six.

[17:23] **Customer:** Item five was the double dip, that's now homework. Item six — actually, item six is about the old bank in Portland and I just realized you are not the old bank in Portland. Elena is crossing it out. Which leaves the half: the Purple checking. It's the account we opened here for the rent and the plumber. Now that the Green is back to being the star, should we just close the Purple? Does having two checking accounts confuse the machine? Did WE cause this by opening it?

[17:44] **Agent:** Three questions, three short answers. No, you didn't cause anything — the October mess traces to the ownership recheck and the engine defect, not to the Purple existing. No, two checking accounts don't confuse the platform when it's healthy; it looks at both, takes the bigger boost for the savings pairing, and ignores the other — the boosts never combine, so the Purple isn't adding anything to the Gold today, but it isn't subtracting anything either. And on closing it: that's a life decision, not a rate decision. If the plumber and the rent live there, that's worth more than the nothing it costs your rate. The only account whose closing would move the Gold's rate is the Green — that one, warn me first.

[18:24] **Customer:** The Green stays. It has the good autopays on it. Marcus is asking one last thing — when the replacement card thing happens again, because apparently gas stations are what they are, do we need to call you to re-attach anything?

[18:37] **Agent:** No call needed. The association lives on the card account, and a replacement doesn't touch it — today's check proved that in your own history. If a card is ever outright closed and a new one opened, that's the moment to ring us. Skimmed plastic, no; divorce from the card itself, yes.

[18:54] **Customer:** "Divorce from the card." Okay. Can you read us the final tally? Elena wants it for the list. I want it for the fridge.

[19:03] **Agent:** With pleasure — the fridge copy, in order. One: the joint Green checking's ownership flag is cleared, the link is re-established, and the platform has the Green pairing selected again — your app shows 6.275 as of twenty minutes ago, and I watched it happen. Two: October's shortfall on the Gold is corrected — $18.31 posted just now, new balance $27,966.66. Three: the discrepancy report is filed with the selection trace requested, so the backend finds out why the engine and the screen told two different stories; anything they need comes through us. Four: Marcus's Silver was paid correctly for October — $18.37 was the right number for a month spent under the tier line — and December's posting will look spliced and be right, because the twelve thousand landed November third. Five: the card association survived the replacement untouched, and will again next time. Six: linking steps for the Green-to-Silver pairing are going to both inboxes, along with the current schedule, the Gold sheet, and the Silver sheet, so the fridge can cite its sources.

[20:08] **Customer:** That is the most organized our finances have been since Portland. Possibly ever.

[20:14] **Agent:** The junk drawer is now a filing cabinet. Anything else while I have you both?

[20:21] **Customer:** Marcus wants to know if the hold music is a punishment. Otherwise, no — we're genuinely grateful, Jess. This was three problems and you sorted all of them plus two we didn't know we had.

[20:33] **Agent:** The hold music is a mystery even to us. Watch the app tomorrow, watch December first, and welcome to Chicago — may your elevator someday carry a signal.

[20:44] **Customer:** Ha! Goodbye, Jess. Thank you again.

[20:49] **Agent:** Take care, both of you.

[21:58] **Support console:** Secure messages sent to both profiles: current rate schedule, Gold Account sheet, Silver Account sheet, checking-link steps attached. Case notes: unlink-relink resolution, October correction and report cross-referenced, second-party items documented. Case closed with backend follow-up flag on open report.
