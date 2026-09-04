# DEP-HOLD-KEY — deposit hold reason codes

RHO BANK · DEPOSIT OPERATIONS · Key DEP-HOLD-KEY · 2025-03 issue ·
Owner: R. Salcedo, Deposit Operations · Companion to the item-review desk

Reason codes stamped on held or reviewed deposit items. These codes
name why an item is being looked at; they do not set availability.
Availability for an accepted item is read from the availability matrix
(Doc DEP-AVAIL, rev per the console reference field) and the app's
status screen.

## Codes

| Code | Reason                                    |
|------|-------------------------------------------|
| H01  | New-account seasoning window              |
| H02  | Item amount atypical for the account      |
| H04  | Redeposited item — prior return on record |
| H07  | Image legibility flagged at processing    |
| H09  | Endorsement irregularity at processing    |
| H12  | Suspected duplicate presentment           |
| H15  | Payee-name mismatch at processing         |
| H21  | Fiduciary documentation pending           |

## Desk notes

- A code answers "why is this item in review", not "when will it be
  available". Do not read service levels off this key.
- H12 items feed the duplicate-presentment queue; the detector ticket
  trail (DEP Jira project) is the record of detector behavior over
  time.
- Codes are stamped by processing; servicing never sets or clears a
  code by hand.
