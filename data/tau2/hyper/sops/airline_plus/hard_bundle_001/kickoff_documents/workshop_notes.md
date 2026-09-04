# Workshop notes — reservation shape and servicing limits

Document status: Confirmed workshop decision
Series: Project Atlas design workshops, sessions four through six
Dates: January 16, January 23, January 30
Note-taker: Sofia Grant, reviewed by session participants before circulation

## Why these three sessions are grouped

Sessions four through six all circled one theme: what the assisted channel can and cannot do to the shape of an existing reservation — its travelers, its structure, its fundamental identity. Earlier sessions had covered tooling and staffing; these were the sessions where the whiteboard filled with reservation diagrams and the arguments got specific. These notes consolidate the three sessions because the decision they produced only makes sense with all three days of context.

## Session four, January 16 — the party-size question arrives

The session was scheduled to cover traveler detail edits and spent forty minutes there before the real topic arrived by way of a legacy case Tomas Rivera brought in: a family who had booked four seats and called wanting to add a fifth traveler to the same confirmation. The legacy team had handled it by explaining it could not be done on the existing reservation, but — and this was Tomas's point in raising it — three different agents had given the family three different explanations of why, one of which implied the limitation was temporary and worth calling back about. The callback happened. It went to a fourth agent, who invented a fourth explanation.

The room agreed the case was the perfect specimen of the problem the workshop series exists to solve: a real boundary, informally understood, expensively unexplained. Rina Mehta asked that the question be formulated precisely for decision at the next session, and that engineering bring the system-level facts rather than folklore.

## Session five, January 23 — the system facts

Theo Beaumont opened with the reservation model as it actually exists. A reservation's traveler set is written at creation, and the pricing, seating, and settlement records all hang off that set. The servicing surfaces can edit details within a traveler entry, but the count of entries is structural — the model treats a four-traveler reservation and a five-traveler reservation as different objects, not as versions of one object. Nothing in the servicing toolchain creates or destroys traveler entries on a live reservation, and building such a path was estimated, when it was last scoped years ago, as a rewrite of the settlement layer.

Elena Marquez asked the question that shaped the eventual wording: is this a boundary we are choosing, or one we are acknowledging? Theo's answer, recorded verbatim by request: "Acknowledging. The choice was made by the data model a long time ago; the workshop is deciding whether to be honest about it." The distinction matters for training — a chosen boundary invites appeals to exceptions, an acknowledged one does not.

The session closed with agreement in principle, pending the exact sentence, which Priya Nair volunteered to draft against the scope-language conventions the program had already adopted for other boundaries.

## Session six, January 30 — the decision

Priya presented the draft sentence, the room amended nothing, and the accountable owners present — Rina for operations, Theo for product — approved it for the Atlas scope set. As approved:

Customer service cannot change the number of passengers on an existing reservation.

The confirmed decision above is the reference point; what follows is the guidance discussion that surrounded it, which is context rather than additional policy.

On explanation: the workshop spent its remaining time on what agents should do at the boundary, since the specimen case from session four showed the cost of improvisation. The agreed teaching approach, owned by Sofia Grant for the training materials, is a two-part move — state the boundary plainly, then pivot to what can be done, which in the specimen case would have been discussing a separate booking for the additional traveler. The training draft is due February 13 and will be rehearsed in the February mock-call cycle.

On measurement: Noel Tran will add a contact tag for party-size requests so the pilot learns how often the boundary is hit. The legacy organization never counted them; the four-agent family suggests the count is not zero.

On tone: June Calloway asked that customer-facing phrasing avoid the word "impossible," which reads as unwillingness, in favor of describing what the reservation can hold. Her line from the session, kept here because the room kept quoting it afterward: "We are not refusing the fifth traveler; we are finding the fifth traveler the right place to sit."

## Items the workshop declined to decide

Three adjacent questions were raised and explicitly parked. First, whether group bookings above the standard party size should get a promoted path to the group desk in the booking flow — that belongs to the booking product roadmap, and the workshop recorded interest without claiming authority. Second, a question about how party-size boundaries interact with lap infants was referred to the family travel desk's documentation rather than answered from the room's collective memory, which several participants noted was pulling in different directions. The refusal to answer from memory was itself a small demonstration of Atlas discipline, and the note-taker records it with approval. Third, the checked-bag question that discovery's payment interviews carried in — the legacy floor's remembered practice of taking a paid bag off a reservation and returning the baggage fee, on a cutoff no two agents stated alike — was ruled outside this workshop's charter and sent to the servicing-authority follow-up already on the calendar for February 6, whose outcomes are recorded in the servicing scope sheet. The room's contribution was taxonomy: an authority-list row, not a reservation-shape question, decided where those rows live.

## Attendance and review

Session four: Rina Mehta, Theo Beaumont, Maya Wei, Elena Marquez, Tomas Rivera, Sofia Grant, June Calloway. Session five: the same group plus Priya Nair and Noel Tran. Session six: full working group. These notes circulated in draft on February 1; corrections from Tomas (the specimen case involved four seats, not five, before the requested addition) and Elena (attribution of the choosing-versus-acknowledging question) are incorporated. No corrections touched the decision language, which is reproduced above exactly as approved.

Questions about these notes go to Sofia Grant. Questions about the decision go to the accountable owners. The distinction, as ever in Atlas, is the point.
