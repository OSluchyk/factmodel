# D-016 Public-domain code lists as fixtures

Date: 2026-10-27 · Status: accepted
Platform that forced it: QCEW (`examples/qcew`)

## Context

Plan ground rule 3 keeps data out of the repository: examples use synthetic rows. QCEW's hierarchies (county to state, NAICS child to parent) live in its code lists, the BLS title files. Synthetic code lists would hide exactly what the example has to show, for example that the BLS area file repeats 4,649 of its 4,809 codes. The title files are public domain (BLS publishes everything it produces in the public domain and asks to be cited), small, and hold codes and names of areas and industries, not people.

## Decision

Plan ground rule 3 gains one exception. A code list may be committed under `examples/<model>/sources/codelists/` when all of these hold:

- it is in the public domain;
- the file is under 1 MB;
- `sources/codelists/SOURCES.md` has a line for it with the URL, the read date and the citation the publisher asks for;
- it holds no personal data.

The file is copied unchanged, defects included. Everything else in an example stays synthetic.

## Consequences

- `spec/IMPLEMENTATION_PLAN.md` ground rule 3 states the exception.
- The `privacy` gate stage still runs on the files; a code list that trips it is not committed.
- QCEW commits five BLS title files (511,232 bytes together).

## Evidence

- Owner decision in the owner brief of 2026-10-27 on M2, QCEW and the freeze (private working notes), section 3.
- BLS public-domain notice and the title file URLs: owner's `README.md` and `profile.md` A3, read 2026-10-23.
