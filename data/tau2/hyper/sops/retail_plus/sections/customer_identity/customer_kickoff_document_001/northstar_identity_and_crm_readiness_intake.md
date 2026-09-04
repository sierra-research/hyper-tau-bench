# NorthStar Customer Care — Identity and CRM Readiness Intake

Customer program: NorthStar assisted-service pilot
Document owner: Customer Experience Enablement
Technical partner: Commerce Platform Architecture
Working group: Customer Care, Trust and Safety, CRM Operations, Digital Product
Document status: Workshop draft with approved pilot decisions
Prepared for: Agent build and integration discovery
Last working-session date: April 29, 2026

This intake collects the current operating context for customer identification,
account lookup, and profile access. It is intentionally broader than the first
pilot. Many fields are incomplete because the customer and implementation teams
are still doing discovery.

## Decision status legend

Only an item labeled **Confirmed pilot decision** is an operational requirement
for the first release. Items labeled **Proposed**, **Future-state discussion**,
**TBD**, **Observation**, or **Not in pilot** are planning context and must not
be treated as approved customer-care behavior.

If an entry is blank, the working group has not supplied an answer. A blank
field does not authorize an implementation choice.

---

## Account snapshot

Customer: NorthStar Marketplace
Business profile: Direct retail and marketplace commerce
Primary region: United States
Customer-care organization: Distributed internal and partner teams
Commerce channels: Web, mobile web, assisted service
Primary pilot channel: Web chat
Possible later channels: Voice and asynchronous messaging
Pilot budget:
Target live date:
Traffic allocation:
Executive sponsor:
Procurement owner:
Security review date:

Account-team note: The identity workstream is being separated from password
management, fraud operations, and loyalty-program design. Those adjacent areas
appear in this intake so that their owners can be found; they are not part of
the approved agent behavior unless a confirmed decision says otherwise.

## Pilot goals and constraints

### Working goals

- Reduce repeated profile-search effort for straightforward service contacts.
- Avoid exposing account information before the correct customer is verified.
- Give the build team a stable customer-record entry sequence.
- Preserve a simple conversation model for the first release.
- Produce enough audit detail for quality review.

Status: Observation. These are program goals, not executable policy steps.

### Candidate success measures

Identity completion rate: Definition pending
Median lookup time: Baseline not supplied
Incorrect-profile access rate: Measurement owner pending
Repeat-contact rate: Window not agreed
Transfer rate: Reason taxonomy incomplete
Customer satisfaction: Survey design under review
Quality-review pass rate: Rubric not approved

No numerical target in this section has been approved.

### Pilot boundaries still under discussion

Guest checkout support: Future-state discussion
Business purchasing accounts: Future-state discussion
Marketplace seller profiles: Not in pilot
Employee accounts: Not in pilot
Loyalty-only profiles: Proposed for later discovery
Password reset: Not in pilot
Multi-factor authentication changes: Not in pilot
Fraud-case investigation: Not in pilot
Marketing-preference updates: Not in pilot

## Current contact landscape

### Directional channel volumes

Web chat: Approximately 51,000 conversations per month
Inbound voice: Approximately 118,000 offered calls per month
Email: Approximately 17,000 created cases per month
Social care: Managed in a separate workspace
Marketplace seller contacts: Counted by a different operations group
Seasonal peak: November and December
Monday volume effect: Believed material; not quantified
Identity-related contact share: Not reliably tagged

Volume note: These sources use different units and reporting windows. Do not
sum them into a single demand forecast.

### Contact reasons mentioned during discovery

- Order status and delivery timing
- Pending-order changes
- Returns and exchanges
- Default-address updates
- Payment questions
- Product availability
- Password and sign-in trouble
- Gift-card balance questions
- Marketplace seller requests
- Loyalty and promotional questions

Status: Observation. This list describes historical contact labels and does not
define what the pilot agent may do.

### Current human workflow observations

Representatives report switching among a chat workspace, a profile search
panel, an order console, and a knowledge portal. Some partner teams use a
different profile-search layout. Screen names and click paths vary by queue.

