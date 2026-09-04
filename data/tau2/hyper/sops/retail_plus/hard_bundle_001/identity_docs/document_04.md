# Pilot Governance and Measurement Register

Register owner: Priya Shah · Definitions co-owner: Analytics (via Aisha Karim's team)
Effective: July 2026 · Reviewed at each governance checkpoint
Purpose: one place where the pilot's measures are defined and its governance
rhythm is written down. This register defines and schedules; it does not
decide. Decisions live in the intake.

---

## Governance rhythm

| Forum | Cadence | Chair | Standing output |
| --- | --- | --- | --- |
| Workstream checkpoint | Weekly, Tuesdays | Priya Shah | Open-actions delta |
| Readiness review | At each addendum | Evan Kessler | Signed addendum |
| Governance checkpoint | Monthly, last Thursday | Grace Okafor | Register review + risk walk |
| Measurement calibration | Monthly, first week | Analytics | Definition confirmations |

Escalations between forums travel as one-line items with an owner, and a
forum can send an item up but never sideways: the checkpoint escalates to
governance, not to whichever meeting happens sooner.

## Measurement definitions

Each measure has exactly one definition and one counting owner. A deck that
needs a variant must name it differently rather than redefining these.

**Lookup success.** A lookup attempt that returns the intended customer
record on the first result. Counted per attempt, not per conversation, by
the platform log. Owner: platform engineering.

**Assisted-resolution time.** Elapsed time from conversation assignment to
the closing disposition, measured in the servicing tool. Pauses are not
subtracted; the measure deliberately includes waiting because customers
experience waiting. Owner: care program analytics.

**Coverage of the field map.** Share of integration reads that reference a
mapped, owned field. The quarantined legacy columns count against coverage
if anything reads them, which nothing should. Owner: Mia Tran until the
platform team takes the map.

**Calibration spread.** The reviewer-score spread on the shared QA sample,
as defined by the QA program's own documentation — this register points to
that definition rather than restating it, so the two can never disagree.
Owner: QA program.

## Risk register (walked monthly)

| # | Risk | Watching for | Owner | State |
| --- | --- | --- | --- | --- |
| R1 | Field map drifts after handoff | Reads of unmapped fields ticking up | Mia Tran | Watch |
| R2 | Sandbox notification-hook gap masks a defect | A flow passing in sandbox, failing in rehearsal | Evan Kessler | Watch |
| R3 | Failure taxonomy stalls in review | A5 still open at the August governance checkpoint | Tomas Egan | Active |
| R4 | Measurement double-definition | The same metric name with two formulas in one deck | Priya Shah | Closed July — basis labels shipped |

A risk enters the register with the sentence that would appear in the
post-incident review if it fired; if that sentence cannot be written, the
risk is not yet specific enough to register.

## Change control for this register

Definition changes require the counting owner and the register owner in the
same room, plus a note in the following governance checkpoint's minutes. The
register's history section lists every changed definition with its date and
the deck generation it first affected, because a metric that changes silently
is worse than a metric that was always wrong.

## History

- July 3 — Register created; four measures, three risks.
- July 25 — R4 closed following the basis-label rollout; lookup-success
  wording tightened from "returns a record" to "returns the intended
  customer record" after calibration caught the ambiguity.
