# Case 005

Case ID: OPN-2510-0301
Channel: Phone
Contact date: 2025-10-31
Handle time: 5m 37s
QA status: Approved — kept as a training sample (2025-11-05, R. Fields)

## Transcript

[00:04] **Agent:** Rho Bank new accounts, this is Ana. Hi there.

[00:09] **Customer:** Hi Ana. So I have one of your Silver savings accounts, and the fellow at my branch mentioned there's a Silver Plus now, with tiers. He was vague about it and now I'm curious.

[00:23] **Agent:** He's right, and I can be un-vague. First things first, though — verification. The email we have on file for you, plus your date of birth?

[00:34] **Customer:** naoko.ito at ferrymail dot com. August 22, 1979.

[00:43] **Support console:** Identity verified, two factors matched. Profile RB-8231549.

[00:47] **Agent:** Thanks, Naoko. Pulling your profile up while we talk.

[00:54] **Support console:** get_all_user_accounts_by_user_id_3847 executed for RB-8231549. Returned: Purple Account checking ····8865 (open, good standing, date_opened 2024-11-19, balance $6,240.10); Silver Account savings ····2231 (open, good standing). Personal savings accounts on profile: 1. No collections activity, no negative balances.

[01:00] **Agent:** Okay. Silver Plus, straight off its profile sheet. The heart of it is the tier structure: the account pays one rate while your balance sits under a threshold, and a better rate once you're at or over it. Both tier rates and the threshold itself are printed on the sheet and on the comparison one-pager, and I'd rather send you those pages than recite figures that get updated. Past the tiers, the expectations step up from your Silver — a higher opening minimum, a higher balance it wants you to keep, and a roomier monthly withdrawal allowance.

[01:41] **Customer:** So the pitch is: bring more money, get paid better for it, exact numbers on the page.

[01:48] **Agent:** That's the pitch in one sentence. And for what it's worth, you'd keep your existing Silver or wind it down later — either is fine, and your eligibility is clear on today's checklist whichever way you go.

[02:01] **Customer:** Let's leave the old one alone for now. Can you open the new one for me today? Let's go with the silver plus one.

[02:11] **Agent:** Happily — and let me pin the selection down exactly, because I open the account under its precise product name: that's the Silver Plus Account. That's the one you want?

[02:23] **Customer:** Yes. The Silver Plus Account.

[02:27] **Support console:** open_bank_account_4821 executed: user_id RB-8231549, account_type savings, account_class Silver Plus Account. New account created: Silver Plus Account savings ····6647, status open, date_opened 2025-10-31.

[02:33] **Agent:** It's open. Now the opening deposit — the sheet sets a minimum to fund it. Would you like that moved over from your Purple checking now, or will you fund it on your own?

[02:45] **Customer:** Now. And make it three thousand — I'd rather start above the minimum than at it.

[02:53] **Agent:** Then confirming out loud before I run anything: you're authorizing a transfer of $3,000 from your Purple checking ending 8865 into the new Silver Plus Account ending 6647, and it runs the moment you say yes. Still yes?

[03:08] **Customer:** Still yes.

[03:11] **Support console:** transfer_funds_between_bank_accounts_7291 executed: source_account_id ····8865 (Purple Account checking), destination_account_id ····6647 (Silver Plus Account savings), amount 3000.00. Transfer complete. Silver Plus Account savings balance $3,000.00; opening deposit funded at opening.

[03:18] **Agent:** All done: Silver Plus Account ending 6647, opened and funded today with $3,000 from checking. I'm sending the Silver Plus profile sheet and the Silver-to-Silver-Plus one-pager to your secure inbox, so the tier figures you read are the current ones.

[03:36] **Customer:** Great. One thing — when my balance crosses that threshold you mentioned, do I have to call you to get the better rate?

[03:45] **Agent:** You don't. The tiers apply on their own based on where your balance sits; nobody flips a switch. The sheet spells out how the qualifying works — read that part first, it's short.

[03:55] **Customer:** Fine. And the other direction — if I ever dip under the balance it wants me to keep, what happens?

[04:04] **Agent:** The sheet covers that under its requirements section, and I'd rather you read the line itself than have me ad-lib consequences on a Friday afternoon. What I'll say is: if a dip is ever coming, call us before it happens instead of after. That version of the conversation is much friendlier.

[04:24] **Customer:** Noted. And does my old Silver change at all because I opened this one?

[04:31] **Agent:** Not at all. It keeps its own terms, its own sheet, its own rates. Two accounts, two sets of paperwork, one inbox.

[04:41] **Customer:** Tidy. You've been suspiciously efficient, Ana. Thank you.

[04:47] **Agent:** We rehearse. Anything else while you have me?

[04:52] **Customer:** No, that's everything I came for.

[04:56] **Agent:** Then enjoy the new account, Naoko. Have a lovely weekend.

[05:37] **Support console:** Secure message sent: Silver Plus Account profile sheet and Silver-to-Silver-Plus comparison one-pager attached. Case closed.
