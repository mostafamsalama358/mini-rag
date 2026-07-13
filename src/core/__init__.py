"""core/ — shared RAG pipeline engine (domain-agnostic).

This package contains the ONE shared pipeline: retrieval fusion (RRF, hybrid,
dedupe, merge), structural splitting, and chunking primitives. Domain-specific
patterns live in `fields/{domain}/*.yaml` and are injected via FieldProfile.

Constitution G1: core MUST NOT import from `fields/` and MUST contain no
domain-specific regex (research R1, plan Phase B).
"""
