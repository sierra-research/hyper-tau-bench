# Case 005

Case ID: ATM-2510-0342
Channel: Phone
Contact date: 2025-10-14
Handle time: 13m 21s
QA status: approved

## Transcript
[00:06] **Agent:** Rho Bank checking support, Anh speaking. How can I help?

[00:12] **Customer:** Good morning. My name is Roger Ashby, and I have in front of me a printed spreadsheet of every cash withdrawal my wife and I made in Vienna and Prague last month, and a bank statement that does not agree with my spreadsheet, and I would like to reconcile the two before I say anything I regret.

[00:45] **Agent:** That's the most organized opening I've had all week, Mr. Ashby. Let's do it. Email on the profile and date of birth first?

[00:59] **Customer:** r.ashby at ashbyandgrange dot com. June 2, 1951.

[01:05] **Support console:** Identity verified, two factors matched. RB-9034172, Blue Account checking.

[01:07] **Agent:** Thank you. How many withdrawals are we reconciling?

[01:14] **Customer:** Six. Four in Vienna, two in Prague. I'll go in order. September ninth, Vienna, the machine at the hotel — I took out what worked out to forty dollars and eleven cents, and your fee line says five dollars. Five dollars on forty. That's twelve and a half percent, which I did not agree to.

[01:44] **Agent:** Let me pull the account so we're looking at the same lines. This'll take me a minute — the statement view loads month by month. Can you hold for a moment?

[02:02] **Customer:** I've held for worse.

[02:55] **Support console:** Account history loaded for 2025-09-01 through 2025-09-30. Six international ATM withdrawals with associated fee line items. Current Blue Account page: international ATM withdrawal fee is the greater of 3% of the U.S. dollar equivalent or $5.00 per withdrawal, calculated on the cash dispensed.

[02:58] **Agent:** Thanks for holding. I have all six with their fee lines. So — the forty-dollar one. On the Blue Account, the international withdrawal fee runs as the greater of three percent of the dollar equivalent or five dollars. Three percent of forty is a dollar twenty, which is under five, so that withdrawal took the five-dollar minimum. That's the twelve percent you didn't agree to — it's the minimum doing that, not a percentage.

[03:39] **Customer:** Hm. It was on some page somewhere, I suppose.

[03:45] **Agent:** It's on the Blue Account fee page, with worked examples. I can send it when we're done.

[03:56] **Customer:** Do. All right, second line. September tenth, also Vienna — two hundred dollars even, near enough, and the fee says six dollars. That one I can follow: three percent of two hundred.

[04:16] **Agent:** Exactly right. Six dollars, percentage side, minimum doesn't come into it.

[04:24] **Customer:** Third. September twelfth, another two hundred, and the fee's the same six — but this is the one that has me. My spreadsheet says I withdrew on the twelfth, and your statement charges me the fee on the fourteenth. Two days later. What was the machine doing for two days?

[04:49] **Agent:** Nothing sinister. That withdrawal settled on the fourteenth, so the fourteenth is the day the fee went on. The cash left the machine on the twelfth; the paperwork between the Austrian network and us finished two days later. Same fee either way — it's a timing difference, not an extra charge.

[05:16] **Customer:** As long as it's not charging me rent for the two days. Fourth line, then. September thirteenth, and there are two charges next to one withdrawal. Your six dollars — fine, it was two hundred again. But there's also a line that says, and I'm reading it, A-T-M-S-R-V-C, E-U-R three fifty. What is [inaudible] —

[05:44] **Agent:** Sorry — the line breaks up there. Did you say the code reads A-T-M-S-R-V-C, and then euros, three-fifty?

[05:56] **Customer:** That's it. ATM SRVC. Three euros fifty.

[06:00] **Agent:** That one isn't ours. That's the machine owner's own service fee — the operator of that particular ATM charges it, on top of our fee, and it's their charge to set. It should have shown on the machine's screen before you confirmed, usually with a button to cancel out.

[06:26] **Customer:** Eleanor — my wife — says she remembers a screen in German asking something with a number on it. We pressed the green one.

