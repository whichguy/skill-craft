---
bump: patch
---
- **Refusals say the current terms:** four refusals still used words the 2.9.0 renames retired. Three said "run the same
  complete command again" (the spec write-back gate, a retired `blocked_by` field and an unsupported result field);
  they now say "run the same callback again". One said an open plan assumption "whose consumer is" a work item; it now
  says "whose due_item is". Each phrase was split across two string literals, so the line-based term check missed it;
  run 5 printed two of them.
