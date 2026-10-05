---
name: shiploop-run-review
description: >-
  Update the owner's ShipLoop Run Review page after an E2E run: export the run's
  measured numbers from its output directory, find or create the page, upload the
  documents, add the judgement and give the owner the link. Use after a ShipLoop E2E
  run or iteration, or when asked for the Run Review page or a run export.
version: 0.1.0
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: script-backed
---

# ShipLoop Run Review

The owner's iteration tool: expected versus observed for each run, the Backchain ledger, the plan's
iterations with editable expectations, and a prompt builder. The page is a static template; every run adds
data, not template code. The data contract is [SCHEMA.md](SCHEMA.md).

The exporter turns a run output directory of skill-craft's `test/shiploop_e2e/run.py` into the page's
documents. It reads only the run's own records and holds numbers only. The judgement (observations, a revised
expectation with its reason, the iteration result) is yours to add from your review of the run.

## Binding

Run the exporter only from the selected, loaded `SKILL.md`. Let `SKILL_ROOT` be the absolute directory
containing that file and bind the bundled files from it for the current tool call:

```sh
# Replace this illustrative path with the selected absolute location before running.
SKILL_ROOT="/absolute/directory-containing-the-loaded-SKILL.md"
python3 -B "$SKILL_ROOT/scripts/export.py" "/absolute/run/output/directory"
```

Do not infer `SKILL_ROOT` from the project's working directory, a source checkout, `PATH` or a same-named
skill. The exporter writes only under `--out` (default `<run output>/review-export/`), needs only the Python
standard library, and makes no network or model calls. The template and the starting defaults are the files
`$SKILL_ROOT/template/index.html` and `$SKILL_ROOT/defaults/`.

## After every iteration

An iteration is one run (or batch) that has been reviewed and journaled. Do this straight after the learnings
commit.

1. **Export.** `python3 -B "$SKILL_ROOT/scripts/export.py" <run output directory>` writes the run's documents,
   `writes.json` and `facts.md` under `<output>/review-export/`, plus one compact `review-export.json` to commit
   with the learnings entry. `test/shiploop_e2e/iterate.py` and `run.py` do this for you. A `metrics.json` with no
   `unmeasured` record is refused (it predates the harness recording which counters a host cannot measure): regrade
   the finished run first, as the message says.
2. **Find or create the page.** With the Artifact tools: `Artifact list` for the title "ShipLoop Run Review". If
   there is none, publish `template/index.html` with `capabilities: {db: {}}`, then seed the starting
   expectations with `export.py --defaults` (create-only: list what exists first and skip it).
3. **Upload.** Apply `writes.json` with `ArtifactData` `batch`. For a document that already exists, read its
   version and pin `if_version`; never overwrite what the owner edited on the page.
4. **Add the judgment.** Write observations (what we expected, what we saw, the evidence path) from the review,
   set the result of the iteration card, and revise an expectation, with its reason, when the evidence shows the
   expectation was wrong rather than the engine.
5. **Provide it.** Open the page once (`Artifact` action `open`) and give the owner the link with a short
   narrative: what was done, what is running and why, the conclusions, what was learned, what is next.
6. **No Artifact tools?** Keep `review-export.json` with the learnings entry and say the page was not updated.

## Rules

- Data changes never republish the template. A template change is one republish, recorded in the journal
  (`docs/shiploop-run-review-journal.md` in a source checkout).
- A number the host could not measure is absent, with its reason in `runs.unmeasured`, and the page says "not
  measured"; never write or read it as 0. A stage with no accept time has `min` null and reads "n/a".
- A hand-set verdict stays interim; derive from digests and receipts where the run kept them.
- The journal and the committed `review-export.json` are the durable record; the artifact database is the
  working copy.
