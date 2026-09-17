# ShipLoop capability experiments

This directory contains the September 14, 2026 experiment apparatus, not a
production MCP server or a change to ShipLoop's runtime. The study compares an
additional capability-selection instruction against current public CLI packets.
The plan and final report live in `docs/`.

The published checkout includes regression apparatus and portable fixtures. Historical
task-owned reports, raw `evidence/` directories and `*.local.txt` study pointers
described below are optional local research artifacts, excluded from publication
and unnecessary for the hermetic regression tests. Operator trial reproduction
requires explicitly supplied runtime and study inputs; legacy study-copy paths
may no longer exist. The machine-specific `gas_reader.py` and
`platform-preflight.md` are also retained locally, not shipped or required by
hermetic tests. Command-execution trials still require macOS `sandbox-exec`.

The follow-up implementation is recorded in
`docs/shiploop-discovery-followup-implementation-2026-09-14.md`. Its conditional
async-result guidance extends the existing discovery policy; it does not require
MCP/skill selection at every checkpoint. New evidence belongs in
`evidence/followup-2026-09-14/`; the original `evidence/2026-09-14/` retains its
invalid scores, incomplete comparisons and frozen runtime hashes.

The local Checkers fixture exercises discovery, repair, served readiness and test
expansion. It is a deliberately small synthetic client/server system, not a
complete game or an emulator for Salesforce or Apps Script. Hosted evidence must
remain separate from fixture evidence.

## Components

| File | Responsibility |
| --- | --- |
| `fixture_setup.py`, `fixtures/` | Export public specifications and baked scenario sources; keep fault selectors outside worker roots. |
| `prepare.py` | Freeze public ShipLoop packets, local skill/catalog inputs and paired workspaces. |
| `run_trials.py`, `gateway.py` | Launch fresh Codex contexts with a cumulative action/time allowance and task-local file/command access. |
| `gas_reader.py` (local only) | Read one privately pinned Apps Script example through existing authorized tooling. No target override, new login, writer or deployment. |
| `grade.py`, `oracle-review.md` | Independently specified behavioral checks and test-suite mutation evaluation. |
| `semantic_rubric.json` | Preregistered observation/readiness criteria for blinded report grading. |
| `collect_blind.py` | Collect anonymized completed-arm evidence; keep the arm mapping private. |
| `summarize_runs.py` | Collect actual actions, durations, usage and cleanup without equating normal exit with success. |
| `preregistration.md` | Execution clarifications, caps, gating and retention policy. |
| `../../shiploop-capability-async.test.cjs` | Executes the existing HTML client with synthetic DOM/fetch, reverses two refresh completions, and compares a minimal in-memory sequence guard. No browser or remote service is exercised. |

## Running or inspecting a study

`STUDY_ROOT.local.txt` points to this machine's retained experiment directory.
It contains frozen runtime copies, prompts, input hashes, raw local receipts and
private grading material. It is not a portable install path. Private platform
source and account-specific identifiers must not be copied into repository
evidence.

The apparatus requires macOS `sandbox-exec`, a working Python runtime, the Codex
CLI with existing authentication, and the pinned local dependencies referenced
by preparation. The optional filesystem MCP package and its probe are cached
from the earlier discovery experiment, not downloaded by these trials.
`prepare.py` currently depends on that local cache. Apps Script preparation also
requires a separately established authorized target and existing reader; do not
infer either from a remembered project name.

Before a new study, create a new task-owned directory, freeze the plan, candidate,
runtime and evaluation inputs, and set its deadlines. Calibrate the fixed correct
reference and every hidden mutant before exposing any worker output. Verify an
actual public `next` and `complete` through the sandbox, alongside negative access
checks. Do not reuse completed arm directories or reset their budgets.

For the follow-up apparatus, the no-agent macOS completion preflight is:

```sh
task_study="$(mktemp -d /tmp/shiploop-capability-followup.XXXXXX)"
python3 test/experiments/shiploop_capabilities/prepare.py \
  --study "$task_study" --freeze-runtime
python3 "$task_study/frozen/runtime-v3/run_trials.py" \
  --study "$task_study" --preflight --deadline-seconds 300
```

