# Case 009

Case ID: OPN-2510-0257
Channel: Phone
Contact date: 2025-10-24
Handle time: 6m 31s
QA status: Approved — kept as a training sample (2025-11-10, R. Fields)

## Transcript

[00:04] **Agent:** Rho Bank deposit desk, Marcus here. What can I do for you?

[00:11] **Customer:** Hi Marcus. I'd like to open one more savings account. We do a big family trip every other summer, and I want that money sitting somewhere I won't accidentally spend it.

[00:26] **Agent:** A trip fund — we can absolutely do that. First things first, I have to verify you: the email on your profile and your date of birth, please.

[00:39] **Customer:** d.rao at lumenmail dot com, and it's June 2, 1983.

[00:46] **Support console:** Identity verified, two factors matched. Profile RB-3318209.

[00:51] **Agent:** Thanks, Devika. Let me pull everything on your profile so I can see what we're working with.

[01:00] **Support console:** get_all_user_accounts_by_user_id_3847 executed for RB-3318209. Returned: Purple Account checking ····8842 (open, good standing, date_opened 2019-05-16); Bronze Account savings ····0917 (open, good standing); Silver Account savings ····4471 (open, good standing); Green Account savings ····2205 (open, good standing); Silver Plus Account savings ····9034 (open, good standing); Gold Account savings ····6688 (open, good standing).

[01:05] **Agent:** Okay — there's your Purple checking, and on the savings side you are running a whole fleet. Bronze, Silver, Green, Silver Plus, and the Gold. That's five savings accounts, all in good standing.

[01:20] **Customer:** Everything has its own job, I promise. Is five a lot? My sister-in-law keeps insisting there's some limit and that I'm already sitting on it.

[01:33] **Agent:** Let me read the requirements page instead of guessing... here we go. Active checking with us — the Purple's been open since 2019, so that's covered. Everything in good standing — it is. And on the count, the page says a customer cannot have more than 5 — you're at five, so we're fine. Room for one more.

[01:59] **Customer:** Ha. I get to tell her she's wrong, that's the best part of my day. Okay — what kind of account should a trip fund be?

[02:11] **Agent:** For money you park and deliberately ignore, the Bronze is the easy answer. Nothing about it punishes you for leaving it alone, and the profile sheet spells out the numbers — I'll send it to you after the call so you have the terms in print.

[02:32] **Customer:** I already have a Bronze, though. The one ending zero-nine-one-seven, that's my car-repair cushion. Is it weird to have two of the same kind?

[02:44] **Agent:** Not even slightly. Separate account, separate job — the whole point is that the trip money and the timing-belt money never meet. Plenty of folks run two or three of the same product as envelopes.

[03:01] **Customer:** Then let's do that. Bronze it is.

[03:06] **Agent:** To confirm before I open anything: a new Bronze Account, on your profile, alongside everything you already have. Yes?

[03:16] **Customer:** Yes. Go ahead.

[03:19] **Support console:** open_bank_account_4821 executed: user_id RB-3318209, account_type savings, account_class Bronze Account. New account created: Bronze Account savings ····7541 (open). Opening confirmation queued to profile email.

[03:24] **Agent:** Done — your new Bronze ends seven-five-four-one, and it's live as of right now. Next question: do you want the first chunk of trip money moved into it right away, out of the Purple checking, while I've got you on the line?

[03:44] **Customer:** Not today. Payday is next Friday, and the trip math happens after my husband and I stare at the calendar this weekend. I'll set the transfer up myself from the app once we've picked a number.

[04:00] **Agent:** That works fine. One thing to keep on the fridge: a brand-new savings account comes with a funding window — the confirmation note that's headed to your email lays out how long you have and what happens if nothing ever lands in it. Payday-next-Friday is well inside it, so your plan is safe; just don't let the account sit empty and forgotten until spring.

[04:29] **Customer:** Understood. Money in after payday, no spring surprises.

[04:34] **Agent:** Perfect. And I'm noting on the case that you're funding it yourself from the app. Anything else while you have me? Any questions on the fleet?

[04:47] **Customer:** Actually, yes — quick one. Does the new account change anything about the others? Rates, fees, anything shuffling around?

[04:57] **Agent:** No. Each account stands on its own terms, and opening a new one doesn't touch the existing five. Whatever each sheet says, it keeps saying.

[05:09] **Customer:** Great. Oh — one more. In the app, both Bronzes are going to look identical, aren't they? I don't want to fund the timing belt by mistake.

[05:22] **Agent:** They'll show the same product name but different endings — zero-nine-one-seven is the old one, seven-five-four-one is the trip. You can also give each a nickname in the app, under account settings, so they read as "car" and "trip" instead of twins. I'd do that before the weekend calendar summit.

[05:45] **Customer:** Nicknames it is. Then that's everything. This was faster than my sister-in-law promised, too.

[05:53] **Agent:** We aim to beat the family gossip. The Bronze sheet is on its way to your inbox along with the opening confirmation. Enjoy the trip planning, Devika.

[06:06] **Customer:** Thanks, Marcus. Bye.

[06:09] **Support console:** Secure message sent: Bronze Savings Account profile sheet attached. Case notes: sixth savings account opened per customer request; customer to self-fund from app after 2025-10-31 payday. Case closed.
