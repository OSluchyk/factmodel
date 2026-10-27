"""Release: the readable copy of a model for consumers.

``build`` partitions every file of the model repository with the release allowlist
(``spec/ALGORITHMS.md``, algorithm 3), strips internal notes, and writes the copy with a
``VERSION`` file and an append-only ``RELEASE_NOTES.md``. ``check`` is the reduced gate a
release must pass.
"""
