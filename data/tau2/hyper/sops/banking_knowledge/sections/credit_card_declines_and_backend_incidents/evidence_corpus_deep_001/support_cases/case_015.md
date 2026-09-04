# Case 015

Case ID: CCD-2511-0611
Channel: Live chat
Contact date: 2025-11-09
Handle time: 44m 37s
QA status: approved

## Transcript
[19:41] **Customer:** FRAUD. my card just got declined at the hotel front desk and when I opened the app there are charges I never made. a $1 charge and a $312 charge from something called "STAYWELL PROP MGMT LLC" which I have NEVER heard of. freeze the card RIGHT NOW and get me the fraud department

[19:42] **Agent:** Hi, this is Monica. I hear you, and if there's unauthorized activity on this card we will treat it exactly that seriously. Before I take a step as big as freezing the card you're traveling with, give me ninety seconds to look at what those charges actually are — a freeze at a hotel desk at night is hard to undo if this turns out to be something else. First, verification: the email on your file and your date of birth, please.

[19:43] **Customer:** halvarado@brightpine.net 11/02/1975. please hurry, there's a line behind me and my wife is still at the desk

[19:44] **Support console:** Identity verified, two factors matched. RB-4471566. Card ending 9917: pending $1.00 and $312.48, merchant STAYWELL PROP MGMT LLC, both today 19:12. Authorization declined 19:38, $312.48, same merchant. No other activity since 11/06.

[19:45] **Agent:** Verified — thank you, Hector. Now, one question that decides a lot: the hotel you're standing in. Could you tell me its name exactly as it's on the sign?

[19:46] **Customer:** the maplecourt inn & suites. why

[19:47] **Agent:** Because hotels very often bill under their parent company's name rather than the name on the sign. Give me a moment to look at the merchant record on those charges.

[19:48] **Customer:** are you saying I'm being scammed by my own hotel lol

[19:49] **Support console:** Merchant record, STAYWELL PROP MGMT LLC: lodging category, billing entity operating multiple properties incl. "Maplecourt Inn & Suites". Merchant location matches authorization location.

[19:50] **Agent:** The opposite, happily. STAYWELL PROP MGMT is the company that owns the Maplecourt — the $1 is their card check and the $312.48 is the room hold they placed when you checked in tonight. Both were made by the hotel, in person, on your card. There's no stranger on this account.

[19:51] **Customer:** ok but then why was the card DECLINED five minutes ago. if the hold went through the card obviously works

[19:52] **Agent:** Fair question, and the timing tells the story. The hold from 19:12 is still sitting on the card as pending. When the desk ran it again at 19:38 — it looks like they attempted the hold a second time — the card said no, because the first $312.48 is already spoken for and the second one together with it went past your available credit. The card isn't broken; it's refusing to be double-charged.

[19:53] **Customer:** hang on my wife is talking to the desk person

[19:56] **Customer:** ok the desk says their system "timed out" at check in so they ran it again. they're saying it's declined on their screen and I need to fix my card

[19:57] **Agent:** Their timeout explains everything — their first attempt succeeded on our side even though their screen never got the answer. So they're holding your room money once, trying to hold it a second time, and reading our refusal as your problem. The fix is on their side: ask them to check in their system for an approved authorization from 19:12 for $312.48. If they find it, they attach the room to that approval and nobody runs anything again.

[19:58] **Customer:** telling my wife to say that. this is like a game of telephone

[19:59] **Customer:** while she does that. now that I'm actually READING my pending list for once, what is "CRSTL SPRNG VNDG $4.50" from thursday. I don't buy crystals

[20:00] **Agent:** Let me look — and for what it's worth, this is the healthiest possible use of a hotel-lobby wait.

[20:00] **Support console:** Merchant record, CRSTL SPRNG VNDG: automated retail category, vending operator "Crystal Spring Vending Services". Card ending 9917: $4.50 settled 11/06, contactless, in-person.

[20:01] **Agent:** Crystal Spring Vending — it's a vending machine operator, and the charge was contactless and in person on Thursday. Ring any bells? Office building, gym, hospital lobby?

[20:02] **Customer:** ...the water bottles at my office. I tap my card on that machine literally every day. why does it say thursday if I use it daily

[20:03] **Agent:** Vending operators usually batch a few days of taps into one charge, so a Thursday line item can be Monday through Thursday's bottles wearing one name tag. If the amounts ever stop matching your bottle habit, that's worth a chat — but $4.50 is a very honest number for a week of water.

