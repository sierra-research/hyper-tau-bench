# Rewrite this synthetic Slack MCP capture for conversational realism

The complete input is in the attached or repository file:

`data/tau2/hyper/sops/airline_plus/sections/modifying_reservation/slack_mcp_dump_001/reservation_servicing_slack_mcp_capture.json`

Read that entire JSON file before editing. It is the source capture; do not
reconstruct it from the summaries below. If you cannot access the repository,
stop and ask for `reservation_servicing_slack_mcp_capture.json` to be attached.

You have access to real workplace Slack messages. Use that access only to learn
aggregate communication patterns: message length, informality, threading,
acknowledgements, disagreement, follow-up, reactions, and how teams reopen a
decision after new evidence appears.

Do not quote or closely paraphrase any real message. Do not reuse real names,
company names, customer information, URLs, project names, identifiers, or
confidential details. The result must remain wholly fictional. This is a style
edit of synthetic benchmark data, not a request to redesign the policy.

## Your task

Rewrite the human-authored Slack message text so it reads like a plausible
export from a cross-functional product project. Preserve every policy detail,
the chronology of decision-making, and the MCP envelope.

You may change:

- message `text`;
- reaction names, counts, and fictional user membership; and
- minor non-policy wording in MCP text-result summaries.

You must not add, remove, reorder, or merge any calls, threads, or messages.

## Structural invariants

- Return one complete, valid JSON object in the same Slack MCP tool-call-log
  format.
- Preserve exactly 22 tool calls, including 20 thread-reply calls.
- Preserve exactly 20 distinct threads and 155 distinct thread messages.
- Preserve every `call_id`, JSON-RPC method, tool name, tool argument,
  timestamp, `thread_ts`, channel, user, permalink, workspace field, and cursor.
- Keep every root message's `reply_count` consistent with its replies.
- Preserve the intentional retrieval overlap: search, channel history, and
  thread replies can repeat the same root message. Repeated copies of a message
  must receive the same rewritten text.
- Meridian Airlines is the fictional first-party airline. Project Atlas is its
  internal project. Do not rename either.

## Exactly three current policy facts must survive

The final governing decision must still establish all and only these facts:

1. Customer service may update an existing passenger's name or date of birth.
2. Passenger count on an existing reservation cannot be changed.
3. A supervisor cannot override the passenger-count restriction.

Do not introduce policy about booking a flight, reservation lookup, flight or
cabin changes, pricing, payment methods, certificates, gift cards, baggage,
insurance, cancellation, refunds, or compensation. Operational or technical
defects may motivate a decision, but must not accidentally establish another
airline rule.

## Required decision arc

`D1` through `D6` are author-side labels for checking the arc. They must not
appear anywhere in the rewritten Slack capture. Refer to prior choices by their
substance, timing, implementation, or linked evidence instead. Do not make key
facts visually obvious with bolding, labels, or unnatural summary language.

- D1: the team genuinely agrees that all passenger fields are view-only. A
  later thread reopens that settled choice after contact-volume evidence shows
  routine passenger corrections drive unexpectedly high transfers.
- D2: the team then genuinely agrees to allow minor name corrections and
  pre-check-in removal while keeping date of birth locked. A later identity
  review confirms verified DOB correction is permissible, and Engineering
  finds a supervisor-scoped traveler operation, so D2 is reopened.
- D3: the team genuinely agrees to allow verified name and DOB corrections and
  supervisor additions or removals before check-in. A later non-atomic
  inventory defect affecting additions reopens D3.
- D4: the team genuinely agrees to keep name and DOB corrections, prohibit
  additions, and allow ordinary removals. A later defect shows removal can
  orphan ancillary records, so D4 is reopened.
- D5: the team genuinely agrees to prohibit general passenger-count changes
  while retaining a supervisor-only duplicate-removal exception. A later audit
  replay shows the durable event cannot distinguish that exception from a
  prohibited count change, so D5 is reopened.
