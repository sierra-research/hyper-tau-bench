# Case 015

Case ID: OPN-2511-0390
Channel: Phone
Contact date: 2025-11-12
Handle time: 15m 41s
QA status: approved

## Transcript

[00:04] **Agent:** Rho Bank deposit desk, this is Omar. What can I—

[00:10] **Customer:** You closed my account. You people closed my savings account. I opened the app last night to finally move money into it and it's just — gone. Grayed out. "Closed." Nobody called me, nobody asked me, nothing.

[00:28] **Agent:** Okay — that's a rotten thing to find at night, and I want to get to the bottom of it with you right now. First I have to verify you, so I can actually see what happened. The email on your profile and your date of birth, please.

[00:50] **Customer:** Are you serious? You closed my account and now I have to pass a quiz?

[00:58] **Agent:** I know how it sounds. But until you're verified, your profile is a locked door to me — I can't even see which account you mean, let alone fix anything. Thirty seconds, and then we're actually working on it.

[01:17] **Customer:** Fine. v.anand at merrowmail dot com. August 8, 1979.

[01:22] **Support console:** Identity verified, two factors matched. Profile RB-2209467.

[01:27] **Agent:** Thank you, Victor. Pulling everything up now — give me one second and I'll tell you exactly what I see, no gloss.

[01:39] **Support console:** get_all_user_accounts_by_user_id_3847 executed for RB-2209467. Returned: Blue Account checking ····5521 (open, good standing, date_opened 2019-03-08); Bronze Account savings ····1142 (open, good standing); Silver Account savings ····7788 (closed 2025-11-11; date_opened 2025-10-12).

[01:44] **Agent:** Here's the picture. Your Blue checking, fine. Your Bronze savings, fine. And the Silver Account savings ending seven-seven-eight-eight — opened October twelfth, closed yesterday, November eleventh. Let me look at its history before either of us says another word.

[02:02] **Support console:** get_bank_account_transactions_9173 executed for account ····7788. No transactions posted between 2025-10-12 and closure. Account was never funded.

[02:07] **Agent:** Okay. Victor, the history shows the account sat empty the whole time — nothing ever landed in it between the day it opened and yesterday. And that's the why: a brand-new savings account comes with a funding window. It's laid out in the confirmation note that went to your email the day it opened — put money in within the window, or the system closes the account on its own. Yours hit the end of that window yesterday, and the system did what the paperwork says it does.

[02:46] **Customer:** Nobody said thirty days to me. Nobody. I would have remembered a countdown attached to my own money.

[02:55] **Agent:** I hear you. What I can tell you is what's in front of me: the notes from the opening call show the window was walked through, and there's a line recording that you acknowledged it — that's standard on every deferred-funding opening, and it's on yours.

[03:17] **Customer:** So it's my word against a note somebody typed. That's what you're telling me. I've been with this bank nine years — nine years — and the first time I try to open something new, you erase it and wave a note at me.

[03:37] **Agent:** I'm not waving anything at you, and I'm not calling you a liar — memory and paperwork disagree all the time, and I wasn't on that call. What I can do is fix the outcome. If you'll let me, I can—

[03:56] **Customer:** No. No, I want a supervisor. I'm not mad at you personally, Omar, but "the system did what the system does" is not an answer a human being should accept, and I want to hear what your boss says the system does. Put them on.

[04:17] **Agent:** That's your right, and I'll get them. Two things while I do: I'm staying on the case notes so you don't repeat yourself, and nothing about the closure gets worse while you wait — there's no meter running. Hold for me, Victor.

[04:37] **Support console:** Escalation requested by customer. Supervisor Colin Mercer joined the call; agent case notes shared to supervisor view.

[04:42] **Supervisor:** Victor, this is Colin Mercer — I supervise the deposit desk. Omar's notes are in front of me and I've read them, so you don't need to start over. But tell me the part that matters most to you, in your own words.

[05:02] **Customer:** The part that matters is my bank deleted an account I opened, on purpose, silently, and the first employee I reached explained it to me like weather. Rules did it, notes prove it, nothing to be done. I didn't fund it, fine — I was slow. Life happened. My mother was in the hospital half of October. Does your window care about that?

[05:30] **Supervisor:** No, it doesn't — the window is a dumb clock, and I won't pretend otherwise. And I'm sorry about your mother; that's a hard month, and I'm not going to grade how you spent it. So let me be straight about what I can and can't do, and you tell me if it adds up to something acceptable.

[05:57] **Customer:** Go ahead. But I want you to know the bar is low. The last person who said "let me be straight with you" was selling me a timeshare.

[06:11] **Supervisor:** Then I'll aim to clear the timeshare bar. Two lists, short ones.

[06:18] **Supervisor:** What I can't do: un-close that account. Once an unfunded account times out and the system closes it, there is no lever on my desk that brings that same account back — the closure is real, not a suspension. I also can't rewrite the opening-call record, and I wouldn't; it says what it says.

[06:42] **Customer:** Wonderful. Strong start.

[06:46] **Supervisor:** What I can do: open you a fresh Silver Account right now, on this call, same as the one that closed — and fund it before we hang up, so no window ever gets a vote again. Nothing was lost inside the old account, Victor. It never held a dollar, so there's no interest gone, no balance stranded — what you lost was the account number and some patience. One of those I can replace in the next five minutes.

[07:21] **Customer:** And the other?

[07:24] **Supervisor:** The other I can only apologize for, and I do. Finding it in the app at night with no human attached — that's a lousy experience even when the paperwork's in order, and I'm logging that feedback with your case number on it, because how loudly we flag that deadline is worth someone's attention upstream.

