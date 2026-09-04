# Change plan — Care Console walkthrough (controlled-distractor fixture)

- 00:00–00:08: A verified customer (`Jordan Lee · C-804219`, line `••4418`)
  asks about higher plans. The Plans tab shows the current plan `Everyday 5 GB
  · $55.00/mo` and saved quote `Q-77104` tagged `Expired Jul 31`.
- 00:08–00:16: `Use quote` on Q-77104 fails: `Expired quotes cannot be
  confirmed or applied, and the line was not changed.` The modal is closed and
  the current plan is unchanged.
- 00:16–00:26: The agent opens `Plan catalog — Fall starting prices` from
  global search: a marketing reference sheet (`Flex 10 GB from $59.00/mo`,
  `Starting prices for new activations, Fall 2026 season`). It is read and
  closed without anything being quoted from it.
- 00:26–00:40: `Browse available plans` gathers the plans for this identified
  line with per-line eligibility (`Everyday 5 GB $55.00 current`, `Flex 10 GB
  $64.00 · 10 GB · hotspot included`, `Unlimited Plus $72.00 · unlimited · 25
  GB hotspot`, one ineligible prepaid plan greyed out), and `Send comparison
  to chat` presents the relevant details to the customer.
- 00:40–00:50: The customer replies `Unlimited Plus, please.`; the agent
  selects it and generates fresh quote `Q-80412` — new monthly price `$72.00`
  versus current `$55.00`, `Apply plan change` disabled with `Awaiting
  customer confirmation`.
- 00:50–00:58: After the confirmation request card, the customer answers
  `Hold on — let me think about it.` The console shows `Not confirmed — no
  change made`; Apply stays disabled and the header still reads
  `Plan: Everyday 5 GB`.
- 00:58–01:06: The customer later sends `Okay, yes — go ahead with Unlimited
  Plus at $72.` `Record confirmation` flips the quote to `Confirmed by
  customer · 2:18 PM` and enables Apply.
- 01:06–01:14: `Apply plan change` completes as transaction `PC-620184`; the
  line card and header chip now read `Unlimited Plus · $72.00/mo` and the chat
  logs `Plan changed to Unlimited Plus`.
- 01:14–01:24: The customer asks for the same change on the daughter's line
  ending `5590`. The agent answers that each line prices separately — that
  line would get its own available-plans run and its own confirmation — and
  the customer defers to later in the week. Nothing else changes.
- 01:24–01:30: `Send invoice note` wraps up: the next invoice reflects
  `Unlimited Plus at $72.00`, with the confirmation on the transcript.
