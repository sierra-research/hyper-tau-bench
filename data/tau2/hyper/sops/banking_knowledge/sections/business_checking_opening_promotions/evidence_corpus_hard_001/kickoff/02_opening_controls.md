# Account-opening controls workshop notes

**Session:** 29 September 2025, 10:00–11:15 PT
**Facilitator:** Luis Ortega
**Notes:** Erin Walsh (lightly cleaned up after the call)
**Document state:** Working notes; three decisions need confirmation

## Why we met

The current opening material mixes customer steps, back-office checks, and
support recovery paths. We need a shared sequence for the refresh without
pretending that every exception follows the happy path.

## Walk-through as described on the call

1. Customer chooses a business-checking product.
2. The opening experience collects business and signer information.
3. Eligibility and identity checks run before an account-opening action is
   completed.
4. If the checks cannot finish in-session, the application may need a manual
   review. The exact queue name is still being verified.
5. Once the account exists, the customer receives the appropriate confirmation
   and next-step instructions.

Luis emphasized that this is a sequence description, not a promise that every
screen appears in exactly this order. Mobile and desktop can combine some of the
collection screens.

## Product-specific verification rows

Step 3 also runs product-specific checks on top of the shared identity and
eligibility work. Only one was walked in full on this call; the rest need
owners from the inventory sheet before they can be added here.

| Product | Verification row in the shared sequence | Confirmed on call? |
|---|---|---|
| Sky Blue | Eligibility requires confirming the company is within 4 years of formation. | Yes — Luis read the check out from the eligibility copy. |
| Others | Not enumerated in this session. | No — collect from the product owners. |

## Decision log

| # | Decision / issue | State | Owner | Due |
|---|---|---|---|---|
| O-1 | Keep product selection ahead of the opening action in the shared diagram. | Agreed | Luis | Done |
| O-2 | Label manual review as an exception path, not a normal customer step. | Agreed | Erin | Done |
| O-3 | Confirm the team name shown for escalations. | Open | Jamal | 10/03 |
| O-4 | Determine whether branch-assisted openings use the same confirmation template. | Investigating | Lena | 10/06 |
| O-5 | Remove the old self-service concept diagram from the facilitator packet. | Proposed | Nina | TBD |

## Notes that should not be smoothed over

- Lena said branch staff sometimes start with document readiness before they
  discuss a specific product. That is a conversation pattern, not a change to
  the digital control sequence.
- Jamal asked whether support can see why an application entered review. The
  answer was "sometimes," depending on the signal. We did **not** resolve which
  reasons are safe to repeat to a customer.
- The team used "identity," "verification," and "business validation"
  inconsistently. Priya will bring the approved labels to the copy review.

## Parking lot

- What happens when the chosen product is not available for the business type?
- Is there a documented re-entry point for an abandoned application?
- Which system sends the final confirmation for a branch-assisted opening?
- Do we need a separate operating note for known-device recovery?

## Before the next workshop

- [ ] Jamal: paste the escalation queue name and operating hours here.
- [ ] Priya: annotate the copy under review with approved control labels.
- [ ] Luis: confirm whether the existing diagram covers the mobile variant.
- [ ] Erin: schedule 20 minutes with Branch Enablement; no full-group meeting.

Next working session is penciled in for 7 October at 2:30 PT. Do not circulate
the diagram outside the project group until O-3 and O-5 are closed.