Run these from the repository root. Freezing refuses a nonempty study. The
preflight needs Python and macOS `sandbox-exec`, but does not launch a model,
install an MCP server, or require platform authentication. Its result belongs in
that study's `reports/capability-runtime-preflight/result.json`. A successful
check establishes the tested local gateway/CLI route; it does not establish
Salesforce or Apps Script access.

An already prepared frozen study can be launched with:

```sh
python3 /absolute/study/frozen/runtime/run_trials.py \
  --study /absolute/study --arms explicit,prepared,arm,names \
  --parallel 4 --deadline-seconds 900
```

Use the runtime assigned in that study's manifest. The original eight September
14 screen arms used v1; later arms used a separately frozen v2 after a recorded
path-resolution correction. Never silently replace an earlier runtime receipt.

The launcher enforces a shared 64 gateway-action / 900-second allowance, including
both contexts of timing arms, with exploration cutoff at 56 actions or 780 seconds.
Commands can contain multiple HTTP requests; this is not a 64-request guarantee.
The two-capability/three-experiment instruction is a worker policy, not an
independently enforced counter. Overall deadlines and concurrency are recorded
in the study manifest.

## Interpretation limits

The sandbox separates workspace file data, but permits localhost traffic and
does not provide separate network namespaces. A clean trace establishes observed
behavior; it does not prove that cross-arm network access is impossible. The
runner's legacy `gateway_only` metadata describes observed tool routing, not
complete isolation. Treat these runs as exploratory evidence for prompt effects.

The frozen nominal reference passed the initial calibration, but expanded tests
later exposed malformed-actor failures, including a disconnected HTTP response
where the public contract calls for JSON 400. It remains unchanged to preserve
the original study. The follow-up repairs the current reference and recalibrates
the public HTTP contract separately. Do not reuse the old frozen reference as a
proven-correct reference or turn an invalid
mutation grade into a zero-quality score. Repair and independently recalibrate
any future reference revision before another test-quality claim.

The current r2 reference validates JSON actor types before membership checks.
Scored oracle cases use actual loopback HTTP, including malformed-body cases and
fresh-reader persistence checks. Direct `Store` diagnostics remain separately
labeled compatibility checks and are not public-contract scores. Optional
response metadata must not become a hidden correctness requirement.

Evidence-grade calibration and TEST require explicit `--mutant NAME=PATH`
arguments for all five declared families: `duplicate`, `stale`, `cache`,
`wrong_actor`, and `invalid_move`. Use distinct sources produced by
`fixture_setup.materialize_mutant()` and retain the generator/source hashes.
Missing, unknown, duplicate or reference-equivalent sources invalidate the set.
Calibration without mutant arguments is only a selector diagnostic; its
`diagnostic_passed` field is not an evidence-grade pass. Score receipts record
input hashes, selected checks and whether temporary grading workspaces survived.
Never reuse a nonempty case workspace.

For the follow-up, authoritative HTTP receipts belong in the coordinator's run
directory outside the gateway workspace. The worker-visible observation log is
only an inspection copy; mode bits alone are not an integrity boundary. Receipts
use a fixed allowlist, including requested actor class, status and persisted
version observations, and exclude raw bodies and credentials. A requested role
is not authenticated identity, and bracketing versions alone do not establish
causation during concurrent requests. Missing receipts remain evidence gaps.

The first blind collector omitted successful direct note/report operations and
successful CLI calls, creating a misleading timing evidence difference. Original
dossiers and the invalid first ranking are retained; corrected action metadata
is supplied separately. Receipt counts must include all observed actions even
when their instruction or private content is removed.

Keep application grades, accepted ShipLoop transitions, optional MCP use, actual
hosted reads, deployment and intended-user behavior as distinct results. A skill
read is not evidence that its procedure improved the result. A correct native
solution receives equal credit. Preserve ties, failures, skipped prerequisites,
false test failures, partial work and cleanup obligations.
