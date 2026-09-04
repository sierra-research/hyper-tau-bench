# DD-SCHED — employer payroll posting schedule (rev C)

RHO BANK · PAYROLL SERVICING · Doc DD-SCHED rev C · Effective 2025-10-20 ·
Owner: Y. Toure, Payroll Servicing · Companion: Key DD-PATTERN

Servicing-side expectations for employer ACH payroll credits. This
document sets expectations; the account's transaction feed confirms
actual postings.

## Reading rules

- Employer direct deposits post on specific days determined by the
  employer's payroll schedule — there is no bank-wide payday. Customers
  often check before the scheduled posting time, especially when a
  neighboring employer has already paid.
- Absent an employer-specific note on the profile, credits post in the
  standard morning window on the scheduled pay date; submitter patterns
  and how files map into that window are read from Key DD-PATTERN.
- Some employers process payroll 1-2 business days before the official
  pay date, while others process it on the pay date itself. The
  submitter pattern describes the file, not the money: early files
  still post on the pay date.

## Pattern grid

| Pattern | File arrival (typical)                  | Credit posts                                   |
|---------|------------------------------------------|------------------------------------------------|
| T-2     | two business days before the pay date    | pay date, morning window                       |
| T-1     | one business day before the pay date     | pay date, morning window                       |
| T-0     | pay date, pre-dawn                       | pay date, morning window; a file that misses the cutoff posts in the next processing window |

Pattern codes are defined in Key DD-PATTERN. Set patterns from extract
history, never from a customer's guess.

## Holiday shifts — through 2026 first quarter

A pay date falling on a Federal Reserve holiday posts the next business
day; the morning window applies on that day.

| Official pay date  | Holiday                    | Posting day        |
|--------------------|----------------------------|--------------------|
| Tue 2025-11-11     | Veterans Day               | Wed 2025-11-12     |
| Thu 2025-11-27     | Thanksgiving Day           | Fri 2025-11-28     |
| Thu 2025-12-25     | Christmas Day              | Fri 2025-12-26     |
| Thu 2026-01-01     | New Year's Day             | Fri 2026-01-02     |
| Mon 2026-01-19     | Martin Luther King Jr. Day | Tue 2026-01-20     |
| Mon 2026-02-16     | Washington's Birthday      | Tue 2026-02-17     |

Employers on T-1/T-2 patterns typically submit around the holiday
(expect most files for the 2025-11-11 pay date by Mon 2025-11-10);
the posting day still follows the table above.

## Desk notes

- The window is a posting expectation, not a promise of spendability
  ordering within the window — files post as they process.
- A customer calling inside the window is early, not wrong. A customer
  calling after the window with no posted credit is the rare case:
  check the file-arrival extract before anything else.

Doc DD-SCHED rev C · Effective 2025-10-20 · Payroll Servicing
