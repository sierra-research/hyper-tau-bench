# DD-PATTERN — employer submitter pattern key

RHO BANK · PAYROLL SERVICING · Key DD-PATTERN · 2025-09 issue ·
Owner: Y. Toure, Payroll Servicing · Companion to Doc DD-SCHED (all revs)

Pattern codes describe when an employer's payroll file moves, not when
funds become spendable. The posting expectation for any pattern is read
from Doc DD-SCHED at the rev the console reference field names.

## Codes

| Code | Submitter behavior                                            |
|------|----------------------------------------------------------------|
| T-2  | File submitted two business days before the official pay date  |
| T-1  | File submitted one business day before the official pay date   |
| T-0  | File submitted on the official pay date, typically pre-dawn    |

## Key notes

- A pattern is a property of the employer's payroll provider, not of
  the customer's account. Two colleagues at different employers can
  have the same pay date and different patterns — and the T-2
  colleague's early file is not the T-0 colleague's missing money.
- Patterns say nothing about amounts, about the employer's internal
  approval steps, or about which pay dates an employer uses.
- Patterns are recorded on the profile from extract history
  (console macro: Employer pattern capture). An empty pattern field
  means no history, not pattern T-0.
- Provider cutoffs are the sharp edge of T-0: a file that misses the
  window cutoff is a late file, and late files post in the next
  processing window. The file-arrival extract, not the pattern code,
  says which happened.
