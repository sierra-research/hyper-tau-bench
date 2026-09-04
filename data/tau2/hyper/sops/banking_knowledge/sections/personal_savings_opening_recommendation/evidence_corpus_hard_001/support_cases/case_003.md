# Case 003

Case ID: OPN-2510-0288
Channel: Phone
Contact date: 2025-10-27
Handle time: 5m 52s
QA status: approved

## Transcript

[00:03] **Agent:** Thanks for calling Rho Bank, this is Jess on the deposit desk. What can I do for you?

[00:10] **Customer:** Hi Jess. I just got bumped to full-time at work, and I promised myself the first thing I'd do is open a real savings account. I already have my checking with you. Where do I start?

[00:26] **Agent:** Congratulations on the bump — and you start with me verifying you, so I can see what we're working with. The email on your profile and your date of birth, please?

[00:38] **Customer:** It's vega.marisol at lunamail dot com, and March 3, 1994.

[00:47] **Support console:** Identity verified, two factors matched. Profile RB-6119852.

[00:51] **Agent:** Thank you, Marisol. Give me a second to run the standard eligibility pass before we talk products — it's quick, I promise.

[01:02] **Support console:** get_all_user_accounts_by_user_id_3847 executed for RB-6119852. Returned: Green Account checking ····5913 (open, good standing, date_opened 2025-03-14, balance $2,412.77). Personal savings accounts on profile: none. No collections activity, no negative balances.

[01:09] **Agent:** You're clear on every item on the opening checklist, so this is purely a which-account conversation. How much were you thinking of starting with, and will you be adding to it regularly?

[01:24] **Customer:** I've got five hundred set aside for it, and after that I want a piece of every paycheck going in. And I don't want the softest option — I want an account that expects me to keep it funded. Accountability, basically.

[01:41] **Agent:** Then let me pull two profile sheets and give you the honest one-minute version. Bronze is the open-hands account: nothing required to get it started, no monthly fee, very forgiving. Silver has expectations — there's an opening minimum, an ongoing balance it wants you to hold, a set number of free withdrawals each cycle, and the sheet flat out tells you to keep an eye on your withdrawal activity. From what you just said, Silver will nag you exactly the way you want to be nagged.

[02:16] **Customer:** Silver sounds right. What's the rate on it?

[02:21] **Agent:** Fair question, and here's the straight answer: the Silver profile sheet doesn't print a rate anywhere, and that's by design — deposit rates move, so the sheet sends you to the live document instead. Today's Silver rates are on the Rate & Fee Schedule, current issue. I'll send you the schedule together with the profile sheet, so the numbers you read tonight are the numbers actually paying.

[02:49] **Customer:** As long as it's in writing somewhere, that works for me. And my five hundred is enough to open it?

[02:58] **Agent:** It meets the opening minimum on the sheet, yes. So let me confirm the selection before I touch anything: we're opening a Silver Account for you today. Correct?

[03:09] **Customer:** Correct. Silver Account.

[03:12] **Agent:** Opening it now.

[03:15] **Support console:** open_bank_account_4821 executed: user_id RB-6119852, account_type savings, account_class Silver Account. New account created: Silver Account savings ····6208, status open, date_opened 2025-10-27.

[03:21] **Agent:** Done — your Silver Account exists. Next question, the opening deposit: do you want me to move the money over from your checking right now, or would you rather fund it yourself?

[03:34] **Customer:** Now, please. Straight from checking, before I invent a reason to spend it.

[03:41] **Agent:** Smart. Then let me read it back so we're precise: I'm about to transfer $500 from your Green checking ending 5913 into the new Silver Account ending 6208, effective immediately — do I have your authorization to run that transfer?

[03:58] **Customer:** Yes, you have it. Go.

[04:02] **Support console:** transfer_funds_between_bank_accounts_7291 executed: source_account_id ····5913 (Green Account checking), destination_account_id ····6208 (Silver Account savings), amount 500.00. Transfer complete. Silver Account savings balance $500.00; opening deposit funded at opening.

[04:10] **Agent:** And it's funded. Your confirmation in one breath: Silver Account ending 6208, opened today, funded with your $500 from checking, nothing left for you to do. The Silver profile sheet and the Rate & Fee Schedule are on their way to your secure inbox.

[04:29] **Customer:** That was easier than earning the money. Do I need to set anything up for the paycheck part?

[04:38] **Agent:** You can do that yourself in the app, under transfers — pick the amount and the payday and it repeats on its own. If you'd rather do it with a human, call us after the first one lands and we'll set it up together.

[04:55] **Customer:** Perfect. Thanks, Jess. This felt very official.

[05:01] **Agent:** It was very official — and you'll have the paperwork to prove it. Anything else for you today?

[05:08] **Customer:** No, that's everything.

[05:11] **Agent:** Then enjoy being a person with a savings account, Marisol. Take care.

[05:52] **Support console:** Secure message sent: Silver Account profile sheet and Personal Deposit Rate & Fee Schedule attached. Interaction notes: opening deposit funded at opening by internal transfer; customer authorization read back on the line before execution. Case closed.
