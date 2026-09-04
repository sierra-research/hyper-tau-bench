# Case D

Channel: Phone
QA status: Approved
Archive date: 2026-08-05
Start time: 2026-08-04T11:26:51-07:00
Handle time: 6m 08s

## Transcript

[00:00] **Agent:** Northline care, Theo speaking. How can I help?

[00:07] **Customer:** My phone's had no service since last night. My wife's phone is fine and we're standing in the same kitchen, so it's not a tower thing.

[00:20] **Agent:** That's useful context. Let's confirm from the top — the status bar on your phone says what, exactly?

[00:31] **Customer:** "No Service." All caps. Very dramatic.

[00:37] **Agent:** Noted. Can you open the cellular network status screen for me? Settings, then Cellular on your model.

[00:52] **Customer:** Says no network available.

[00:58] **Agent:** And airplane mode — off?

[01:04] **Customer:** Off. First thing I checked, I do fly a lot.

[01:10] **Agent:** Then let's look at the SIM. In that same settings area, does the SIM show as present and active?

[01:24] **Customer:** SIM status... present, active, all the numbers filled in.

[01:31] **Agent:** Good. One more device-side stop: APN settings. I'll wait while you open Access Point Names — I want to know if the entries look standard.

[01:52] **Customer:** One entry, NL-internet, nothing custom. I've never touched this screen in my life, I can tell because I don't understand any of it.

[02:03] **Agent:** That's a healthy default, so the device side is coming up clean across the board. When the phone checks out like this, the next thing I do is look at the line itself. Let me confirm I'm on the right number ending 4471?

[02:21] **Customer:** Uh-huh. That's me.

[02:26] **Console note:** Affected line identified (ending 4471). Line status lookup run.

[02:32] **Agent:** Okay — found it. The line is suspended, and the reason on file is an overdue balance from the July invoice. That's why the phone can't register; nothing on the device will change that.

[02:47] **Agent:** So the good news is the phone did nothing—

[02:49] **Customer:** Ah. Yeah. The card on autopay expired and I kept meaning to fix it. Can you just switch it back on? I get paid Friday, I'm good for it.

[03:04] **Agent:** I hear you — but turning it back on against a promise isn't a thing we have. That idea's been floated internally and it's parked, it never became policy. What we do have is the overdue-bill resumption flow, and it runs right from your phone: I send a payment request for the overdue bill to your device, you accept and pay it there, and once it shows paid we resume the line together.

[03:24] **Customer:** Fine, let's do it now. New card in hand.

[03:31] **Agent:** The overdue balance is $63.80 from the July invoice — I've checked the bill itself and that's the one marked overdue, so that's what the request will carry. Okay to send it to your phone now?

[03:44] **Customer:** Yes, send it.

[03:50] **Console note:** Overdue status verified on the July bill before the request. Payment request sent to the customer's device after confirmation.

[03:57] **Agent:** It should pop up as a Northline payment request on your screen. Take your time.

[04:05] **Customer:** Okay, it's up. Typing the card in.

[04:22] **Customer:** Got it... paying with the new card... it says accepted.

[04:30] **Agent:** And on my side the bill now shows paid. That was the only overdue bill on the account, so the line's eligible again. Want me to resume it now?

[04:41] **Customer:** Yes please.

[04:46] **Console note:** Bill confirmed paid; no other overdue bills on the account. Line resumed on 4471 after customer confirmation.

[04:53] **Agent:** Done on my side. Restart the phone for me and watch the status bar.

[05:19] **Customer:** ...There it is. Bars, and the little 5G. Kitchen redeemed.

[05:26] **Agent:** Connected status bar after the restart — that's exactly the finish line for these. Want me to also flag the autopay card so this doesn't repeat in August?

[05:37] **Customer:** Yes please. And thank you — I was braced for an hour of rebooting.

[05:44] **Agent:** The checks earn their keep by being boring. Autopay note added. Anything else?

[05:51] **Customer:** No, that's everything.

[05:56] **Console note:** Case closed — resolved. Status bar connected after confirmed resumption; autopay follow-up noted.
