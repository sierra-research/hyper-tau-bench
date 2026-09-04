# Release task set manifest

The curated τ^τ release set: 53 construction tasks across four source
domains — 35 banking_knowledge, 6 airline_plus, 6 retail_plus, 6 telecom. Task ids are sequential within
this folder; the digits carry no configuration semantics. The task JSON
files are the frozen executable contract: they define everything a run
needs and never carry results.

Each task combines a subset of these axes:

- **Evidence variant** (`sop_variant_manifest_path`) — which compiled
  evidence bundle the sandbox kit materializes: core packs, hard packs with
  deeper per-fact representation arcs, and hard+client packs where part of
  the knowledge is held by the Client and must be elicited. Banking tasks
  marked `kb` ship the raw knowledge-base corpus instead of a compiled
  bundle.
- **Performance tier** (`performance_profile`) — the allowed inner-agent
  model menu and its mean-credit budget, written out in full in each task
  file (the tier name is informational).
- **Seeded starting workspace** (`starting_workspace_path`) — brownfield
  builds start from a pinned pre-existing implementation instead of an
  empty scaffold.
- **Client API defects** (`client_api_deployment_manifest`) — the kit's
  REST deployment carries deterministic defects (pagination limits,
  transient failures, projection lag, contract mismatches) the Developer
  must handle.
- **Live experiment** (`live_experiment_task_ids`) — the Developer may run
  `run_live_experiment()` once against a held-out pilot-traffic partition.
- **Response phrasing** (`composition_pipeline`) — the built agent is
  additionally graded on response-phrasing conformance.

