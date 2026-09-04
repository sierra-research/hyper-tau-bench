# Case E

Channel: Phone
QA status: Approved
Archive date: 2026-08-04
Start time: 2026-08-03T05:58:31-07:00
Handle time: 4m 01s

## Transcript

[00:00] **Agent:** Thanks for calling Northline, Ravi speaking.

[00:06] **Customer:** Hi, we're a family of four in Rome, two phones on your network, and neither has data. I have a list. May I read my list?

[00:18] **Agent:** Please, I love a list.

[00:23] **Customer:** One: my phone, no data. Two: my son's phone, no data, and it also says something about the line at the top. Three: the other two family phones are on a different carrier and working perfectly, which everyone keeps saying out loud.

[00:39] **Agent:** Let's take yours first since it's in your hand. Settings, Cellular, and tell me whether Data Roaming is on.

[00:53] **Customer:** It's off. Turning it on... should I do the speed test thing? My son does them recreationally, he told me about it.

[01:05] **Agent:** He'll be thrilled to be right — yes, run it.

[01:14] **Customer:** It's doing the circle thing.

[01:31] **Customer:** It says excellent! Item one resolved!

[01:38] **Agent:** Beautiful — phone-side switch was the whole story for your line, and I can see the carrier allowance was already on. Now the son's phone: what does it say at the top exactly?

[01:52] **Customer:** Okay, reading it. "Line suspended — contact carrier." He hit some limit thing before we left, there was A Whole Conversation about it.

[02:03] **Agent:** Let me look at that line... yes, I see it — the line's suspended on our side. And that changes what I can do here: the roaming allowance is something we switch for an active line. While this line is suspended, there's no roaming step to run — the suspension is the problem, and it has its own flow.

[02:24] **Customer:** So you can't just turn his roaming on extra hard?

[02:31] **Agent:** Not even at maximum strength. The order matters: the line has to come back to active through the suspended-line handling first, and once it's active the roaming layers work like they did on yours. I can start that flow with you right now — it looks like an overdue balance is behind it.

[02:50] **Customer:** Yes, fine, let's do it. He's been drafting a speech about his human right to data since the airport.

[02:59] **Console note:** Second line confirmed suspended (overdue). Case handed into the resumption flow for that line; roaming allowance untouched pending active status.

[03:08] **Agent:** Flow's open — the overdue bill is on screen, and it works from your phone: I send a payment request to your device, you pay it there, I confirm it's cleared, and then with your go-ahead I resume the line. Once it's active again, have him check his phone-side roaming switch too, then a speed test — recreationally, if he prefers.

[03:29] **Customer:** He will do it before you finish the sentence. Thank you — item two is in progress, and the list is dying happy.

[03:39] **Agent:** Give the list my regards. Sending that payment request now...

[03:46] **Console note:** Resumption flow continued on the second line (payment request, confirmation, and resumption handled under that workflow's own record).
