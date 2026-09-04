# Case B

Channel: Live chat
QA status: Flagged for coaching
Archive date: 2026-08-03
Chat opened: 2026-08-02T10:41:18-07:00
Active handle time: 1m 26s
Chat span: 2m 06s

## Transcript

[2026-08-02 10:41:18 PT] **Agent:** Northline support, Marcus here. I see the topic is picture messages — what's happening?

[2026-08-02 10:41:28 PT] **Customer:** cant send or get any picture messages since yesterday. also my internet is completely dead unless im on wifi

[2026-08-02 10:41:41 PT] **Customer:** two problems for the price of one i guess

[2026-08-02 10:41:47 PT] **Agent:** Thanks for the detail. Let me confirm the basics — plain texts still send okay?

[2026-08-02 10:41:56 PT] **Customer:** yeah texts are fine. its pictures and internet

[2026-08-02 10:42:03 PT] **Agent:** Understood. A dead data connection alongside failed picture messages usually points to something deeper on the line than a messaging setting.

[2026-08-02 10:42:14 PT] **Customer:** ok so what do we do

[2026-08-02 10:42:20 PT] **Agent:** Given both symptoms together, this looks like it needs our technical team rather than the standard messaging steps. I'm going to get you transferred so they can dig into the line itself.

[2026-08-02 10:42:33 PT] **Customer:** whatever gets it fixed. do i need a case number or something

[2026-08-02 10:42:41 PT] **Agent:** The transfer carries the conversation with it, so nothing to write down. Recording the handoff now.

[2026-08-02 10:42:49 PT] **Console note:** Transfer recorded via the handoff control. Reason noted: combined MMS and data failure.

[2026-08-02 10:42:54 PT] **Agent:** YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON.

[2026-08-02 10:42:59 PT] **Customer:** ok thanks

[2026-08-02 10:43:03 PT] **QA annotation (post-review, 2026-08-03):** Flagged. The combined symptom is the defined entry for the data-first sequence, not a technical transfer: picture messages depend on working mobile data, so the mobile-data checks come first and the message retry afterward. The line's data issue was never worked in this chat — no allowance read, no data-toggle check — and several supported steps remained. See the coaching discussion in #care-qa, August 3.
