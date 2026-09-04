# Conversational-realism review: NorthStar Beacon Slack MCP capture

You are reviewing a fully synthetic Slack MCP tool-call capture for conversational realism. The capture is the adjacent repository file `beacon_servicing_slack_mcp_capture.json` (attach or open it alongside this prompt).

## Fiction

Workspace: NorthStar Outfitters (fictional retailer), Project Beacon — a cross-functional program standing up an assisted customer-servicing channel. All people, channels, ids, and events are fictional. February to May 2026, eight channels, twelve recurring participants.

## What must survive any edit

The capture carries four decision arcs. Only each arc's final decision thread states policy that downstream evaluation depends on; the exact phrases below must remain verbatim, each appearing exactly where it does now:

- `accepted_cancel_reason_no_longer_needed`: "no longer needed still counts when the customer words it their own way"
- `accepted_cancel_reason_ordered_by_mistake`: "ordered by mistake is the second accepted reason"
- `unaccepted_cancel_reasons_decline_and_offer_transfer`: "anything outside those two, the agent explains we cannot take that reason and offers to bring in a person"
- `return_refund_destination_original_or_existing_gift_card`: "lands on the original payment method or a gift card already saved on the profile — already saved meaning the card was on the profile before the return request was opened; a card added mid-conversation does not qualify"
- `return_refund_destination_disallowed_options`: "no new gift cards, no different card, and no PayPal that was not on the order"
- `exchange_refund_destination_any_saved_payment_method`: "can land on any payment method already saved on the profile, original or not, and the method picked is recorded on the exchange at submission; it does not change after that"
- `cannot_change_order_quantity`: "does not change item quantities on an order"
- `cannot_split_shipments`: "does not split an order into separate shipments"
- `cannot_change_profile_email`: "the email address on a profile cannot be changed by customer care"

Every superseded decision thread likewise carries one dated historical phrase (listed in `eval_manifest.json`) whose wording must survive. Dates, thread ordering, channel placement, user attribution, and reaction placement are all load-bearing; do not move messages between threads or reorder replies.

Several threads state policy for an explicitly different scope — the wholesale pilot book, a self-expiring promo weekend, the archived predecessor program. Their scope qualifiers (wording like 'wholesale accounts only' or 'expires on its own') are load-bearing and must survive any rewrite. Two proposal threads end parked with no decision; they must stay unresolved. The capture also contains unthreaded channel-surface messages, three thread roots whose replies were never fetched (their reply counts are intentional), a misspelled first search with zero hits, and two history calls that fail on an archived and a private channel — all deliberate; do not repair them.

## Decision arcs (author-side summary, never to appear in the capture)

### cancellation_reasons

- 2026-02-06 `decision_cr1_freetext` (superseded): Assisted cancellations record the reason as free text for the pilot month.
- 2026-02-17 `decision_cr2_picklist` (superseded): Cancellation reasons move to a five-option pick list with a note only on other.
- 2026-02-26 `decision_cr3_pricematch` (superseded): Cheaper-elsewhere cancellations get a one-per-order price-match counteroffer.
- 2026-03-16 `decision_cr4_pause_cheaper` (superseded): Counteroffer removed; cheaper-elsewhere cancels pause to an escalation queue pending the abuse review.
- 2026-03-30 `decision_cr5_trim_three` (superseded): Reason list trimmed to three; cheaper-elsewhere and other removed after the risk review.
- 2026-04-08 `decision_cr6_reroute_slow` (superseded): Shipping-too-slow moves to the carrier escalation flow; agents match the two remaining reasons verbatim.
- 2026-04-20 `decision_cr7_paraphrase` (superseded): Verbatim matching dropped; agents map customer wording to the nearest of the two reasons.
- 2026-04-29 `decision_cr8_final` (FINAL): Two accepted reasons — no longer needed (customer phrasing counts) and ordered by mistake; anything else is declined with an offer to bring in a person.

### refund_destinations

