# Case 016

Case ID: OPN-2511-0399
Channel: Phone
Contact date: 2025-11-13
Handle time: 14m 48s
QA status: approved

## Transcript

[00:04] **Agent:** Rho Bank deposit desk, this is Ana. What can I help you with?

[00:11] **Customer:** Hi Ana. Lorraine Whitcomb. I want a sixth savings account, and I have a suspicion you're going to tell me no, so I've cleared my morning and brought coffee.

[00:25] **Agent:** A caller who arrives pre-braced — my favorite kind. Let's find out together. Verification first: the email on your profile and your date of birth?

[00:38] **Customer:** l.whitcomb at ashgrove dot net, and May 15, 1969.

[00:44] **Support console:** Identity verified, two factors matched. Profile RB-4415062.

[00:49] **Agent:** Thanks, Lorraine. Let me lay out your whole shelf before we do anything.

[00:56] **Support console:** get_all_user_accounts_by_user_id_3847 executed for RB-4415062. Returned: Purple Account checking ····2210 (open, good standing, date_opened 2021-02-17); Bronze Account savings ····3301 (open, good standing); Bronze Account savings ····7742 (open, good standing); Silver Account savings ····5570 (open, good standing); Green Account savings ····6612 (open, good standing); Gold Account savings ····8830 (open, good standing).

[01:01] **Agent:** So: your Purple checking, and then five open savings — two Bronzes, a Silver, the Green, and the Gold. Which means your suspicion is right, but only halfway. The opening checklist this desk runs needs you under five open savings accounts before a new one goes through, so a straight sixth is a no today.

[01:26] **Customer:** I knew it. And the other half?

[01:31] **Agent:** The other half is that nothing says the five have to be these five. If one of them closes first, the count drops, and the rest of this call is completely routine. So the real question is whether one of your five has stopped earning its spot.

[01:52] **Customer:** Oh, I like this game. Okay — walk the shelf with me. The Bronze ending three-three-oh-one is my emergency fund, that one's sacred. The Silver is vacation money. The Green is from when you people migrated whatever it was called before, it has my garden money in it. The Gold is where the serious cash sits. And the other Bronze — huh. Which one is that?

[02:22] **Agent:** Ending seven-seven-four-two. Let me look at its life story.

[02:28] **Support console:** get_bank_account_transactions_9173 executed for account ····7742. Balance $112.60. Last customer-initiated transaction 2025-06-30. No deposits since 2025-04-15.

[02:33] **Agent:** It holds a hundred twelve dollars and sixty cents, and nobody's touched it since the end of June. Last deposit was mid-April.

[02:44] **Customer:** That's the kids' pool money! We set that up two summers ago for the neighborhood pool passes, and then the pool changed to a cash-only punch card system and the account just... stayed. That's embarrassing. Yes. That one can go.

[03:02] **Agent:** No embarrassment on this desk — abandoned pool funds are practically a genre. Now, the tidy way to close it: first we empty it, then we close it. I can move the hundred twelve sixty into your Purple checking right now, if you tell me to.

[03:24] **Customer:** Do it. Officially: yes, move the pool money, all of it, from that Bronze into my checking.

[03:33] **Support console:** transfer_funds_between_bank_accounts_7291 executed: source_account_id ····7742, destination_account_id ····2210, amount $112.60. Transfer complete. Bronze Account ····7742 balance: $0.00.

[03:38] **Agent:** Moved. The Bronze is sitting at zero, and now I'm submitting the closure.

[03:45] **Support console:** Closure request submitted for Bronze Account ····7742; balance $0.00 confirmed; account status: closed. Closure confirmation queued to profile email.

[03:50] **Agent:** And it's closed. You are now a four-savings-account household, which means the door's open. So — tell me about the sixth. What's it for?

[04:02] **Customer:** A house. Well — a down payment, someday, on a small place near my sister in Vermont. I want to put real money at it, three thousand to start, and then aggressively every month. Which is why I didn't want to just stuff it in the vacation Silver — this one needs to be separate and it needs to work harder.

[04:30] **Agent:** Then let's talk about what "work harder" looks like, because for that shape of saving there's an obvious candidate: the Silver Plus. You know the regular Silver — the Plus is its more demanding sibling. I'm going to describe it from the comparison sheet, not from memory, so give me one second to open it.

[04:54] **Support console:** Reference opened: Silver-to-Silver-Plus comparison one-pager, current issue, and Silver Plus Account profile sheet.

[04:59] **Agent:** Here's the shape of it, reading off the sheet. The Plus runs two rate tiers — everything earns at the first tier, and once your balance crosses a line printed on the sheet, it earns at the second, better one. Your down-payment fund is exactly the kind of balance that grows toward that line and stays over it. There's also a relationship-bonus row at the bottom — a small extra that stacks on when you hold the right combination with us — and the withdrawal allowance is roomier than the regular Silver's, though for a fund like yours that hardly matters; you're feeding it, not raiding it.

[05:46] **Customer:** Numbers, Ana. What are the tiers?

[05:50] **Agent:** In print, not from me — that's a house rule I actually like. Savings rates move, and the last thing you want is a number I recite today going stale in your head by February. The sheet I'm sending has the tier structure, and it points you at the live rate document for what the tiers pay this week. What I will say out loud is the part that doesn't move: two tiers, a crossing line, a bonus row.

[06:25] **Customer:** Fine, fine. What about minimums? I'm starting with three thousand.

[06:32] **Agent:** The opening minimum is printed on the Plus profile sheet — and with three thousand going in on day one, you're clear of it comfortably. There's also an ongoing-balance line the sheet describes, the level it wants you to stay above month to month. Same story: comfortably clear at your starting number, and your plan only climbs from there.

