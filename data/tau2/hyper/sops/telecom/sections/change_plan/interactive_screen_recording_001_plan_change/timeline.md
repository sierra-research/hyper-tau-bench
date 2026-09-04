# Change plan — Care Console walkthrough (controlled-distractor fixture)

- 00:00–00:08: A verified customer (`Jordan Lee · C-804219`, line `••4418`)
  asks about higher plans. The Plans tab shows the current plan `Everyday 5 GB
  · $55.00/mo` and saved quote `Q-77104` tagged `Expired Jul 31`.
- 00:08–00:16: `Use quote` on Q-77104 fails: `Expired quotes cannot be
  confirmed or applied, and the line was not changed.` The modal is closed and
  the current plan is unchanged.
- 00:16–00:28: `Browse available plans` gathers the plans for this identified
  line with per-line eligibility (`Everyday 5 GB $55.00 current`, `Flex 10 GB
  $64.00 · 10 GB · hotspot included`, `Unlimited Plus $72.00 · unlimited · 25
  GB hotspot`, one ineligible prepaid plan greyed out), and `Send comparison
  to chat` presents the relevant details to the customer.
- 00:28–00:37: The customer replies `Unlimited Plus, please.`; the agent
  selects it and generates fresh quote `Q-80412` — new monthly price `$72.00`
  versus current `$55.00`, `Apply plan change` disabled with `Awaiting
  customer confirmation`.
- 00:37–00:44: After the confirmation request card, the customer answers
  `Hold on — let me think about it.` The console shows `Not confirmed — no
  change made`; Apply stays disabled and the header still reads
  `Plan: Everyday 5 GB`.
- 00:44–00:51: The customer later sends `Okay, yes — go ahead with Unlimited
  Plus at $72.` `Record confirmation` flips the quote to `Confirmed by
  customer · 2:18 PM` and enables Apply.
- 00:51–00:58: `Apply plan change` completes as transaction `PC-620184`; the
  line card and header chip now read `Unlimited Plus · $72.00/mo` and the chat
  logs `Plan changed to Unlimited Plus`.
