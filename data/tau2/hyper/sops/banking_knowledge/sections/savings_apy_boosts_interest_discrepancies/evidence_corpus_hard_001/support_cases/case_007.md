# Case 007

Case ID: SAV-2511-0233
Channel: Phone
Contact date: 2025-11-10
Handle time: 14m 27s
QA status: Approved

## Transcript

[00:04] **Agent:** Good afternoon — could I speak with Arthur Chen? This is Omar with the Rho Bank deposit desk, calling about the savings case you opened with us last week.

[00:14] **Customer:** Speaking. I was beginning to think you'd all filed me under a rug somewhere.

[00:21] **Agent:** Not under a rug — your filing bounced, and I'll explain exactly what that means. But since I'm the one who dialed, let me make sure I'm talking to the right Arthur Chen first. The email on your profile, and your date of birth?

[00:36] **Customer:** chen.arthur at plummail dot net. March 2, 1954.

[00:44] **Support console:** Outbound contact, number on file. Identity confirmed — email of record and date of birth both matched. get_all_user_accounts_by_user_id_3847 executed for RB-3390417. Returned: Silver Account savings ····7208 (open, good standing); Green Account checking ····5561 (open, good standing, linked to ····7208 on 2025-08-18); Green Rewards Card ····9902 (active, added 2025-11-03). Prior case SAV-2511-0102 on file: interest discrepancy report returned by backend for component re-review.

[00:51] **Agent:** Thank you. So, the honest version: the report my colleague filed after your call last Wednesday went to the backend team, and the backend sent it back to us. Not into a void — back to the desk, for a component check, because the expected rate written on it doesn't line up with the current documents. I'd like to rebuild it with you now, number by number, so the next filing sticks.

[01:15] **Customer:** The expected rate is the one part I'm sure of, Omar. I did the arithmetic myself. Base rate, 2.75. A quarter point for linking my checking. And the 0.025 relationship bonus. That comes to 3.025, and meanwhile your app has been showing me 2.5 like it's proud of it.

[01:37] **Agent:** You have a printout in front of you right now, don't you.

[01:41] **Customer:** The rate schedule. I picked it up at the branch in September and I keep my paperwork, which is more than I can say for some institutions.

[01:50] **Agent:** Fair hit. And here's the thing — on that page's own terms, your arithmetic is clean. Those three numbers really do add to 3.025. What moved is underneath the page. There's a newer issue of the schedule, effective November third, and two of its changes land on you. The September issue printed the numbers inline — base, boost, everything on the one page; the current issue moved the boost percentages out to the product documents. And the Silver base on the current issue is 2.5, not 2.75. These rates are variable; a printed schedule is a snapshot with a date on it, and yours is two issues of news old.

[02:29] **Customer:** So my homework was graded against last season's answer sheet.

[02:34] **Agent:** Kindly put, yes. Let's rebuild the stack from the current paper, on the record. Base on the Silver Account today: 2.5. Your Green checking with your Silver savings is still a qualifying pairing, and the percentage now lives in the product documentation — I have the Green checking product's sheet open: for your pairing it's 0.25%. Same quarter point as before; it just changed address. And the relationship bonus, 0.025 — your profile picked that up on November third, when your new card came on. Add the three and your expected rate is 2.775.

[03:16] **Customer:** 2.775. Alright, I'll surrender the 3.025. But 2.5 is still not 2.775, so the app and I still have a disagreement. Where has my quarter point been living since August?

[03:30] **Agent:** The right question — and why I'm glad the backend bounced the first filing: the shortfall is real, it was just wearing the wrong number. Let me show you what the account actually paid.

[03:52] **Support console:** get_bank_account_transactions_9173 executed for account ····7208. Interest credits posted: 2025-09-01 $9.09; 2025-10-01 $19.48; 2025-11-01 $20.13. Balance $9,480.00 at each month-end; interest amounts transferred out to ····5561 on posting day per customer standing habit.

[04:00] **Agent:** Three postings since you linked: $9.09 in September, $19.48, then $20.13 on November first. Every single one of them is base-only money. Your linked boost has never been inside a posting — not once since the link went live on August eighteenth. That's the defect, and it's on our side.

[04:22] **Customer:** I knew something was leaking. And you can see I move the interest over to checking the morning it lands — the nine-four-eighty itself never moves. Makes my ledger tidy.

[04:34] **Agent:** It makes my ledger tidy too, because a balance that holds still makes the make-whole exact instead of approximate. Here it is: a quarter of one percent, on $9,480, for the seventy-five days from August eighteenth through the end of October. That comes to $4.87.

[04:53] **Customer:** Seventy-five days of being shorted comes to four dollars and eighty-seven cents? I've spent more than that being angry about it.

[04:53] **Agent:** At this balance the boost is small change per day — which is exactly how it hid for two and a half months. The dollars are modest; the principle is what I file. One boundary, so it's said: I can only true up interest that has already posted. The November days are still accruing — the backend fix should land before the December first posting, and if December comes through base-only anyway, call us and we escalate on the open case rather than starting over.

[05:20] **Customer:** Understood. Put it through.

[05:25] **Support console:** apply_savings_account_credit_6831 executed: account_id ····7208, amount 4.87, credit_type interest_correction. Credit posted. New available balance $9,484.87.

[05:32] **Agent:** Done — $4.87 is on the Silver Account as of this minute, categorized as an interest correction, and your new balance is $9,484.87. It shows as its own line, not a rewritten interest posting, so your records stay honest.

[05:47] **Customer:** And the report that bounced? I don't want this dying in a tray again.

[05:54] **Agent:** Refiling it right now, with the number I can defend: expected 2.775 against the 2.5 you've actually been getting, and the $4.87 difference attached.

