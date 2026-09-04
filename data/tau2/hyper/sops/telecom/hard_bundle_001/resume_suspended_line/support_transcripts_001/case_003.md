# Case C

Channel: Live chat
QA status: Coached
Archive date: 2026-07-10
Chat opened: 2026-07-06T16:05:33-07:00
Active handle time: 1m 56s
Chat span: 3m 04s

## Transcript

[2026-07-06 16:05:33 PT] **Agent:** Thanks for reaching Northline support, I'm Iris.

[2026-07-06 16:05:42 PT] **Customer:** Hi Iris. My daughter's phone line got suspended — we got the email an hour ago. Can we sort it out here?

[2026-07-06 16:05:55 PT] **Agent:** We can. Which line is hers — the one ending 7716 on your account?

[2026-07-06 16:06:06 PT] **Customer:** That's her.

[2026-07-06 16:06:12 PT] **Console note:** Affected line identified (ending 7716). Line record read: Suspended, reason Overdue balance.

[2026-07-06 16:06:19 PT] **Agent:** Suspended for an overdue balance, and the suspension note points at the May bill — $39.95. That's the one that tripped it. The amount due is $39.95; want me to send the payment request to your phone?

[2026-07-06 16:06:37 PT] **Customer:** Yes — send it to my phone, not hers, please.

[2026-07-06 16:06:45 PT] **Agent:** It goes to the account holder's phone, which is you. Sending now.

[2026-07-06 16:06:52 PT] **Console note:** May bill verified Overdue. Payment request sent after customer confirmation.

[2026-07-06 16:07:20 PT] **Customer:** Paid. It says accepted.

[2026-07-06 16:07:29 PT] **Agent:** May shows Paid on my side. That was the bill that suspended the line, so we're clear — resuming now, okay?

[2026-07-06 16:07:41 PT] **Customer:** Yes, go ahead.

[2026-07-06 16:07:46 PT] **Console note:** Line resumption run on 7716 after customer confirmation.

[2026-07-06 16:07:53 PT] **Agent:** Done! Have her restart the phone and check for bars. It was lovely helping you — anything else?

[2026-07-06 16:08:05 PT] **Customer:** She says it's back. Thank you, that was quick!

[2026-07-06 16:08:11 PT] **Console note:** Case closed — resolved. Line resumed; customer reports service restored.

[2026-07-06 16:08:18 PT] **QA annotation (post-review, 2026-07-09):** Coached. The resumption check is a full bill review, not a check of the bill named in the suspension note: the account had a second bill — June — still marked Overdue when the resume action ran. The platform's eligibility sweep reads the whole account, and it re-suspended the line within hours (see the follow-up contact). Paying the bill that triggered the suspension is necessary, never sufficient; every bill in Overdue has to show Paid before the line is resumed. This case and its follow-up were included in the July pattern review of same-day re-suspensions.

## Follow-up contact

Channel: Live chat
Chat opened: 2026-07-07T08:44:10-07:00
Active handle time: 2m 29s
Chat span: 3m 22s

[2026-07-07 08:44:10 PT] **Agent:** Northline support, this is Omar.

[2026-07-07 08:44:20 PT] **Customer:** Hi. We did this whole dance yesterday — paid the bill, line came back — and this morning my daughter's phone is suspended AGAIN. Same email, same everything.

[2026-07-07 08:44:36 PT] **Agent:** That's frustrating, and I can see exactly why it happened. Give me a second with the account... yesterday the May bill was paid and the line was resumed, but the June bill was also overdue — it still is. When any bill is left in Overdue, the system re-checks and pulls the line back into suspension.

[2026-07-07 08:44:59 PT] **Customer:** So we paid the wrong bill?

[2026-07-07 08:45:07 PT] **Agent:** You paid a right bill — May was genuinely overdue. It just wasn't the only one. June is $44.10 and still shows Overdue. Once that's paid, there's nothing left for the system to object to. Want me to send that request now?

[2026-07-07 08:45:24 PT] **Customer:** Yes. Both barrels this time.

[2026-07-07 08:45:31 PT] **Console note:** June bill verified Overdue — the only remaining overdue bill on the account. Payment request sent after customer confirmation.

[2026-07-07 08:45:59 PT] **Customer:** Paid. Accepted.

[2026-07-07 08:46:08 PT] **Agent:** June shows Paid, and this time I've run the full review: no bill anywhere on the account in Overdue. Now the line — shall I resume it?

[2026-07-07 08:46:21 PT] **Customer:** Yes please.

[2026-07-07 08:46:26 PT] **Console note:** All bills confirmed clear of Overdue. Line resumption run on 7716 after customer confirmation.

[2026-07-07 08:46:33 PT] **Agent:** Done. Same routine as yesterday — restart, then the status bar — but this one will stick.

[2026-07-07 08:46:51 PT] **Customer:** She's restarted it. Bars are back. If it's gone again tomorrow I'm putting you on retainer.

[2026-07-07 08:47:00 PT] **Agent:** Accepted, but it won't come to that — the account's fully clear. Anything else this morning?

[2026-07-07 08:47:09 PT] **Customer:** No, we're good. Thanks Omar.

[2026-07-07 08:47:15 PT] **Console note:** Case closed — resolved. Full bill review clean before resumption; status bar confirmed by customer.
