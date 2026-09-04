# Identity Workstream — Workshop Notes (Running Log)

Maintained by: Priya Shah (program) — corrections in comments, not in the body
Covers: discovery workshops, May through July 2026
Relationship to the intake: these are working notes. Anything that reads like
a decision here is a paraphrase; signed pilot decisions live only in the
Identity and CRM Readiness Intake, and that document wins every conflict.

---

## Session log

### May 14 — CRM field inventory walkthrough

Room: Evan Kessler, Mia Tran, Grace Okafor, Priya Shah; Marcy Doyle joined
for the last half hour.

Evan walked the group through the CRM export column by column. The inventory
surfaced ninety-one fields, of which roughly a third have no documented owner
and at least six are legacy imports whose names lie about their contents
(the memorable one: a column named `fax` that has stored a courier account
number since 2019). Mia is building the annotated field map; unowned fields
get flagged rather than guessed at.

Actions: Mia to circulate the annotated map before the next session. Evan to
chase the two columns whose meaning nobody in the room could state.

### May 28 — Lookup paths and edge cases

Room: full working group minus Grace (traveling), plus Lena Ortiz from care.

Lena demonstrated the three ways agents currently find a customer record and
the improvisations each one invites when the first attempt misses. The group
catalogued the miss cases on the whiteboard without proposing fixes — the
catalogue itself is the deliverable, and it went into the shared folder as
photographed. Tomas raised the duplicate-record question; it is real, it is
old, and it is explicitly out of scope for the pilot per the intake.

Actions: Lena to tag one week of miss cases with their whiteboard category so
the catalogue gets frequencies. Priya to add the duplicate-record question to
the future-state backlog where it can be admired safely.

### June 10 — Access model review

Room: Marcy Doyle, Noor Danesh, Evan Kessler, Priya Shah; Sanjay Rao read the
pre-materials and sent written comments instead of attending.

Marcy presented the current access tiers and who holds each one. Sanjay's
written comments were sharper than the meeting: two service accounts still
carry review-era permissions from the spring audit, and the recertification
evidence should be attached to the workstream record, not just to the audit
folder. Both points were accepted without debate, which Noor noted is the
meeting equivalent of a standing ovation.

Actions: Marcy to complete the two downgrades and file the receipts in both
folders. Noor to rewrite the access-request microcopy that three people have
now misread the same way.

### June 24 — Data mapping working session

Room: Mia Tran, Evan Kessler, Bea Sandoval, Priya Shah.

The annotated field map met the design mock for the first time. Most fields
paired cleanly. Two labels disagree between the CRM export and the mock —
same data, different names — and the group chose to reconcile toward the
export's names because the export is what downstream tooling reads. Bea
flagged that the training materials screenshot the mock, so the rename has a
training cost; she owns the screenshot refresh once the mock updates.

Actions: Mia to file the two renames with the design team. Bea to hold the
screenshot refresh until the mock lands, then batch it.

### July 8 — Monitoring and failure visibility

Room: Mia Tran, Tomas Egan, Priya Shah; Hank Fischer as a guest for the
warehouse-adjacent question that turned out to be a mislabeled ticket.

Tomas walked through how a failed lookup currently appears in monitoring,
which is to say: barely. The dashboard counts failures without
distinguishing why, and the one alert that exists pages on volume, not on
pattern. The group agreed the pilot needs failure reasons before it needs
failure counts, and Tomas sketched the categories on the call. Nothing here
changes agent behavior; it changes what engineering can see.

Actions: Tomas to draft the failure-reason categories against a week of logs
and bring the draft, not a proposal, to the next session.

### July 22 — Pre-readiness review

Room: full working group.

Walked the open-actions list top to bottom. Eleven items closed since May,
four remain open, none blocking. The two CRM renames are with design; the
failure-reason draft is in review; the screenshot batch waits on the mock;
the miss-case frequencies arrive with Lena's July tally. The group agreed
the workstream is ready for the readiness addendum to be drafted, which is a
separate document with a drier personality than this one.

---

## Standing notes

Corrections to these notes arrive as comments and get folded in with a dated
strike-through, never a silent edit. The photographed whiteboards live in the
shared folder under their session dates. Attendance is recorded because it
explains which sessions a question could have been raised in, not to take
roll.
