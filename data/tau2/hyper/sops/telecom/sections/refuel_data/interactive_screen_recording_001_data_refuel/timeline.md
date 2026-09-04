# Refuel data — Care Console walkthrough (controlled-distractor fixture)

- 00:00–00:07: The verified line `••4418` shows `Attached · 5G` while the
  customer reports nothing loads off Wi-Fi; the Usage tab has no usage loaded
  for the session yet.
- 00:07–00:18: `Load usage` pulls the line's carrier-side plan and usage
  before any refuel talk: `Everyday 5 GB · $55.00/mo`, `5.5 GB of 5.5 GB total
  available used` (plan 5.0 GB + previously refueled 0.5 GB), `Refueled this
  cycle 0.5 GB of 2.0 GB max`, `Refuel price (plan) $12.00 per GB`.
- 00:18–00:26: A `2.0` GB refuel request is blocked: `2.0 GB would take the
  line to 2.5 GB total refueled — above the 2.0 GB maximum. No refuel was
  applied.` Create quote stays disabled.
- 00:26–00:34: The amount is corrected to `1.0` GB (`1.0 GB × $12.00/GB =
  $12.00`), and quote `RF-88241` is created showing `Awaiting confirmation —
  amount and charge` with Apply disabled.
- 00:34–00:41: The confirmation card goes to chat but the customer only asks
  `Wait — will that charge hit today?` — the quote panel still reads `Not
  applied — usage unchanged (5.5 of 5.5 GB used)`.
- 00:41–00:50: The customer confirms `Yes — 1 GB for $12, go ahead.`; the
  quote flips to `Confirmed · 3:06 PM — 1.0 GB for $12.00`, Apply enables, and
  the refuel applies as `RF-88241` — the meter updates to `5.5 GB of 6.5 GB`
  with `1.0 GB available` and `Refueled this cycle 1.5 GB of 2.0 GB max`.
- 00:50–00:58: With the refuel applied, the agent asks the customer to rerun
  the speed test in the Northline app; the reply `42 Mbps down now` is
  recorded on the case (`Speed test (customer) 42 Mbps down · 3:07 PM`).
