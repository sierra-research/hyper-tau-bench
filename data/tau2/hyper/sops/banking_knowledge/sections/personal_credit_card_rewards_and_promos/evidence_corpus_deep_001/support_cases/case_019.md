# Case 019

Case ID: RW-2511-0138
Channel: Live chat
Contact date: 2025-11-08
Handle time: 47m 30s
QA status: approved

## Transcript
[09:31] **Customer:** Hi. My EcoCard bonus tracker has been stuck at $4,110.75 for SIX DAYS. I've made at least four purchases this week. My window ends November 19 and I am not missing this bonus because of a frozen widget. Fix it please.

[09:32] **Agent:** Good morning, this is Omar with Rho Bank card support — let's figure out what the tracker is doing. Can you verify the email on the account and your date of birth?

[09:33] **Customer:** t.abara at lumenpost dot com. March 14, 1988.

[09:34] **Support console:** Identity verified, two factors matched. RB-9134086, EcoCard, opened 2025-10-19. Qualifying-spend tracker: $4,110.75, last movement 2025-11-02.

[09:35] **Agent:** Thanks, Tunde. I can confirm what you're seeing: the tracker last moved on November 2. Now let's find your four purchases. Can you give me roughly where and when?

[09:37] **Customer:** Monday: Fairhaven Garden Supply, $212 and change. Tuesday: Brightline Transit pass reload, $95. Wednesday: a restaurant, Casa Molina, about $180 with tip. And Thursday: Novabooks online, $76.

[09:40] **Support console:** Transaction search: Fairhaven Garden Supply $212.40 pending, auth 2025-11-03. Brightline Transit $95.00 posted 2025-11-05. Casa Molina $180.45 pending, auth 2025-11-05. Novabooks $76.12 posted 2025-11-07.

[09:42] **Agent:** Found all four, and here's the picture: two of them — Brightline for $95.00 and Novabooks for $76.12 — have posted. The other two, Fairhaven and Casa Molina, are still pending: the merchant authorized the charge but hasn't finalized it on their side yet. The tracker counts purchases when they post, so right now it should be reflecting the two posted ones... which it isn't. So you've actually caught two different things: two purchases that are simply still pending, and a tracker that's behind on the two that have posted. Let me dig into the second one.

[09:44] **Customer:** Ha! So I'm right that it's broken, just less broken than I thought.

[09:47] **Support console:** Rewards profile refresh executed. Tracker recalculated: $4,281.87. Delta $171.12 = Brightline $95.00 + Novabooks $76.12.

[09:48] **Agent:** Partly right, and now partly fixed: I ran a refresh on your rewards profile and the tracker now reads $4,281.87 — it picked up both posted purchases. The display had gone stale on November 2 rather than the counting being wrong; the refresh snapped it back to what the ledger already knew.

[09:49] **Customer:** Why did it go stale? I check that screen every morning like a lunatic. I don't want to chat you every week for a refresh.

[09:52] **Agent:** Fair question. The honest answer is I can see that it went stale but not why from my seat, so I'm filing a ticket with the rewards platform team with your account and the November 2 date — if there's a refresh job that hiccuped, they can see it and keep it from recurring. You shouldn't need to do anything with the ticket; it's about the display job, not your money.

[09:53] **Customer:** Huh — November 2. My app updated itself that weekend, I remember because the icons moved and I hate when the icons move. Related? If your update broke my tracker I feel like that's worth putting in the ticket.

[09:55] **Support console:** App release history reviewed: version 8.14 rolled out 2025-10-30 through 2025-11-03, staged by region. Account device on 8.14 since 2025-11-01. No tracker-refresh incidents linked to 8.14 in current advisories.

[09:56] **Agent:** I checked — your phone did move to the new app version on November 1, the day before the tracker went stale, so the timing genuinely is suspicious and I've put both dates in the ticket. But I'll be straight with you: there's no known link between that release and tracker refreshes as of right now, and your tracker lives on our side, not in your phone — which is why my refresh from this chair fixed it without you touching the app. The platform team can rule the update in or out with actual logs rather than the two of us squinting at a calendar.

