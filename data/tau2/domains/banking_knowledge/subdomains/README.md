# Banking subdomains

Journey-scoped slices of the `banking_knowledge` domain, packaged as
policy-embedding domains in the style of retail/airline/telecom: the agent
prompt inlines each subdomain's knowledge-base documents in full, and no
retrieval tools (`KB_search*`, grep, shell) are exposed. The transactional
DB, banking toolkits, user tools, and task definitions are shared with
`banking_knowledge` — a subdomain only scopes which tasks run and which
documents the policy carries.

Run one like any other domain:

```
tau2 run --domain banking_card_selection ...
```

| domain | journeys (hyper sections) |
|---|---|
| `banking_deposit_opening` | personal checking/savings opening + Green checking FAQ |
| `banking_deposit_services` | APY boosts, ATM rebates, checking referrals, mobile deposit, direct deposit delays |
| `banking_card_selection` | credit card application/recommendation, rewards & promos, cash-back disputes, card referrals |
| `banking_card_servicing` | transaction disputes, CLIs, declines/incidents, replacements, account services, closure/retention |
| `banking_business` | business checking/savings opening promos, business credit card selection |
| `banking_debit_security` | debit lost/stolen/freeze/replace, debit disputes/declines/PIN, account closure, transfer/recovery boundaries |

## manifest.json

Generated — do not edit by hand. Regenerate after editing banking tasks or
the hyper banking section schemas:

```
python -c 'from tau2.domains.banking_knowledge.subdomains import write_manifest; write_manifest()'
```

`tests/test_domains/test_banking_knowledge/test_subdomains.py` fails when the
committed manifest drifts from a recompute.

Membership rules (implemented in
`src/tau2/domains/banking_knowledge/subdomains.py`):

- The section grouping (`SUBDOMAIN_SECTIONS`) is authoritative and hand-curated
  along journey-trio lines.
- Each task is assigned to exactly one subdomain: the one owning its *primary
  section* — the section whose source documents overlap the task's
  `required_documents` the most (ties break toward the section with fewer
  source documents, then alphabetically).
- A subdomain's document set is the union of its sections' source documents
  plus every member task's required documents. Shared product reference
  documents may therefore appear in more than one subdomain's policy; the
  task partition itself is exact (97 tasks, each in exactly one subdomain).

The base `banking_knowledge` domain (full 698-document KB, retrieval
variants) is unchanged and remains the retrieval-architecture benchmark.