Supervisors believe representatives often search by email, but the analytics
team has not validated the claim. The current tools expose several search
fields whose mere presence does not mean they are approved identity inputs.

Status: Observation.

## Conversation and session model

### Account boundary

Status: **Confirmed pilot decision**

The automated conversation serves one customer and that customer's own profile.
It must not switch to, inspect, or act on a friend's, spouse's, relative's, or
other person's account, even when the person in the conversation knows the
other account's order numbers, delivery address, or item details.

The working group selected this boundary to keep the first release auditable.
Delegated access, household profiles, caregiver access, and business-account
roles remain outside the approved design.

### Request handling within a verified session

Status: **Confirmed pilot decision**

After one customer has been verified, that same customer may make more than one
request in the conversation. A second request from the verified customer does
not require starting a new conversation merely because the topic changes.

This decision does not permit changing to another person or another person's
profile. It only allows multiple requests for the same verified customer.

### Session duration

Idle timeout: TBD
Maximum conversation duration: TBD
Reverification after inactivity: Future-state discussion
Reverification before a high-risk action: Trust and Safety review pending
Browser-tab continuity: Technical behavior not documented
Cross-channel continuation: Not in pilot

### Household and delegated access

Shared household profile concept: Proposed; no approved model
Parent helping an adult child: No delegated workflow approved
Spouse with order details: No delegated workflow approved
Caregiver role: Future-state discussion
Business purchasing delegate: Not in pilot
Minor account handling: Legal review not scheduled

These entries are planning context. They do not create exceptions to the
confirmed one-customer, own-profile boundary.

## Customer identification workflow

### Entry requirement

Status: **Confirmed pilot decision**

The first task in every conversation is to identify who the customer is. The
agent does not begin by opening orders, addresses, or saved payment information
and then work backward to establish the customer.

The experience team may later revise the greeting copy, but the order of work
is fixed for the pilot: customer identification comes first.

### Candidate greeting approaches

Option A: Ask for an account identifier immediately
Status: Proposed copy; not approved

Option B: Ask how the customer would like to be found
Status: Proposed copy; not approved

Option C: Infer identity from an authenticated web session
Status: Future-state discussion; session signal not available to the pilot

The selected wording is intentionally absent. This intake establishes the work
sequence, not a required sentence.

### Pre-identification context

Anonymous page URL: May be available; technical inventory incomplete
Shopping-cart identifier: Proposed telemetry only
Order number in chat entry form: Product idea; not approved as identity
Browser cookie: Privacy assessment pending
Campaign source: Analytics field; not an identity decision
Locale: May be supplied by the page; mapping not finalized

No item in this list changes the confirmed entry requirement.

## Lookup configuration

### Approved ways to find a customer profile

Status: **Confirmed pilot decision**

The pilot has three supported lookup routes:

1. A unique account identifier.
2. The email address on the customer profile.
3. First name plus last name plus ZIP code, supplied together.

These routes locate a candidate customer profile. The account-identifier route
has an additional ownership check described in the verification section.

### Candidate lookup field inventory

| Candidate input | Discovery status | Notes |
|---|---|---|
| Unique account identifier | Confirmed pilot decision | Supported lookup route |
| Profile email | Confirmed pilot decision | Supported lookup route |
| First name + last name + ZIP | Confirmed pilot decision | Supported composite lookup route |
| Phone number | Proposed | Data quality and consent review open |
| Order number | Not approved as identity | Useful in later service work only |
| Loyalty identifier | Future-state discussion | Program ownership unresolved |
| Gift-card number | Not approved as identity | Payment instrument, not a profile key |
| Shipping street address alone | Not approved as identity | Match behavior undefined |
| Device identifier | Not in pilot | Privacy review not started |
| Social handle | Not in pilot | Social care uses another workspace |

The proposed and rejected rows are included because the CRM screen currently
contains more fields than the pilot is allowed to rely on.

### Search-result behavior

Zero-result copy: TBD
Multiple-result handling: TBD
Typographical correction: Proposed; matching behavior not approved
Email normalization: Technical investigation open
Name punctuation: Technical investigation open
ZIP formatting: Technical investigation open
International postal codes: Not in the US pilot
Search retry limit: TBD
Search-event analytics: Proposed