[06:42] **Agent:** The green one usually means yes, I'll pay it. So that fee rode along with your withdrawal. We don't set it and we don't get it — it goes to the machine's operator.

[07:01] **Customer:** All right. I'll allow it, grudgingly. Prague, then. September nineteenth — hundred and sixty dollars equivalent, your fee is five dollars. Wait. Three percent of one sixty is four eighty. So — the minimum again?

[07:22] **Agent:** You've got the rule now. Four eighty is under five, so it took the minimum. You were twenty cents of withdrawal away from the percentage.

[07:38] **Customer:** If I'd taken out seven more dollars the fee would have been... four... no. Hang on. If I'd taken out more, the fee goes up. There's no winning move there, is there.

[07:56] **Agent:** Not at one sixty, no. The two just cross at about one sixty-seven — below that you pay the flat five either way.

[08:11] **Customer:** Noted for next year. Last one. September twentieth, Prague airport, and this is the one I want struck from the record. There's another operator fee — three euros again — and Eleanor and I are both certain we cancelled at that screen. Certain. The machine was asking too much and we walked to the next one. My spreadsheet has the withdrawal at the second machine, not the first.

[08:46] **Agent:** Let me look at how it came through. One moment.

[09:29] **Support console:** TXN-B2K9107V: ATM withdrawal, USD equivalent $150.30, posted 2025-09-22, Rho fee $5.00. Separate operator fee line EUR 3.00 (USD $3.28) same terminal ID as declined attempt 2025-09-20 14:02 local. Operator fee review task opened with network services; reference OPS-88401.

[09:31] **Agent:** So — your spreadsheet and the statement actually agree with each other more than either agrees with that operator. The withdrawal itself posted from the second machine, like you said. The three-euro line carries the first machine's terminal ID, the one where you cancelled. That's the operator's charge, not ours, so I can't just delete it from here — but a cancelled attempt shouldn't have produced it, so I've opened a review with our network services team to take it up with that operator. Reference is OPS, dash, eight-eight-four-zero-one.

[10:15] **Customer:** OPS-88401. In the spreadsheet it goes.

[10:21] **Agent:** If the operator reverses it, it'll appear as its own credit line — same statement section. Give it two to three weeks before you worry.

[10:34] **Customer:** And if they don't reverse it in three weeks?

[10:41] **Agent:** Call us with that reference and we'll push on it. I can't promise their answer, but the attempt is on record now either way.

[10:54] **Customer:** Very well. Eleanor wants to know — one second. She wants to know whether next year we should just carry more cash from home and skip the machines entirely. She's been saying it since Vienna.

[11:14] **Agent:** Honest answer? A little of both is what tends to work. Enough cash from home for the first day or two, then the machines for the rest — carrying a whole trip's cash has its own risks, and the exchange counters at airports will cost you more than any fee we've discussed today. Tell Eleanor the machines lost this round on paperwork, not on price.

[11:49] **Customer:** She says that's a very diplomatic answer. She's writing it in the margin.

[11:57] **Agent:** The margin is an honor. Anything else on the list?

[12:05] **Customer:** Just the summary, so we agree on the record. My columns: your fees were five, six, six, six, five, and five — all correct by your formula, irritating as the minimum is — the two-day gap is paperwork, one Austrian service fee we bought with the green button, and one Czech fee under dispute.

[12:34] **Agent:** That's exactly the picture. You reconciled it better than most statements reconcile themselves. I'm sending the Blue Account fee page to your email now, examples included.

[12:49] **Customer:** Thank you, Anh. Eleanor says thank you as well. The spreadsheet says nothing, but it's satisfied.

[13:00] **Agent:** Give the spreadsheet my regards. Anything else today?

[13:06] **Customer:** No, that's the lot.

[13:10] **Support console:** No adjustment to Rho fee lines; all six match the current Blue Account fee page. Operator fee dispute OPS-88401 open with network services; customer to call back with reference if unresolved after three weeks. Fee page link sent to verified email.
