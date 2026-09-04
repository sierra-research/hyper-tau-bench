# Case 010

Case ID: CCR-2511-0102
Channel: Internal chat — support engineering triage
Contact date: 2025-11-03
Handle time: 22m (async)
QA status: n/a — internal

## Transcript
[09:14] **Requester (N. Price, card services):** Morning — I'm getting permission denied on the pending-orders lookup. Worked for me all of last week. Account id is right this time, I triple-checked, CCA-19-4471.

[09:20] **Support engineering (Y. Tanaka):** Two usual suspects for a denial. One: your session — gateway sessions expire on their own clock, so if you signed on before your first coffee, sign out of the internal environment fully and back in, then retry.

[09:26] **Requester (N. Price, card services):** Re-authenticated, retried, same denial. And yes it was a full sign-out, I even got the annoying survey.

[09:29] **Support engineering (Y. Tanaka):** Then suspect two: the role grant itself. Weren't you on the deposits desk until recently? The lookup permission rides on the card-services role, and transfers sometimes land with the old role still attached for a few days.

[09:33] **Requester (N. Price, card services):** Transferred October 27th. My console says card services everywhere I can see it.

[09:36] **Support engineering (Y. Tanaka):** The console label and the gateway grant aren't the same thing, annoyingly. Checking the grant table... yep, there it is: your gateway role updated but the tool-access group didn't come with it. Provisioning miss on the transfer, not anything you did. I've pinged access management with the fix — usually inside an hour.

[10:12] **Requester (N. Price, card services):** Just retried on a fresh session — clean response, orders list and everything. That was quick.

[10:15] **Support engineering (Y. Tanaka):** Access management had a good morning. For your case notes: denial cause was a stale tool-access group after desk transfer; resolved by provisioning fix; re-auth alone was correctly attempted first and ruled out the session. If anyone else from your transfer cohort hits this, send them straight to me with their transfer date.

[10:18] **Requester (N. Price, card services):** Will do — there were four of us in that cohort, forwarding this thread to the other three preemptively. Thanks, Yuki.
