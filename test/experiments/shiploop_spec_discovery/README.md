# Planning improvements: benefits, costs and regressions

Small supported improvements with little consequence are viable to retain. This
evaluation keeps useful refinements and resource trade-offs visible even when
coarse quality scores tie. It also preserves regressions instead of subtracting
them from gains in a single score.

## Reproduce the arithmetic

From any checkout with Python 3 and no third-party dependencies:

```sh
python3 -B test/experiments/shiploop_spec_discovery/compare.py \
  test/experiments/shiploop_spec_discovery/replay.json
python3 -B test/experiments/shiploop_spec_discovery/test_scoring.py
```

The first command prints the paired comparison and aggregate summaries. Keep its
output alongside `replay.json`, which retains provenance and unpaired grade details. `--output /path/to/new.json`
writes a new file and refuses to overwrite an existing result. Neither command
calls a model, reads an external run archive, or changes a historical result.
The tests are also registered as the `planning-score` core suite; edits anywhere
in this directory select it in quick CI.

[replay.json](replay.json) is an explicitly identified arithmetic projection:
trial/pass identity, validity, nullable anchors, obligation statuses, findings,
resource vectors and provenance hashes. It reproduces the published tables using
the validity labels supplied by the original evidence checker. It does **not**
revalidate quotations, artifact roles, full-packet delivery or model behavior.
The complete original packets, tool output, failed attempts and judgments remain
unchanged in the owner's retained archive. This compact file was never substituted
for the full evidence in a judge prompt.

## What the comparison established

Seven retained subjects were regraded twice with fresh Sol 6.1/high sessions.
All fourteen calls completed; thirteen grades validated. One pass on unpaired
current trial 16 was invalid because a finding lacked subject-artifact evidence.
Both matched pairs have all four valid judgments. Repeated grading does not add
independent subject replications.

| Matched case | Consistent quality gains | Consistent regressions | Other observations |
|---|---|---|---|
| API parity, trials 13/14 | None on the ordinal anchors | Verification closure: current 3/3, candidate 0/0 | Actionability and grounding have judge disagreement; prerequisite anchors tie |
| No-reference CLI, trials 01/02 | None on the ordinal anchors | None on the ordinal anchors | All four dimensions tie; minor candidate findings remain visible |

Candidate API recorded the socket denial accurately in its initial strategy,
where current API first recorded intended success and then corrected it. It also
made a passing unchanged-reference characterization suite an explicit prerequisite
before application RED tests. These are useful process/readiness observations,
not proof the prompt caused a general improvement. The latter pattern also occurs
in unpaired current trial 16, and its additional implementation effort was not
measured. An apparent relative-path harness improvement was rejected after finding
equivalent targeting in the baseline's incorporated environment document.

Candidate API's accepted Spec required HTTP evidence before acceptance, while its
Plan permitted a skip without an equally explicit closure condition. A later
operator, command and test were named: this is a handoff inconsistency, not an
absent requirement or an observed defective release. The same type of gap also
appears in an unpaired current run. Minor scope/probe-attribution repairs do not
automatically erase other benefits; material verification defects remain distinct.

| Original subject resources, candidate vs current | Cached input | Uncached input | Output | Elapsed |
|---|---:|---:|---:|---:|
| API pair | −17.63% | +8.37% | −29.98% | −24.26% |
| CLI pair | −37.19% | −8.43% | −22.88% | −20.84% |

These are descriptive observations from an audit-selected subset. The full twenty
attempts instead show uncached input +7.29% and median duration +3.09%, alongside
cached input −5.03%, output −1.24% and summed duration −2.64%. Aggregate summaries covering all twenty attempts are retained in the replay input
and carried forward without recomputing them; individual observations remain in the
original archive. Original runs overlapped
other work; the no-reference case is a conditional-negative control. Neither
table proves a causal speedup, statistical non-degradation or a dollar saving.

## Scoring and retention

The [exact revised rubric](rubric.md) grades acceptance actionability, evidence
grounding, prerequisite handoff and verification closure separately: 0 material
defect, 1 minor repair, 2 usable, 3 useful refinement; unavailable artifacts get
null. A gain requires both candidate scores to exceed both current scores.
The reverse is a regression. All-equal anchors tie; other overlaps remain judge
disagreement. A one-anchor gain is sufficient; no large-effect threshold applies.
Missing or invalid passes cannot confirm a contrast, and duplicate passes are
rejected. Corrected process findings remain distinct from surviving final issues.

Qualitative observations are kept separately so useful improvements within a
coarse anchor are not lost. They require counterpart evidence and a consequence,
not merely more words, headings, tests or steps. Minor costs and repairs are
considered in retention judgment; the comparator does not automatically promote
or veto a candidate. Cached and uncached input, output and time stay separate.
Unknown, negative or non-finite resource observations cannot establish dominance.

The initial revised calibration failed and remains retained. A separate revision
corrected its evidence adapter and synthetic fixtures; all thirteen controls then
passed. The original local scorer passed eighteen offline tests and every measured
full input/answer/usage binding verified. This portable arithmetic extraction has
its own regression tests. It makes no new live-model or product-delivery claim.

The original twenty-cell prediction remains **inconclusive**, with thirteen
bundles held and unsent. The owner-directed incremental retention decision is
separate from that unchanged experiment. The publication records the methods and
observations; it does not relabel the original prediction or its failed checks.
