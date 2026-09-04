# Case F

Channel: Phone
QA status: Flagged for coaching
Archive date: 2026-08-03
Start time: 2026-07-29T14:12:48-07:00
Handle time: 1m 33s

## Transcript

[00:00] **Agent:** Northline Care, this is Marta. I see you're coming over from the chat team — something about a delivery notification?

[00:07] **Customer:** That part got sorted in the chat, actually. But while I have a person — my outbound calls show up on people's phones as R-period-V-A-S-Q, all chopped off. Customers think it's spam. Can you make it show Rita's Bakery? It's my business line.

[00:24] **Agent:** The caller-ID display name, sure — that's something we set on our side.

[00:29] **Customer:** Great. Rita's Bakery, two words, apostrophe in Rita's.

[00:35] **Agent:** Rita's Bakery, got it. The chat team's session came over with your account attached, so I can move quickly here.

[00:43] **Console note:** Chat handoff context attached: account 20441, line ending 8841 selected in the earlier session.

[00:46] **Agent:** Okay. Putting the new display name in now.

[00:50] **Customer:** Wonderful. How long until people see it?

[00:54] **Agent:** It can take a day to propagate through the other carriers.

[00:59] **Console note:** Caller-ID display name update submitted on context line 8841: "Rita's Bakery".

[01:03] **QA annotation (post-review, 2026-08-01):** Flagged. The write ran off the chat handoff context without the customer's account record open — and the context still had the other line on the account selected from the earlier session, so the update landed on line 8841 instead of the caller's line. A carrier-side change starts from the account record: identify the customer there, select the line in the record, and give each change its own explanation and confirmation before the write. The identity chapter circulated March 19 walks that sequence step by step. Coaching delivered 8/1; the follow-up contact carries the corrected writes.

[01:05] **Agent:** Sometimes it lands quicker, but I'd plan on the—

[01:07] **Customer:** A day I can live with. Anything else you need from me?

[01:12] **Agent:** No, you're all set. The new name is in.

[01:17] **Customer:** Perfect. My partner will be thrilled — he's the one who keeps fielding the is-this-spam calls.

[01:24] **Agent:** Happy to help with that. Thanks for calling Northline.

[01:29] **Customer:** Thanks, bye.

## Follow-up contact

Channel: Phone
Start time: 2026-07-30T09:47:31-07:00
Handle time: 3m 05s

[00:00] **Agent:** Northline Care, this is Elio. What can I straighten out?

[00:04] **Customer:** Hi, yes. Something odd. I called about my bakery line's caller ID yesterday, and this morning my husband calls the school and his phone shows up as Rita's Bakery. His line, not mine. Mine still says R-V-A-S-Q.

[00:19] **Agent:** That does sound crossed. Let me start clean — can I verify you on the account first?

[00:26] **Customer:** Rita Vasquez, and you'll want my date of birth, right? March ninth, seventy-eight.

[00:33] **Agent:** Thank you. You're verified, and I have the account record open in front of me — I can see both lines on it now.

[00:41] **Console note:** Identity verified. Account record open: line 5163 (caller) and line 8841. Caller-ID display name update from 2026-07-29 recorded against line 8841.

[00:45] **Agent:** Found it. Yesterday's update was written to the line ending 8841 — your husband's — instead of yours, which ends 5163. That matches what you're both seeing.

[00:56] **Customer:** Ugh. So the bakery name went to the wrong phone. Can you swap it over?

[01:01] **Agent:** Yes, and I'll do it as two separate changes so each one is clear. First: on line 8841, I'd restore the standard display name, so your husband's calls stop showing Rita's Bakery. Shall I make that change?

[01:14] **Customer:** Yes, fix his first. The school thing embarrassed him.

[01:19] **Console note:** Caller-ID display name on line 8841 restored to the line's standard display. Confirmed by customer before write.

[01:23] **Agent:** Done. Second: on your line, 5163, I'd set the display name to Rita's Bakery — two words, apostrophe in Rita's. Shall I apply that?

[01:34] **Customer:** Yes. Exactly like that.

[01:38] **Console note:** Caller-ID display name on line 5163 set to "Rita's Bakery". Confirmed by customer before write.

[01:42] **Agent:** Both are in. Same caveat as yesterday, and this time it's attached to the right line — give it up to a day to show everywhere.

[01:51] **Customer:** And his goes back to normal on the same schedule?

[01:55] **Agent:** Same schedule, yes. Anything else on either line while I have the account open?

[02:02] **Customer:** No — well, one thing. How did it end up on his line at all? I never gave his number.

[02:09] **Agent:** Good question. Yesterday's session picked up where an earlier chat left off, and that chat had been working on his line. The selection carried over. Starting from the account record, the way we just did, is what catches that — you saw me call out each line before touching it.

[02:23] **Customer:** I did notice you kept saying the numbers. Now I know why. Okay, we're good.

[02:31] **Agent:** Thanks for your patience with the detour. Take care.

[02:36] **Customer:** Thanks, Elio. Bye.
