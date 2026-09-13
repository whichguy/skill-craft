# ShipLoop step-local microplan increment

**Completed historical plan — delivered in `3f79978`.** The original findings
and plan below describe the pre-change baseline; [implementation evidence](#implementation-and-review-evidence)
records the result. See the [proposal disposition index](shiploop-proposal-closeout.md)
for current dispositions; the deferred parser is not unfinished approved work.

## Decision and boundary

Adopt a compact execution microplan and a backward prerequisite check inside
the existing initial/Improve plan loop. Do not add a second scheduler, external
Backchain invocation, result schema, or per-row completion cursor. The global
DAG owns cross-step work; the local plan explains how one selected step will
achieve its already-approved outputs in the actual worktree.

The existing implementation already binds the plan, code, environment, knowledge
and suppliers to checked/audited passes. Its missing instruction is an explicit
local breakdown with evidence-bearing inputs. A new parser/version migration
would add compatibility cost without proving semantic prerequisite sufficiency;
defer it. The host reviews these semantics and authors meaningful planning
checks; the script retains the candidate and enforces existing evidence gates.

## Native Backchain application

Mode: **native-unvalidated**; no external packaging or scheduler-readiness claim.
The forward draft is guidance, durable roundtrip tests, then integrated review.
Dependency review asks whether existing Markdown carries local rows after context
loss (yes), whether a new schema is necessary (no), and whether local missing
authority can be synthesized as a row (no). Evidence: the current candidate
body, context projection, convergence and disposition paths in
`shiploop_step_planning.py` and `shiploop_protocol.py`. These are inspected facts,
not an assumption that the enhancement already works.

```json
{
  "goal": "Selected-step microplans are explicit, recoverable and scope bounded.",
  "initial_state": [
    "ShipLoop persists selected-step plan bodies in Markdown with digest bindings.",
    "Initial and Improve routes share the existing step-plan convergence gate."
  ],
  "steps": [
    {
      "id": "S1",
      "statement": "Initial, Improve and revision guidance defines a bounded local microplan.",
      "produces": ["The local microplan guidance is consistent across action routes."],
      "inputs": [{"need": "Initial and Improve routes share the existing step-plan convergence gate.", "from": null}],
      "origin": "seed"
    },
    {
      "id": "S2",
      "statement": "Cold recovery of local rows and prerequisite references is regression tested.",
      "produces": ["Cold microplan recovery has executable regression evidence."],
      "inputs": [{"need": "ShipLoop persists selected-step plan bodies in Markdown with digest bindings.", "from": null}],
      "origin": "seed"
    },
    {
      "id": "S3",
      "statement": "The integrated guidance and tests have been checked against the intended boundary.",
      "produces": ["Selected-step microplans are explicit, recoverable and scope bounded."],
      "inputs": [
        {"need": "The local microplan guidance is consistent across action routes.", "from": "S1"},
        {"need": "Cold microplan recovery has executable regression evidence.", "from": "S2"}
      ],
      "origin": "seed"
    }
  ],
  "parallel_groups": [],
  "unresolved": []
}
```

Backward review closes the integration need with both S1 and S2; neither
instruction text alone nor an unchanged roundtrip proves the entire improvement.
Forward verification orders their integrated check after both inputs. No new
world-state supplier, credential, installation or deployment is justified.

## Verification and limits

- Add red/green prompt/template checks and real-Git cold roundtrips on initial
  and Improve routes. Preserve source-draft deletion and tampering rejection.
- Check references, syntax/lint, existing packet/protocol/step-plan regression
  suites, and the ShipLoop-only plugin mirror. Independently challenge ordering,
  no-change plans, unresolved prerequisites, and context-loss behavior.
- Microplan rows are reviewed planning content, not machine-certified dependency
  proofs or separately replayable commands. Missing required prerequisites stay
  material/unresolved; a local plan cannot authorize new writers or change the DAG.
- The existing script-selected action/done interface and derived HTML report
  remain unchanged. Platform discovery, remote release controls, security/fuzz
  policy and scheduled maintenance are adjacent audit topics, not implementations
  included in this increment.

External check: the [planning self-critique study](https://arxiv.org/abs/2310.08118)
provides contrary evidence to treating repeated model approval as proof. This
supports retaining actual-worktree inspection, meaningful checks, unresolved
findings and fresh finalization rather than promising exhaustive backchaining.

## Implementation and review evidence

The initial, Improve and revision result templates now retain a local-work table
and backward check inside the existing Markdown candidate. Draft/review/apply
packets select the same guidance; no protocol version or result schema changed.
The cold CLI tests remove the actual submitted draft and recover local IDs,
prerequisite sources and case mappings from the stored candidate, including
after finalization. Existing digest, scope-disposition and repair guards remain.

Independent review identified current-prerequisite deferral and unsafe row
replay as boundaries to make explicit. Both are now prohibited in guidance.
The plugin mirror was regenerated from the canonical skill. A suspected absence
of packet-size assertions was disproved by the existing protocol tests; their
unchanged 7,000-character fixture limit actually caught this increment's longer
packets, including under the harness's longer temporary paths. Repeated prompt
text was shortened instead of increasing the limit or dropping test criteria.

An independent offline planning trial used a two-line local lookup function,
the supplied selected-step contract and selected planning-reference sections.
It produced a local code/fixture/test/doc sequence without inventing a remote
system or global DAG changes. Review exposed an unsupported runtime claim and
an attempted lint waiver. The latter motivated explicit missing-lint blocker
guidance. The revised trial keeps both readiness gaps open; no trial product
code, probe or test was executed. This is a useful observed failure/revision,
not a general semantic-quality certificate or a converged ShipLoop run.

Verification is scoped to this increment, not the full repository release
suite. The local harness's supplied-command `suite_scope=full` label describes
the selected command, not every ShipLoop test; its parser also does not count
successful default-unittest dots. Use the raw `Ran N tests` totals and package
audit result, not its zero parsed-case count, for this evidence.

The default Python could not run skill-creator's optional quick validator because
PyYAML is unavailable. No dependency was installed; the repository-native
frontmatter validator passed all 17 skill packages instead.

### Final validation

| Check | Observed result |
| --- | --- |
| `test/shiploop-packets.test.py` | 17 passed, including all draft/revision templates and six cold guidance roles. |
| `test/shiploop-protocol.test.py` | 33 passed, including the unchanged packet-size assertions. |
| `test/shiploop-step-planning.test.py` | Full 17-test rerun passed in 248.657 seconds; includes both expanded cold CLI routes, bound certificates, scope disposition and drift repair. |
| `test/shiploop-boundaries.test.py` | 10 passed. |
| `test/shiploop-evidence.test.py` | 8 passed. |
| `test/shiploop-until.test.py` | 7 passed. |
| Ruff on the five changed Python files | Passed. |
| `node test/skill-frontmatter.test.js` | All 17 packages passed. |
| `bash scripts/sync-plugin-views.sh --check shiploop` | Passed after canonical-to-plugin synchronization. |
| `git diff --check` | Passed. |
| Final read-only review | No remaining actionable findings in this increment. |

Total: **92 tests across six selected Python suites**, not the whole repository.
The full step-planning rerun preceded only the final missing-lint reference
clarification and its packet assertion; the final packet/protocol gate below ran
after that clarification. No state-machine or receipt behavior changed between
those checks.

Final audited gate: **PASS_CLEAN_SCOPED**, 50 packet/protocol tests, zero package
file deltas or blocking control findings. Run:
`/Users/dadleet/.grok/runs/test-harness/shiploop/20260912T152122Z-100f85`.
Its `report.json`, `report.html` and `round-1/stderr.log` retain machine result,
human report and raw test totals. This is a local test-hygiene report, not a
production deployment or a completed end-to-end ShipLoop delivery run.

### Generic ShipLoop improvement journal

- Broaden future offline planning trials beyond a local helper to exercise
  missing fixtures, permissions, configured lint and external-effect recovery.
  Keep expected unresolved findings in the fixtures; a fluent plan is not proof.
- Consider measured, bounded semantic-check helpers only when a corpus shows a
  useful failure they detect. Do not introduce a second task scheduler or claim
  that a row parser certifies prerequisite truth.