This intake does not define how the system ranks or resolves ambiguous search
results.

## Verification gate

### Account-identifier result handling

Status: **Confirmed pilot decision**

A supplied account identifier is not sufficient on its own to establish that
the profile belongs to the person in the conversation. Before proceeding, the
agent must match either:

- the email address on the profile, or
- the combination of first name, last name, and ZIP code on the profile.

Knowing order details, an item name, a delivery city, or the last four digits
of a payment instrument does not replace this confirmed match for the
account-identifier route.

### Other verification proposals

One-time passcode by SMS: Future-state discussion
One-time passcode by email: Future-state discussion
Knowledge-based questions: Trust and Safety does not recommend for pilot
Payment-card verification: Not approved
Recent-order amount: Not approved
Device trust score: Not in pilot
Web-session authentication handoff: Architecture investigation open
Government identification: Not in pilot

These proposals are not alternate pilot verification methods.

### Mismatch and failure handling

Mismatch retry count: TBD
Lockout behavior: TBD
Customer-facing explanation: Brand review pending
Human escalation route: Queue owner not confirmed
Fraud signal creation: Future-state discussion
Audit-event severity: Security review pending

No operational handling for failed verification is established by this
intake. The build team should not invent a retry or escalation rule from the
open fields.

## Profile access

### Post-verification data load

Status: **Confirmed pilot decision**

Only after the customer has been verified does the agent pull the complete
customer profile. The loaded profile provides the customer's orders,
addresses, and saved payment methods for the service work that follows.

Profile lookup and full-profile access are distinct stages: locating a
candidate record does not itself authorize loading the customer's service
history and saved details.

### Candidate profile data inventory

Customer name: Present
Profile email: Present
Default shipping address: Present
Saved payment methods: Present
Orders: Present
Marketing preferences: Owner not confirmed
Loyalty status: Separate system under discussion
Support-case history: Availability differs by queue
Fraud annotations: Restricted system; not in pilot
Returns history: Data location under review
Product reviews: Not relevant to assisted service
Wishlist: Not in pilot scope
Browsing history: Privacy review not started

Status: Observation. Data being present in a source system does not authorize a
new agent action.

### Data minimization questions

Should the agent receive every saved address? TBD
Should expired payment methods be omitted? TBD
Should cancelled orders be returned by default? TBD
Should older orders be paginated? Proposed
Should support notes be redacted? Security review pending
Should marketplace seller data be separated? Architecture review pending

The confirmed pilot decision is about sequencing the profile load after
verification, not the unresolved shape of every response field.

## CRM and integration readiness

### Systems mentioned in discovery

Customer profile service: Expected source of profile records
Order service: Expected source of order records
Payment vault: Tokenized saved-method metadata only; interface review pending
Address service: Ownership not confirmed
Chat platform: Customer-managed web experience
Identity provider: Used for website sign-in; pilot integration not approved
Analytics destination: Candidate event sink; schema TBD
Specialist workspace: Possible assisted-support destination
Knowledge portal: Content export method under review

Status: Observation. System names do not establish available tools or methods.

### Interface inventory

Profile search endpoint: Design review pending
Profile detail endpoint: Design review pending
Authentication method: TBD
Sandbox tenant: Requested
Rate limit: Unknown
Timeout expectation: Unknown
Retry policy: Unknown
Idempotency behavior: Not applicable to read-only discovery; review later
Regional routing: Proposed
Maintenance window: Not supplied
Schema versioning: Owner to confirm

### Sample field names heard in workshops

customer_id
email
first_name
last_name
zip_code
phone_number
default_address
payment_methods
orders
created_at
updated_at

Status: Observation. These are workshop notes, not a committed API schema.

### Error and availability planning

Profile service unavailable: Handling TBD
Partial profile response: Handling TBD
Stale address cache: Architecture question
Payment-vault timeout: Future integration question
Order-service timeout: Future integration question
Search index lag: Measurement not available
Duplicate-profile merge: CRM Operations process, not in pilot

## Security and privacy review

