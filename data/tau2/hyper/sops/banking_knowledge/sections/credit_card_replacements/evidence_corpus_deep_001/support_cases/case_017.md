# Case 017

Case ID: CCR-2511-0288
Channel: Phone
Contact date: 2025-11-06
Handle time: 13m 40s
QA status: approved — kept-call library

## Transcript
[10:02] **Agent:** Rho Bank card services, this is Priya. Who am I speaking with today?

[10:02] **Customer:** Morning — Warren Hollis. I need my credit card replaced. There's a charge on it from a gas station in a state I haven't been to since college, so I'm assuming the number's out there somewhere.

[10:03] **Agent:** That's the right instinct, Mr. Hollis — let's treat it that way from the start. First I need to verify you: the email on the profile and your date of birth, and I'll text a code to the number on file.

[10:04] **Customer:** w.hollis@plainsnet.com, third of July, 1981. And the code just came through — 517209.

[10:05] **Support console:** Identity verified, two factors matched. Account lookup: RB-2214906. Card: Silver Zoom ending 4180, plan code CT-M1, status ACTIVE. Replacement history, trailing 60 days: none. One disputed transaction flagged this morning, dispute case open.

[10:05] **Agent:** Verified, and I can see the dispute your fraud team contact opened this morning, so that part's already moving. I'm freezing the card ending 4180 right now. Frozen. Now — for the card itself, I'm recording the replacement reason as suspected fraud, and on suspected fraud we strongly recommend expedited shipping, because the sooner the compromised card is out of circulation entirely, the better.

[10:06] **Customer:** How fast is expedited, and what's the damage? Actually — the Zoom card's the fancy one, right? My wife's Gold card came with all the free perks. I'd assume mine ships free too.

[10:07] **Agent:** That's exactly the assumption I want to check rather than guess at, because the names mislead people constantly. Give me one second — I'm reading your account header, not the card's name. The header shows plan code CT-M1. Now I'm putting that against the fee schedule... the CT-M1 row — that's our mid tier — shows expedited at ten dollars, two to three business days. The Zoom name sounds premium, I grant you, but Silver Zoom sits in the mid tier. Your wife's Gold card is a CT-P1 — premium row, which is where the complimentary expedited lives.

[10:08] **Customer:** Huh. So the zippy name is just a name.

[10:08] **Agent:** Just a name. If it helps, there's a public card-directory article that lists every card with its plan code, because you're not the first to ask — the green-looking card isn't the green-named one either, and I've seen an agent trip on that, so we're trained to read the code, not the name. So: expedited at ten dollars, or standard at no fee, seven to ten business days. Given it's suspected fraud, my recommendation stays expedited.

[10:09] **Customer:** Do it expedited. Ten dollars to make this go away faster is fine.

[10:10] **Agent:** Then I need your explicit okay on the record: a ten-dollar expedited delivery fee applies to this replacement and posts with the order. Do you acknowledge the fee?

[10:10] **Customer:** Yes, I acknowledge the ten dollars.

[10:10] **Support console:** Field fee_acknowledged set. Expedited fee $10.00 per CT-M1 schedule row.

[10:11] **Agent:** Thank you. Address check — I show 1418 Corrow Lane, unit noted as none. Is that where the courier should go?

[10:11] **Customer:** That's the house, yes. No unit.

[10:12] **Agent:** Confirmed as read. And while I place this: after the order goes in, your current card is cancelled outright — the dispute on the gas-station charge isn't affected, that's on its own track. The new card arrives with different numbers, so streaming services, the toll transponder, anything saved — those get the new number once it's in your hands.

[10:13] **Customer:** Understood. The toll thing would've bitten me. Good warning.

[10:13] **Support console:** Eligibility confirmed per knowledge base. Discoverable tool unlocked: order_replacement_credit_card_7291. Order submitted — reason fraud_suspected, expedited, $10.00 acknowledged, confirmed address 1418 Corrow Lane; note: dispute case open on gas-station charge, customer aware card cancellation is independent of dispute. Order RPL-71102.

[10:14] **Agent:** Order's in. You'll get an email now and a second when it ships — with expedited that's usually same day, and you should be holding the card within two to three business days. While you wait, keep an eye on the account in the app; the frozen card can't spend, but the dispute team may message you there.

[10:15] **Customer:** Will do. And the ten dollars shows up where?

[10:15] **Agent:** On the next statement, as "Expedited card delivery," ten even. Anything else I can do for you today?

[10:16] **Customer:** No — that covers it. You saved me from arguing about a fee that was never going to be free. Thanks, Priya.

[10:16] **Agent:** Read the code, not the name — it's the house rule. Take care, Mr. Hollis.

[10:17] **Support console:** Case documented: fraud_suspected replacement RPL-71102, expedited with fee acknowledged, freeze applied prior to order, dispute independence explained, saved-card update guidance given.

## QA review — G. Ott, 2025-11-10
Kept for the library, and I want this one in the next coaching rotation. The customer arrives with a plausible wrong belief — premium-sounding name, therefore premium treatment — and the agent neither agrees nor argues from memory: she reads the plan code off the account header, resolves it against the schedule row out loud, and names the trap explicitly. The fee acknowledgement is captured as its own beat, on the record, before submission. This is what "quote the row, not the name" sounds like on a live call.
