# ATM pricing and reimbursement — data-source worksheet

**Working owner:** Priya Nair
**Review pair:** Daniel Cho / Erin Walsh
**Phase:** Discovery, second pass
**Next review:** 2025-10-21, 1:00 p.m. PT

## The distinction we need to preserve

Customer conversations often group every ATM-related charge together. The
project needs sources that keep bank-assessed fees, network or terminal-owner
surcharges, and any reimbursement behavior distinct. This worksheet identifies
where those answers live. It should not be used as a standalone pricing guide.

## Source map

| Question | Candidate source | Confidence | Gap / owner |
|---|---|---|---|
| What does the bank assess? | Current business pricing schedule | High | Daniel to confirm product labels. |
| What can a terminal owner assess? | ATM disclosure and transaction detail | Medium | Need customer-safe explanation from Servicing. |
| When is a reimbursement posted? | Servicing procedure | Medium | Timing examples are inconsistent. |
| How does support identify the charge? | Statement descriptor guide | High | Verify access for branch staff. |
| Where is a dispute routed? | Helpdesk routing configuration | Partial | After-hours path is blank. |

## Sample scenario review

**Scenario A — out-of-network withdrawal.** The statement shows two separate
lines. The support rep should identify who assessed each charge before discussing
the product terms. Priya has requested an anonymized statement image for the
coaching packet.

**Scenario B — expected reimbursement not visible.** The intake team needs the
posting-date convention and the escalation threshold. Daniel has the pricing
source; Erin is looking for the operational timing source. Status: **Open**.

**Scenario C — customer cites a campaign page.** Keep the promotion question
separate from the transaction analysis. Promotions will confirm whether the page
was live on the relevant date.

## Validation checklist

- [x] Use “bank fee” only for an amount assessed by the bank.
- [x] Preserve terminal/network surcharge as a separate concept.
- [ ] Obtain a realistic statement example with approved redaction.
- [ ] Confirm the reimbursement posting convention.
- [ ] Test the ticket fields with Branch Support.
- [ ] Assign the after-hours escalation owner.

## Sky Blue usage lines captured at the 21 October review

Servicing brought four customer-safe usage lines for Sky Blue, the product the
coaching packet leads with. Daniel checked the two figures against the pricing
schedule in the room; Erin captured the wording as read. The packet re-verifies
values against the schedule at publication.

- Using in-network ATMs when possible avoids the out-of-network ATM fee of
  $1.50.
- If multiple cash withdrawals are anticipated, taking out cash less
  frequently in larger amounts can reduce the number of per-transaction
  domestic out-of-network ATM fees.
- For international withdrawals, because a minimum fee of $3.00 applies,
  fewer larger withdrawals may reduce the effective fee rate on small cash
  needs.
- Review the ATM's on-screen disclosures before confirming a withdrawal to
  see any operator surcharges.

## Notes from the first pass

The prior support card collapsed reimbursement and fee-waiver language into one
bullet. Erin asked that it remain available for the migration review but not be
used for new coaching. Daniel also flagged a planning deck whose footnote omits
the terminal-owner distinction; the deck owner has been notified. No copy change
will be made from this worksheet alone.

## Unanswered for Tuesday

Can the servicing team reliably tell the difference from the statement
descriptor without opening a second system? If not, the launch-week route needs
to account for that delay. Priya will ask two agents to walk through recent
examples before the review.
