# Deposit availability matrix — mobile check deposit

RHO BANK · DEPOSIT OPERATIONS · Doc DEP-AVAIL · Rev B · Effective 2025-09-02 ·
Owner: M. Okafor, Deposit Operations · Distribution: servicing desks, ops leads

Availability is read from the account-type row and the amount band.
Amount bands (B1–B3) and class behavior are defined in DEP-BAND-KEY
(2024-11 issue); this matrix does not restate them.

## Matrix

| Account type          | B1  | B2  | B3  |
|-----------------------|-----|-----|-----|
| Personal checking     | STD | STD | XRV |
| Personal savings      | STD | XRV | XRV |
| Business checking     | STD | XRV | XRV |
| Estate / fiduciary    | XRV | XRV | XRV |

## Standard service note

STD — standard mobile check deposits clear to available funds on the
standard service schedule; the day-count for the STD class lives with
the servicing macros (customer-support-core workspace), not in this
matrix. The mobile app shows the expected availability date on the
deposit's status screen once the item is accepted.

XRV cells route to extended review. Review outcomes and customer
messaging live with the servicing macros (customer-support-core
workspace), not in this matrix.

## Reading notes

- Class is decided per item at submission, not per customer per day.
- The band is taken from the check amount as entered and verified
  against the imaged amount during processing.
- Rev letter and effective date identify this issue.