### Review checklist

Data classification: Draft in progress
Threat model: Not started
Privacy impact assessment: Scheduling pending
Audit-event retention: TBD
Conversation retention: Existing platform setting under review
Access logging: Required in principle; schema not supplied
Redaction of payment tokens: Architecture review pending
Representative access controls: Existing process not documented here
Third-party processor review: Procurement to coordinate

### Sensitive-data handling questions

Full payment number in chat: Existing platform prevention controls under review
Government identifiers: Not required for pilot
Date of birth: Not approved as a lookup or match input
Phone number: Candidate future lookup input; not approved
Device fingerprint: Not in pilot
IP address: Analytics availability unknown
Fraud-case details: Restricted and out of scope

### Access-review observations

Trust and Safety wants a traceable boundary between finding a candidate profile
and opening the full record. CRM Operations wants the build team to avoid
assuming that every field visible to a human representative belongs in the
automated experience.

Status: Observation. The confirmed sequence is recorded in the profile-access
section and decision register.

## Channel, language, and accessibility context

Pilot channel: Web chat
Voice: Possible later phase
Asynchronous messaging: Product discovery only
Email automation: Not planned
Social messaging: Separate operations team
English: Expected pilot language
Spanish: Demand estimate requested
French: No decision
Screen-reader requirements: Accessibility review scheduled
Keyboard navigation: Chat surface team owns
Low-bandwidth behavior: Not evaluated
Mobile viewport: Supported by current chat surface; test plan pending

Identity controls are intended to be channel-independent, but this intake does
not approve deployment outside the web-chat pilot.

## Operations and quality

### Proposed quality checks

- Customer identification occurs before service-record access.
- Approved lookup routes are used accurately.
- A supplied account identifier receives the required ownership match.
- The conversation remains on one customer's own profile.
- Multiple requests from that verified customer are handled consistently.
- Full profile data is loaded only after verification.

Status: Proposed review categories. Scoring definitions and thresholds are TBD.

### Workforce context

Internal care sites: Three reported
Partner sites: Two reported
Training curriculum owner: Customer Care Learning
Identity refresher cadence: Unknown
Quality sampling rate: Not supplied
Supervisor escalation model: Varies by site
Peak-season staffing plan: Drafting in progress

### Measurement questions

What counts as an identification attempt?
How are lookup retries grouped?
How is a customer-abandoned session classified?
Can an incorrect candidate result be observed without opening it?
What event marks successful verification?
How are multiple requests counted?
Which fields can quality reviewers see?

## Stakeholder map

| Workstream role | Team | Current posture | Influence | Named owner | Notes |
|---|---|---|---|---|---|
| Business sponsor | Customer Experience | Supportive | High |  | Pilot owner to confirm |
| Care operations | Customer Care | Supportive | High | Marisol Vega | Owns workflow review |
| CRM product owner | Commerce Platform | Engaged | High | Ian Mercer | API inventory pending |
| Trust and Safety | Trust and Safety | Cautious | High | Asha Venkat | Verification proposals constrained |
| Privacy reviewer | Privacy | Not engaged | High |  | Review not scheduled |
| Security architect | Security | Engaged | High | Darius Cole | Threat model pending |
| Chat surface owner | Digital Product | Engaged | Medium | Noelle Park | Entry copy unresolved |
| Quality lead | Care Quality | Supportive | Medium | Keisha Morgan | Rubric draft pending |
| Analytics lead | CX Analytics | Cautious | Medium | Leo Brandt | Definitions incomplete |
| Partner operations | Vendor Management | Neutral | Medium |  | Site differences undocumented |
| Loyalty owner | Loyalty | Not engaged | Low |  | Future-state only |
| Fraud operations | Loss Prevention | Not engaged | Medium |  | Not in pilot |

### Stakeholder callouts

**Customer Care:** Keep the first release on one customer per conversation. The
same verified customer should not have to restart merely to ask about another
order or a second supported issue.

**CRM Operations:** A search result is a candidate, not blanket permission to
open the entire record. Preserve the verification gate before loading orders,
addresses, and saved methods.

