# Changelog

## 1.0.2 — Banking construction scoring correction

**Scoring changes:** Hyper-τ `banking_knowledge` scores produced with 1.0.1
and 1.0.2 are not directly comparable. Other domains and standard τ³ banking
evaluation retain their grading behavior. The 53 construction tasks and
held-out case definitions are unchanged.

### Fixed

Construction DB comparison already excluded `agent_discoverable_tools` from
the agent DB view, but still hashed it in the user DB view. Banking shares one
DB between those toolkits. Reference discoverable calls wrote audit rows that
an otherwise correct constructed agent did not produce, so customer-state
comparison incorrectly failed. Both views now exclude this one reference
wrapper audit table, before ID normalization. Business state, user-tool state,
identity verification, and the Client REST trace grounding check remain graded.
The shared helper covers both text and full-duplex environment evaluators.

### Verification and impact

A deterministic replay at pre-fix commit
`6e9f34c685d40fa7a9f5935d8970af6fd9d5f118` executes each banking golden
trajectory twice: once through the reference discoverable wrapper and once
through the same underlying banking operations without its agent audit writes.
All 144 agent DB comparisons match. Of the 86 user DB comparisons that fail,
85 are DB-graded and therefore lose reward; the remaining case is action-graded.
After this fix, all 144 DB comparisons match on both views. No previously
matching DB comparison becomes a mismatch.

Weighting the 85 blocked cases by each of the 35 banking construction tasks'
held-out sets gives a **37.58% banking mean ceiling** under the old scorer,
before any other failures or budget penalties. Assuming perfect scores on the
18 non-banking tasks gives a **58.78% overall ceiling** from this defect alone.
The flat case fraction, 59/144 = 40.97%, is not the banking leaderboard mean.
These are defect-only upper bounds, not measured model performance.

Regression coverage includes all 144 reference final states, shared and
separate DB instances, both evaluator modes, standard-mode audit comparisons,
unchanged input DBs, and rejection of wrong balances, missing accounts, and
user-tool state mismatches. Existing grounding tests continue to require the
correct reads and writes. Run:

```bash
uv run pytest tests/test_hyper/test_banking_construction_grading.py \
  tests/test_hyper/test_construction_eval.py \
  tests/test_hyper/test_grounding_check.py \
  tests/test_hyper/test_recording.py
```

This verifies the reported scoring defect, not every policy/golden-action
choice or the issue author's private 175-build / 939-conversation rescore.

### Versioning and historical scores

- Package and lockfile version: **1.0.2**. New Hyper-τ checkpoints and final
  recordings include `scorer_version`; older recordings remain readable and
  must not be assumed to use the corrected scorer when that field is absent.
- Preserve existing published scores as historical release-v1 results.
  Re-score saved construction submissions with the 1.0.2 scorer before
  publishing corrected scores, recording the scorer version and source commit.
  Keep the original task definitions, model configuration, and credit budgets.
- If replayable submissions or complete scoring inputs are unavailable, rerun
  the sealed evaluation and identify it as a new evaluation. Aggregate scores
  alone cannot recover the corrected result. Do not replace leaderboard values
  with an estimated uplift or mix old and corrected banking scores.
- Pin the pre-fix commit above to reproduce historical scoring. This PR updates
  the source version; publishing a release/tag follows repository maintainer
  review and merge.

Reference: [hyper-tau-bench issue #3](https://github.com/sierra-research/hyper-tau-bench/issues/3).
