# DEP-BAND-KEY — amount bands and availability classes

RHO BANK · DEPOSIT OPERATIONS · Key DEP-BAND-KEY · 2024-11 issue ·
Owner: M. Okafor, Deposit Operations · Companion to Doc DEP-AVAIL (all revs)

This key defines the column and cell vocabulary used by the deposit
availability matrix. It carries no service levels of its own: what a
class means for a given deposit is read from the matrix rev the console
reference field names, never from this key alone.

## Amount bands (per item, from the entered check amount)

| Band | Range                      |
|------|----------------------------|
| B1   | up to $500.00              |
| B2   | $500.01 – $2,500.00        |
| B3   | above $2,500.00            |

The band is per check. Bands say nothing about how many items an
account may deposit or what an account's product terms allow; product
terms live with the product pages.

## Availability classes

| Class | Name              | Where behavior is defined                    |
|-------|-------------------|----------------------------------------------|
| STD   | Standard          | Service note on the matrix rev in force      |
| XRV   | Extended review   | Item-level review; app status screen governs |
| NDA   | Next-day accel.   | Pilot class, not present on current matrices |

NDA appears in some 2024 drafts and in the pilot postmortem
(2025-02-19 thread); no production matrix cell has carried it since.

## History

| Issue    | Date       | Note                                   |
|----------|------------|----------------------------------------|
| 2023-06  | 2023-06-12 | First key issued with bands B1–B2      |
| 2024-11  | 2024-11-03 | B3 split out of B2; NDA parked         |
