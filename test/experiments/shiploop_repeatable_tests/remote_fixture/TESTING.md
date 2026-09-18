# Retained test plan and evidence

## Boundary and harness decision

Initial revision: `02a54ab3449504e093a47828402c0ec0cbbd6de2`.
Repository inspection found only GUIDANCE.md, SPEC.md and PLATFORM.md: no runner,
dependencies, CI, production code or existing adequate tests. Those inputs remain
immutable. SPEC explicitly requests a new tiny fixture module, which is the only
product-like code authored here. Node's built-in test runner and `vm` suffice;
no packages, MCP client, network, credentials or remote services are used.

The supplied documents contain no manifest `T-` IDs, `produces` fields or behavior
model. The following local T- aliases identify verbatim SPEC acceptance strings;
they do not claim an absent upstream manifest. This matrix was written before
source implementation. Executable assertions will remain the detailed oracle.

## Criteria matrix

All remote cases execute in the Apps Script CommonJS module
`common-js/remote-repeatable-tests`; the local route executes the same definitions
in Node using simulated services. Local checks are `LOCAL-SYNTAX`, `LOCAL-TEST`
and `LOCAL-IDENTITY`; later remote checks are `REMOTE-EXEC` and `REMOTE-CLEANUP`.

| Cases / contract alias and exact acceptance | Preconditions / input | Expected observation | Planned selector / environment |
| --- | --- | --- | --- |
| TC-01 / T-01: “both arguments are nonnegative integers excluding booleans; reject invalid inputs; return their product.” | Stateless; zero, ordinary and integer boundaries | Independent exact products; no state | `runRepeatableTests(["TC-01"])`; local simulation and remote; LOCAL-TEST / REMOTE-EXEC |
| TC-02 / T-01: “both arguments are nonnegative integers excluding booleans; reject invalid inputs; return their product.” | Stateless; invalid values in either argument | Explicit errors, including booleans, fractions, negatives, missing/non-numeric inputs | `["TC-02"]`; local simulation and remote; LOCAL-TEST / REMOTE-EXEC |
| TC-03, TC-04 / T-02: “Also test project-local ScriptProperties using names beginning with a unique suite-owned prefix.”; “Preserve unrelated properties.” | Per-invocation and per-case property namespace; set/read/update fixtures | Exact values and deletion in finally; unrelated state unchanged; repeat and reverse order independent | `["TC-03"]`, `["TC-04"]`; local simulation and remote; LOCAL-TEST / REMOTE-EXEC / REMOTE-CLEANUP |
| NC-01, NC-02 / T-03: “Include stateful cases and controlled setup/assertion-failure injections, demonstrating cleanup and accurate failure reporting.” | Explicit-only controls create a sentinel then fail during setup or assertion | Failed case, preserved primary error and cleanup observation, no sentinel after teardown | `["NC-01"]`, `["NC-02"]`; local simulation and remote; LOCAL-TEST / REMOTE-EXEC / REMOTE-CLEANUP |
| Local orchestration checks / T-04: “Support selecting stable test IDs, a useful smoke selection, full selection, and explicit reordered selection.”; “Unknown IDs must be rejected explicitly.” | Full, smoke, explicit array/object; invalid and empty selections | Exact selected/executed membership and order, accurate counts; invalid selection errors before writes | `tests/local.test.cjs`; LOCAL-TEST; remote replay procedure |
| Local recovery checks / T-05: “Expose a read-only `inspectOwnedState()` for checking that no suite-owned property remains after a failed or interrupted invocation.” | Injected dependency and cleanup errors; residual owned state | Read-only inspection identifies residue; setup blockage / assertion failure distinguished; cleanup errors never hidden | `tests/local.test.cjs`; LOCAL-TEST; remote interruption procedure remains unrun |
| Identity checks / T-06: “Include a stable test-definition revision marker in results; external receipts will bind it to actual uploaded file hashes.” | Retained source bytes and revision marker | Local consistency only; later external receipts bind actual uploaded bytes | `scripts/verify.cjs`; LOCAL-IDENTITY; remote receipts unrun |

## Repeatable commands and lifecycle

Run from this repository with Node >=18 (observed v25.9.0). There is no install
step. Full local verification (syntax, canonical marker and all local regression
checks): `node scripts/verify.cjs`. This is the `verify` entrypoint requested by
GUIDANCE; no pre-existing `verify` command existed. Individual check commands are
`node scripts/verify.cjs --syntax`, `--identity`, and `--test`.

