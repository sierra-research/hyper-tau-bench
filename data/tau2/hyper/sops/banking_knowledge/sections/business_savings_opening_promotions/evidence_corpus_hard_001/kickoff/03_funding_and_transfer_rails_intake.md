# Funding and transfer rails — intake memo

FROM     Tom Nguyen, process operations
TO       Marcus Bell; Dana Okafor; Rob Castellanos
DATE     2025-11-06 — second pass; the 10/29 first pass sits in the folder
         history and should not be circulated. Coaching annex added at the
         11/13 sitting; nothing above it changed.

Purpose. The ops runbook needs one place that says, for each business
savings account class, which money-movement rails apply and who picks up
when a rail misbehaves. What this memo must not become is a second copy of
the published pages. Where a rail is a product feature, the flag lives on
that product's published page, and the runbook points there. Full stop.

## Question set, with where each answer actually lives

Q1. Which rails are in scope?
    Internal transfers between Rho accounts, same-day ACH, domestic
    wires, and external deposits used to fund a newly opened account.
    Nothing else came up in either pass.

Q2. Which account classes carry same-day ACH?
    Per published page, class by class. The first pass of this memo had
    a yes/no column here; it came out, because that column would rot the
    first time a page changed and nobody would notice. The runbook links
    each class's published page instead.

Q3. Wires — availability and pricing?
    Same treatment: per published page. Wire pricing questions from the
    desk go to Marcus's pricing queue, not to this memo and not to
    whoever happens to remember.

Q4. What governs funding a newly opened account?
    The approved funding flowchart, and only that. The old working board
    SAV-FND-01 came out of service in October — my dated 10/21 email is
    the verdict of record. Do not lift steps or timing numbers from that
    board; it carried draft values that were never approved.

Q5. Internal transfers at opening?
    Covered by the approved opening-sequence flowchart. Nothing to
    collect here; the runbook links the chart.

Q6. What may the desk say about deposit and withdrawal cadence?
    The coaching annex at the bottom of this memo, and nothing beyond
    it. Wording captured as read at the 11/13 sitting; the annex header
    says what was checked and by whom.

## Contact roster — operational escalation, not customer-facing

| Path | Who picks up | State on 11/06 |
|---|---|---|
| ACH desk | Payments Operations shared queue; duty pager rotates weekly | queue alias confirmed 11/04 |
| Wire room | staffed banking days | after-hours path unconfirmed — see open items |
| Funding exceptions | the exception step in the funding flow; ownership sits with process operations (me) | standing |
| Checking side of a funding transfer | business banking line 1-888-555-0146 — their desk owns the checking ledger; we stay on the savings side | standing |
| Page discrepancy | Dana Okafor | same day it is spotted |
| Anything pricing | Marcus Bell | standing |

Open items:

- [ ] After-hours wire contact. Asked 11/05, nudged 11/12, still nothing.
- [ ] Where the runbook lives — next to the flowcharts or in the support
      wiki. Rob and I settle this before December planning.
- [ ] Whether the ACH duty-pager rotation gets published to the desk or
      stays inside Payments Operations. Their call; asked 11/06.
- [ ] Long-term home for the coaching annex — the desk packet or Rob's
      floor material. Rob decides before the December cycle.

— T.N.

## Annex — savings cash-flow coaching lines, captured 11/13

Context, so nobody mistakes this for a pricing table: deposit servicing
brought these lines to the 11/13 sitting for the desk coaching packet.
They are usage coaching — how a customer moves money over a month — not
terms. Marcus checked the three figures below against the 2025-11 issue
of the savings rate and fee schedule (RB-SRF-01) in the room; I captured
the wording as read. Every other number stays on the published pages and
the schedule, same as the rest of this memo.

Business Bronze Saver — deposits:

- Deposits can be made via transfer from the customer's business banking
  source of choice.
- Larger, less frequent deposits generally help maintain a higher
  average balance, increasing total interest earned at the same APY.
- Periodic transfers may be scheduled weekly, biweekly, or monthly to
  match the customer's cash-flow cycle.
- Keeping funds in the account for as long as possible during the month
  helps maximize interest at 2.0%.

Business Bronze Saver — withdrawals:

- Withdrawals are initiated through online banking transfers, and
  authorized users who help manage deposits and withdrawals can be
  added.
- Multiple smaller withdrawals can be planned within the generous
  monthly limit when periodic cash needs are expected.
- Larger sums can be consolidated into fewer transfers to stay
  comfortably within the monthly allowance.
- Withdrawals can be scheduled toward the end of the billing cycle when
  possible to keep funds earning 2.0% longer.

Silver Saver Account:

- Keeping a buffer above $25,000 helps avoid brief dips that could move
  the account into the lower APY tier.
- If large withdrawals are planned, timing deposits can help the balance
  remain at or above $25,000.

Silver Plus Saver:

- If the balance is anticipated to dip below $5,000, timing deposits and
  withdrawals can help avoid falling under the requirement.
