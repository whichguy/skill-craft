---
bump: patch
---
- **Nomenclature check (E2E SPEC S-16):** the audit reads a run's `nomenclature` record and checks the packets the
  model acted on against ShipLoop's glossary. A retired term, two terms for one concept or one term in two meanings is
  a workflow finding. A repair checks the terms it adds, reuses or retires against the glossary, and updates the
  glossary in the same commit.
