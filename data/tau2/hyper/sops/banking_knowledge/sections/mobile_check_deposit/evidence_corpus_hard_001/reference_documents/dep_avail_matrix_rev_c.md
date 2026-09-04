# Deposit availability matrix — mobile check deposit

RHO BANK · DEPOSIT OPERATIONS · Doc DEP-AVAIL · Rev C · Effective 2025-11-03 ·
Owner: M. Okafor, Deposit Operations · Distribution: servicing desks, ops leads

Availability depends on the account type and the deposit amount. Read a
deposit down the account-type row and across the amount band, then apply
the class printed in the cell. Amount bands (B1–B3) and class behavior
beyond the standard note below are defined in DEP-BAND-KEY (2024-11
issue); this matrix does not restate them.

## Matrix

| Account type          | B1  | B2  | B3  |
|-----------------------|-----|-----|-----|
| Personal checking     | STD | STD | XRV |
| Personal savings      | STD | STD | XRV |
| Business checking     | STD | XRV | XRV |
| Estate / fiduciary    | XRV | XRV | XRV |

## Standard service note

STD — standard mobile check deposits are typically available within 1-2
business days of submission. The mobile app shows the expected
availability date on the deposit's status screen once the item is
accepted; the date the app shows is the date that governs.

XRV cells route to extended review. Review outcomes and customer
messaging live with the servicing macros (customer-support-core
workspace), not in this matrix.

## Reading notes

- Class is decided per item at submission, not per customer per day.
- The band is taken from the check amount as entered and verified
  against the imaged amount during processing.
- Where a cell and the app's status screen ever show different dates,
  the app's status screen reflects item-level review and wins.
- Rev letter and effective date identify this issue. Ops-desk
  references to "the availability matrix" resolve through the console
  reference field, which names the rev it points to.
