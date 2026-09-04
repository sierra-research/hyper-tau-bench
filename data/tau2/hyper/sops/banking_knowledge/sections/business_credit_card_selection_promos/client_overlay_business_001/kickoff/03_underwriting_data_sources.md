# Card underwriting data sources — discovery worksheet

Requested by: Priyanka Rao, underwriting.
Systems pass: Evan Sokolov.
Second revision, after the 10/16 review. Previous version is in the folder
history; this one supersedes it for working purposes.

## What this covers

Where each input to a card decision actually comes from, who owns the feed,
and what we still cannot answer. Scope is the three business tiers. This is a
plumbing map — the decisioning configuration itself stays with Evan's team.

## Source map

| Input | Source / feed | Owner | State | Gap |
|---|---|---|---|---|
| Personal credit score | Bureau pull at application | Evan Sokolov | Working | Contract question below on soft vs hard pull timing. |
| Business credit (PAYDEX) | D&B batch file, nightly | Evan Sokolov | Working | Batch is nightly; no intraday refresh. See question 2. |
| Financial documents | Secure-upload requests from the underwriting queue | Priyanka Rao | Working | Retention period unconfirmed — Hana reviewing. |
| Bank references | Manual collection on Platinum applications | Priyanka Rao | Manual | No system of record; lives in the case notes today. |
| Application data | Online application intake | Marcus Adeyemi (product side) | Working | Field-level mapping doc is stale, last touched in June. |

For reference while reading tickets, the floors as configured in decisioning
today: Bronze reads its personal-score floor off the underwriting floor sheet
(not copied here), with a PAYDEX of 20 treated as helpful and skipped entirely
for brand-new businesses; Silver sits at 700 personal with 47 on the business
side; Platinum at 765 and the business floor per the sheet. One flag from
the 10/16 review: an old draft matrix in the shared drive still shows Silver
at 690. That draft never got approved — decisioning is configured at 700, and
Evan pulled the stale file out of the folder on 10/20.

## PAYDEX feed notes

The nightly batch means a vendor payment posted today shows up in tomorrow's
decision, not today's. Priyanka is fine with that for Bronze and Silver.
For Platinum, where the business-side score does more work, Evan is asking
D&B whether an on-demand pull is available on our contract tier and what it
costs per call. No answer yet.

New businesses with no D&B file at all: handled today by the no-file path on
Bronze. Whether Silver's "newer business, strong personal credit" cases route
cleanly without a file is question 3 below.

## Unanswered questions

1. Soft pull at prequalification versus hard pull at submit — what does the
   bureau contract actually permit? Evan checking with the vendor manager;
   nobody in the room on 10/16 had the contract open.
2. Is there any intraday PAYDEX refresh option, and who pays for it if so?
3. Do no-file businesses route correctly on Silver, or do they dead-end in
   the manual queue? Evan to pull two recent cases and walk them.
4. Financial-document retention: how long do uploaded statements live, and
   where? Hana owns the answer; asked 10/17, follow-up sent 11/3.
5. Bank references on Platinum — does anyone ever call them, or are they
   filed and forgotten? Priyanka suspects the latter and wants the step either
   made real or dropped from the checklist.

Next pass after Evan's vendor answers land. No meeting scheduled; updates go
in this file.
