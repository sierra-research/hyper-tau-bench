# Case D

Channel: Phone
QA status: Flagged for coaching
Archive date: 2026-08-11
Start time: 2026-08-08T11:52:07-07:00
Handle time: 3m 23s

## Transcript

[00:00] **Agent:** Northline care, Kofi speaking.

[00:06] **Customer:** Hi — my phone's been dead since Tuesday. No service at all. The app says the line is suspended, and honestly I do have an old bill I never got around to, so I'm guessing that's the story.

[00:22] **Agent:** Let's find out. Confirming the line ending 9926?

[00:31] **Customer:** Yes, that's mine.

[00:36] **Console note:** Affected line identified (ending 9926). Line record read: Suspended.

[00:42] **Agent:** Okay — the line is suspended, and you're right that there's a bill from April still showing Overdue, $37.25. So let's do this: we clear that bill, and I resume the line right after. The amount due is $37.25 — want me to send the payment request to your phone?

[01:02] **Customer:** Sure, if that gets me my phone back today, send it.

[01:09] **Console note:** April bill verified Overdue. Payment request sent after customer confirmation.

[01:17] **Agent:** On your phone now — Northline payment request.

[01:26] **Customer:** Okay, tapping through it now.

[01:44] **Customer:** Paid. Says accepted.

[01:52] **Agent:** April shows Paid, and that was the only overdue bill on the account. Now the resume... hm. The resume control isn't going — it's staying locked on this line.

[02:06] **Agent:** Which usually means it needs a—

[02:08] **Customer:** Locked meaning what? I just paid the bill.

[02:16] **Agent:** The payment's fine — the bill is settled and that needed doing regardless. The control just isn't releasing. Sometimes these need to sync after a payment. I'd expect it to sort itself out by tomorrow; the payment is in, so there's nothing else you owe on it.

[02:35] **Customer:** So I wait? Again? It's been dead since Tuesday.

[02:44] **Agent:** I know. I've written the whole thing up on the case so any colleague can pick it up if it's not back tomorrow. You won't have to re-explain.

[02:56] **Customer:** Fine. Tomorrow. I'm holding you to the write-up.

[03:03] **Console note:** Case closed — pending sync per agent note. April bill paid; resume control locked; line not resumed.

[03:11] **QA annotation (post-review, 2026-08-10):** Flagged. The suspension reason was never read: the line record shows Reason: Contract ended, not an overdue balance. The recorded cause selects the recovery path, and everything after the payment ran against an unread cause — the write-up promises an overnight sync that nothing on the record supports. Sent to the August 6 contract-lifecycle calibration owners with the case attached; disposition to follow their review. Coaching assigned on cause-before-path.