**Trust and Safety:** An account identifier is easy to forward or copy. Match
the profile email or the customer's first name, last name, and ZIP before
continuing on that route.

**Digital Product:** Greeting language can be tested later. The pilot still
needs customer identification to be the first task in the interaction.

**Analytics:** Do not treat order number, phone number, loyalty identifier, or
device data as approved identity routes just because the current tools expose
or log them.

## Confirmed pilot decision register

### ID-01 — Conversation account boundary

Decision date: April 18, 2026
Status: **Confirmed pilot decision**
Decision: Serve one customer and only that customer's own profile in a
conversation. Do not act on a friend's, spouse's, relative's, or other
person's account even if the caller knows the order details.
Decision owner: Customer Care Operations
Revisit trigger: Approved delegated-access model

### ID-02 — Multiple requests for one verified customer

Decision date: April 18, 2026
Status: **Confirmed pilot decision**
Decision: The same verified customer may make multiple requests during the
conversation; a topic change alone does not require a fresh session.
Decision owner: Customer Care Operations
Revisit trigger: Cross-channel session design

### ID-03 — Identification is the entry step

Decision date: April 21, 2026
Status: **Confirmed pilot decision**
Decision: Identify the customer as the first task in every conversation,
before opening the profile and beginning account-specific service work.
Decision owner: Customer Experience Enablement
Revisit trigger: Approved authenticated-session handoff

### ID-04 — Supported lookup routes

Decision date: April 21, 2026
Status: **Confirmed pilot decision**
Decision: Find the customer by unique account identifier, profile email, or
first name plus last name plus ZIP code.
Decision owner: CRM Operations
Revisit trigger: Approval of an additional identity signal

### ID-05 — Account-identifier ownership match

Decision date: April 24, 2026
Status: **Confirmed pilot decision**
Decision: An account identifier alone does not verify ownership. Match either
the profile email or first name plus last name plus ZIP before proceeding.
Decision owner: Trust and Safety
Revisit trigger: Approved stronger authentication method

### ID-06 — Full profile follows verification

Decision date: April 24, 2026
Status: **Confirmed pilot decision**
Decision: Pull the complete profile only after verification; the profile then
provides orders, addresses, and saved payment methods for service work.
Decision owner: CRM Operations
Revisit trigger: Data-minimization design review

## Decision candidates not approved

### C-01 — Phone-number lookup

Status: Proposed
Rationale under review: Broad historical coverage but inconsistent formatting
Open owner: CRM Operations
Pilot effect: None

### C-02 — Order-number identification

Status: Rejected as an identity route for the pilot
Rationale: Order details can be known by someone other than the profile owner
Pilot effect: None; an order number may be used only after customer identity
work under the approved service flow

### C-03 — Loyalty identifier lookup

Status: Future-state discussion
Rationale under review: Separate data ownership and incomplete account linkage
Pilot effect: None

### C-04 — Authenticated web-session handoff

Status: Future-state discussion
Rationale under review: Token exchange and assurance level not designed
Pilot effect: None

### C-05 — Household delegation

Status: Future-state discussion
Rationale under review: Consent, revocation, minor accounts, and auditability
Pilot effect: None

## Workshop notes

### April 9 — program framing

Attendees: Customer Experience, Customer Care, Digital Product

- The group wants a web-chat pilot before discussing additional channels.
- Contact-reason reporting is too coarse to isolate identity effort.
- Password reset appears frequently in historical labels but belongs to a
  separate program.
- The team requested a broad intake so unresolved dependencies remain visible.

Follow-up: Invite CRM Operations and Trust and Safety.
Owner: Program manager
Due: Complete

### April 14 — CRM inventory

Attendees: CRM Operations, Commerce Platform Architecture, Analytics

- The human search panel exposes more fields than the pilot should use.
- Email quality is believed strong but has not been measured.
- Phone formats differ across source systems.
- Duplicate-profile cleanup remains a manual CRM process.
- API names used in the meeting were placeholders.

Follow-up: Separate approved lookup inputs from fields merely visible in the
existing interface.
Owner: CRM product owner
Due: Complete

### April 18 — care operations session

