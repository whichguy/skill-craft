---
bump: minor
---
The implement packet carries the step, not a path list. Its printed head now shows:
- the step's task;
- the criteria it serves;
- its Proof, a command ShipLoop runs at done, which must exit 0;
- the spec, architecture and environment sections it is anchored in;
- its coding cards, its skills and the item's existing example to follow;
- the later steps by ID and criteria;
- the last two commits.

Before, the head printed no step at all.

The guidance is static text read from `references/implement-guidance.md`: a method, eight domain-neutral
considerations (whole step, interactions, building, deploying, state, operating, what exists, proof), evidence rules
and write-back rules. A done implement result answers `considerations` and gives `evidence` for each assigned
criterion; ShipLoop refuses empty answers and missing or foreign evidence.

Code craft lives in `references/code-craft.md` and gains rules 10 to 14: concurrency where it pays, the platform
first, bounded remote calls, configuration not constants, and determinism seams. Rules 3, 4, 6 and 9 gain tombstones,
token-efficient comments, resource release and build-to-compose. The rubric prints only for steps that change code;
the printed head carries it one line per rule, and the packet file carries it in full.

Step plans now give each step a `check` and `cards` (`[]` with `cards_na`), and the item a `match` contract. Per-step
`paths` are optional.