[20:04] **Customer:** this app should just SAY crystal spring vending. and the hotel should say maplecourt. is there a reason merchant names are all in witness protection

[20:05] **Agent:** You've found the single most-asked question in card support. The name on the charge comes from how the merchant registered with their payment processor, sometimes decades ago, and we display what they send. I agree it's unhelpful — and it's also why the first move on a scary charge is the lookup I just did, not the freeze. Most "fraud" dissolves the moment the legal name gets translated.

[20:06] **Customer:** ok wife update. the desk person says she sees it in a "pending batch" but her manager says policy is to run a fresh auth at check in and the pending one will "fall off"

[20:07] **Agent:** That policy works fine when the card has lots of headroom — the fresh hold approves, the old one falls off in a day or two, nobody notices the overlap. Tonight the overlap is exactly what your available credit can't hold, which is the only reason you're in this chat instead of at dinner. Two honest options, and I'll help with either. One: I can temporarily raise nothing and change nothing — you ask the manager to attach the room to the 19:12 approval, which their own batch shows. Two: if the manager won't budge, I can release the 19:12 hold from our side while you stand there, and their fresh authorization will have room to approve.

[20:08] **Customer:** option two sounds faster. do that

[20:09] **Agent:** One thing to know before I do: releasing the hold takes a few minutes to reflect, and if the desk runs the new auth before it clears, we're back where we started. So the order matters — I release, we watch it drop off your pending list together, and *then* the desk runs the card. Agreed?

[20:10] **Customer:** agreed. my wife is negotiating a free breakfast out of this in the meantime

[20:11] **Support console:** Authorization release executed after customer confirmation: $312.48 hold from 19:12 released. Card ending 9917: pending $1.00 only.

[20:12] **Agent:** Released on our side. Watch your app — the $312.48 pending line should disappear within a few minutes. The $1 will linger a day or two and vanish on its own; that one never turns into money.

[20:13] **Customer:** while we wait, explain something. if the card was too full for the second $312, how did the $1 go through at the same time? your math has a hole in it

[20:14] **Agent:** Fair audit, and the math survives it. The $1 ran at 19:12 alongside the first hold, back when the card still had room for both — it's the card check hotels run before the real hold, and a dollar fits almost anywhere. The thing that bounced at 19:38 was the second $312.48, because by then the first $312.48 was already sitting on the card. Order of operations, not arithmetic.

[20:14] **Customer:** ok that tracks. my wife says the manager is now claiming the release "won't show on their end for 24 hours" and wants a different card

[20:15] **Agent:** The manager is describing their settlement report, which does lag — but authorizations don't read from that report. When they run the card, the request comes to us live, and on our side the room's worth of credit is free right now. You don't need a different card; you need them to press the button. If it declines again with the hold released, I'll be right here looking at exactly what reached us, and we'll know whose end it's on.

[20:15] **Customer:** she relayed that basically word for word. the desk person is overruling the manager which is the best thing I've seen all day

[20:16] **Agent:** Front desk staff who watch the batch screen all day usually know it better than the policy does. While they run it: your app should now show only the $1 from earlier — confirm that matches what you see before they submit, so we're testing one change at a time.

[20:16] **Customer:** confirmed, just the $1. running it now

[20:17] **Customer:** it's gone from the app. desk is running the card again. moment of truth

[20:19] **Customer:** APPROVED. room key in hand. breakfast negotiations also successful

[20:20] **Agent:** Excellent on both counts. Recap for your records: no fraud tonight — every charge was the hotel under its parent-company name, the decline was the card refusing a double hold, and the account needed no freeze, no new card, nothing. Your card is exactly as safe as it was this morning.

[20:21] **Customer:** honestly I came in ready for a war. thank you for not just freezing it, I'd have been stuck at the desk with a dead card

[20:22] **Agent:** That's exactly why we look before we freeze — a freeze is the right tool when there's a stranger on the account, and the wrong one when the "stranger" turns out to be your own hotel. One last thing: keep an eye on checkout day. If the desk's system hiccups again and you see a second room charge appear, chat back in with this case number — the whole history is on file.

[20:23] **Customer:** will do. goodnight monica

[20:24] **Customer:** my wife says thank you too

[20:25] **Agent:** Goodnight to you both, and enjoy the breakfast you won.
