# Case G

Channel: Live chat
QA status: Flagged for coaching
Archive date: 2026-08-05
Chat opened: 2026-08-01T17:02:44-07:00
Active handle time: 2m 41s
Chat span: 4m 48s

## Transcript

[2026-08-01 17:02:44 PT] **Customer:** hi, boarding a flight in 25 min

[2026-08-01 17:02:51 PT] **Customer:** need 2 more gigs on my line before we take off

[2026-08-01 17:03:02 PT] **Agent:** I can help with that. Verifying the identified line first.

[2026-08-01 17:03:19 PT] **Console note:** Line 6640 identified and selected. Everyday 5 GB. Refueled this cycle 0.0 GB of 2.0 GB max.

[2026-08-01 17:03:26 PT] **Agent:** You're verified, and nothing has been added this cycle, so two gigabytes is available.

[2026-08-01 17:03:40 PT] **Customer:** great, do it

[2026-08-01 17:03:48 PT] **Customer:** they're calling my group soon

[2026-08-01 17:03:57 PT] **Agent:** Confirming: two gigabytes added to this cycle — shall I apply?

[2026-08-01 17:04:11 PT] **Customer:** yes 2 GB confirmed

[2026-08-01 17:04:19 PT] **Agent:** Applying now.

[2026-08-01 17:04:24 PT] **QA annotation (post-review, 2026-08-04):** Flagged. The pre-apply review here covered the gigabyte amount only. The review reads the amount and the calculated dollar charge together before anything is applied — confirming the amount does not carry the price with it, as the follow-up contact on this case shows. Coaching delivered 8/4.

[2026-08-01 17:04:31 PT] **Console note:** Refuel RF-80644 applied. Line 6640 refueled 2.0 GB this cycle. Charge $24.00 posted to the account.

[2026-08-01 17:04:38 PT] **Agent:** Done — two gigabytes are live on the line. Safe travels.

[2026-08-01 17:04:52 PT] **Customer:** thanks

[2026-08-01 17:06:03 PT] **Customer:** wait, just got a text saying $24??

[2026-08-01 17:06:14 PT] **Customer:** you never said a price. where does 24 come from

[2026-08-01 17:06:29 PT] **Customer:** boarding now. calling tomorrow

[2026-08-01 17:07:32 PT] **Console note:** Chat closed by customer. Charge question unresolved at close; callback expected.

## Follow-up contact

Channel: Phone
Start time: 2026-08-02T09:18:25-07:00
Handle time: 2m 01s

[00:00] **Agent:** Northline Care, this is Ada. What can I look into?

[00:04] **Customer:** I added two gigs by chat at the airport yesterday and then got a text about a twenty-four dollar charge nobody mentioned. I'm not saying I won't pay it, I just want to know where the number came from.

[00:17] **Agent:** That's a fair ask. Let me pull up the line and yesterday's transaction.

[00:23] **Console note:** Line 6640 selected. Refuel RF-80644 on 2026-08-01: 2.0 GB, $24.00. Plan record: Everyday 5 GB, refuel price $12.00 per GB.

[00:24] **Agent:** Right, found it.

[00:27] **Agent:** Here's the breakdown. Your plan prices refuels at twelve dollars per gigabyte. You added two gigabytes, and two times twelve is the twenty-four on the text.

[00:38] **Customer:** Okay. So the math is right, it just never came up in the chat.

[00:44] **Agent:** Correct — and it should have. The review before applying is supposed to put the amount and the dollar figure in front of you together, so you're saying yes to both. I'm logging that feedback on yesterday's chat.

[00:56] **Customer:** Appreciated. The data worked fine on the layover, so keep it as is.

[01:03] **Agent:** Understood — the refuel stands and nothing changes on the line today. Anything else while I have the account open?

[01:11] **Customer:** Actually yes — does that twenty-four show up on this month's bill or next month's?

[01:17] **Agent:** One moment, I'll check how it posted.

[01:22] **Console note:** Charge $24.00 posted 2026-08-01 to the current billing period.

[01:26] **Agent:** It posted to the current period, so it will be on this month's bill rather than the next one.

[01:33] **Customer:** Perfect. That's everything.

[01:37] **Agent:** Thanks for flagging the missing price — that helps us fix it. Have a good day.

[01:43] **Customer:** You too. Bye.