Attendees: Customer Care, Care Quality, Partner Operations

- Operations selected a one-customer conversation model for the pilot.
- The same customer commonly has more than one order question in a contact.
- Partner queues use different screen arrangements.
- Quality wants the account boundary included in the first rubric draft.
- Delegated access needs a separate policy and was not approved.

Follow-up: Record the session decisions and circulate for Trust and Safety
review.
Owner: Care operations lead
Due: Complete

### April 21 — lookup design

Attendees: CRM Operations, Digital Product, Customer Experience

- The group approved three lookup routes for the initial build.
- Phone number remains a candidate, not an approved route.
- Greeting copy has not been selected.
- The product team asked whether authenticated web context could arrive later.
- Analytics requested lookup-attempt events but supplied no schema.

Follow-up: Document the difference between locating a candidate record and
verifying the customer.
Owner: CRM product owner
Due: Complete

### April 24 — verification and access review

Attendees: Trust and Safety, CRM Operations, Security Architecture

- An account identifier alone was rejected as proof of profile ownership.
- The working group approved email or first name, last name, and ZIP as the
  match for that lookup route.
- Full-profile access must follow verification.
- Retry counts and failure escalation remain unresolved.
- Security requested a later threat-model workshop.

Follow-up: Add the confirmed decisions to the register without filling open
failure-handling fields.
Owner: Trust and Safety lead
Due: Complete

### April 29 — build handoff preparation

Attendees: Customer Experience, Solutions Engineering, Care Quality

- Preserve the difference between confirmed decisions and planning context.
- Keep phone, order number, loyalty ID, and web-session proposals visibly
  unapproved.
- Do not invent timeout, retry, lockout, or transfer behavior.
- Include the incomplete system inventory for discovery planning.
- Use the decision register as the handoff source of record.

Follow-up: Share the intake with the agent-build team.
Owner: Customer Experience Enablement
Due: Before kickoff

## Action tracker

| Work item | Customer owner | Program owner | Status | Latest note |
|---|---|---|---|---|
| Confirm profile-search API | Commerce Platform | Ian Mercer | In progress | Design review pending |
| Supply sandbox tenant | Commerce Platform |  | Open | Request submitted |
| Define failed-verification handling | Trust and Safety | Asha Venkat | Open | Separate workshop needed |
| Select greeting copy | Digital Product | Noelle Park | In progress | Three drafts exist |
| Define audit-event schema | Security | Darius Cole | Open | Threat model first |
| Confirm privacy review date | Privacy |  | Not started | Owner unassigned |
| Establish lookup baseline | CX Analytics | Leo Brandt | Blocked | Event definitions missing |
| Draft quality rubric | Care Quality | Keisha Morgan | In progress | Decisions ID-01 to ID-06 included |
| Inventory partner-screen differences | Vendor Management |  | Open | Site owners not confirmed |
| Review Spanish demand | Customer Experience |  | Proposed | After pilot scope freeze |
| Evaluate phone lookup | CRM Operations | Ian Mercer | Deferred | Not a pilot dependency |
| Design delegated access | Trust and Safety |  | Deferred | Future program |

## Open questions and parking lot

- What event should mark successful verification?
- What should happen after a verification mismatch?
- How many retries, if any, are appropriate?
- Which assisted-support queue would receive a failed-verification contact?
- Can the chat surface safely pass authenticated session context in a later
  phase?
- Which profile fields should be omitted from the automated response?
- How long should lookup and access events be retained?
- How should duplicate profiles be surfaced?
- Does the pilot need international postal-code handling?
- How will partner operations receive training updates?
- What sample size is needed for the first quality readout?
- Who approves any expansion beyond web chat?
- When should Loyalty and Fraud Operations join discovery?

## Draft history

Version 0.1 — Account snapshot and contact landscape
Version 0.2 — Added CRM field inventory and integration questions
Version 0.3 — Added session-model workshop notes
Version 0.4 — Added approved lookup routes
Version 0.5 — Added verification and profile-access decisions
Version 0.6 — Separated confirmed decisions from proposals and open questions
Next update — After failed-verification and API-design workshops
