---
bump: minor
---
- **`KNOWLEDGE` replaces `HOME`:** packets now name the knowledge home (`docs/shiploop/`) by the symbol `KNOWLEDGE`, as in
  `KNOWLEDGE/spec.md`. `HOME` read too much like the user's `$HOME`. The References block defines it
  (`KNOWLEDGE = <path> (knowledge home)`), and the stage goals, duties and gate texts use it.
- **Evidence paths:** an `evidence_refs` entry may lead with `KNOWLEDGE/`. One led by `HOME/` is now refused as an unknown
  root, with the defined roots named.
- **Packet size:** each head grows by 6 to 51 characters. The tightest, the inline step-plan head, is 19,971 characters and
  still fits the 20,000-character cut.
