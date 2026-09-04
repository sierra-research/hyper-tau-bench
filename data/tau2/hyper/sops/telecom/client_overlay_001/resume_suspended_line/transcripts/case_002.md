# Case B

Channel: Live chat
QA status: Flagged for coaching
Archive date: 2026-07-30
Chat opened: 2026-07-24T13:41:05-07:00
Active handle time: 2m 31s
Chat span: 3m 37s

## Transcript

[2026-07-24 13:41:05 PT] **Agent:** Northline support, Marco here. How can I help today?

[2026-07-24 13:41:16 PT] **Customer:** My phone has no service and the app says my line is suspended. I assume I owe you money. Let's fix that.

[2026-07-24 13:41:29 PT] **Agent:** Appreciate the directness! I've got the account open off your contact info — first, just to confirm the line: ending 3384?

[2026-07-24 13:41:38 PT] **Customer:** Yes.

[2026-07-24 13:41:46 PT] **Console note:** Affected line identified (ending 3384). Line record read: Suspended, reason Overdue balance.

[2026-07-24 13:41:56 PT] **Agent:** Right — suspended for an overdue balance. Pulling your recent bills now... I see the July bill sitting there at $74.90 — that'll be our target.

[2026-07-24 13:42:02 PT] **Console note:** Recent bills pulled for the account.

[2026-07-24 13:42:05 PT] **Agent:** The amount due is $74.90 — want me to send the payment request to your phone?

[2026-07-24 13:42:12 PT] **Customer:** Sure, send it.

[2026-07-24 13:42:19 PT] **Console note:** Payment request sent for the July bill.

[2026-07-24 13:42:26 PT] **Agent:** It should appear as a Northline payment request on your phone in a moment.

[2026-07-24 13:42:57 PT] **Customer:** Okay, paid it. It went through — my bank app agrees, sadly.

[2026-07-24 13:43:06 PT] **Agent:** Perfect. Refreshing the account... hm. The July bill shows Paid now, but the line still isn't showing as eligible to resume.

[2026-07-24 13:43:21 PT] **Customer:** Meaning what? I just paid the thing.

[2026-07-24 13:43:29 PT] **Agent:** You did, and the payment's fine. The eligibility just isn't updating on my screen. Sometimes billing takes a while to sync overnight — I'd give it until tomorrow morning, and the line should come back once the system catches up.

[2026-07-24 13:43:48 PT] **Customer:** So I paid and I still have no phone until maybe tomorrow? Great.

[2026-07-24 13:43:57 PT] **Agent:** I know that's not the answer you wanted. I've noted everything on the case, and if it's not back by mid-morning, reach out and reference this chat.

[2026-07-24 13:44:09 PT] **Customer:** Fine. Noted. Goodnight, I guess.

[2026-07-24 13:44:14 PT] **Console note:** Case closed — pending overnight sync per agent note. Line not resumed.

[2026-07-24 13:44:21 PT] **QA annotation (post-review, 2026-07-29):** Flagged. The July bill this chat paid was never overdue — its status was Issued when the request went out. The June bill — the one actually marked Overdue and the recorded cause of the suspension — was never touched, which is why eligibility never moved. There is no overnight sync. Billing Operations unwound the misdirected request the next day (see the follow-up contact); the incident review circulated to care leads on July 28, and the procedure revision that described the send control as validating the selected bill at send time was archived on July 26. Coaching works from the current revision of NW-BILL-8112 and its bill-state handling reference.

## Follow-up contact

Channel: Live chat
Chat opened: 2026-07-25T09:22:18-07:00
Active handle time: 2m 36s
Chat span: 3m 40s

[2026-07-25 09:22:18 PT] **Agent:** Good morning, this is Anaya with Northline care — you chatted with us yesterday about the line ending 3384. I have good news and a correction.

[2026-07-25 09:22:32 PT] **Customer:** The phone still says no service, so I'm ready for both.

[2026-07-25 09:22:41 PT] **Agent:** The correction first: yesterday's payment request went against your July bill, which wasn't overdue — it was just issued and wasn't due yet. Billing Operations has unwound that request this morning, and the payment you made is being applied correctly, so you won't be out anything.

[2026-07-25 09:23:02 PT] **Customer:** So I paid a bill that didn't need paying, and the one that got me suspended is still sitting there?

[2026-07-25 09:23:14 PT] **Agent:** Exactly right, and that's on us. The bill behind the suspension is June, $52.40, and it still shows Overdue. That's the one the request should target. Want me to send it to your phone now?

[2026-07-25 09:23:30 PT] **Customer:** Yes. Let's pay the correct bill, as a novelty.

[2026-07-25 09:23:37 PT] **Console note:** June bill verified Overdue before the request. Payment request sent after customer confirmation; yesterday's misdirected request unwound by Billing Operations (ref BO-2214).

[2026-07-25 09:23:46 PT] **Agent:** Request is on your phone.

[2026-07-25 09:24:12 PT] **Customer:** Paid. Again. But with feeling this time.

[2026-07-25 09:24:21 PT] **Agent:** June shows Paid, and the full bill check comes back clean — nothing else in Overdue. The next step resumes the line. Go ahead?

[2026-07-25 09:24:34 PT] **Customer:** Yes please.

[2026-07-25 09:24:39 PT] **Console note:** All bills confirmed clear of Overdue. Line resumption run on 3384 after customer confirmation.

[2026-07-25 09:24:46 PT] **Agent:** Done — the resumption ran clean, and the record shows the line ending 3384 back to Active on my side.

[2026-07-25 09:25:10 PT] **Customer:** I just restarted the phone for luck... and we have bars. Finally.

[2026-07-25 09:25:18 PT] **Agent:** That matches what I'm seeing here — and no overnight anything required. Thanks for your patience with the detour.

[2026-07-25 09:25:29 PT] **Customer:** Thanks for the correction. Tell yesterday's system I said nothing polite.

[2026-07-25 09:25:37 PT] **Agent:** Will do. Quick recap before you go: June bill paid and showing Paid, line ending 3384 resumed, and service back on your end. Anything else?

[2026-07-25 09:25:46 PT] **Customer:** No, that's everything. Thanks Anaya.

[2026-07-25 09:25:53 PT] **Console note:** Case closed — resolved. Correct overdue bill paid, line resumed after confirmation; customer reports service restored.
