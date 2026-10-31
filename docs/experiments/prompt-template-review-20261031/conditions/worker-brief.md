# Per-run condition test: worker brief

Read `plan.md` in this folder first. You carry out its procedure for **one** run, offline. The decision rule and
measures are fixed. Do not change them.

**Inputs.**
- `conditions/<key>.requirements.json` holds the frozen spec texts:
  - `requirements` (changed R-<n> texts);
  - `repo`: the final worktree, which you must never edit;
  - `run_dir`: ShipLoop's run records;
  - `baseline`: the commit before the run.

**Order matters (selection control).**
1. Write `conditions/<key>/conditions.json` from `requirements.json` alone, **before opening any file in `repo` or
   `run_dir`**.
2. Shape: `[{"id": "R-n.k", "requirement": "R-n", "quote": "<verbatim span>", "observable": "<what an outside check
   sees>", "kind": "behaviour|error|boundary|format|structural|tests-themselves|preserved", "candidate": true|false,
   "exclude_reason": "<when not a candidate>"}]`.
3. Then write `shasum -a 256 conditions.json > conditions.sha256`.

**Copy and baseline.**
- Hash the original before you start, and again at the end:
  `cd <repo> && find . -type f -not -path './.git/*' -not -path '*/node_modules/*' | LC_ALL=C sort | xargs shasum | shasum`.
- `cp -R <repo> <scratch>/<key>/work`, where scratch is
  `/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/conditions`.
- Find the run's own full-suite command. Use its records: `run_dir/tests/*-verify*.md` (the regression or suite
  command), the test-strategy result in `run_dir/results/`, and the system-test-author commands. Prefer the widest
  command the run itself ran.
- Run it on the copy. It must exit 0. Do not install anything from the network. If it needs a missing dependency,
  or fails on the unchanged copy, record the run as excluded with the output and stop.
- Use your port range for anything that listens (set `PORT` or the equivalent when the suite honours it). Other
  workers run at the same time.

**Per candidate condition.**
1. **Variant.** Make the smallest edit to **product code only** (never tests, fixtures or test helpers) that breaks
   exactly this condition and leaves the rest working. Save it with `git -C <copy> diff > conditions/<key>/patches/<id>.patch`.
2. **Witness.** Write `conditions/<key>/witnesses/<id>.sh` (or `.py`/`.js`): an independent check of the condition
   from outside the code, through HTTP, the CLI or the module's public function. Do not reuse the run's tests. It
   must exit 0 on the unchanged copy and non-zero on the variant. If you cannot make it tell them apart, the verdict
   is `unwitnessed`.
3. **Suite.** Run the full-suite command on the variant. Record its exit code and the failing test names. Nonzero
   is `killed`; zero is `survived`.
4. **Restore.** `git -C <copy> checkout -- . && git -C <copy> clean -fdq`, then confirm the suite still passes every
   five conditions or so.

**For each survivor**, look in `run_dir` (`tests/`, the test-spec results under `results/`, the step-plan criteria) and record:
- `claimed_by`: the test case whose text or requirement field claims this behaviour, or `"none"`;
- `owning_step`: the step whose criteria name it;
- `why_survived`: e.g. the assertion is too broad, the case is absent, or it is tested only through a mock.

**Output.**
- Write `conditions/<key>/results.json`:
  ```
  {"run", "suite_command", "baseline_exit", "baseline_summary", "original_hash_before", "original_hash_after",
   "conditions": [ ...conditions.json rows plus "verdict" (killed|survived|unwitnessed|excluded),
                   "witness", "witness_exit_original", "witness_exit_variant", "suite_exit_variant",
                   "failing_tests", "patch", plus the survivor fields when survived ],
   "counts": {"candidates", "witnessed", "killed", "survived", "unwitnessed", "excluded"}}
  ```
- Return a final message of at most 300 words with:
  - the counts;
  - each survivor in one line: id, the quote, why it survived;
  - anything that went wrong.

**Rules.** Never edit `repo`, `run_dir` or anything outside `conditions/<key>/` and your scratch directory. Do not
commit. Make no model calls and touch no external services.
