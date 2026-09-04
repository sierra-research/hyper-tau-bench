# Case 006

Case ID: CCR-2510-0791
Channel: Live chat
Contact date: 2025-10-22
Handle time: 11m 05s
QA status: approved — kept-call library

## Transcript
[15:42] **Customer:** Hello — I've managed to lose my credit card somewhere between a taxi and a restaurant last night. I've looked everywhere it could reasonably be. I fly to Lisbon on Friday, which is why I'm not waiting another day to report it.

[15:43] **Agent:** Hi, this is Victor — let's get you sorted well before Friday. Verification first: the email on your profile and your date of birth, please, and I'll send a code to your phone.

[15:44] **Customer:** h.okonkwo@brightmail.com, 14 February 1969. Code received: 902241.

[15:45] **Support console:** Identity verified, two factors matched. Account lookup: RB-6704415. Card: Platinum Rewards Card ending 2277, plan code CT-P1, status ACTIVE. Customer travel note on file from prior contact: none. Replacement history, trailing 60 days: none.

[15:45] **Agent:** Verified. Before anything else I'm freezing the card ending 2277 so nothing can happen while we talk. Done. Now — you said Friday. Tell me about the trip, because it changes what I recommend.

[15:46] **Customer:** Two weeks in Portugal, leaving Friday morning. I'd very much like to not be abroad with no credit card.

[15:47] **Agent:** Agreed, and here's the honest picture. I'm recording this as a lost card and ordering the replacement now. Standard delivery runs seven to ten business days — with your Friday flight that's not even close. With your trip coming up, expedited shipping is how we make sure the replacement card is in your hands within the accelerated timeframe — it moves by courier instead of regular mail. Today's Wednesday; that puts it at your door before you leave, with a day of cushion.

[15:49] **Customer:** And what does the courier option cost me?

[15:49] **Agent:** Let me answer that from the row rather than from memory — your account header shows plan code CT-P1, and I'm reading the premium row of the fee schedule against it. On your card it costs nothing — expedited shipping is complimentary on the Platinum Rewards Card. The $0.00 will show on the order confirmation, which I realize is a slightly absurd line item, but there it is. And because the fee is zero there's no consent box for me to read you — that step only exists when a fee applies.

[15:50] **Customer:** The best kind of line item. Yes, expedited, please.

[15:51] **Agent:** Now the address, and given the deadline I want this exact: I show 92 Halloway Court on file, no unit. Is that where the courier should deliver?

[15:52] **Customer:** Yes — but it's the coach house behind the main house, the drivers miss it constantly. Can you note that? "Coach house at rear, ring the side bell."

[15:53] **Agent:** In the order notes verbatim, along with your travel date so fulfillment sees the constraint. Placing the order now.

[15:54] **Support console:** Eligibility confirmed per knowledge base. Discoverable tool unlocked: order_replacement_credit_card_7291. Order submitted — reason lost, expedited, $0.00 complimentary, confirmed address with delivery note: coach house at rear, ring side bell; note: customer departs Friday AM, Lisbon two weeks. Order RPL-70914.

[15:54] **Agent:** Done — order confirmed. You'll get an email now and another when it ships, likely tomorrow. Watch for the courier Thursday. If Thursday evening comes and there's no card, call us immediately — there are things we can still do before a Friday morning flight, but only if we know Thursday.

[15:56] **Customer:** Understood. And if the old card turns up in a jacket pocket in March?

[15:56] **Agent:** Cut it up — it stopped being a card the moment this order went in. The new one has different numbers, so anywhere that bills you automatically will want updating once it arrives; the packet that comes with the card walks through it.

[15:58] **Customer:** Very good. You've been unreasonably efficient. Thank you, Victor.

[15:58] **Agent:** Enjoy Lisbon — and check the coach house bell works before Thursday. Anything else today?

[15:59] **Customer:** Nothing. Goodbye.

[15:59] **Support console:** Case documented: lost card, expedited replacement RPL-70914 with travel constraint and courier delivery note, freeze applied prior to order, customer advised on Thursday fallback window.

## QA review — G. Ott, 2025-10-27
Kept for the library. Two lessons now. First, the fee quote: the agent reads the plan code off the account header and quotes the row it maps to — never the card's name, which on other tiers has burned people. Second, the sequencing: the agent surfaces the timeline pressure before quoting anything, so the shipping recommendation lands as a plan rather than an upsell. The delivery-note capture and the Thursday fallback are the kind of specifics that make expedited actually work for a travel deadline instead of just being faster on paper.
