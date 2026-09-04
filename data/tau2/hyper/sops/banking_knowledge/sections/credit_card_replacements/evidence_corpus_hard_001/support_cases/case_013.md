# Case 013

Case ID: CCR-2511-0166
Channel: Internal chat — support engineering triage
Contact date: 2025-11-06
Handle time: 51m (async)
QA status: n/a — internal

## Transcript
[13:40] **Requester (B. Nguyen, card services):** Something odd from the pending-orders lookup. Account CCA-25-6617 — the response came back basically blank. Not the normal nothing-pending answer, I know what that one looks like. This has no orders key at all, just an empty braces pair and a request id.

[13:44] **Support engineering (B. Holt):** Good eye distinguishing those — a real no-pending answer still has its structure, echo of the account id and all. An actually-empty body is not a valid answer to anything. First move: run it again, same identifier.

[13:49] **Requester (B. Nguyen, card services):** Retried once. This time I got structure back but it's... weird? The orders list is there but one entry has a status I've never seen — it just says QUEUED_MIGRATION, and there's no created date on it. The other entry looks normal, delivered in September.

[13:55] **Support engineering (B. Holt):** Yeah, that's past what a retry fixes and past what you should have to interpret. That account is flagged for the platform migration wave and something upstream is emitting a state the tool contract doesn't know about. Don't guess at what QUEUED_MIGRATION means for the customer — send it up.

[13:58] **Requester (B. Nguyen, card services):** Escalating now — what do you need in the ticket?

[14:02] **Support engineering (B. Holt):** The full call context: the account id you queried, timestamps of both calls, what came back each time — the empty body and the weird second response, paste both — and note that a retry was already done. That combination lets us pull the gateway traces without a round of twenty questions.

[14:11] **Requester (B. Nguyen, card services):** Ticket SUPENG-8841 filed with both responses, both timestamps, the identifier, and the retry noted. Customer side I've paused the workflow that needed the answer and set a follow-up.

[14:26] **Support engineering (B. Holt):** Picked it up. Traces show the first call hit a node mid-deploy — that explains the empty body. The QUEUED_MIGRATION state is a migration-tooling leak; the platform team has been told their states are escaping into production responses. For your workflow: I re-ran the lookup from our side just now and got a clean, normal response — one delivered order, nothing pending. Trust that one; screenshot attached to the ticket.

[14:31] **Requester (B. Nguyen, card services):** Clean answer received and recorded with your ticket reference. Resuming the workflow. Thanks for the fast turnaround, Brian.
