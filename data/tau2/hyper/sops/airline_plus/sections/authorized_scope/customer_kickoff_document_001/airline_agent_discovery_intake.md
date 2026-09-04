# Airline Customer — Commercial / Agent Build Handoff Notes

Commercial owner: Casey M.
Solutions partner: Devon R.
Customer working group: Digital Care
Document state: In progress
Prepared for: Initial customer workshop

These notes collect what the account team currently understands before the
agent-build team begins discovery. Some entries come from early conversations,
some are planning assumptions, and several fields remain open. Items labeled
“confirmed scope” are the only operational requirements established here.

---

## Account Snapshot

Customer: Airline partner — external name omitted from this working copy
Business profile: Scheduled passenger airline with digital and assisted-care
channels
Primary operating region: North America
Customer team location: Multiple time zones
Commercial structure: Under discussion
Pilot budget:
Target pilot end date:
Contracting notes: Security review expected; procurement timing unknown

Account-team note: The customer wants to begin with a narrow chat scope. Broader
airline servicing discussions are exploratory and should not be read as
approved agent behavior.

## Agent Scoping

### Initial candidate requests

Candidate #1: Account payment-method maintenance
Status: Confirmed scope boundary
Requirement: The AI agent must not add a new payment method to a customer account.
Customer expectation: Make the limitation clear without suggesting that an
account update occurred.
Volume: Not isolated
Process contact: Payments Operations
Source material: Link still needed

Candidate #2: Party-size changes after a booking exists
Status: Confirmed scope boundary
Requirement: The AI agent must not change the number of passengers on an existing reservation.
Customer expectation: Treat adding or removing a traveler from the existing
booking as outside the agent's supported scope.
Volume: Believed to be low; not validated
Process contact: Reservation Operations
Source material: Draft notes mentioned, location not provided

Candidate #3:
Status: Not selected
Requirement:
Volume:
Process contact:
Source material:

Scoping note: No behavior should be inferred for Candidate #3. Other airline
workflows will be discussed separately.

### Current contact picture

Total annual contacts: Not normalized across channels
Chat: Approximately 38,000 conversations per month
Inbound voice: Approximately 92,000 offered calls per month
Email: Approximately 11,000 created cases per month
Messaging: Not currently active
Outbound: Reporting owner to confirm
Other: Social care sits with another team
Volume notes: These sources use different counting methods. Do not sum them
into one forecast.

Pilot-addressable volume: TBD. The customer has not mapped the two confirmed
candidate requests to a reliable contact-reason report.

Primary channel interest: Chat
Possible later channel interest: Voice
Initial product interest: Core customer-service outcomes
Language coverage:
Hours of operation:
Geographic rollout:

### Possible system touchpoints

**Help-site chat surface**
Expected entry point for the pilot. Placement and traffic allocation have not
been approved.

**Customer account service**
Potential source for account context. Interface owner, available operations,
and sandbox access are unknown.

**Reservation platform**
Expected to be relevant during later solution design. This document does not
define which reservation operations are exposed.

**Specialist workspace**
Possible destination when a conversation leaves the automated experience.
Queue ownership and transferred context remain under review.

**Analytics destination**
Customer Analytics would like event and outcome data for pilot reporting.
Required fields and delivery method are undecided.

**Internal content library**
Likely source of customer-approved support content. Platform name, export
method, and refresh ownership are still open.

Voice platform:
Chat platform: Customer-managed web experience
Existing automation provider:
Other platforms under evaluation: Customer has not shared
Additional technology context: Architecture asked the team not to commit to
specific interfaces before its inventory review.

---

## Additional Working Context

### Account summary

The airline is considering a chat-first customer-service pilot and wants early
discovery to stay deliberately constrained. Digital Care is coordinating, with
separate process input expected from Payments Operations and Reservation
Operations. The customer has not yet supplied normalized volume data, a final
system diagram, or approved success thresholds.

The account team has two confirmed boundary cases. Digital Care wants both
exercised during pilot acceptance before any expansion conversation. A third
candidate may be added later, but nothing has been selected.

### Scale and operating context

The reported channel totals are directional. Chat is counted as conversations,
email as created cases, and voice as offered calls. Analytics cautioned that
the figures are not comparable without additional work. Monday mornings and
large disruption events are believed to produce contact spikes, but no
seasonality analysis has been attached.

