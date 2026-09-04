# Case C

Channel: Live chat
QA status: Coached
Archive date: 2026-07-10
Chat opened: 2026-07-06T16:05:33-07:00
Active handle time: 1m 58s
Chat span: 3m 18s

## Transcript

[2026-07-06 16:05:33 PT] **Agent:** Thanks for reaching Northline support, I'm Iris.

[2026-07-06 16:05:42 PT] **Customer:** Hi Iris. My daughter's phone line got suspended — we got the email an hour ago. Can we sort it out here?

[2026-07-06 16:05:55 PT] **Agent:** We can. Which line is hers — the one ending 7716 on your account?

[2026-07-06 16:06:06 PT] **Customer:** That's her.

[2026-07-06 16:06:12 PT] **Console note:** Affected line identified (ending 7716). Line record read: Suspended, reason Overdue balance.

[2026-07-06 16:06:19 PT] **Agent:** Suspended for an overdue balance, and the record points at the May bill.

[2026-07-06 16:06:31 PT] **Customer:** The email said $39.95. Can we pay that right now?

[2026-07-06 16:06:40 PT] **Agent:** We can — the amount due is $39.95. Want me to send the payment request to your phone?

[2026-07-06 16:06:52 PT] **Customer:** Yes — send it to my phone, not hers, please.

[2026-07-06 16:07:00 PT] **Agent:** It goes to the account holder's phone, which is you. Sending now.

[2026-07-06 16:07:06 PT] **Console note:** May bill verified Overdue. Payment request sent after customer confirmation.

[2026-07-06 16:07:26 PT] **Customer:** Hold on — the request says $42.15, not $39.95?

[2026-07-06 16:07:37 PT] **Agent:** The request reads straight from the bill, so $42.15 is the live figure — a late adjustment posted after that email went out. Sorry for the jump. Go ahead with it.

[2026-07-06 16:07:58 PT] **Customer:** Paid. It says accepted.

[2026-07-06 16:08:06 PT] **Agent:** May shows Paid on my side — resuming the line now.

[2026-07-06 16:08:12 PT] **Console note:** Line resumption run on 7716.

[2026-07-06 16:08:18 PT] **Agent:** Done! The record shows the line back to Active on my side — how does her phone look?

[2026-07-06 16:08:31 PT] **Customer:** She says it's back. Thank you, that was quick!

[2026-07-06 16:08:37 PT] **Console note:** Case closed — resolved. Line resumed; customer reports service restored.

[2026-07-06 16:08:44 PT] **QA annotation (post-review, 2026-07-09):** Coached. The $39.95 the agent quoted was the customer's email figure repeated back, not the amount on the bill record — a late adjustment had posted in between, and the customer met a different number on the payment request. Amounts are quoted from the bill record at the moment of quoting; a notification email is a snapshot. The in-chat recovery was handled cleanly.
