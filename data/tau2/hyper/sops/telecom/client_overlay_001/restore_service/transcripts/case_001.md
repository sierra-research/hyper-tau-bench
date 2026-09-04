# Case A

Channel: Live chat
QA status: Reviewed — no findings
Archive date: 2026-07-31
Chat opened: 2026-07-30T09:12:44-07:00
Active handle time: 4m 49s
Chat span: 6m 42s

## Transcript

[2026-07-30 09:12:44 PT] **Agent:** Northline support, this is Asha. I see "phone says no service" on the topic line — happy to dig in.

[2026-07-30 09:12:55 PT] **Customer:** yeah since this morning. calls fail, nothing loads unless im on wifi

[2026-07-30 09:13:03 PT] **Agent:** Let's start at the top of the screen. What does the status bar show right now where the signal bars usually are?

[2026-07-30 09:13:15 PT] **Customer:** literally the words No Service

[2026-07-30 09:13:21 PT] **Agent:** Okay, that puts us squarely in the no-service track. Next can you open your cellular network status — on your phone that's Settings, then Connections, then Mobile networks.

[2026-07-30 09:13:42 PT] **Customer:** ok im there. it says not registered on network

[2026-07-30 09:13:50 PT] **Agent:** Thanks. While you're in settings, is airplane mode on by any chance? It hides in the quick panel sometimes.

[2026-07-30 09:14:02 PT] **Customer:** checked, its off

[2026-07-30 09:14:08 PT] **Agent:** Good. Next stop is the SIM itself. Settings, then Connections, then SIM manager — does your SIM show up there, and does it say it's active?

[2026-07-30 09:14:28 PT] **Customer:** it shows my number and says active

[2026-07-30 09:14:35 PT] **Agent:** So the SIM is present and active but you're still not registering. The next thing I want to look at is your APN settings — that's the access point configuration the phone uses to talk to our network. Settings, Connections, Mobile networks, Access Point Names.

[2026-07-30 09:15:00 PT] **Customer:** theres like four entries in here?? one says NL-internet and the rest are weird ones like fastnet-eu

[2026-07-30 09:15:11 PT] **Customer:** oh. i followed an APN guide last week trying to fix slow hotel wifi lol. that was for a different carrier i think

[2026-07-30 09:15:23 PT] **Agent:** That would do it — the phone can end up trying to attach through a profile that our network won't accept. The fix is to reset the APN settings to default, reboot the phone, and then we check the status bar again.

[2026-07-30 09:15:42 PT] **Customer:** reset how

[2026-07-30 09:15:48 PT] **Agent:** On the Access Point Names screen, tap the three-dot menu top right, then Reset to default. After it confirms, hold the power button and restart.

[2026-07-30 09:16:10 PT] **Customer:** ok done, rebooting now

[2026-07-30 09:17:25 PT] **Customer:** its back up... give it a sec

[2026-07-30 09:17:56 PT] **Customer:** BARS. it says Northline 5G up top

[2026-07-30 09:18:03 PT] **Agent:** That's what we want. Try one quick thing off wifi — load any page, or a Fast.com check if you like seeing numbers, just so we know it's really carrying traffic.

[2026-07-30 09:18:28 PT] **Customer:** page loaded fine and i just rang my partner, went through

[2026-07-30 09:18:36 PT] **Console note:** Resolution recorded — APN reset to default, reboot, status bar shows connected service. Customer verified call and data off Wi-Fi.

[2026-07-30 09:18:43 PT] **Agent:** Then you're set. The custom APN profile was the whole story — status bar's connected and the case closes as resolved. Anything else while I have you?

[2026-07-30 09:18:56 PT] **Customer:** no thats it. thanks for not making me reboot it five times first

[2026-07-30 09:19:02 PT] **Agent:** We save that for special occasions. Take care!