[06:06] **Support console:** submit_interest_discrepancy_report_7294 executed: account_id ····7208, user_id RB-3390417, expected_apy 2.775, actual_apy 2.5, amount_difference 4.87. Report accepted; backend queue reference returned. Linked to prior returned filing on case SAV-2511-0102.

[06:14] **Agent:** Accepted, with a queue reference this time, and tied back to the first filing so the backend sees the whole story. They fix the engine; the credit already fixed you.

[06:27] **Customer:** Hold on — before we leave the report entirely. The first filing, the one that bounced. Where does it live now? I ask because I once had a lender keep a dead application in a drawer for ten years and produce it at the worst possible moment, and I have been suspicious of institutional drawers ever since.

[06:54] **Agent:** A reasonable suspicion, and here the drawer works in your favor. The returned filing isn't marked false and it isn't marked against you — it's marked returned for component re-review, which is bookkeeping between the backend and this desk, not a judgment about the customer. It stays attached to your case history, and I've tied today's refiling to it on purpose: anyone who opens the case sees one continuous story — first filing, the component check, today's rebuild — instead of two mysterious attempts. Nothing about it touches your standing, and nothing about it is the kind of thing that resurfaces at a bad moment.

[07:41] **Customer:** So the drawer has a window in it. Good. And the ten-year lender is not a bank I keep anymore, in case you were wondering about your competition.

[07:55] **Agent:** I'll resist asking for names. The short version is: paper that explains itself is on your side, and as of today this case explains itself.

[08:08] **Customer:** One more thing, since you're being useful. The new card — does it add its own bonus on top? My neighbor claims his card is worth half a percent.

[08:18] **Agent:** Depends entirely on which savings product the card sits next to — the per-card numbers are set product by product, on each product's sheet. On a Silver Account, the Green Rewards Card carries no card bonus of its own; what it did do is bring the relationship bonus onto your profile, and that 0.025 is already inside your 2.775. Your neighbor may genuinely get half a percent — on his product, off his sheet.

[08:42] **Customer:** Off his sheet. You realize you've armed me for an insufferable conversation at Thursday cards night. He has been waving that half a percent at the table for a month like a winning hand.

[08:59] **Agent:** Then deal him this: the number only means something next to the product it's printed on. Two true numbers on two different sheets aren't a competition — they're two different accounts. If he wants to compare hands properly, the sheets are public; bring reading glasses instead of a calculator.

[09:22] **Customer:** So no card envy required. And which papers should I keep now that my September one is an antique?

[09:30] **Agent:** Three, headed to your secure inbox now: the current rate schedule, the Silver Account sheet, and the Green checking sheet with your pairing's percentage. The September printout can retire to the scrapbook — it did its job, it got you to call.

[09:47] **Customer:** The secure inbox is the part of your app I visit least, which is saying something. I'm a paper man, Omar — you may have gathered. Can those three come by post as well, or does that cost me a stamp of my own these days?

[10:09] **Agent:** It costs you nothing but patience — paper copies ride along with your next statement mailing, so give it a week or a little more. I've set that going now. For the impatient version in the meantime: in the app, the same three documents sit under the documents tab on your account screen, current issues only, each with its effective date printed at the top. That last part matters for a paperwork keeper — the date on the page is what tells you whether your copy is still the copy.

[10:50] **Support console:** Document mailing requested: current rate schedule, Silver Account sheet, Green Account checking sheet to address of record with next statement cycle. Secure inbox delivery confirmed.

[10:57] **Customer:** A date on every page. If your documents people had put that habit about thirty years earlier, you and I would never have met.

[11:10] **Agent:** And my afternoon would be poorer for it. The September schedule had a date on it too, for the record — the trouble was never the page, it was that nobody told the page it had been outlived. That's the gap the current setup closes: the app copy updates itself, and the paper copy is your souvenir.

[11:37] **Customer:** It'll get a frame. What should I see between now and December?

[11:43] **Agent:** Tomorrow, your account details screen should show all three components and an effective 2.775 — give it a day, then audit it; I'd expect nothing less. December first, the posting arrives with the boost inside. If either disappoints you, call and reference this case.

[12:02] **Customer:** One wrinkle in the middle, then. You said you can only true up interest that has already posted, and the fix is supposed to land before December. The days in November between the first and whenever the engine gets fixed — do they arrive already corrected, or is that another call?

[12:26] **Agent:** They should arrive already corrected, and here's why without the machinery: your November interest doesn't exist as a posting yet. It becomes one number on December first, computed at that point by the engine as it stands then. If the fix lands mid-month the way it should, the December posting is built right from the start — nothing to true up, no odd days stranded. The only world where you and I speak about this again is the one where December first arrives base-only anyway, and for that world you have the open case and my instruction to escalate rather than re-explain.

[13:12] **Customer:** So either the number is right and I frame the printout, or it's wrong and I have a queue reference. I can live in both of those worlds.

[13:26] **Agent:** Live in the first one until proven otherwise — and still audit the screen tomorrow. Trust, then verify, then frame.

[13:37] **Customer:** You've restored a little of my faith, Omar. Not all of it. A little.

[13:43] **Agent:** I'll take a little — it compounds. Anything else while I have you, Mr. Chen?

[13:50] **Customer:** No, that's the lot. Thank you for calling me instead of making me chase you.

[13:56] **Agent:** That one was owed. Enjoy the rest of your Monday.

[14:27] **Support console:** Secure message sent: current rate schedule, Silver Account sheet, Green Account checking sheet attached. Case notes: component rebuild recorded; credit and refiled report cross-referenced to SAV-2511-0102. Case closed.
