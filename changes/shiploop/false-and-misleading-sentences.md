---
bump: patch
---
Sentences that told a cleared model something false or incomplete are corrected, each against the behaviour it describes.
- The run reference file's rules section lists the planning results that start an Improve child for the run's own
  `planning_review` option (a `none` run lists two, not the seven of a `stage` run).
- On the ask-agent route, where one implement action builds every step of a plan of several steps, the Goal, the loop's
  exit conditions and the Improve review focus name those steps ("S1 to S2") and their paths instead of "this step"; a
  one-step plan and every inline run keep the per-step wording. The loop's Work line no longer ends "in order,.".
- A loop's Work cites the duty items the packet prints, counted from the duty text (step-plan 1-12, test-spec 1-7,
  validate-existing 1-4, implement 1-7, test 1-8, document 1-7, carry-forward 1-4; verify 1-9, where its duty says items
  1-7 repeat and items 8-9 are done once). The step-plan, test-spec and test Work say to run the Callback command with
  `--check-only` added (no packet printed a command of its own); the test Work says what that runs, and its Repeat adds
  "a check-only refusal". Verify's assembly item (8) prints on the ask-agent route only.
- The Checked-by line says `complete --check-only` prints the first refusal without accepting and is repeated until it
  accepts (a gate raises at the first fault, so it never printed every refusal).
- Removed or corrected: "HOME/spec.md (quoted below)" at spec (the spec stage quotes no file; it now says to read it
  whole), the spec goal's "FEATURE/spec.md", the lint gate sentence "only the item's last step is gated" (every
  implement step is), "a list too large for the loop contract is refused" (no gate refuses a size), and the test-only
  step refusal's "test-author" (no such stage; it now names the test-spec).
- A validate-existing stage ShipLoop records itself (every expectation matched) has the summary "ShipLoop ran every
  expectation check on the unchanged checkout and each matched its state." in place of the 143-character sentence the
  status line cut mid-word; the check record stays in `evidence_refs`.
- `SKILL.md` limits "launches no model process" to the skill and its navigator commands and names the optional outer
  driver `scripts/shiploop-drive`.
