# CRM Integration Readiness — Addendum to the Intake

Addendum number: 1
Drafted: July 24, 2026 · Evan Kessler, with review by Mia Tran and Priya Shah
Scope: integration readiness facts discovered after the intake was signed.
Nothing in this addendum amends a pilot decision. Where an item appears to
touch one, the item says so and stops; amendments go through the intake's
change process.

---

## A1. Field map is complete and versioned

The annotated CRM field map reached its first complete version on July 11.
Every field now carries an owner, a plain-language description, and a
sensitivity marker. The map is versioned in the shared workspace; the export
tooling reads the map's names as canonical. The two label mismatches with the
design mock were resolved toward the export names on June 24 (workshop notes,
same date, for the discussion).

Status: complete. Consumers should cite map version 1.3 or later.

## A2. Legacy columns quarantined, not deleted

Six legacy columns whose names misdescribe their contents are quarantined in
a read-only view pending owner sign-off on disposal. Quarantine means new
integrations cannot reference them; existing readers are unaffected. The
courier-account column formerly known as `fax` is the type specimen and has
been renamed in the map with its history noted.

Status: complete for the pilot's purposes; disposal is a post-pilot item.

## A3. Service-account permissions recertified

The two service accounts flagged in the June access review were downgraded on
June 26, and the recertification receipts are attached to the workstream
record as well as the audit folder. The quarterly recertification cadence now
includes both accounts by name rather than by group membership, which is what
allowed the drift in the first place.

Status: complete, with the cadence change as the durable fix.

## A4. Sandbox parity

The integration sandbox now refreshes from a masked weekly snapshot rather
than the hand-built seed data that had drifted since spring. Masking follows
the same field-sensitivity markers as the map, so a field's sandbox behavior
predicts its production handling. One known gap: the sandbox's notification
hooks are stubs, so flows that end in a customer message succeed silently
there. Test plans need to assert on the hook call, not the message.

Status: complete with the documented gap.

## A5. Failure-reason categories (in review)

Monitoring currently counts lookup failures without classifying them. Tomas
Egan's draft taxonomy — checked against one week of production logs — is in
review with platform engineering. Until it lands, failure dashboards remain
volume-only, and readiness reviews should treat failure-pattern questions as
unanswerable rather than answered by the volume chart.

Status: in review; the only open item this addendum carries.

## A6. Environments and cutover rehearsal

A cutover rehearsal on July 17 exercised the integration end to end in the
sandbox: map-driven field reads, quarantine enforcement, and the masked
snapshot all behaved. The rehearsal script and its timing log are filed with
this addendum. A second rehearsal will run against the failure-reason build
once A5 closes, and the pilot's go decision — which belongs to the intake,
not to this document — should wait for that rehearsal's log.

Status: first rehearsal complete; second scheduled behind A5.

---

## Reading order for newcomers

Intake first, always. Then the workshop notes for how the items above were
argued, then this addendum for where they landed. The measurement register is
the fourth document and owns definitions; this addendum deliberately contains
no metric names so that it cannot drift from it.
