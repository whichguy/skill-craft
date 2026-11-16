# Readiness: claims a script has proven

Nothing a model declares or proposes counts. A claim is ready only when a probe has run and printed a state from its ladder.
`loop readiness --manifest M [--campaign C] [--workspace WS] [--require-start]` runs the probes it is allowed to and reports the
state of every claim, whether the start rule holds, which claims it allows, and what blocks it. With `--campaign` it also **records**
the result (the claim states, `start_ok`, the allowed claims and the boundary hash it was run against) in the campaign.

| Claim id | Ladder (lowest to highest) | What reaching the top proves |
| --- | --- | --- |
| `cases.runs[:CASE]` | declared, **runs** | the case runs at the current build, writes evidence, and its cleanup receipt is verified |
| `grading.scores` | declared, **scores** | `evaluate` returns floors and measures for a real run |
| `grading.sensitive:PROPERTY` | unknown, **sensitive** | the measure separates a known-bad from a known-good for that property |
| `grading.calibrated:PROFILE` | unmeasured, **calibrated** | an A/A noise report exists for that profile (host, model, effort) |
| `improver.bounded` | declared, **bounded** | build and verify pass on the tip and a planted out-of-bounds edit is caught |
| `improver.invocable` | declared, **invocable** | the improver lands a trivial in-bounds change on a throwaway branch: plumbing only, never improvement quality |

**Start rule.** At least one `cases.runs` at `runs`, one `grading.scores` at `scores` and one `improver.bounded` at `bounded`.
`--require-start` exits 1 when it does not hold. A manifest that declares none of a kind cannot start. **The rule is a gate, not advice:**
`step` starts nothing until the owner has ratified the current boundary hash, a recorded readiness for that same hash shows the start
rule, and every selected case is released (an owner-gated case needs `approve` or `init --approve-case`). It prints `blocked` with the
reason instead, and exits 1.

**Allowed claims** follow from proven claims, not from the start rule:
- efficiency under an owner-stated tolerance, labelled "stated, not measured", once the start rule holds;
- quality claims about property P only with `grading.sensitive:P` at `sensitive`; with none, the report says so and allows no quality claim;
- measured efficiency on a profile only with `grading.calibrated:PROFILE` at `calibrated`;
- model-judged quality only for `evaluation_class: judge-only`, labelled with the recorded judge reliability. Whether such a verdict
  may *promote* a change is the owner's per-subject policy, not this skill's.

**Effect and ratification.** A claim's `effect` is `read-only` or `effectful`. An effectful probe runs commands, so it is not run
until the owner has ratified the boundary (`ratify --yes-owner-approved`, bound to `boundary_sha256`); until then its state stays at
the bottom of the ladder with the evidence "not run". An insensitive evaluator that returns valid scores is `scores`, never `declared`.
A probe may report `consumed`; it is charged to the campaign budget like any other work.

**Proving sensitivity.** Use, in this order of preference: a seeded defect the evaluator must catch; a known-bad build or tree
against a known-good one; an independently specified mutation of the subject; a metamorphic relation for a named property. If none
exists, the claim stays `unknown` and the report says sensitivity is unknown: do not guess.

**A refresh withdraws the old result first.** `readiness --campaign` records a not-passing result before it probes, so a refresh
that fails or is interrupted leaves the campaign unstarted rather than standing on the earlier pass. It must run in the campaign's own
workspace (`--workspace` may be spelled out but must equal it), and the recorded result is re-derived from its claims whenever the
campaign is loaded: a record that does not follow from them is malformed state.

**The recorded allowed claims travel.** The certificate and `report.md` repeat them, so a result is never reported with a stronger
claim than readiness allowed.

**A proven claim needs evidence.** A probe that reports a state above the bottom of its ladder without `evidence` is refused. The
recorded readiness keeps each claim's state and evidence, the boundary hash and the scoring identity it was proven under. When the
evaluator's scoring identity changes, the recorded claims no longer count (rerun `readiness`); a later readiness that fails the
start rule makes the certificate incomplete (check C7) and blocks the next start.

**A probe must be script-run, repeatable and honest about its limits.** Its `evidence` says what it did. A probe that checks one
property on one case certifies that property on that case, nothing wider.
