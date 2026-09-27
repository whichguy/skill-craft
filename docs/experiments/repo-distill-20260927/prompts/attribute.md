# Attribute each oracle failure to where it was lost

**Intent.** A program was rebuilt, in a clean room, from a specification that
was distilled from an original repository. A black-box oracle (ported from the
original's tests and admitted: it passes on the original, fails on a stub)
now fails on the rebuild. For every failing check, find **where the behaviour
was lost**, so the right component is fixed. The distiller is as much a
suspect as the builder; do not assume either.

**Inputs in the current directory** (read-only):

- `original/`: the original repository;
- `spec.md`: the distilled specification the builder received (nothing else);
- `rebuild/`: the rebuilt program, including any planning or spec documents
  its builder wrote;
- `oracle/`: the oracle tests and `MAPPING.md`;
- `results.json`: per-test results on the rebuild (`fail` entries), and
  `oracle.tap`: the oracle's full output, with each failure's message.

## Locations (pick exactly one per failure)

| location | holds when |
|---|---|
| `distill:omission` | no claim in spec.md covers the behaviour the check tests |
| `distill:error` | a claim covers it, and the original contradicts the claim |
| `distill:ambiguity` | a claim covers it, but its wording also admits the rebuild's behaviour |
| `build:intake` | a clear, correct claim is missing or changed in the builder's own spec or plan documents |
| `build:plan` | the builder's documents keep the claim, but no plan item or test covers it |
| `build:implementation` | covered and planned (or no planning documents exist), but built wrong |
| `oracle` | the check depends on something the spec rightly left free (internals, wording), or is flaky |
| `unattributed` | none holds; say what you would need to decide |

Use `build:implementation` for a builder with no planning documents.

## Method

For each failing test: read the oracle check and its failure message; find the
spec claim(s) that cover that behaviour (quote the claim ID); confirm the
original's behaviour at its source; inspect how the rebuild behaves and why.
Group failures that share one root cause, but classify each.

## Output

Write `attribution.json`:

```json
{"failures": [{"test": "...", "location": "...", "claims": ["D-12"],
  "evidence": "one or two sentences with file:line citations",
  "root_cause": "short id shared by failures with the same cause"}],
 "root_causes": [{"id": "...", "location": "...", "tests": 3,
  "fix": "the general change to the distiller, the builder or the oracle that would prevent this class of loss (never specific to this product)"}]}
```

Before finishing, check: every failing test in `results.json` appears exactly
once; every `distill:*` verdict quotes the claim or states that none exists;
every `build:*` verdict names the spec claim it relies on. End with
`ATTRIBUTED: <n> failures, <k> root causes`.
