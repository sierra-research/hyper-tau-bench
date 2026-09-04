# Case 019

Case ID: CCR-2510-0655
Channel: Live chat (with desk follow-up)
Contact date: 2025-10-16
Handle time: 16m 20s + follow-up 2025-10-18
QA status: reviewed — process reference

## Transcript
[13:07] **Customer:** Hi. I need a third card in two months and I already know how that sounds. Please hear the whole story before the system says no.

[13:08] **Agent:** Hi, this is Nadia — I promise to hear the story either way. Verification first: email on the profile and date of birth, and a code to your phone.

[13:09] **Customer:** r.castellanos@ferngrove.org, 29 September 1990. Code: 344160.

[13:10] **Support console:** Identity verified, two factors matched. Account lookup: RB-8811037. Card: EcoCard ending 6641, plan code CT-E1, status ACTIVE. Replacement history, trailing 60 days: RPL-70072 (damaged, delivered 2025-09-24), RPL-70269 (returned to sender, closed 2025-10-14).

[13:11] **Customer:** So: September, my card cracked in half in a laundromat dryer — that's the first one. The replacement arrived fine. Then I moved apartments the same week, and the second card — the one replacing the first replacement, long story, the mailing address hadn't updated — went to the old building and came back to you as undeliverable. I never touched it. Now I have no working card and I'm two replacements deep.

[13:12] **Agent:** Let me line your story up with what I see, because it actually matches cleanly. First replacement in September, delivered. The October one shows as returned to sender — carrier couldn't deliver, card came back to us, so it was never in your hands. And your card is an EcoCard, which is our entry tier: the account header shows plan code CT-E1, and the CT-E1 row of the request-limits table allows up to two replacement requests per sixty days. You're at two within the last five weeks, so a third request today is over your tier's limit — the system will refuse it, and honestly it should; that cap exists to stop account-takeover patterns.

[13:14] **Customer:** But one of those two never existed, from my point of view.

[13:14] **Agent:** From the counting system's point of view it was a real order — but from a human's point of view, you've had exactly one card in your hands in two months, and that's precisely the situation the exception path is for. The public limits article says it directly: a legitimate need beyond the tier limit goes to a manual review of the case. I can't override the limit from this desk, and I won't pretend otherwise — what I can do is open the review request now, with the whole history attached: the dryer, the address change, the returned envelope.

[13:16] **Customer:** How long does the review take, and what do I do for money meanwhile?

[13:17] **Agent:** Reviews of this shape usually come back within a business day or two — a specialist reads the account history and decides. I can't promise the outcome, but a returned-to-sender order with a documented address change is about as clean as these get. Meanwhile the account itself is fine; it's the plastic that's missing. If the review approves, the new order ships to your NEW address, which I'm confirming with you right now before anything else happens — what should be on file?

[13:18] **Customer:** 77 Marsh Landing Road, apartment 3B. The 3B matters, evidently.

[13:18] **Agent:** 77 Marsh Landing Road, apartment 3B, confirmed and saved as primary. The review request is open — reference CS-31958 — with the address correction noted so this can't repeat. You'll hear by email, and whichever way it goes a human decided it, not the counter.

[13:19] **Customer:** Thank you. Genuinely. I came in braced for a no.

[13:20] **Agent:** The limit gave you the no; the review exists for the story. Anything else today?

[13:20] **Customer:** That's everything.

[13:21] **Support console:** Case documented: third-request-over-limit conversation, CT-E1 row cited, manual review CS-31958 opened with full history and address correction, no order placed, customer expectations set on review timing.

## Desk follow-up — 2025-10-18
**R. Castellanos (returning, chat):** Got the approval email — what now?

**Agent (Nadia):** Saw it too — CS-31958 approved by the review specialist this morning. Placing the order now against the approval reference, standard delivery to 77 Marsh Landing Road, apartment 3B.

**Support console:** Eligibility confirmed via manual-review approval CS-31958. Discoverable tool unlocked: order_replacement_credit_card_7291. Order submitted — reason other, standard, confirmed address with unit 3B; note: manual review CS-31958 approval attached, prior order returned-to-sender due to stale address, address corrected 2025-10-16. Order RPL-70725.

**Agent (Nadia):** Order's in with the approval attached — RPL-70725, standard delivery, seven to ten business days to the new address. The 3B is on the label. Third time's the charm, and this one's actually addressed correctly.

## QA note — reviewed as process reference
Not a kept call — the ordering interview here is fragmentary by design since the first contact places no order. Referenced by the review desk as the shape of a well-documented exception request: the agent quotes the tier row from the plan code, refuses the override honestly, opens the review with the evidence attached, and fixes the root cause (the address) before any new plastic moves.
