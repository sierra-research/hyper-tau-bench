# Rate-history evidence reconciliation

Requested by: Daniel Cho, Rate Operations
Reconciliation window: 2025-07-01 through 2025-11-14
Status as of 10/10: **Source collection complete; comparison in progress**

## Objective

Create a traceable index of the rate records that a researcher or support lead
might encounter while preparing the business-checking launch. Historical values
must remain findable, but a reader should be able to tell which record was in
force at a given time. This sheet records locations and ownership, not a new rate
table.

## Sources received

| Source | Location / reference | Coverage | Owner | Reconciliation note |
|---|---|---|---|---|
| Published pricing schedule | Deposit Ops archive / 2025 schedules | Monthly snapshots | Daniel | Primary effective-date record. |
| Product-page capture set | Project drive / web-captures | Selected dates | Nina | Visual display only; gaps in August. |
| Campaign calendar | Promotions workspace / FY25 Q3–Q4 | Campaign windows | Aisha | Includes canceled rows. |
| Support rate card | Knowledge admin export | Current plus one prior | Jamal | Prior card lacks removal timestamp. |
| Launch workbook | Product Ops / drafts | Planning values | Marisol | Working material; never assume publication. |

## Reconciliation method agreed with Product Ops

For every apparent change, record the product label used, source timestamp,
effective boundary if stated, and the person who can resolve a conflict. A page
capture proves what was displayed; it does not, by itself, prove when a rate
became effective. Planning sheets and meeting notes are useful for chronology
but require a published or approved record before they can answer a customer
question.

## Exceptions log

| Ref | Observation | Disposition | Next action |
|---|---|---|---|
| RH-07 | August capture folder has a nine-day gap. | Accepted gap | Check release logs only if a disputed date falls inside it. |
| RH-09 | One support card has no exported removal time. | Open | Jamal to pull admin audit history. |
| RH-12 | Launch workbook uses a rounded value in a chart label. | Context only | Keep workbook; do not copy chart label into guidance. |
| RH-14 | Campaign calendar row was canceled after creative review. | Resolved | Preserve row with cancellation status. |

## Spot-check queue

- [x] Confirm that each published schedule has an effective date.
- [x] Match product display names to the product inventory.
- [ ] Sample two support cases against the source that was current on call date.
- [ ] Get the missing admin-history entry for RH-09.
- [ ] Record who owns the quarterly archive review after launch.

## Handoff note

Daniel will deliver the reconciled index as a CSV with one row per source
version. Nina will retain the screenshots in their original folders. Nobody
should rename files to “final” during reconciliation; use the lifecycle field in
the index so filenames remain stable. Target delivery is 17 October, but RH-09
can remain open if its owner and follow-up date are visible.

Open question for the launch lead: do we want a recurring archive spot-check in
the first week of each quarter, or is that handled by the existing pricing
control? Decision owner is still TBD.