[06:58] **Customer:** And fees? The Green account makes me take paperless statements, which I've made peace with, but my husband hasn't. He likes paper the way I like coffee.

[07:11] **Agent:** Then good news for the marriage: the Plus doesn't force that choice. There's a statements line on the comparison sheet — paper is available on the Plus, and the sheet says on what terms. The paperless requirement is a Green quirk; it doesn't follow you to other products.

[07:33] **Customer:** He'll be thrilled. My friend Dara also said something about ATM fees getting refunded on hers? She has the Plus, it's half of why I'm asking about it.

[07:47] **Agent:** Dara's telling the truth — there's an ATM rebate line on the comparison sheet too, with a monthly allowance printed right on it. I keep gesturing at this sheet, I know, but it's one page and it'll be in your inbox before we hang up. Between it and the profile sheet, every number we've danced around is in print. Tell Dara her word held up, too — that's rarer than you'd think with account gossip.

[08:20] **Customer:** All right, I'm sold, pending the fine print. Let's do it — wait. First tell me why the limit is five at all. Who's counting my savings accounts and why do they care?

[08:36] **Agent:** The ceiling comes from the published requirements page — the same one that says you need an active checking with us and everything in good standing. The why behind it is above my pay grade, but the what is firm, and today it's working in your favor: you cleared a slot fair and square. Now, before I open anything, the checklist gets a fresh pass — the closure changed your profile, so I run it again, out loud.

[09:10] **Support console:** Eligibility review, profile RB-4415062: identity verified this call; active checking ····2210, date_opened 2021-02-17; open personal savings count: 4; no collections activity; no negative balances. All checklist items confirmed.

[09:15] **Agent:** All clear. Checking's been with us since 2021, four open savings, nothing in collections, nothing negative. You're eligible. So, confirming the selection: the account we're opening is the Silver Plus?

[09:30] **Customer:** The Plus, yes.

[09:33] **Agent:** And precisely, for the record — it goes on the books as a Silver Plus Account, that's the full product name. One new Silver Plus Account on your profile, opened now. Yes?

[09:48] **Customer:** Yes. Open the Vermont fund.

[09:53] **Support console:** open_bank_account_4821 executed: user_id RB-4415062, account_type savings, account_class Silver Plus Account. New account created: Silver Plus Account savings ····0195 (open). Opening confirmation queued to profile email.

[09:58] **Agent:** Open. Ending oh-one-nine-five, and I already like it more than the pool account. Now funding — you said three thousand to start. Do you want that moved right now, out of the Purple checking?

[10:14] **Customer:** Yes. And say the whole thing back to me the way you did with the pool money — I've decided I like the ceremony.

[10:26] **Agent:** With pleasure. On your instruction: three thousand dollars, from your Purple Account checking ending two-two-one-oh, into your brand-new Silver Plus Account ending oh-one-nine-five, moving immediately. Is that a yes?

[10:40] **Customer:** That's a yes.

[10:43] **Support console:** transfer_funds_between_bank_accounts_7291 executed: source_account_id ····2210, destination_account_id ····0195, amount $3,000.00. Transfer complete. Silver Plus Account ····0195 balance: $3,000.00. Purple Account checking ····2210 remaining balance: $6,847.33.

[10:48] **Agent:** Done and funded. Three thousand in the Vermont fund as of this moment, and your checking's holding about sixty-eight hundred after the move. Because it's funded today, the funding window on new accounts never comes into play for you — but the confirmation note spells it out anyway, so read it once and recycle it.

[11:13] **Customer:** Speaking of which — the monthly feeding. Can I automate it? I know myself. If it's manual, some months the house fund eats out instead.

[11:25] **Agent:** You can, from the app: a recurring transfer from the Purple checking into the new Plus, any amount and day you like. Set it for just after payday and the fund feeds itself before you ever see the money. If you want, set a balance alert on the Plus as well — the sheet mentions where the interesting balance line sits, and it's satisfying to get the ping the month you cross it.

[11:58] **Customer:** And if money comes from outside? My husband's bonus lands at his credit union in December, and some of it is allegedly Vermont money.

[12:10] **Agent:** Outside money feeds it just as well — an external transfer from his credit union into the Plus works through the app too, it just takes a bit longer to land than the internal kind. The fund doesn't care where its dinner comes from.

[12:30] **Customer:** An alert for crossing the line. That's the most motivating thing a bank has ever offered me. Okay — last thing. The two accounts we touched today. The pool Bronze is gone-gone? It won't lurk?

[12:47] **Agent:** It'll show in your history as closed — a record, not a lurker. It can't charge anything, hold anything, or reopen on its own. And the money's already in your checking; you watched it move. If pool passes ever go back to needing a bank account, you come see us and we'll do this dance in reverse.

[13:12] **Customer:** Wonderful. Send me my sheets, Ana. I have a fund to feed and a husband to tell about paper statements.

[13:23] **Agent:** Both sheets are on their way, plus the requirements page since you asked the why question — you strike me as someone who'll actually read it. It's been a genuine pleasure, Lorraine. Go get the house.

[13:40] **Customer:** Thank you. Vermont, here we come. Bye now.

[13:45] **Support console:** Secure message sent: Silver-to-Silver-Plus comparison one-pager, Silver Plus Account profile sheet, and published requirements page attached. Case notes: Bronze ····7742 emptied and closed at customer request; fresh eligibility pass confirmed; Silver Plus Account ····0195 opened and funded $3,000.00 from checking ····2210 on recorded customer instruction; recurring-transfer and alert setup discussed for self-service. Case closed.
