# Discovery intake — payment and account boundaries

Document status: Confirmed scope boundary
Prepared for: Project Atlas assisted-service discovery
Compiled by: Maya Wei (Harbor Point CX), with contributions credited inline
Covers: discovery interviews and system walkthroughs, December 5 through December 29

## How to read this intake

This document separates three kinds of material, and the separation is the point. Confirmed boundaries have been approved by the accountable owners and may be treated as settled. Observations are things we saw or were told during discovery that nobody has ratified. Open questions are exactly that. During the December sessions we watched several well-meaning readers of early drafts treat observations as rules, so each section below is labeled, and the label wins over the prose.

## Confirmed boundary

The following requirement was approved on December 27 by Rina Mehta as the accountable operations owner and Theo Beaumont for Reservation Products, and it governs the assisted channel from pilot onward:

Customer service cannot add a new payment method to a customer account.

Discovery context for the boundary, for readers who want the reasoning rather than just the rule: the payment instrument lifecycle — adding, verifying, and storing cards and other methods — lives entirely in the customer-controlled account surface, behind the customer's own authentication. The assisted channel operates against the reservation and servicing surfaces, which consume stored instruments but were never built to originate them. During the December 14 walkthrough, Theo demonstrated that the servicing console exposes no entry path for instrument creation, so the boundary is enforced by the software as well as by the rule. The working group chose to write it down anyway, on the argument Priya Nair made in that session: software changes on someone else's schedule, and a written boundary survives a release.

## 1. Account surface walkthrough

Devon Okafor hosted the December 7 account-surface session. The team traced a customer's self-service journey from sign-in through stored traveler details, communication preferences, and the payment wallet. Two observations worth preserving: first, the wallet presents stored instruments to downstream flows as masked references, so no complete instrument detail ever transits the servicing tools; second, the account recovery path is owned by a separate identity team with its own controls, and nothing in Atlas discovery touched it.

Observation, not a rule: agents shadowing the session noted customers frequently describe the wallet as "my saved cards" even when it holds other instrument types. Training materials may want to mirror the customer's vocabulary before introducing the system's.

## 2. Reservation surface walkthrough

Theo Beaumont hosted the December 14 reservation-surface session, covering search, booking, and servicing screens in the rehearsal environment. The reservation surface reads from the wallet at the moment of payment and writes nothing back to it. The one place discovery found where a payment method appears on screen inside the servicing console is the settlement step of a change, where stored instruments are listed for selection by their masked references.

Open question raised in this session, owner Theo, due at the January readiness review: whether the settlement step should display instrument nicknames the customer set in their wallet, which would help identification on calls, or keep the bare masked references it shows today.

## 3. Interviews with the current support organization

Between December 11 and December 22, Maya Wei and Sofia Grant interviewed eleven agents and three supervisors from the legacy support team. On payments, the interviews were unanimous in an instructive way: every interviewee independently described customer requests to "just take a new card number over the phone," and every interviewee described declining, though their explanations to customers varied widely in accuracy and grace. The variation is the finding. The rule was already effectively in force; what the organization lacked was a shared, approved sentence to say about it. That is what the confirmed boundary above supplies, and the training workstream owns turning it into customer-friendly language.

One supervisor's phrasing from the December 22 interview struck the team as worth keeping for the training deck: "The account belongs to the customer; the reservation is where we can help." It is not policy language, but it is the right shape of explanation.

Observation, not a rule: the same payments interviews preserved a piece of legacy floor practice before it evaporates. Seven of the eleven agents, unprompted, described settling a flight-change charge with a travel certificate from the customer's wallet by running the change through the reissue screen on the old reservation front-end — a reissue rewrote the whole trip and took whatever instrument the wallet already held. "A certificate was as good as cash for a change fee," the December 16 session's recurring phrasing. The ending is dated: the reissue screen did not survive the August front-end consolidation. Where change charges get settled now lives on Meridian's servicing surfaces and help pages; this intake, as ever, links rather than quotes.

One more legacy practice surfaced in the refund portions of the same interviews. Agents in the December 13 and December 20 sessions independently described what the floor calls the bag walk-back: a customer who had paid for a checked bag could call back, have the bag taken off the reservation, and see the baggage fee returned, provided the request beat a cutoff. On the cutoff the floor agreed on nothing — the nightly settlement batch, midnight, check-in, a day from purchase — each version delivered with confidence. Two agents offered to demonstrate in the old fulfillment tool; its first screen no longer accepts that input, and neither could say when that changed. An observation in the intake's strict sense, ratified by nobody; whether the assisted channel has any version of it is logged under follow-ups below, not answered here. The label wins.

## 4. Adjacent boundaries recorded elsewhere

Discovery repeatedly brushed against boundaries that belong to other documents, and this intake deliberately does not restate them. Identity and profile edits surfaced in the December 11 and December 18 interviews; the workshop series covers reservation-shape questions; the servicing scope sheet covers the full authority list. Restating boundaries in multiple documents was specifically argued against by Priya in the December 27 session — every copy is a chance to drift — and the working group adopted her position for all Atlas documentation. Where this intake touches an adjacent topic, it links rather than quotes.

## 5. Risks and follow-ups

Four follow-ups left discovery with owners attached, three of them dated. Devon owns confirming that the account-surface session's findings hold for the mobile app's wallet implementation, due January 10. Sofia owns the first draft of customer-facing phrasing for the payment boundary, due January 17, with June Calloway reviewing tone before anything reaches a script. Noel Tran owns adding a tracking category for payment-boundary contacts to the reporting warehouse, due January 12, so the pilot can measure how often the boundary comes up rather than guessing. Maya owns carrying the bag walk-back question into the workshop series, with whatever gets decided landing in the servicing scope sheet; its date belongs to the workshop calendar.

One risk is recorded without an owner because it belongs to everyone: discovery found the legacy team's informal explanations of the payment boundary ranged from correct to inventively wrong, and several of the wrong versions were more memorable than the right one. The mitigation is not more documentation; it is the approved sentence above, taught early, repeated verbatim, and reinforced by evaluators who score against it.

## Session log

December 5: intake kickoff, full working group. December 7: account surface walkthrough, hosted by Devon Okafor. December 11, 13, 16, 20: legacy support interviews, Maya Wei and Sofia Grant. December 14: reservation surface walkthrough, hosted by Theo Beaumont. December 27: boundary ratification session, accountable owners present. December 29: intake review and sign-off for circulation.

Corrections to this document route to Maya Wei; disputes about the confirmed boundary route to the accountable owners, not to this document's compiler.