| Task | Domain | Evidence variant | Seeded | API defects | Live exp. | Phrasing | Tier |
|---|---|---|:-:|:-:|:-:|:-:|---|
| `001_airline_plus_construction_core_evidence_all_defects_live_experiment_performance_medium` | airline_plus | `core_evidence_bundle_001` |  | ✓ | ✓ |  | medium |
| `002_airline_plus_construction_core_evidence_seeded_performance_hard` | airline_plus | `core_evidence_bundle_001` | ✓ |  |  |  | hard |
| `003_airline_plus_construction_core_evidence_hard_all_defects_performance_easy` | airline_plus | `core_evidence_bundle_hard_001` |  | ✓ |  |  | easy |
| `004_airline_plus_construction_core_evidence_hard_client_performance_medium` | airline_plus | `core_evidence_bundle_hard_client_001` |  |  |  |  | medium |
| `005_airline_plus_construction_core_evidence_hard_client_seeded_all_defects_performance_hard` | airline_plus | `core_evidence_bundle_hard_client_001` | ✓ | ✓ |  |  | hard |
| `006_airline_plus_construction_core_evidence_response_phrasing_performance_medium` | airline_plus | `core_evidence_bundle_001` |  |  |  | ✓ | medium |
| `007_retail_plus_construction_core_evidence_seeded_all_defects_performance_easy` | retail_plus | `core_evidence_bundle_001` | ✓ | ✓ |  |  | easy |
| `008_retail_plus_construction_core_evidence_performance_hard` | retail_plus | `core_evidence_bundle_001` |  |  |  |  | hard |
| `009_retail_plus_construction_core_evidence_hard_seeded_live_experiment_performance_medium` | retail_plus | `core_evidence_bundle_hard_001` | ✓ |  | ✓ |  | medium |
| `010_retail_plus_construction_core_evidence_hard_client_all_defects_performance_medium` | retail_plus | `core_evidence_bundle_hard_client_001` |  | ✓ |  |  | medium |
| `011_retail_plus_construction_core_evidence_hard_client_all_defects_performance_hard` | retail_plus | `core_evidence_bundle_hard_client_001` |  | ✓ |  |  | hard |
| `012_retail_plus_construction_core_evidence_hard_client_all_defects_response_phrasing_performance_hard` | retail_plus | `core_evidence_bundle_hard_client_001` |  | ✓ |  | ✓ | hard |
| `013_telecom_construction_core_evidence_seeded_all_defects_performance_medium` | telecom | `core_evidence_bundle_001` | ✓ | ✓ |  |  | medium |
| `014_telecom_construction_core_evidence_seeded_performance_hard` | telecom | `core_evidence_bundle_001` | ✓ |  |  |  | hard |
| `015_telecom_construction_core_evidence_hard_all_defects_performance_medium` | telecom | `core_evidence_bundle_hard_001` |  | ✓ |  |  | medium |
| `016_telecom_construction_core_evidence_hard_client_all_defects_performance_easy` | telecom | `core_evidence_bundle_hard_client_001` |  | ✓ |  |  | easy |
| `017_telecom_construction_core_evidence_hard_client_live_experiment_performance_hard` | telecom | `core_evidence_bundle_hard_client_001` |  |  | ✓ |  | hard |
| `018_telecom_construction_core_evidence_hard_client_response_phrasing_performance_medium` | telecom | `core_evidence_bundle_hard_client_001` |  |  |  | ✓ | medium |
| `019_banking_knowledge_construction_evidence_corpus_hard_live_experiment` | banking_knowledge | `all_sections_evidence_corpus_hard_001` |  |  | ✓ |  | easy |
| `020_banking_knowledge_construction_evidence_corpus_hard_performance_medium` | banking_knowledge | `all_sections_evidence_corpus_hard_001` |  |  |  |  | medium |
| `021_banking_knowledge_construction_evidence_corpus_hard_performance_hard` | banking_knowledge | `all_sections_evidence_corpus_hard_001` |  |  |  |  | hard |
| `022_banking_knowledge_construction_kb_performance_medium` | banking_knowledge | `kb` |  |  |  |  | medium |
| `023_banking_knowledge_construction_kb_performance_hard` | banking_knowledge | `kb` |  |  |  |  | hard |
| `024_banking_knowledge_construction_client_api_cards_super` | banking_knowledge | `core_evidence_bundle_001` |  |  |  |  | easy |
| `025_banking_knowledge_construction_client_api_cards_super_performance_medium` | banking_knowledge | `core_evidence_bundle_001` |  |  |  |  | medium |
| `026_banking_knowledge_construction_client_api_cards_super_performance_hard` | banking_knowledge | `core_evidence_bundle_001` |  |  |  |  | hard |
| `027_banking_knowledge_construction_client_api_deposits_business_super` | banking_knowledge | `core_evidence_bundle_001` |  |  |  |  | easy |
| `028_banking_knowledge_construction_client_api_deposits_business_super_kb_performance_medium` | banking_knowledge | `kb` |  |  |  |  | medium |
| `029_banking_knowledge_construction_client_api_deposits_business_super_live_experiment_performance_hard` | banking_knowledge | `core_evidence_bundle_001` |  |  | ✓ |  | hard |
| `030_banking_knowledge_construction_client_api_card_selection` | banking_knowledge | `core_evidence_bundle_001` |  |  |  |  | easy |
| `031_banking_knowledge_construction_client_api_card_selection_seeded_performance_medium` | banking_knowledge | `core_evidence_bundle_001` | ✓ |  |  |  | medium |
| `032_banking_knowledge_construction_client_card_selection_client_performance_hard` | banking_knowledge | `card_selection_sections_hard_client_001` |  |  |  |  | hard |
| `033_banking_knowledge_construction_client_card_selection_client_seeded_performance_hard` | banking_knowledge | `card_selection_sections_hard_client_001` | ✓ |  |  |  | hard |
| `034_banking_knowledge_construction_client_api_deposit_opening` | banking_knowledge | `core_evidence_bundle_001` |  |  |  |  | easy |
| `035_banking_knowledge_construction_client_api_deposit_opening_performance_hard` | banking_knowledge | `core_evidence_bundle_001` |  |  |  |  | hard |
| `036_banking_knowledge_construction_client_deposit_opening_client` | banking_knowledge | `deposit_opening_sections_hard_client_001` |  |  |  |  | easy |
| `037_banking_knowledge_construction_client_deposit_opening_client_seeded_performance_medium` | banking_knowledge | `deposit_opening_sections_hard_client_001` | ✓ |  |  |  | medium |
| `038_banking_knowledge_construction_client_api_deposit_services_seeded_performance_medium` | banking_knowledge | `core_evidence_bundle_001` | ✓ |  |  |  | medium |
| `039_banking_knowledge_construction_client_api_deposit_services_response_phrasing_performance_medium` | banking_knowledge | `core_evidence_bundle_001` |  |  |  | ✓ | medium |
| `040_banking_knowledge_construction_client_api_deposit_services_performance_hard` | banking_knowledge | `core_evidence_bundle_001` |  |  |  |  | hard |
| `041_banking_knowledge_construction_client_deposit_services_client_performance_hard` | banking_knowledge | `deposit_services_sections_hard_client_001` |  |  |  |  | hard |
| `042_banking_knowledge_construction_client_api_card_servicing` | banking_knowledge | `core_evidence_bundle_001` |  |  |  |  | easy |
| `043_banking_knowledge_construction_client_card_servicing_client_seeded_performance_medium` | banking_knowledge | `card_servicing_sections_hard_client_001` | ✓ |  |  |  | medium |
| `044_banking_knowledge_construction_client_card_servicing_client_response_phrasing_performance_medium` | banking_knowledge | `card_servicing_sections_hard_client_001` |  |  |  | ✓ | medium |
| `045_banking_knowledge_construction_client_card_servicing_client_performance_hard` | banking_knowledge | `card_servicing_sections_hard_client_001` |  |  |  |  | hard |
| `046_banking_knowledge_construction_client_api_business_seeded_performance_medium` | banking_knowledge | `core_evidence_bundle_001` | ✓ |  |  |  | medium |
| `047_banking_knowledge_construction_client_api_business_performance_hard` | banking_knowledge | `core_evidence_bundle_001` |  |  |  |  | hard |
| `048_banking_knowledge_construction_client_business_client` | banking_knowledge | `business_sections_hard_client_001` |  |  |  |  | easy |
| `049_banking_knowledge_construction_client_business_client_performance_hard` | banking_knowledge | `business_sections_hard_client_001` |  |  |  |  | hard |
| `050_banking_knowledge_construction_client_api_debit_security` | banking_knowledge | `core_evidence_bundle_001` |  |  |  |  | easy |
| `051_banking_knowledge_construction_client_api_debit_security_seeded_performance_hard` | banking_knowledge | `core_evidence_bundle_001` | ✓ |  |  |  | hard |
| `052_banking_knowledge_construction_client_debit_security_client_seeded_performance_medium` | banking_knowledge | `debit_security_sections_hard_client_001` | ✓ |  |  |  | medium |
| `053_banking_knowledge_construction_client_debit_security_client_response_phrasing_performance_medium` | banking_knowledge | `debit_security_sections_hard_client_001` |  |  |  | ✓ | medium |