[09:57] **Customer:** "Squinting at a calendar" is exactly what I was doing, yes.

[09:58] **Customer:** Okay. Now the important math. Tracker says $4,281.87. I need $5,000 by November 19. The two pending ones — Fairhaven $212.40 and Casa Molina $180.45 — when do those land?

[10:00] **Agent:** Merchants control their own finalization timing, so I can't promise dates, but I can tell you the patterns from your own account: Fairhaven's authorization was Monday and garden centers commonly batch within a few business days; restaurants like Casa Molina usually finalize once the tip is settled, typically two to four days. Both are inside your window with room to spare if they follow those patterns. Once they post you'd be at $4,674.72, which leaves $325.28 to go before November 19.

[10:01] **Customer:** And there's one more thing that might already cover it. Last Saturday there's a $340 charge from Hillcrest Hotel on my card that I DIDN'T make — wait, no, I did make it, it's my cousin's wedding block deposit. But it shows twice on my app. $340 and then $340 again. If one of those is fraud I want it gone, but if they're both real that's my $325 covered.

[10:03] **Support console:** Transaction search: Hillcrest Hotel $340.00 posted 2025-11-01. Hillcrest Hotel $340.00 authorization hold placed 2025-11-01, status: hold, not posted. No duplicate posting found.

[10:05] **Agent:** Good news on two fronts. There's exactly one real $340.00 charge from Hillcrest — posted November 1, and it's already inside your $4,281.87. The second $340 you're seeing is an authorization hold the hotel placed the same day; holds show in the app but they aren't postings, and this one will simply drop off on its own, usually within a week or two of the stay. So: no fraud, no duplicate, but also no extra $340 toward the bonus — the hold never becomes spend.

[10:07] **Customer:** So the wedding already counted, the ghost $340 is a mirage, and I still need $325.28 after the garden store and the restaurant land. Correct?

[10:08] **Agent:** Exactly correct on all three. You've got eleven days and you're buying holiday things anyway, I'd guess — just keep an eye on posting dates rather than purchase dates for anything after about November 15, since the tracker follows postings.

[10:09] **Customer:** Side question while we're in there — Fairhaven is a garden center, that's about as green as shopping gets. Does that one earn at the higher rate too, or is that a whole other thing?

[10:10] **Agent:** Whole other thing, and worth keeping separate in your head: the bonus tracker we've been staring at counts eligible spend toward your $5,000 no matter what rate the purchase earned. Which rate a given merchant earns is its own question with its own rules in the program guide — I can send that along with your case summary, and the app shows the earned points per transaction once each one posts, so you'll see what Fairhaven actually earned without either of us guessing.

[10:11] **Customer:** Does it matter that some of this will post on a weekend? The restaurant will probably finalize Saturday. Last thing I need is my $180 sitting in some Monday-morning queue past the 19th.

[10:12] **Agent:** Postings process on weekends too — Saturday finalizations show up like any other day, so no Monday queue to worry about. The only calendar advice I'd give is the one I already gave: after about November 15, watch posting dates, because a purchase made on the 18th that posts on the 20th is a posting on the 20th.

[10:13] **Customer:** Last thing and I'll let you go. If the tracker freezes again and I don't notice, and I actually DID spend the $5,000 in time — do I lose the bonus because a widget lied to me?

[10:15] **Agent:** No — and this is worth saying clearly: the tracker is a display. Qualification runs on your posted transactions, not on what the widget managed to show you on a given morning. If the display ever understates you, your postings are still your postings. That said, you shouldn't have to live with a flaky display, which is why the platform ticket matters — and I've put today's refresh, the recalculated figure, and the ticket number in your case notes so any future agent sees the history in one line.

[10:16] **Customer:** TK-88291 or something like that for the ticket?

[10:16] **Agent:** TK-88317 — I just added it to the notes. Anything else this morning?

[10:17] **Customer:** No. Genuinely helpful, thank you. I take back what I said about the widget. Mostly.

[10:17] **Agent:** I'll pass the "mostly" along to the platform team. Good luck with the last $325, Tunde.
