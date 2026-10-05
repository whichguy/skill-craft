# Writing advice and options for a run

Intent: turn one run's evidence into findings, advice and options the owner can tick, so repairing the run is a
choice and not a research task. Outcome you can observe: a review file that `export.py --check` accepts (exit 0, every
warning read), in which every anomaly of the run is a finding with measured numbers and a path, every fix is an option
an agent could run as written, and each criterion you examined has a one-line basis. Grade your file against that
outcome before you stop.

## Inputs

Read these in order. The first one stops you from inventing numbers.

1. `facts.md` and the run's export (`review-export/` in the run output, or the committed
   `test/shiploop_e2e/evidence/<name>.json`). Read the unmeasured list first: a counter on it was not measured, so never
   advise from it. A missing number is unknown, never 0; when it matters, offer a gather-evidence option for it.
2. `result.json` verdicts, and `mismatch.md` when the run failed (the triage words are mapped below).
3. The harness reviewer's `review.json`: its findings are candidate findings and options, not conclusions.
4. The last three entries of `test/shiploop_e2e/LEARNINGS.md`.
5. Findings still open from earlier reviews (the earlier `*.review.json` files in the evidence directory) and the
   findings and options the owner added on the page (read the `observations` and `actions` collections). Keep each
   one in your file as the owner wrote it; add fields, never rewrite or drop it.
6. The clauses S-1 to S-15 of `test/shiploop_e2e/SPEC.md`, and `skills/shiploop-run-review/defaults/expectations.json`
   for the criterion keys.

## Steps

1. **Findings.** For each anomaly write a finding, or merge it into an earlier one: `title`; `criterion` (an
   expectation key); `kind`; `expected` and `observed` with measured numbers; `evidence` (a path or a commit; a
   run-relative path is fine, the prompt prints the run directory beside it); `status`; `run` or `runs`; `phase`;
   `effect`; and a `figure` when the finding is a number (below).
2. **Advice.** `advice` is one recommended path and its reason, in at most three sentences. Mark an inference
   `Inferred:`.
3. **Options.** Offer one to four per finding, normally at least two kinds, and always `accept` when a normal run would
   not hit the gap. Give each `effort` (S one commit with a test, M a few increments, L a live run or days), and a
   `cost` when it spends money or a live run. Verify `status` from `git log`, the branch and the plan document: `open`
   (nothing built), `planned` (a written plan exists; cite it in `ref`), `built` (code exists, unreleased or
   unverified; cite the commit in `ref`), `done` (landed and verified).
4. **Ground.** Tie each change to a spec clause, predict what else it could harm (name that clause or expectation), and
   name the unknowns with how each would be resolved. An unknown is written down, never filled with a guess.
5. **Review.** Write `reviews/<runKey>`: `summary`, the arc in 3 to 6 lines (what was done, what the run showed,
   conclusions, learnings, next), and `basis`, one line for each criterion you examined that holds.
6. **Check.** Run `export.py --check FILE` until it exits 0, then read each warning and fix it or leave it on purpose.

## Effect, phase and figure

- **Effect.** Every open finding carries `effect` when it hits an expectation: `broken` (the expectation does not
  hold in this run) or `bent` (it holds with a cost or a workaround). Leave it unset only when the finding hits no
  expectation (a choice for the owner, a note on the harness): the page then shows it as "not rated" and `--check`
  warns. Never set `bent` just to silence the warning.
- **Phase.** Always set `phase` (an order of the phase documents, 0 Understand to 7 Release) when the finding sits at a
  stage: the page draws a "where it happened" strip from it and the run's visits. Leave it out when the finding is
  spread over the run, such as a total.
- **Figure.** For a numeric finding add `figure` `{kind: "bars", items: [{label, value, unit?, lowerBound?, tone?}]}`
  comparing what was expected with what was seen: at most 6 items, labels at most 22 characters, `value` a non-negative
  number (a measured 0 draws a stub), `lowerBound: true` for a count known to be only a lower bound, `tone` one of
  `expected`, `saw`, `limit`. Never put raw SVG or HTML in any field: the page draws the figure and escapes text. The
  figure decorates; `expected`, `observed` and `evidence` stay in words.

## Option form

`goal` is the self-contained instruction, in this form and in this order:

`Do: ... Files and symbols: ... Test: ... Done when: ...`

- **Do** the change, in a sentence or two.
- **Files and symbols** are paths and names, never line numbers.
- **Test** is the script-run test that confirms it, or "none; this records a known limit".
- **Done when** is an observable end state a test or a command shows. It ends the instruction; `--check` refuses an
  instruction that does not end with it.