- D6: the team genuinely agrees to the final rule: name or DOB may be updated;
  passenger count cannot change; supervisors have no exception. This is the
  current governing decision.

Every D1-D5 decision must feel settled at the time. Its reopening must happen
later, in a separate thread, because of genuinely new information—not because
someone simply restates an objection that was already unresolved.

## Stakeholder continuity

Keep the existing fictional people and roles:

- Rina Mehta — Product
- Theo Beaumont — Operations
- Marcus Bell — Engineering
- Priya Nair — Compliance
- Elena Marquez — QA
- Maya Wei — project coordination

Each decision D1-D6 must preserve verifiable agreement from Product,
Operations, Engineering, Compliance, and QA. Express agreement naturally and
with varied language; avoid giving every person the repeated phrase
“[Function] approves.” Maya may summarize closure after those five signals.

## Thread-by-thread authoring map

Keep each thread in its existing position and preserve its purpose:

1. `kickoff_owners` — distractor: ownership and working-team logistics.
2. `weekly_cadence` — distractor: recurring meeting timing.
3. `initial_options` — deliberation before D1; no decision.
4. `decision_1_view_only` — establishes D1.
5. `reopen_1_contact_volume` — new volume evidence reopens D1.
6. `uat_access` — distractor: test-environment access.
7. `correction_copy_review` — distractor: passenger/traveler terminology only.
8. `decision_2_limited_corrections` — establishes D2.
9. `reopen_2_identity_findings` — identity guidance and API discovery reopen D2.
10. `reservation_api_review` — technical deliberation before D3; no decision.
11. `decision_3_supervisor_count` — establishes D3.
12. `dashboard_colors` — distractor: reporting colors.
13. `reopen_3_inventory_defect` — addition/inventory defect reopens D3.
14. `decision_4_removal_only` — establishes D4.
15. `reopen_4_ancillary_defect` — removal/ancillary defect reopens D4.
16. `duplicate_exception_review` — deliberation before D5; no decision.
17. `decision_5_duplicate_exception` — establishes D5.
18. `launch_screenshots` — distractor: launch screenshots.
19. `reopen_5_audit_replay` — audit replay evidence reopens D5.
20. `decision_6_final` — establishes final D6.

Distractor threads should remain believable project context and should not
contain any of the three policy facts. Deliberation and defect threads may
discuss proposals or implementation evidence, but must not sound authoritative.

## Realism requirements

- Use a realistic distribution of lengths and tones rather than making every
  message a polished memo.
- Include plausible contractions, sentence fragments, callbacks, short
  acknowledgements, follow-up questions, corrections, and occasional
  clarification where appropriate.
- Give the recurring participants distinguishable voices without caricature.
- Do not make every root message perfectly self-contained.
- Do not bold, headline, or otherwise emphasize the important policy language.
- Do not use benchmark-author language such as “authoritative fact,” “gold
  answer,” “final policy representation,” or “this thread is a distractor.”
- Do not repeat a fact merely to help a reader find it. Preserve only repetition
  caused by the MCP retrieval overlap.
- Keep the chronology coherent: nobody should refer to evidence or a decision
  before it exists.

## Required output

Return exactly these three sections:

1. `REWRITTEN_CAPTURE`: one fenced `json` block containing the full rewritten
   capture. Do not truncate it and do not use ellipses.
2. `SEMANTIC_AUDIT`: a concise table that identifies where D1-D6 is established,
   where D1-D5 is reopened and by what new evidence, how each required
   stakeholder's agreement remains observable, and which exact output message
   establishes each of the three final facts. Report the tool-call, thread, and
   message counts.
3. `REALISM_NOTES`: a short description of the aggregate Slack patterns you
   applied. Confirm that you did not quote real messages or reuse real
   identities or confidential details.

Before returning, check that the JSON parses, duplicate retrieval copies are
consistent, all six decisions and five reopenings remain recoverable, and no
new airline policy was introduced.
