# Case 004

Case ID: CRD-2510-0417
Channel: Phone
Contact date: 2025-10-29
Handle time: 12m 05s
QA status: approved

## Transcript
[00:00] **Agent:** Rho Bank card services, this is Tom. What can I do for you today?

[00:07] **Customer:** Yeah, hi. My debit card got declined at the gas station just now. Twice. There's money in the account, I checked the app while I was standing there.

[00:20] **Agent:** That's an annoying way to start a morning — let's figure out what the machine was objecting to. Can I get the email on the account and your date of birth?

[00:33] **Customer:** hector.iribarren@corvusfab.net. March 3rd, 1979.

[00:39] **Support console:** Identity confirmed. RB-7702154, Green Account checking. Debit card lookup: card ending 5531, status ACTIVE, issued 03/24, expires 03/28.

[00:57] **Agent:** Thanks, Hector. Card's active on our side, so it isn't a freeze or a hold. Give me a second to look at the two declines themselves.

[01:10] **Support console:** Authorization log: two declined attempts 09:47 and 09:49, Pump 4, Kwik Fuel #221, both response code 82.

[01:28] **Agent:** Okay. Both attempts came back with decline code 82 — that's what the network calls Negative CAM/CVV Results. In plain terms, when the pump read your card, the chip data or the security code didn't match what's on file for it. That happens for one of two reasons: the card itself is damaged, or someone made a copy of your card and the copy doesn't carry the real chip data. So before anything else — has the card been through anything rough lately? Washing machine, bent in a wallet, scratches on the chip, anything like that?

[02:07] **Customer:** No, it lives in my phone case. It looks fine. The chip's not scratched, I'm looking at it right now.

[02:18] **Agent:** Good — because if the chip were scratched up or the stripe worn, I'd be telling you the card itself is what's garbling the read, and the fix is boring: we order you a replacement and you're done. A healthy-looking card changes the question. No trouble with it at other machines recently — no spots where it needed three or four tries?

[02:28] **Customer:** No, it worked at the grocery store yesterday. Tap, though, not the chip.

[02:37] **Agent:** Alright. Since the card looks healthy, I have to treat this as a security question rather than a hardware question, and I want to explain what that means before I go digging through your account. A code 82 on an undamaged card can mean a counterfeit copy of the card was used — cloned cards carry the printed numbers but they can't reproduce the real chip data, so the network flags the mismatch. It doesn't prove anything happened; a flaky pump reader can do it too. But the way we check is I go through your recent transactions with you and we look for anything you don't recognize. That alright?

[03:22] **Customer:** Yeah, go ahead. Now you've got me worried.

[03:29] **Support console:** Transaction history pulled, account RB-7702154, last 30 days, 41 posted transactions.

[03:45] **Agent:** Reading the last couple of weeks back to you, stop me if something's wrong. Yesterday: $61.18, Hollis Grocery. Monday: $12.40, Corner Pharmacy, and $45 even at an ATM on Delancey. Sunday: $28.75, Vito's. Saturday: two at the hardware store, $19.06 and $112.90...

[04:02] **Customer:** The hardware ones are me, that was shelving. Keep going.

[04:08] **Agent:** ...Thursday: $9.99 streaming, recurring. Wednesday: $84.03, Fuel stop on Route 9. Tuesday last week: $37.61, Hollis Grocery again. That's the last two weeks of card activity.

[04:21] **Customer:** That's all mine. Nothing weird in there.

[04:25] **Agent:** Good — that's the outcome we wanted. To be straight with you about the process: if anything in that list had been yours-but-not-yours, we'd have treated this as a stolen card from that moment and followed that protocol — closed it on the spot and gone through the dispute side. Since the history's clean, what I recommend instead is this: we freeze the card now, and we get a replacement with a fresh number moving to you. The freeze means that if there is a copy of your card out there, it stops working the moment we hang up — and freezing is reversible, so nothing's burned if this turns out to be Pump 4's fault. Once the new card's activated, the old one goes away permanently.

[05:17] **Customer:** How do I buy gas in the meantime?

[05:23] **Agent:** Two things while frozen: transactions on the card will decline, but your ATM access with your PIN still works, so cash is available the whole time. And the replacement doesn't take long.

[05:36] **Customer:** Fine. Freeze it, send the new one.

[05:43] **Agent:** Doing the freeze now.

[05:45] **Support console:** freeze_debit_card_3892 executed, card ending 5531. Status FROZEN. Customer informed: new transactions decline while frozen; recurring payments and subscriptions decline; already-authorized pending items may still process; unfreeze available anytime by phone or app.

[06:08] **Agent:** Frozen. One heads-up from that list we read — your $9.99 streaming charge runs on this card, and while it's frozen that charge will decline too, so if the timing lands this week you may get a nudge from the streaming service. Now the replacement. You're set for our standard delivery unless you need it faster, and the standard blue design unless you want something else.

[06:37] **Customer:** Standard everything. Same as what I have.

[06:41] **Support console:** order_debit_card_5739 executed. Replacement order, issue reason fraud. Delivery STANDARD, design CLASSIC. Fees applied per account tier: $0.00 delivery, $0.00 design. Confirmation and tracking to verified email.

[07:01] **Agent:** Order's in, and the confirmation with tracking is on its way to your email — you can also follow the shipment in the app. When the new card arrives, call us or use the app to activate it, and it needs a fresh PIN at that point. The frozen card stays frozen until then; if the pump thing nags at you in the meantime, you can unfreeze from the app any time, but my advice is to leave it frozen and let the new number take over.

[07:38] **Customer:** And if something weird does show up on the account this week?

[07:44] **Agent:** Then you call us the moment you see it and we take it down the fraud path — that's exactly what the review-and-dispute process is for. But nothing in your history says that's where this is headed. I'd bet on the pump.

[08:03] **Customer:** Alright. Thanks for walking through it instead of just reading a script at me.

[08:10] **Agent:** That's the job. Anything else while I've got you?

[08:17] **Customer:** No, that covers it.

[08:22] **Support console:** Card ending 5531 FROZEN. Replacement order confirmed, PENDING. No disputes filed. Interaction notes: code 82 x2 at third-party fuel pump; card physically undamaged per customer; security explanation given prior to transaction review; 30-day history reviewed with customer, all transactions recognized; freeze recommended and applied pending replacement arrival.
