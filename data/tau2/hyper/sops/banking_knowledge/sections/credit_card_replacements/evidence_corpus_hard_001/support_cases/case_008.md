# Case 008

Case ID: CCR-2510-0951
Channel: Internal chat — support engineering triage
Contact date: 2025-10-30
Handle time: 14m (async)
QA status: n/a — internal

## Transcript
[11:02] **Requester (M. Grant, closures):** Hey — pending-orders lookup is bouncing an account and I can't see why. Identifier straight off the case: 5311-2209-4417-0083. Error says invalid credit_card_account_id.

[11:05] **Support engineering (B. Holt):** That's why — that's a sixteen-digit card number, not an account id. The lookup wants the account-level identifier, the CCA-prefixed one. Where'd you copy it from?

[11:07] **Requester (M. Grant, closures):** From the card panel on the closure case. ...which is the card list, not the header. I see it. The header shows CCA-33-7208.

[11:09] **Support engineering (B. Holt):** Run it with CCA-33-7208 and you should be fine. Card-level ids never resolve on that tool even when they belong to the right customer — it checks the account, cards hang off it.

[11:13] **Requester (M. Grant, closures):** That did it, clean response this time. Honestly the card panel puts its id front and center and the header id is tiny — I grabbed the shiny one.

[11:15] **Support engineering (B. Holt):** You're not the first this month and you won't be the last. There's a runbook page for exactly this failure — search the tool number in the knowledge base, first article. Worth a bookmark if your team runs these daily now.

[11:18] **Requester (M. Grant, closures):** Bookmarked. Also filing a UI gripe about the tiny header id, because the fix shouldn't be everyone learning the hard way.

[11:20] **Support engineering (B. Holt):** Seconded, cc me on the gripe. For your notes: nothing was wrong with the account or the tool — identifier format issue, resolved on re-run with the account-level id, no data impact. Closing this on my side.

[11:21] **Requester (M. Grant, closures):** Noted on the closure case with the timestamp. Thanks, Brian.
