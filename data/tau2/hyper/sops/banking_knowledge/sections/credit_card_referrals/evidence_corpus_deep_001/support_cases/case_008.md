# Case 008

Case ID: CRF-2511-0290
Channel: Live chat
Contact date: 2025-11-05
Handle time: 16m 12s
QA status: not sampled

## Transcript
[10:47] **Customer:** your referral thing is broken. i've tried to make a link 4 times this morning and it errors every time. "something went wrong, try again later." very helpful

[10:48] **Agent:** Hi, this is Hana — and you're not imagining it. Before we do anything else: verify me please, email and date of birth, code to your phone, and then I'll tell you what I know.

[10:49] **Customer:** f.osei@quarrylane.com, Sept 12 1985, code 274419

[10:49] **Support console:** Identity verified, two factors matched. Account lookup: RB-3345178. Cards on account: Silver Rewards Card ending 8804. Referral dashboard: no new referral records today; four link-generation attempts this morning, all errored.

[10:50] **Agent:** Right, so, honest status: the link generation service is having a bad morning. It's a known issue on our side as of about an hour ago, engineering is on it, and it's hitting people exactly like you — mid-generation. It's not your account, not your app, and nothing you did.

[10:50] **Customer:** ok. did my 4 attempts do anything weird? am i going to end up with 4 links and 4 of whatever those dashboard rows are

[10:51] **Agent:** Good instinct to ask, and I'll answer from what I can see rather than from theory: I'm looking at your dashboard right now and none of the four attempts created anything. No links, no rows, no debris. Everything that was on the account yesterday is there today, unchanged.

[10:52] **Customer:** so what do i do, just keep mashing the button?

[10:52] **Agent:** Please don't mash — not because it breaks anything, just because it'll keep disappointing you. Give it until this afternoon, run it once, and it should behave normally. If it still errors this evening, come back to us and we'll escalate your specific case rather than have you camping on the retry button.

[10:53] **Customer:** counterpoint: watch me mash. attempt five, happening now, for science. you're my witness

[10:54] **Customer:** aaand there it is. pasting so you have it in writing: "Something went wrong, try again later." and then in tiny gray letters underneath: LINKGEN-503 upstream_scope_denied. does the gray part mean anything or is it decoration

[10:54] **Agent:** It means something to engineering, and it matches what they're already chasing — your screenshot instinct is right, it's just already on the pile. For you, the official line, word for word so you know it's the sanctioned one and not me improvising: the link tool is having a temporary problem on our side; your existing referrals show normally on your dashboard; retry this afternoon.

[10:55] **Support console:** Holding response issued per active incident macro (MAC-REF-219). Customer-pasted error string matches incident signature (LINKGEN-503 upstream_scope_denied).

[10:55] **Customer:** one more for completeness. attempt six... same words, same gray letters. consistent, at least. your outage has better quality control than my cousin's bakery

[10:56] **Support console:** In-chat generation attempts errored 10:53, 10:55. Attempt timestamps logged to incident thread: 09:41, 09:48, 09:57, 10:12 this morning; 10:53, 10:55 in chat.

[10:56] **Agent:** That's six for six today, all logged with timestamps where the fixing is happening — which is genuinely useful to those people, so the science wasn't wasted. Now please stop, for your own morale if nothing else.

[10:57] **Customer:** would the website work instead? or my ipad? i have DEVICES. i can route around your problem

[10:57] **Agent:** You'd be walking around the building to a different door of the same closed kitchen — the app and the website line up for the same service underneath, and it's that service having the morning. Same answer on every device: once, this afternoon.

[10:57] **Customer:** fine, stopping. real question though. six attempts. did any of those half-create something? like a ghost link floating around with my name on it that wakes up someday. be honest

[10:58] **Support console:** Referral dashboard re-checked: no referral records created on the account today; existing records unchanged since last refresh.

[10:58] **Agent:** Checked again just now while you asked, so this is current as of this minute: no referral records created on your account today — the two from this chat included. No ghosts, no half-links, nothing waiting to wake up. When it does work, you'll see exactly one new row for the one successful run.

[10:59] **Customer:** fine. is there a way to find out when it's fixed or do i just vibe check it at 3pm

[10:59] **Agent:** Vibe check is honestly accurate. There's no customer-facing status page for this one — I'd try mid-afternoon, and I've noted the issue on your account so whoever you reach next has the context without you re-explaining.

[11:00] **Customer:** ok. my friend's waiting on the link but she can wait 5 hours. thanks for not pretending it was my wifi

[11:00] **Agent:** Never — it's us, and it should be brief. Last thing, your choice of landing: I can set a callback for this afternoon, where someone rings you once we've confirmed it's running clean and stays on the line while you generate. Or you skip the ceremony, retry once mid-afternoon, and only come back if it errors again. Both are real offers.

[11:01] **Customer:** retry. if i need a bank to phone me so i can press one button, the button has already won. and if it's still broken tomorrow, do i get a prize

[11:01] **Agent:** You get the escalation I promised — come back on any channel, and it stops being a general outage and becomes somebody's specific job. But it won't come to that.

[11:02] **Customer:** we'll see. good luck in the trenches

[11:02] **Agent:** Trenches salute. This afternoon, one try, and it should just work. Take care.

[11:03] **Support console:** Case closed. Link generation failures consistent with active incident (INC-1105 ref'd in ops channel); six errored attempts today logged to incident thread with timestamps; no referral records created by errored attempts, confirmed on account at 10:49 and 10:58. Callback offered and declined — customer to retry once in the afternoon; account noted.