Keep status narrative out of `goal` (it belongs in `status` and `ref`). For each fix option (`fix-shiploop`,
`fix-harness`) put one line in `why`: `For: ... Against: ... Verdict: ...`. At most one option per finding is
`recommended`. A `change-expectation` option carries `change` `{target, to, reason}`, where `target` is `page`
(`defaults/expectations.json`) or `spec` (`test/shiploop_e2e/SPEC.md`); no other kind carries `change`.

## Honesty rules

- Read the unmeasured list first and never advise from a not-measured counter.
- State a number with its source, and mark every inference `Inferred:`.
- Invent no threshold ("too high", "slow"): compare with the expectation or with an earlier run.
- At most one recommended option per finding, and one line of for, against and verdict per fix option.
- Verify an option's status from `git log`, the branch and the plan document; never guess whether something is built.

## Triage words in mismatch.md

| mismatch.md says | Write |
| --- | --- |
| product | a `fix-shiploop` option |
| environment | a `fix-harness` option |
| expectation | a `change-expectation` option |
| known limit | an `accept` option |
| owner | a finding that needs the owner's choice: the advice names the choice, the options show each side |
| rerun-first | a `gather-evidence` option |

## Worked example (an example, not a review)

One finding from the committed Luna evidence (`runs.luna1`: 13 refusals), with three options and a figure. The
finding sets no `phase` because the refusals are spread over the run, and `effect` is `bent` because the run
recovered each one.

```json
{
  "schema": "run-review-export/v2",
  "docs": {
    "observations": {
      "ex-refusals": {
        "title": "13 ShipLoop commands were refused on the Luna run",
        "criterion": "P3",
        "kind": "defect",
        "status": "open",
        "run": "luna1",
        "expected": "The model runs the printed command exactly: no refused command.",
        "observed": "13 refused commands (measured): 3 carry a space typed into a long path, 8 are the 'read the current packet' refusal and 2 are something else.",
        "evidence": "test/shiploop_e2e/evidence/codex-gpt-6-luna-1.16.1-battleship-20261003.json runs.luna1.failures",
        "effect": "bent",
        "advice": "Fix the 3 broken paths first: they are the only refusals with a clear cause. Inferred: the 8 packet refusals share one cause, which a read of the failures would show.",
        "figure": {
          "kind": "bars",
          "items": [
            {"label": "Expected refusals", "value": 0, "unit": "commands", "tone": "expected"},
            {"label": "Refused commands", "value": 13, "unit": "commands", "tone": "saw"},
            {"label": "Broken paths", "value": 3, "unit": "commands", "tone": "saw"}
          ]
        },
        "createdAt": "2026-10-04T12:00:00Z"
      }
    },
    "actions": {
      "ex-alias": {
        "title": "Print the run directory as a short alias",
        "criterion": "P3",
        "kind": "fix-shiploop",
        "effort": "S",
        "recommended": true,
        "status": "open",
        "findings": ["ex-refusals"],
        "goal": "Do: print each completion call with the run directory as a short alias that the packet defines once, so a model never re-types a path of more than 100 characters. Files and symbols: `_callback` in skills/shiploop/scripts/shiploop_navigator.py. Test: a contract test in test/shiploop-navigator-contract.test.py that no printed completion call carries a path over 60 characters. Done when: that test passes and the next Luna-class run shows no refused call with a broken path (S-2, S-4).",
        "why": "For: 3 of the 13 refusals were a space typed into a long path, and the alias removes the cause. Against: one more line in every packet. Verdict: worth it for an S-sized change; measure the refusal count on the next run."
      },
      "ex-evidence": {
        "title": "Find what the 8 packet refusals have in common",
        "criterion": "P3",
        "kind": "gather-evidence",
        "effort": "S",
        "status": "open",
        "findings": ["ex-refusals"],
        "goal": "Do: read the 8 refusals in the failures list and name what the model called before each. Files and symbols: runs.luna1.failures in test/shiploop_e2e/evidence/codex-gpt-6-luna-1.16.1-battleship-20261003.json. Test: none; read-only. Done when: the review names a cause for the 8 refusals or says the recorded lines cannot show one.",
        "why": "The numbers say 8 refusals carry one message; they do not say why."
      },
      "ex-accept": {
        "title": "Accept the broken paths as a known limit",
        "criterion": "P3",
        "kind": "accept",
        "effort": "S",
        "status": "open",
        "findings": ["ex-refusals"],
        "goal": "Do: record in test/shiploop_e2e/LEARNINGS.md that 3 of 13 refusals on the Luna run were a stray space in a long path, each recovered in one turn, and change no code. Files and symbols: test/shiploop_e2e/LEARNINGS.md. Test: none; this records a known limit. Done when: the entry names the 3 refused calls and the evidence file.",
        "why": "A normal run with a short run path does not hit it: the paths here were over 100 characters."
      }
    }
  }
}
```