- 2026-02-12 `decision_rd1_discretion` (superseded): Pilot month: refunds may go to any saved instrument the customer picks, with weekly risk review.
- 2026-03-05 `decision_rd2_original_only` (superseded): Refunds restricted to the original payment method only.
- 2026-03-26 `decision_rd3_checks` (superseded): Dead-card refunds switch to mailed checks from a weekly finance batch.
- 2026-04-16 `decision_rd4_interim` (superseded): Checks withdrawn; original method only while a store-side fallback is designed, dead-card refunds hold in a queue.
- 2026-05-04 `decision_rd5_final` (FINAL): Return refunds land on the original payment method or a gift card already saved on the profile; no new gift cards, different cards, or off-order PayPal; exchange cash-outs are exempt — any saved payment method the customer picks.

### quantity_and_splits

- 2026-02-20 `decision_qs1_split_pilot` (superseded): Six-week pilot: agents may split a delayed line into its own shipment.
- 2026-03-11 `decision_qs2_single_warehouse` (superseded): Split pilot narrowed to single-warehouse, same-day-dispatch orders; quantity-trim prototype commissioned.
- 2026-04-02 `decision_qs3_no_quantity` (superseded): Quantity edits ruled out after the prototype readout; gated split pilot runs one final cycle.
- 2026-04-27 `decision_qs4_final` (FINAL): Customer care neither changes item quantities nor splits orders into separate shipments; quantity asks become cancel-and-reorder, delay asks go to the carrier flow.

### profile_email

- 2026-02-27 `decision_em1_workshop` (superseded): Verified typo-grade email corrections allowed in the assisted flow after the identity check.
- 2026-03-20 `decision_em2_pause` (superseded): Email corrections on hold; requests queue to the specialist desk during the account-security review.
- 2026-04-10 `decision_em3_final` (FINAL): Profile email cannot be changed by customer care.

## Thread map

