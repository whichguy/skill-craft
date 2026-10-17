---
bump: minor
---
A packet no longer says a thing twice, or carries a note the run has no use for yet. Each cut has a script that proves the
text is elsewhere in the same packet or that no stage needs it.
- A followed `R-<n>` or `AD-<n>` entry whose exact text sits in the whole-file diff the same block prints below it is listed
  by ID ("each entry is in the diff of HOME/spec.md below"), as one in a file the block quotes whole already was. The
  document and verify packets print the spec diff of a new spec and no longer repeat the followed entries inside it (on the
  long-knowledge fixture the hand-off block of each falls from about 38,000 to about 29,400 characters; a modified file's
  diff, which holds only changed lines, still leaves the entries' text where it is). One item's implement steps share one
  `not_covered (<item> implement)` label, so the test and verify blocks no longer repeat a label that names the item and the
  stage and nothing else.
- "Current planning sources" prints only for a run with a planning reconciliation. The stages up to and including `plan` listed
  every planning stage, most of them "no current accepted result" because they had not run; the current results are the
  "Results this stage builds on" lines of the References block, and a reconciliation is the only event that retires one.
- The last accepted transition drops its "Summary: as the status block's Done line shows." line (the summary prints only
  when it says more than the Done line), and the Improve lessons print one line each, with no blank line between them.
- The consumer-delivery block prints whole only where an observation can be declared or a failure retained (system-test,
  product-acceptance, release-plan, release-check, release, release-verify, operations, handoff), at plan and at
  system-test-author (`consumer_delivery.WHOLE_BLOCK_STAGES`, computed from the observation tables). Every other stage
  prints the anchor, the record, the obligation IDs with their phase and the standing exclusions, plus any replanning or
  recovery notice; the contract, authority and observations are in the record the anchor names.
- A packet that carries a stored lint record prints its findings, the verdict, the gate rule with the `lint_waivers` shape
  and the rerun command, and leaves the scope, coverage, tool, command and Git-plumbing sections to the record, with the
  command that prints it whole. A record whose tool failed or timed out, and a block of several pages, print whole.
- An inline implement packet names each later step by its id and the paths it owns instead of its task (the task is in the
  step plan's result); a step without paths reads "(no paths declared)".
- The test packet prints the shapes of `red_na` and `retired_tests` once, in duty 6. The "Optional at test:" line is gone and
  the base-run and floor rules say "(shape: duty 6)".
