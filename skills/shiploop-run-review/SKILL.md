---
name: shiploop-run-review
argument-hint: "advise RUN_DIR_OR_KEY | export RUN_DIR | publish | check FILE"
description: >-
  Review a ShipLoop E2E run on the owner's Run Review page: export the run's measured
  numbers, write findings, advice and options for the owner to tick, check that review
  file, and publish both to the page. Use after a ShipLoop E2E run or iteration, or when
  asked for the Run Review page, a run export or advice on a run.
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

The owner's iteration tool: one run read in four steps on one page. **1 What happened**: a picture of the run's
visits and its numbers. **2 Expected versus seen**: each expectation reads holds, bent, broken or not examined,
worked out from the findings. **3 Findings and options**: Claude's advice, and options the owner ticks in any mix.
**4 Your plan**: one prompt for Claude Code that the owner copies. The page is a static template: a run adds data,
never template code. The data contract is [SCHEMA.md](SCHEMA.md).

Scripts own the numbers, Claude owns the advice. The exporter reads the run's own records and holds measured numbers
only; a number the host could not measure is absent with its reason, because unmeasured is never zero. Claude writes
the findings, options and arc into a review file following [references/advice.md](references/advice.md), and
`export.py --check` gates that file.

```text
/skill-craft:shiploop-run-review advise RUN_DIR_OR_KEY   after a run: export it, write the review file, check it
/skill-craft:shiploop-run-review export RUN_DIR          the run's numbers only
/skill-craft:shiploop-run-review publish                 put the data on the page
/skill-craft:shiploop-run-review check FILE              validate a review file
```

## Binding

Run the scripts only from the selected, loaded `SKILL.md`. Let `SKILL_ROOT` be the absolute directory containing
that file and bind the bundled files from it for the current tool call:

```sh
# Replace this illustrative path with the selected absolute location before running.
SKILL_ROOT="/absolute/directory-containing-the-loaded-SKILL.md"
python3 -B "$SKILL_ROOT/scripts/export.py" "/absolute/run/output/directory"
python3 -B "$SKILL_ROOT/scripts/export.py" --check "/absolute/review/file.json"
```

Do not infer `SKILL_ROOT` from the project's working directory, a source checkout, `PATH` or a same-named skill. The
exporter needs only the Python standard library and makes no network or model calls. The template and the starting
defaults are `$SKILL_ROOT/template/index.html` and `$SKILL_ROOT/defaults/`.

## export RUN_DIR

Numbers only. `export.py RUN_DIR` writes `<RUN_DIR>/review-export/`: one file per document, `writes.json`, `facts.md`
and one compact `review-export.json` to commit with the learnings entry. `test/shiploop_e2e/run.py` and `iterate.py`
run it for you. A `metrics.json` with no `unmeasured` record is refused: regrade the finished run first, as the
message says. Add `--key KEY` to keep the key the page already has for a run.

## advise RUN_DIR_OR_KEY

`RUN_DIR_OR_KEY` is a run output directory (export it first) or a run already in `test/shiploop_e2e/evidence/`.

1. Read the run's evidence and write `test/shiploop_e2e/evidence/<runKey>.review.json` (the page's key for the run, as in the run document's id),
   following [references/advice.md](references/advice.md): the `reviews`, `observations` (findings) and `actions`
   (options) documents, in the shape of `review-export.json`. Keep every document the owner added on the page.
2. Run `export.py --check FILE` until it exits 0, and read every warning.
3. Commit the review file with the run's learnings entry.

## check FILE

`export.py --check FILE` lists every failure, one per line naming the document (exit 2); warnings are listed and the
exit stays 0. Failures:

- schema and enums: every document passes [SCHEMA.md](SCHEMA.md);
- every option's findings exist in the bundle;
- a change-expectation option has `change` (`target` page or spec, `to`, `reason`), and no other kind has one;
- each option's `goal` ends with a `Done when` clause;
- at most one recommended option per finding;
- a `clauses` id is an `S-n` id that `defaults/expectations.json` uses;
- a finding's `criterion` and each key of a review's `basis` is a key of `defaults/expectations.json`.

Warnings: an open finding no option names (the page shows "no option yet"); a finding's evidence with no path or commit
token; an open finding with no `effect` (the page shows it as "not rated").

## publish

1. **The page.** Ask for the artifact URL, or take it from the user. With none given, find the artifact titled
   "ShipLoop Run Review" (`Artifact list`) and use it. With none at all, publish `template/index.html` once with
   `capabilities: {db: {}}` (load the `artifact-capabilities` skill first; omit capabilities on a redeploy). Never
   create a second page unless asked. The URL may be a draft: a separate artifact with its own empty database, built
   from the same template. The same steps fill it and leave the live page and its data untouched.
2. **The defaults.** Save the page's `expectations` and `config` rows as `ArtifactData` returns them
   (`{docs: {collection: {id: {data}}}}`) and run `export.py --defaults --live FILE --page-url URL --out DIR` (URL: this
   page's artifact URL, which the page cannot read itself; the prompt's head prints it); on an empty page,
   `--defaults --page-url URL --out DIR`. The script merges, never you: it keeps every revision, refuses a page revision the
   defaults lack (copy it into `defaults/` first), and writes only documents the defaults name, with their
   `writes.json`. `set` each with `if_version` where it exists. Never overwrite or delete an owner-added document, or
   any document you did not write.
3. **The run.** Upload the `writes.json` of `export RUN_DIR` the same way, except an existing `backchain` document: it
   may hold hand verdicts the exporter cannot rebuild (`luna1-plan` and `luna1-step-plan` do), so never `set` a
   Backchain document whose id exists with hand-built content.
4. **The review.** `export.py --docs FILE --out DIR` checks the review file, refuses a failing one, and writes its
   documents and a `writes.json`. Read each document that exists live before replacing it: a `status` or field the file
   lacks is the owner's change on the page, so pull it into the file with advise and never overwrite it; otherwise pin
   `if_version`.
5. **Upload** each `writes.json` with an `ArtifactData` `batch` (at most 50 writes a call; add `if_version` to an entry
   whose document exists).
6. **Open and tell.** Open the page once (`Artifact` action `open`) and give the owner the link with the arc: what was
   done, what is running and why, the conclusions, what was learned, what is next.
7. **No Artifact tools?** Say the page was not updated, and keep the review file.

## Rules

- Data changes never republish the template. A template change is one republish, recorded in the journal
  (`docs/shiploop-run-review-journal.md` in a source checkout).
- The page writes only owner-added findings and options and a finding's status. Expectations, settings and runs are
  replicas written by publish; changing an expectation is an option the owner ticks, applied from the repo.
- A number the host could not measure is absent, with its reason in `runs.unmeasured`; the page says "not measured".
  Never write or read it as 0.
- Evidence stays in the repo (the committed export and review file). The artifact database is the working copy.
