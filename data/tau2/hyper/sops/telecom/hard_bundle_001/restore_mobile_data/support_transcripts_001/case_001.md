# Case A

Channel: Phone
QA status: Coached
Archive date: 2026-07-16
Start time: 2026-07-15T10:22:41-07:00
Handle time: 5m 39s

## Transcript

[00:00] **Agent:** Northline Care, this is Dario. What can I look at for you today?

[00:05] **Customer:** My data stopped working around breakfast. Full bars, and my wife's phone on the same account is fine.

[00:14] **Agent:** Okay, bars but no data on your line specifically. Have you been able to run a speed test on it?

[00:22] **Customer:** I tried. It sits on "finding server" and then gives up. No number at all.

[00:29] **Agent:** That's useful on its own. Let me pull up your line — can you confirm the number ending you're calling about?

[00:37] **Customer:** Sure. It ends 0417.

[00:40] **Agent:** Thanks. One moment while I open the allowance record for that line.

[00:47] **Console note:** Allowance card, line ending 0417. Plan allowance 10.0 GB; current-cycle use 11.2 GB.

[00:51] **Agent:** Okay, I can see it. You're at 11.2 gigabytes for the cycle and the plan carries 10, so the line has run past its allowance. That's why nothing loads.

[01:04] **Customer:** That can't be right. I bought extra data in June and again like two weeks ago. Doesn't that count for anything?

[01:14] **Agent:** The top-ups apply in the month you buy them, so the plan number is what matters now.

[01:21] **Customer:** The second one was this cycle though. I have the receipt email from the fifth.

[01:29] **Agent:** Hold on — let me get my lead to sanity-check the record with me rather than guess. One moment.

[01:36] **Call event:** Hold, 40 seconds. A second agent joins the line.

[02:16] **Agent 2:** Hi, this is Imani, I sit with Dario's team. I've got your allowance card open. I want to read all three numbers on it out loud, because one of them got skipped.

[02:29] **Customer:** Please.

[02:32] **Console note:** Allowance card re-read: plan allowance 10.0 GB; previously refueled this cycle 2.0 GB; current-cycle use 11.2 GB.

[02:36] **Agent 2:** The card shows plan allowance ten, and it also shows two gigabytes previously refueled this cycle — that's your purchase from the fifth. Those add together. So the line has twelve gigabytes available, and it has used eleven point two.

[02:52] **Agent 2:** Which puts the picture in a very different—

[02:53] **Customer:** So I'm not actually out.

[02:56] **Agent 2:** Correct. Use gets compared against the plan allowance plus what's been refueled, not the plan number alone. Eleven point two against twelve means there's data left, and the account isn't what's blocking you.

[03:10] **Customer:** Then why is nothing loading?

[03:14] **Agent 2:** That's the right question now. Since the allowance still has room, the next step is the same test we started with — I'd like you to run the speed test again while I stay on.

[03:26] **Customer:** Running it. It's… actually showing numbers this time. Download looks high, the little label says excellent.

[03:37] **Agent 2:** Good. Sometimes the test app fails to reach its server once and the retry is clean. Keep that result open a second — does anything on the phone still refuse to load?

[03:48] **Customer:** Uh… yeah. Mail just synced. Maps is drawing. Looks normal.

[03:54] **Agent 2:** Then I'm not going to touch the account, because nothing on it needed correcting. Your line had data available the whole time.

[04:04] **Customer:** So the first read was just wrong?

[04:08] **Agent 2:** The first read skipped the refueled line on the card, yes, and I'll go over that with Dario after the call — comparing use against the bare plan number isn't how the card is meant to be read.

[04:20] **Customer:** As long as I'm not paying for data I can't use, we're fine.

[04:26] **Agent 2:** You're not. To recap: twelve available this cycle counting the refuel, eleven point two used, speed test now excellent with apps loading. I'm noting the case resolved on that verified result rather than on the earlier failed test.

[04:42] **Customer:** What happens when I do cross twelve?

[04:47] **Agent 2:** Then data would stop again and you'd have a choice to make between a bigger plan or another top-up — but that's a conversation for if it happens, and you'd have the say on it.

[04:59] **Customer:** Fair enough. Thanks for actually reading the whole screen.

[05:05] **Agent 2:** That one's on us. Anything else while you have me?

[05:10] **Customer:** No, that was it.

[05:13] **Console note:** Case resolved on verified excellent rerun. No account change. Coaching flag raised on the initial allowance read for QA follow-up.

[05:19] **Agent 2:** Have a good one. And genuinely — sorry for the scare at the start.

[05:25] **Customer:** No harm done. Bye.