1. `kickoff_owner_map` — #beacon-delivery, 2026-02-03, distractor
2. `cancel_reason_prelim` — #beacon-order-servicing, 2026-02-04, deliberation
3. `decision_cr1_freetext` — #beacon-order-servicing, 2026-02-06, decision
4. `uat_seed_orders` — #beacon-uat, 2026-02-09, distractor
5. `refund_dest_prelim` — #beacon-payments-risk, 2026-02-10, deliberation
6. `decision_rd1_discretion` — #beacon-payments-risk, 2026-02-12, decision
7. `reopen_cr1_reporting` — #beacon-reporting, 2026-02-13, reopening
8. `decision_cr2_picklist` — #beacon-order-servicing, 2026-02-17, decision
9. `office_plants` — #beacon-delivery, 2026-02-18, distractor
10. `split_pilot_prelim` — #beacon-fulfillment-scope, 2026-02-19, deliberation
11. `decision_qs1_split_pilot` — #beacon-fulfillment-scope, 2026-02-20, decision
12. `reopen_cr2_cheaper_volume` — #beacon-order-servicing, 2026-02-24, reopening
13. `staging_down` — #beacon-uat, 2026-02-25, distractor
14. `decision_cr3_pricematch` — #beacon-order-servicing, 2026-02-26, decision
15. `decision_em1_workshop` — #beacon-identity-profile, 2026-02-27, decision
16. `dashboard_palette` — #beacon-reporting, 2026-03-02, distractor
17. `reopen_rd1_rerouting` — #beacon-payments-risk, 2026-03-03, reopening
18. `csv_export_question` — #beacon-reporting, 2026-03-04, distractor
19. `decision_rd2_original_only` — #beacon-payments-risk, 2026-03-05, decision
20. `uat_access_sync` — #beacon-uat, 2026-03-06, distractor
21. `reopen_qs1_fanout` — #beacon-fulfillment-scope, 2026-03-09, reopening
22. `wholesale_pilot_scope` — #beacon-wholesale-pilot, 2026-03-10, near_miss
23. `decision_qs2_single_warehouse` — #beacon-fulfillment-scope, 2026-03-11, decision
24. `reopen_cr3_margin` — #beacon-reporting, 2026-03-12, reopening
25. `pto_handoff` — #beacon-delivery, 2026-03-13, distractor
26. `decision_cr4_pause_cheaper` — #beacon-order-servicing, 2026-03-16, decision
27. `glossary_terms` — #beacon-enablement, 2026-03-17, distractor
28. `reopen_em1_takeover` — #beacon-identity-profile, 2026-03-18, reopening
29. `promo_split_exception` — #beacon-fulfillment-scope, 2026-03-19, near_miss
30. `decision_em2_pause` — #beacon-identity-profile, 2026-03-20, decision
31. `reopen_rd2_dead_cards` — #beacon-payments-risk, 2026-03-23, reopening
32. `campaign_loadtest` — #beacon-uat, 2026-03-24, distractor
33. `ledger_archive_question` — #beacon-order-servicing, 2026-03-25, near_miss
34. `decision_rd3_checks` — #beacon-payments-risk, 2026-03-26, decision
35. `printer_toner` — #beacon-enablement, 2026-03-27, distractor
36. `decision_cr5_trim_three` — #beacon-order-servicing, 2026-03-30, decision
37. `parking_repaving` — #beacon-delivery, 2026-03-31, distractor
38. `reopen_qs2_carrier_sla` — #beacon-fulfillment-scope, 2026-04-01, reopening
39. `decision_qs3_no_quantity` — #beacon-fulfillment-scope, 2026-04-02, decision
40. `retro_scheduling` — #beacon-delivery, 2026-04-03, distractor
41. `reopen_cr5_slow_shipping` — #beacon-order-servicing, 2026-04-06, reopening
42. `vip_quantity_proposal` — #beacon-fulfillment-scope, 2026-04-08, dead_proposal
43. `decision_cr6_reroute_slow` — #beacon-order-servicing, 2026-04-08, decision
44. `snack_budget` — #beacon-delivery, 2026-04-09, distractor
45. `decision_em3_final` — #beacon-identity-profile, 2026-04-10, decision
46. `reopen_rd3_check_fraud` — #beacon-payments-risk, 2026-04-13, reopening
47. `wholesale_cancel_handling` — #beacon-wholesale-pilot, 2026-04-14, near_miss
48. `dashboard_timeout` — #beacon-reporting, 2026-04-15, distractor
49. `reopen_cr6_verbatim` — #beacon-uat, 2026-04-16, reopening
50. `decision_rd4_interim` — #beacon-payments-risk, 2026-04-16, decision
51. `wellness_week` — #beacon-enablement, 2026-04-17, distractor
52. `goodwill_giftcard_proposal` — #beacon-payments-risk, 2026-04-20, dead_proposal
53. `decision_cr7_paraphrase` — #beacon-order-servicing, 2026-04-20, decision
54. `training_screenshots` — #beacon-enablement, 2026-04-21, distractor
55. `wholesale_credit_memo` — #beacon-wholesale-pilot, 2026-04-22, near_miss
56. `reopen_cr7_drift` — #beacon-reporting, 2026-04-23, reopening
57. `badge_reader` — #beacon-enablement, 2026-04-24, distractor
58. `decision_qs4_final` — #beacon-fulfillment-scope, 2026-04-27, decision
59. `decision_cr8_final` — #beacon-order-servicing, 2026-04-29, decision
60. `carrier_webinar` — #beacon-fulfillment-scope, 2026-05-01, distractor
61. `decision_rd5_final` — #beacon-payments-risk, 2026-05-04, decision
62. `tshirt_sizes` — #beacon-delivery, 2026-05-05, distractor
63. `survey_routing` — #beacon-reporting, 2026-05-06, distractor
64. `offsite_poll` — #beacon-delivery, 2026-05-07, distractor
65. `launch_day_warroom` — #beacon-delivery, 2026-05-11, distractor
66. `launch_readout` — #beacon-delivery, 2026-05-12, distractor
67. `identity_mismatch_question` — #beacon-order-servicing, 2026-05-26, deliberation

## Review instructions

1. Read every thread as a human Slack reader would. Flag any message that sounds authored-to-teach rather than written-at-work: narrator summaries, guardrails addressed to a reader, decisions that announce their own status in the record.
2. Check voice consistency per participant and length distribution (one-liners through occasional long context dumps).
3. Check mechanical realism: timestamps in business hours, plausible reply pacing, reactions where a team would actually react.
4. You may use real Slack experience only to infer aggregate communication patterns. Do not copy or closely paraphrase real messages, and do not introduce real people, companies, URLs, or confidential details.
5. Output a semantic audit: a table of (thread key, message index, issue, suggested rewrite) covering every flagged message, followed by an overall pass/fail realism verdict. Rewrites must preserve the protected phrases, dates, and speaker assignments above.

The capture contains 76 MCP calls covering 67 threads. This prompt is author-side material: never copy it, the arc summaries, or the thread map into any delivered artifact.
