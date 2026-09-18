# Improve review one — global plan

## Candidate, scope, and history

- Frozen producer candidate: `<study>/new/run/notes/global-plan.md` at SHA-256 `f70908cb6049a90a1f2c3797085a3df6c31b6b363fb8fa2bc0f5a4b31ef17e51`.
- Scope was limited to that plan and its immediate controlled/spec/test inputs. Product source, all run notes/state/results, frozen guidance, target, and consumer boundaries were read-only. Child writes are confined to this `.shiploop-improve/.../nav-5a5e9e2846cb4077af072160793107c5/` tree.
- Fresh history read: `ec3243d658e24304b306749bc361869154fc4660` — `Fixture: freeze accepted request and controlled target facts`; no older commits exist. History is context only and granted no authority.
- Fresh status reports only untracked `.shiploop-improve/` evidence. Current source and plan digests and the controlled fixture probe are retained in `cycle-one-history-stdout.txt`, `cycle-one-status-stdout.txt`, `cycle-one-source-digests-stdout.txt`, and `cycle-one-probe-stdout.json`.

## Review and decision

The earlier independent producer review found, and the source plan corrected, a durable-authority issue: accepted integration decisions must be linked from W1's repository-owned requirements authority rather than exist only in run evidence. That correction remains applicable.

This distinct review found a material scheduling defect. Original W2 combined the API/packaging contract with actual target and consumer authority, while original W3 made W2 a direct prerequisite even though W3 only bootstraps a local source/test carrier. The read-only dependency audit returned `bootstrap_overgated_by_target_consumer_authority: true` (`cycle-one-dependency-audit-stdout.json`). This would prevent independent local bootstrap whenever external target/session access was absent.

The authorized child-only correction is `global-plan-corrected-decision.md`. It places local bootstrap at W2 after W1, moves API/persistence/asset decisions and durable publication to W3, makes pure behavior W4 depend on W2/W3, preserves local-only UI checks at W5, and reserves real target/API/consumer authority, T-09, and T-10 for W6. The revised generic parent result is `final-result-draft.json`; it will be supplied as `final_result` only after the runtime reaches terminal completion. The producer plan note was intentionally not rewritten.

## Checks and limits

- Current controlled platform probe passed as a fixture observation, not a deployment check.
- The pre-correction dependency audit truthfully failed and identified the material edge.
- `cycle-one-corrected-plan-check-stdout.json` passed: it parses the revised generic result, verifies every referenced artifact, confirms W2 is no longer gated by target/consumer access, W3 publishes durable decisions before behavior work, W4/W5 consume those decisions, W6 owns the real boundary, and confirms the source plan was not rewritten.
- No Node/product tests were run or claimed green; the historical zero-test baseline remains missing coverage. No target/API/consumer action, deployment, installation, or commit occurred.

## Assessment

Classification: **non-trivial**. The dependency correction is material even though it is contained in child-owned evidence and the final result draft. Exit assessment: **unsatisfied** because the required two consecutive distinct trivial-only reviews have not occurred. Continuation: **allowed** for a fresh review of the corrected decision and current evidence. The material finding resets the runtime trivial streak.