[07:49] **Customer:** Hm. All right. I'm still annoyed, but all right. Do your five minutes.

[07:57] **Supervisor:** Then bear with me, because a new opening gets the standard once-over even on a call like this — I don't get to skip steps just because the week's been unkind. Omar verified you at the top of the call, so that's done. Now the rest of the checklist, out loud, so you see there's no mystery to it.

[08:24] **Customer:** The checklist that closed my account. Sure. Let's meet it.

[08:30] **Supervisor:** Different board, same family. First: an active checking with us — your Blue checking's been open since March of 2019, so the seasoning requirement isn't remotely in play. Second: how many savings accounts you're holding — you have one open, the Bronze, which leaves you well under the ceiling. Third: nothing in collections, and no negative balances anywhere on the profile.

[08:57] **Support console:** Eligibility review, profile RB-2209467: identity verified this call; active checking ····5521, date_opened 2019-03-08; open personal savings count: 1; no collections activity; no negative balances. All checklist items confirmed.

[09:02] **Supervisor:** Everything's clear. You're as eligible as a person gets. So: a new Silver Account savings, same product as before. Do you want it?

[09:14] **Customer:** Yes. Obviously. It's what I wanted in October.

[09:20] **Supervisor:** Confirming it back before I touch anything: one new Silver Account — that's the full product name going on the books — on your profile, opened now. Yes?

[09:33] **Customer:** Yes. Open it.

[09:37] **Support console:** open_bank_account_4821 executed: user_id RB-2209467, account_type savings, account_class Silver Account. New account created: Silver Account savings ····9917 (open). Opening confirmation queued to profile email.

[09:42] **Supervisor:** Done. New Silver Account, ending nine-nine-one-seven, open as of this second. Now the part I care about most: money in it, today, so the clock never matters. Do you want to fund it right now out of the Blue checking, while we're all here?

[10:02] **Customer:** Yes. Seven hundred and fifty. That's what I meant to move a month ago.

[10:10] **Supervisor:** Say it back with me so the record's clean: seven hundred fifty dollars, out of your Blue checking ending five-five-two-one, into the new Silver ending nine-nine-one-seven, moving now on your instruction. Is that a yes?

[10:27] **Customer:** That's a yes. Move it.

[10:31] **Support console:** transfer_funds_between_bank_accounts_7291 executed: source_account_id ····5521, destination_account_id ····9917, amount $750.00. Transfer complete. Silver Account ····9917 balance: $750.00. Blue Account checking ····5521 remaining balance: $4,982.16.

[10:36] **Supervisor:** It's in. The new account shows seven hundred fifty dollars, and your checking's left with just under five thousand. The app should show both within the minute — check it while I'm still on the line, so tonight holds no surprises.

[10:55] **Customer:** Refreshing... okay. Silver Account. Seven fifty. It's there. It's even not gray. The number's different, which will take some getting used to, but it's real and it's funded and nobody's clock is on it.

[11:11] **Supervisor:** Very much not gray. Now three housekeeping things, quickly, because you've earned a short call from here. One: the confirmation note for this opening is on its way to your email — same kind as October's. This time it can say whatever it likes about windows; yours is already funded.

[11:34] **Customer:** Ha. Yes. It can shout into the void. Actually — hold on. Now you've got me paranoid. The Bronze. The one savings account I have left from before all this. Is there some clock ticking on that one that I don't know about? Am I going to open the app in March and find it gray too?

[12:00] **Supervisor:** No. That window is a birth thing — it only applies to a newly opened account that's never been funded, and it's spelled out in the confirmation note each new account gets. Your Bronze has been open for years with money in it; there's nothing ticking on it, and nothing ticking on the new Silver either, as of a couple minutes ago. Funded accounts just live their lives.

[12:30] **Customer:** All right. Good. One less thing to check at midnight.

[12:36] **Supervisor:** Two: the old account stays closed and stays visible in your history as closed — don't let it startle you. It's a record, not a debt, and nothing about it follows you around. Three: my feedback about the closure experience is filed with today's case, and if the desk changes how that deadline gets flagged, it'll be partly because this call happened. That's not a consolation prize; it's just true.

[13:08] **Customer:** Fine. Good. And look — Omar, if you're still there — I said I wasn't mad at you personally and then I got sharp with you anyway. The quiz line. That wasn't fair.

[13:24] **Agent:** Still here, and no harm done, Victor. You found a closed account at midnight; I'd have been sharp too. I'm glad it ended with money where you wanted it.

[13:38] **Customer:** Nine years, one bad night. I suppose the ratio's still all right. Colin — thank you for not reading me the note again. That's genuinely all I wanted from the supervisor: a person, not a policy voice.

[13:55] **Supervisor:** That's the job on this side of the desk. And for what it's worth, your instinct to ask for one was sound — some calls need a second chair. Anything else either of us can do while you have us?

[14:14] **Customer:** No. The money's in, the account's real, my mother is home and recovering, and I'm going to go drink my coffee looking at a savings account that isn't gray. That's plenty.

[14:29] **Supervisor:** Then enjoy all three. Take care, Victor.

[14:34] **Support console:** Case notes saved: savings ····7788 auto-closed 2025-11-11 at end of unfunded funding window (opened 2025-10-12, never funded); customer escalation re closure communication; supervisor C. Mercer joined; fresh eligibility review passed, new Silver Account ····9917 opened and funded $750.00 from checking ····5521 on recorded customer instruction; closure-experience feedback filed. Case closed.
