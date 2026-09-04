"""Test-side support for the airline_plus / retail_plus corpora.

The plus domains and their hyper-sops fact trees were originally derived from
the canonical airline/retail corpora by maintainer-only generators and porters
that no longer ship with the benchmark. The expectations those tools computed
live here as pinned literals (plus a small amount of mechanics ported out of
the deleted shared module), so the gates in tests/ assert fixed values instead
of recomputing the answer from the engine that produced the data.
"""
