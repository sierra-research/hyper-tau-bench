# Case E

Channel: Live chat
QA status: Flagged for coaching
Archive date: 2026-08-04
Chat opened: 2026-08-01T13:19:05-07:00
Active handle time: 1m 12s
Chat span: 1m 37s

## Transcript

[2026-08-01 13:19:05 PT] **Agent:** Northline support, Dev here. Topic says no service — tell me more?

[2026-08-01 13:19:14 PT] **Customer:** phone has said no service since i woke up. havent dropped it or anything

[2026-08-01 13:19:23 PT] **Agent:** Let's confirm the basics. Status bar currently shows no service?

[2026-08-01 13:19:32 PT] **Customer:** yes

[2026-08-01 13:19:36 PT] **Agent:** And is airplane mode maybe on?

[2026-08-01 13:19:43 PT] **Customer:** no, off

[2026-08-01 13:19:47 PT] **Agent:** Okay. If it's not airplane mode and the phone just dropped off overnight with no damage, that usually means something deeper on the network side. This needs our technical team — I'll get you over to them now.

[2026-08-01 13:20:01 PT] **Customer:** ok if thats fastest

[2026-08-01 13:20:06 PT] **Console note:** Transfer recorded via the handoff control. Reason noted: no service, cause unknown after basic checks.

[2026-08-01 13:20:11 PT] **Agent:** YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON.

[2026-08-01 13:20:16 PT] **Customer:** alright, holding on

[2026-08-01 13:20:21 PT] **QA annotation (post-review, 2026-08-02):** Flagged. A technical transfer comes after every relevant in-scope step has been worked, and this chat skipped most of the track: cellular network status was never opened, SIM status was never checked, and the APN branch was never considered — the SIM chart's branches were all still available. "Cause unknown" on the handoff reason is usually the tell that steps remain. The only immediate handoff in this workflow is the explicit policy transfer for a PIN- or PUK-locked SIM, which this was not.

## Follow-up contact

Chat opened: 2026-08-03T10:02:33-07:00
Agent: Farah
Active handle time: 3m 15s
Chat span: 4m 20s

[2026-08-03 10:02:33 PT] **Agent:** Hi — Farah with Northline. I see Saturday's chat about no service ended in a transfer queue. Let's actually walk it. Status bar still showing no service?

[2026-08-03 10:02:47 PT] **Customer:** yep still dead. was on hold forever saturday and gave up

[2026-08-03 10:02:56 PT] **Agent:** Sorry about that — we'll do it properly now. Cellular network status first: Settings, Connections, Mobile networks. What does it say?

[2026-08-03 10:03:17 PT] **Customer:** not registered on network

[2026-08-03 10:03:23 PT] **Agent:** Airplane mode off, I assume from Saturday. Next: SIM manager on the same Connections screen — present and active?

[2026-08-03 10:03:38 PT] **Customer:** yes active, my number is there

[2026-08-03 10:03:45 PT] **Agent:** Then the last device-side stop is APN settings — Access Point Names, bottom of Mobile networks. Anything unusual in the list?

[2026-08-03 10:04:04 PT] **Customer:** two entries. NL-internet and one called nl-legacy-wap that says in use??

[2026-08-03 10:04:13 PT] **Agent:** There's our suspect. The phone is attaching through a retired profile. Tap the menu and choose Reset to default, then restart the phone, and we check the status bar after it boots.

[2026-08-03 10:04:36 PT] **Customer:** resetting... rebooting

[2026-08-03 10:06:10 PT] **Customer:** ok. bars are back. Northline shows at the top

[2026-08-03 10:06:17 PT] **Console note:** Resolution recorded — APN reset to default after retired profile found in use; reboot; status bar shows connected service.

[2026-08-03 10:06:24 PT] **Agent:** Connected status bar means we're done — that's the close condition, verified on your side. Sorry again for the detour on Saturday.

[2026-08-03 10:06:36 PT] **Customer:** all good, this was painless. thanks
