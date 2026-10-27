"""Equivalence harness: does a consumer answer like the platform?

A corpus holds requests with the platform's own answer (hand-written reference SQL). The
consumer compiles each request into SQL through its layer; both sides are bound to physical
names, rendered per dialect and compared in one of three modes. Only outcomes and counts are
written, never rows.
"""