- Smoke: `node scripts/run-local.cjs smoke` (TC-01 and TC-03 only).
- Full retained suite, simulated: `node scripts/run-local.cjs full`.
- Focused stateful case: `node scripts/run-local.cjs '["TC-03"]'`.
- Reordered: `node scripts/run-local.cjs '["TC-04","TC-03","TC-02","TC-01"]'`.
- Controlled failure: `node scripts/run-local.cjs '["NC-01"]'` or `'["NC-02"]'`.
  Each intentionally exits 1 with failed:1 and successful cleanup, outside full.
- Focused lifecycle regression: `node --test --test-name-pattern='T-03' tests/local.test.cjs`.

The selector accepts omitted/`"full"`, `"smoke"`, nonempty arrays of stable IDs,
`{suite:"full"}`, `{suite:"smoke"}` and `{ids:["TC-03"]}`. Explicit arrays may
include negative controls. Empty, duplicate, malformed and unknown selections
throw before service access. `executedIds` means case dispatch was attempted,
including cases blocked by dependencies; each has a corresponding case result.
The CLI wraps results with an explicit local execution/target label and exits
1 for failures or invalid selection, 2 for blocked-only results, 0 for passes.

Each local test gets fresh in-memory data; interleaving checks deliberately share
one fake with distinct invocation keys. No local filesystem state is used by
the fixture. Stateless cases have no setup/teardown. Each stateful case owns its
own key, verifies deletion in `finally`, and preserves unrelated and old owned
keys. Local fault injection covers partial writes, denied cleanup and silent
deletion failure. Residue in these fault tests is deliberate, observed and
discarded with the fake; no remote cleanup is inferred. Repeated full/focused/
control cases run within the same fake to check residue and order independence.
No randomized seed is needed: UUIDs are deterministic distinct local counters;
real Apps Script uses `Utilities.getUuid`. No retries hide failing checks.

Full local verification is expected to take under a second on this machine;
remote cost/quotas remain unknown. The later remote route has a 30-second request
timeout, not an asserted suite duration. See [REMOTE.md](REMOTE.md) for exact
invocations, readiness, safe interruption handling, receipts and soft-trash.

## Revision marker and numeric boundary

`sourceRevision` is a reproducible SHA-256 marker of both source modules. Hash
the UTF-8 concatenation of each relative path, NUL, source text, NUL, in order:
fixture then suite. In the suite text alone normalize the one sha256 marker to
`sha256:SOURCE_REVISION_PLACEHOLDER` before hashing. `scripts/verify.cjs`
implements/checks this definition and prints SHA-256 of each actual file too.
After an intentional source change regenerate with
`require('./scripts/verify.cjs').identity()` and replace the marker literal.
The marker excludes its own literal to avoid a self-hash and is not a remote
attestation. `testDefinitionRevision` is the stable label `repeatable-tests-v1`.
External upload/execution receipts must bind these to actual uploaded file
hashes. Selection never accepts a caller-supplied digest.

The fixture uses JavaScript Number integer semantics, matching the specified
function/runtime. It does not invent a safe-integer cap or arbitrary-precision
currency API. Finite integer arguments are accepted; products follow Number
multiplication, including its representability/overflow limits. Cases include
zero and the safe-integer boundary without deriving expectations from the code.

## Observed outcomes and remaining obligations

Initial assembled `node scripts/verify.cjs`: exit 0, all three local checks
passed; 11 tests, 11 passes, 0 failures/skips. The implementation worker's earlier
concurrent harness run reported 2 passes and 9 identity-assertion failures while
the revision placeholder was still present. This was assembly evidence, not a
product-behavior RED: filling the canonical marker resolved it; no behavioral
oracle or input document was changed. Worker report is attributed, not a retained
raw transcript. Current exact commands, environment, hashes, results and exit
codes are retained in `evidence/authoring-checks.txt`; that receipt is bound to
the authored source hashes and initial revision above. Later candidate-bound
Improve evidence lives in `.until-loop/evidence/` and `.until-loop/working.md`.

Remote creation, upload, Apps Script compilation/HEAD execution, reruns, live
permissions/concurrency/timeout behavior, identity confirmation and soft-trash
are NOT RUN, assigned to the later remote operator. No MCP client, network,
credentials or remote services were used. The combined local-plus-remote suite
has NOT RUN. No UI/accessibility, mail, documents or triggers are in scope.

Adequacy: all normal stable cases are registered in full and independently
selectable; both controlled failure cases are explicitly selected by the local
regression checks. Exact product/error assertions, state/value assertions,
selection/count reconciliation and cleanup fault checks provide behavioral
coverage rather than file-existence evidence. No pre-existing tests were removed
or weakened. The absent manifest/behavior-model links in generic GUIDANCE remain
documented inputs, not invented requirements or remote proof.
