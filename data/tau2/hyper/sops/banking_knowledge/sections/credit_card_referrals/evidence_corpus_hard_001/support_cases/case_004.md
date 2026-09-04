# Case 004

Case ID: CRF-2511-0201
Channel: Phone
Contact date: 2025-11-04
Handle time: 15m 41s
QA status: kept-call library — ratified 2025-11-05 norming

## Transcript
[14:06] **Agent:** Rho card services, this is Elif. How can I help?

[14:06] **Customer:** Hi Elif. My friend Dana and I have been talking about her getting the Platinum card — the one I have — and she's finally ready to apply. I know there's a refer-a-friend thing because I've seen it on the website. I've just never actually done one and I don't want to fumble it and cost us both the bonus.

[14:07] **Agent:** That's exactly the right instinct — the fumbles all happen at the start, so let's do it properly. Verification first: the email on your profile and your date of birth, and I'll text a code to your number ending 0071.

[14:08] **Customer:** wren.calloway@brightpost.org. October 30, 1988. And the code is 512096.

[14:08] **Support console:** Identity verified, two factors matched. Account lookup: RB-6108224. Cards on account: Platinum Rewards Card ending 4419. Referral history: one prior referral, bonus posted 2024. Dashboard access: active, app version 3.9.1.

[14:09] **Agent:** All verified, thank you. Two quick checks on my side before we set anything up — this is standard, it takes a minute. First I'm confirming the referral program for the specific card, so give me a moment while I pull the Platinum listing.

[14:09] **Support console:** Knowledge base search: Platinum Rewards Card referral program. Documented program returned: active, published product page, current revision on file.

[14:10] **Agent:** Good — Platinum has an active documented program. Second check: tell me what you're expecting from it. What do you think happens if Dana applies through you?

[14:10] **Customer:** From the page — she applies with my link, and if she's approved and spends whatever the threshold is in the first few months, I get the bonus. And I think it said there's a yearly limit on how many times I can do this.

[14:11] **Agent:** That matches the current program page, including the part people usually miss — the bonus waits on her qualifying spend, not just the approval. Since your picture and the program agree, we're good to set you up. One thing rides along with every link handoff, so here it is: pace yourself if more friends follow Dana. Bonuses cap at two in any rolling seven days, and a third inside that window gets denied automatically. With one referral this isn't your problem today — it's the reminder everyone gets.

[14:12] **Customer:** Noted. Dana's the only one for now. Maybe her husband in the spring, at this rate.

[14:12] **Agent:** Spring is well clear. Okay — the link itself. This part surprises people: I don't make the link. It has to be generated from your side, signed in as you, because the link is tied to your account and that tie is what routes the bonus to you. Me generating it on your behalf isn't a thing I'm allowed to do, and honestly you don't want it to be — you want the record showing it came from you.

[14:13] **Customer:** Okay. So where do I go?

[14:13] **Agent:** Are you near a computer, or on your phone? Either works — the portal has the tools box on the referrals page, and the app has the same thing under the referrals screen.

[14:14] **Customer:** Phone. Hold on, it's telling me the app needs an update. Of course it is. One minute.

[14:15] **Agent:** Take your time. It's a small one this week.

[14:16] **Customer:** It's at forty percent. Riveting. How's your Tuesday going?

[14:16] **Agent:** Quiet enough that I can watch a progress bar with you, which is honestly the good kind of Tuesday. Tell me when it reopens.

[14:17] **Customer:** Okay — updated, I'm in, referrals screen. There's a box that says run a referral tool.

[14:17] **Agent:** That's the one. The tool you're running is called get_referral_link — written out, the full form is get_referral_link(user_id: str, card_name: str). Two inputs, both from you: your own user id, and the card name. Your user id is on your profile screen, top of the page.

[14:18] **Customer:** Found the id. And the card name — I just type Platinum?

[14:18] **Agent:** Type the exact card name, word for word, as the program lists it. If you held our Gold Rewards Card, you'd type 'Gold Rewards Card' — exactly like that, full name. For yours, it's the full 'Platinum Rewards Card'. The tool matches on the name, so 'Platinum' alone or a nickname can grab the wrong program or nothing at all.

[14:18] **Customer:** Okay — my user id, and then Platinum Rewards Card, spelled out. Running it... it worked. I've got a link, and there's a new row on my dashboard for it.

[14:18] **Agent:** Perfect, that's success. Here's what just happened under the hood: the moment that tool ran, a referral record was created on your account — that new row — and it starts in the NO_PROGRESS status, which is just the record saying Dana hasn't applied yet. She takes the link, applies through it, and the row moves on its own from there. You never touch it again; you just watch it.

[14:19] **Customer:** And I send it to her however? Text is fine?

[14:19] **Agent:** However you like — the share button next to it opens your normal options, or copy it into anything. The link is the tracking, not the channel it travels through. One practical thing: it has to be that link she applies through. If she wanders to the website next week and applies fresh without it, the application will go fine and the referral won't attach to you.

[14:19] **Customer:** I'll make her do it while I'm standing there. Wren-supervised application.

[14:19] **Agent:** The gold standard of referral hygiene. Anything else on this while I have you?

[14:19] **Customer:** Two small ones. Does Dana get anything out of this, or is the bonus just mine? She'll ask me and I'd rather not guess.

[14:20] **Agent:** Don't guess — send her to the Platinum referral page itself for her side of it. Some of our programs do welcome the new cardholder with their own offer, and the page states exactly what applies to her, current as of today. If I recite it from memory and the page says otherwise, the page wins and you've quoted me wrong to your friend.

[14:20] **Customer:** Fair. Second one — what happens if she applies and doesn't get approved? Do I need to do anything, call anyone?

[14:20] **Agent:** Nothing on your end. The dashboard row will show where things stand, and if her application doesn't go through, there's simply no bonus attached to anyone — approvals drive the whole thing. Nothing for you to fix or resubmit, and it doesn't count against anything of yours. If she reapplies down the road, that's a fresh conversation and a fresh link is the safe move.

[14:21] **Customer:** Okay. That's everything, honestly. That was painless. Even the update. Thanks, Elif.

[14:21] **Support console:** Case closed resolved. Program documented (KB confirmed), customer terms understanding verified against current listing, pacing reminder delivered. get_referral_link run by customer from own session; referral record created, status NO_PROGRESS, visible on dashboard. Link delivery via customer's own channels.
