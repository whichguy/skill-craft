# Review of exp/four-part-packet-631117 at 57b57612 (E2E fork, read-only, Opus), 2026-10-10

Scope: the engine and SPEC commits (caps, reference.md, the clear-the-context probe). Received by cross-session
message; recorded here verbatim in substance as evidence, with the inner-loop session's verification notes.

## Blockers for using the probe as the S-6 gate
- **B1: the redo metric misses the one real redo on record.**
  - Regrading /Users/dadleet/e2e-runs/20261009/s6-inside-implement-mtime/events.jsonl with clear.redone(p, 101)
    returns []. Line 99 is `printf ... > $W/hello.py`; line 112 is a Write of the same file after the clear.
    REDIRECT hashes the whole command, Write hashes the content, and paths are not normalised.
  - Synthetic misses: heredoc then Write; Write then printf on a relative path; Edit then Write; npm test then
    node --test; the same test with only a notes/inbox write between (any write excuses the rerun); callbacks
    through wrapper scripts (res.sh/imp.sh/sl.sh); make test; Agent subagents.
  - TEST_RUN also matches prose in JSON summaries.
  - The metric was tuned until the baseline read zero, with no positive control.
  - Fix: key on (normalised path, final content) per write and on test-runner families; make the mtime run a
    required positive control.
  - VERIFIED by the inner-loop session: redone() returns []; line 99 yields a write keyed by the command, line 112
    a write keyed by the content.
- **B2: ":inside" is effectively a boundary.** The trigger fires after the first completed non-ShipLoop call,
  which in probe-old-test-green-inside was a read-only grep of the packet. LEARNINGS (2026-10-09 S-6 pair) already
  established that the trigger must be the first change to a worktree file after the stage becomes current.
- **B3: "zero redone work on today's packets" is n=2.** One host, one tiny case, inline, inner stages only, and
  test-green "inside" was really a boundary (B2). The evidence was in a scratchpad, not the repo. Required probes:
  a planning stage, an Improve child, an outer stage, and a second host.

## Should-fix
- **S1:** SKILL.md's static-checks paragraph still says "the 7th refused run" (the code is 11). Pin cap numbers in
  prose to MAX_REFUSED_RUNS with a test.
- **S2:** SPEC S-10 needs a dated carve-out for the 11/7 caps. It must state that the cap is on the stage's
  acceptance gate and that the Until Loop stays uncapped. Raised with the owner. The concision doc's "Open" section
  still shows 3/7.
- **S3:** reference.md hand-copies OUTCOMES_TEXT, AWAITING_TEXT and POLICIES instead of deriving them
  (AWAITING_SHAPE, BLOCKED_BY, _run_rules). The #recovery line is unquoted and breaks on a path with spaces; use
  _callback.
- **S4:** #workspace is written for in-place runs too, and #rules holds all of COMMON, PROGRESS_REPORTING and the
  requirement rules.
  - Do not cite #rules, #blocked or #outcomes in place of packet text: refused obligations and awaiting/no_default
    stay inline.
  - Reconcile the anchor scheme with the proposals (REF/<file>.md#<slug>, absolute paths) before step 3.
- **S5:** slice.drive(first=False) logs the cleared session as "continued", so metrics.fresh_starts is [] and the
  G2 reorientation measure misses the clear. It should be fresh with reason "clear".

## Nits
- no_redo is graded for every host, though only Claude :inside is gated.
- clear.json "action": "" in the evidence.
- REDIRECT produces junk keys from heredoc bodies.
- Don't release reference.md alone (19 KB that nothing reads until step 3).
- shiploop-e2e-slice FlowTests is flaky (2 of 6 runs; actions[-1].stage == '?').

## Clean
keepalive STUCK = 2 x MAX (22). reference.md is deterministic, rewritten in save(), in the run dir, with no
credentials, and nothing cites it yet. No Improve wording. shiploop-reference 4 OK, keepalive 57 OK.