Current human performance:
Current automated performance:
Average handle time:
Transfer baseline:
Customer-satisfaction baseline:

### Pilot shape

Working assumption: Start with a limited help-site chat experience.
Setup period: TBD
Live evaluation period: TBD
Traffic split: Not discussed
Expansion decision: Expected after a cross-functional readout
Production commitment: None

This is not being framed as a broad launch commitment. The immediate objective
is to establish whether the team can agree on precise requirements, technical
ownership, and a credible evaluation method.

### Integration readiness

The Architecture group plans to provide a first-pass system map. Endpoint
availability, authentication, test data, rate limits, and failure behavior have
not been reviewed. Contact Center Engineering has not selected a specialist
queue for pilot handoff testing. Security and Privacy have not evaluated any
historical conversation export.

Readiness rating:
Known API coverage:
Sandbox date:
Technical workshop date: Proposed, not accepted
Customer integration lead:

### Measurement notes

Metrics mentioned so far include correct handling, transfer rate, customer
sentiment, operating cost, and quality-review outcomes. Quality and Analytics
have not agreed on definitions, denominators, exclusions, or baseline periods.
No numerical target in this document is approved.

Other notes: Brand Operations is preparing a smaller set of writing examples.
Existing human-representative scripts should not automatically be treated as
final automated-agent language.

## Evaluation Outline

### Possible decision indicators

- Accurate application of the two confirmed scope boundaries
- Clear separation between confirmed requirements and incomplete planning notes
- Consistent handling when the same request comes back a second time
- Useful transition to assisted support when applicable
- Acceptable customer experience in the chat surface
- Measurable operating impact using agreed definitions
- Technical setup effort that the customer team can sustain

### Expected decision process

1. Confirm the narrow request set.
2. Review system ownership and interface availability.
3. Agree on measurement definitions and a baseline window.
4. Run a limited pilot.
5. Produce a joint readout covering quality, operations, and technical effort.
6. Decide whether to expand, revise, or stop.

Decision-maker:
Approval forum:
Readout date:
Expansion criteria:

### Value themes mentioned

- Reduce avoidable repeat contacts
- Improve consistency on narrow request types
- Learn what integration effort is required
- Establish a trustworthy quality-measurement approach
- Preserve a straightforward assisted-support path

Financial model: Not started
Expected savings:
Revenue impact: Not part of the current discussion
Cost baseline owner: Finance contact not yet identified

## Organization Context

Headquarters:
Industry: Passenger air transportation
Employee count:
Annual revenue:
Customer-care organization size:
How the business describes the pilot: A controlled learning exercise for
digital care

## Engagement Planning

### Stakeholder map

| Pilot role | Name | Customer title / team | Current posture | Influence | Account-team owner | Notes |
|---|---|---|---|---|---|---|
| Executive sponsor |  |  | Unknown | High | Casey M. | Identify before readout planning |
| Business sponsor |  | Digital Care | Supportive | High | Casey M. | Coordinating early scope |
| Payments process owner |  | Payments Operations | Engaged | Medium | Devon R. | Documentation link pending |
| Reservation process owner |  | Reservation Operations | Engaged | Medium | Devon R. | Draft notes mentioned |
| Architecture lead |  | Integration Architecture | Cautious | High | Devon R. | Wants inventory review first |
| Contact-center lead |  | Contact Center Engineering | Unknown | Medium |  | Pilot queue unselected |
| Quality lead |  | Customer Care Quality | Supportive | Medium |  | Rubric follows scope freeze |
| Analytics lead |  | CX Analytics | Cautious | Medium |  | Channel metrics not normalized |
| Brand reviewer |  | Brand Operations | Neutral | Low |  | Reviewer nomination pending |
| Security reviewer |  | Security and Privacy | Not engaged | High |  | Review not scheduled |
| Procurement |  |  | Unknown | High | Casey M. | Timing unknown |

Stakeholder coverage note: Several names are intentionally blank because the
account team has roles but not confirmed participants.

### Stakeholder callouts

**Commercial owner:** Keep the first workshop focused. The customer has raised
many adjacent ideas, but the build team should not treat them as requirements.

