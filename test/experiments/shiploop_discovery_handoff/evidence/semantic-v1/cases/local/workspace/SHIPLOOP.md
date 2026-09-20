# Project knowledge

Read current source and docs/environment.md, then retain the discovery decision and exact evidence locators in this index.

## 2026-09-20 local name-normalization discovery

- **Requested delta:** normalize names by trimming edges and collapsing repeated internal whitespace ([README.md](README.md):3).
- **Observed current behavior:** [src/app.py](src/app.py):1-2 defines the affected `normalize_name` helper and uses `value.strip()`, so it trims only edges. [test_fixture.py](test_fixture.py):4-6 covers that existing edge behavior only.
- **Baseline:** [BASELINE.txt](BASELINE.txt) records the unchanged-content command `python3 -B -m unittest discover -v`; it exited 0 with one passing test. It does not verify internal-collapse behavior.
- **Decision for later implementation:** retain the helper and use Python whitespace splitting followed by a one-space join, with focused tests for repeated spaces, tabs/newlines, empty input, whitespace-only input, and an unchanged one-part name. This is a proposal; discovery changed no product source or tests.
- **Boundary assessment:** [docs/environment.md](docs/environment.md):1-3 documents a local pure-Python helper with no remote service, state, or deployment configuration. Service, storage, remote access, delivery, and source-return work are not applicable to this fixture.