**Solutions partner:** We need a clean distinction between a customer-account
change and use of data already present in an account. Technical feasibility is
still unknown.

**Payments Operations:** The confirmed boundary concerns adding a payment method
to the account. They have not used this intake to define other transaction
rules.

**Reservation Operations:** The confirmed boundary concerns changing party size
after a reservation exists. New-booking limits and supervisor capabilities
belong to other source material.

**Integration Architecture:** System names in conversation have not been
validated. Treat the touchpoint list as a discovery checklist.

**Customer Care Quality:** Do not set a completion-rate target until the sample,
review rubric, and denominator are agreed.

**CX Analytics:** Current channel numbers describe different units. A normalized
view may change the apparent distribution materially.

**Brand Operations:** A reviewer can provide representative language later.
Existing human scripts were written for a different operating model.

## Notes from Account-Team Conversations

### December 6 — volume follow-up

Attendees: Commercial owner, Digital Care, CX Analytics

- Chat reporting appears to include both automated and transferred contacts.
- Voice reporting is based on offered calls.
- Analytics asked for one week to identify a common reporting unit.
- No one approved a total addressable-volume estimate.

Follow-up: Analytics to send a short methodology note.
Owner:
Due:

### December 10 — technical preparation

Attendees: Solutions partner, Integration Architecture, Contact Center
Engineering

- Architecture can share a preliminary diagram.
- Interface-level commitments require platform-owner review.
- The specialist routing destination is still undecided.
- A separate security discussion will be needed before using historical data.

Follow-up: Circulate proposed technical-workshop agenda.
Owner: Devon R.
Due: Before customer scheduling confirmation

### December 13 — quality discussion

Attendees: Digital Care, Customer Care Quality, CX Analytics

- “Correct completion” does not yet have an agreed definition.
- Quality prefers a small reviewed sample before a larger evaluation run.
- Analytics wants transfer categories separated before building a baseline.
- The group agreed to list candidate measures without targets.

Follow-up: Draft definitions after the request set is frozen.
Owner: Quality lead
Due:

### December 16 — internal handoff preparation

Attendees: Commercial owner, solutions partner

- Preserve the two confirmed scope boundaries exactly.
- Keep the third candidate blank.
- Mark integration statements as hypotheses or open questions.
- Add stakeholder roles even when names are missing.
- Carry unresolved issues into the first build-team workshop.

Follow-up: Share this draft with the agent-build lead.
Owner: Casey M.
Due: Prior to kickoff

## Action Tracker

| Work item | Customer owner | Account-team owner | Status | Latest note |
|---|---|---|---|---|
| Confirm channel-count methodology | CX Analytics |  | In progress | Sources use different units |
| Provide process source for Candidate #1 | Payments Operations | Devon R. | Open | Link pending |
| Provide process source for Candidate #2 | Reservation Operations | Devon R. | Open | Draft location unknown |
| Select Candidate #3 | Digital Care | Casey M. | Deferred | Review after complexity discussion |
| Share system diagram | Integration Architecture | Devon R. | In progress | Preliminary version expected |
| Identify specialist queue | Contact Center Engineering |  | Not started | Owner not confirmed |
| Define pilot measures | Quality and Analytics |  | Blocked | Waiting on scope freeze |
| Nominate brand reviewer | Brand Operations |  | In progress | Expected later this month |
| Schedule security review | Security and Privacy |  | Not started | Depends on data proposal |
| Identify executive sponsor | Digital Care | Casey M. | Open | Needed before readout |

## Open Questions / Parking Lot

- Which team owns the help-site chat surface?
- Are historical conversations available in a form suitable for evaluation?
- What data can accompany an assisted-support transition?
- How will chat contacts be sampled for baseline review?
- Is multilingual support relevant to the pilot?
- Does Candidate #3 need to be selected before technical discovery?
- Who approves the measurement definitions?
- What is the expected review cadence after the pilot starts?
- Are there existing platform commitments that affect architecture choices?
- When should Procurement and Security join the working group?

## Draft History

Version 0.1 — Account snapshot and rough channel volumes
Version 0.2 — Added two confirmed candidate boundaries
Version 0.3 — Added integration hypotheses and stakeholder roles
Version 0.4 — Added account-team conversation notes
Next update — After technical-workshop scheduling
