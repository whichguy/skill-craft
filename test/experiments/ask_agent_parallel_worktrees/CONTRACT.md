# Ask Agent parallel experiment contract

This directory is an experimental harness for measuring a native Grok or Claude Code parent
delegating a fixed fixture task to three or five Ask Agent workers. It is not an
Ask Agent runtime, scheduler, plugin, or security boundary. The current source
of truth for a trial is its retained `manifest.json`, operator records, raw
native events, worker receipts, and independent verification reports.

## Portability boundary

The scripts use Python 3.10 or newer and the Python standard library. Git is
required for fixture and worktree operations. Live runs require an already
authenticated Grok Build CLI that exposes the typed native background-worker
tools used by the auditor. The harness does not install the CLI or alter its
global configuration. The target host boundary is macOS/Linux with POSIX file
and Git behavior. Current live qualification is macOS only; Linux and Windows
execution are not established by these retained trials.

The run directory is disposable experiment data, not a sandbox. Git worktrees
separate ordinary writes made through the assigned cwd, but they do not stop a
worker from deliberately accessing other paths, shared Git data, or external
services. The parent prompt narrows the requested work; it does not enforce an
OS permission boundary.

## Phase sequence

### Suite command

`python3 -B suite.py [--suite SUITE] [--list] [--output PATH] [--live] [--case NAME] [--skill-root PATH] [--seed-feedback-backlog] [--seed-compact-ignore-controls] [--grok-binary PATH] [--model MODEL] [--effort EFFORT]`

`--list` prints the available suite cases and makes no model call. The default
suite is the offline `harness`; `SUITE` is `harness`, `smoke`, `functional`,
`timing`, `optimization`, `scripted`, `packet`, or `compact`. Live suite names require `--live` and
a new `--output` directory. `--case` must name a case in the selected suite.

### One case's command sequence

The offline harness does not start a model. A live suite requires explicit
`--live` and a new output directory. One case runs these commands in order:

| Phase | Command shape | Required record or effect |
| --- | --- | --- |
| Prepare | `python3 -B fixture.py prepare --run RUN --workers N --mode MODE [--hold-seconds SECONDS] [--seed-feedback-backlog] [--skill-root PATH]` (`N` is 3 or 5; `MODE` is `parallel` or `sequential`.) | Creates the primary repository, one-commit-ahead dirty caller, frozen package copy, task assignments, probes directory, and `manifest.json` with `schema_version: 1`. Run directory must be absent or empty. |
| Prompt | `python3 -B prompts.py --run RUN --workers N --mode MODE --treatment TREATMENT` (`MODE` is `parallel` or `sequential`; `TREATMENT` is `baseline`, `batched`, `scripted`, `packet`, or `compact`.) | Writes one immutable `operator/parent-prompt.txt`, records treatment identity, and copies the fixture, operations, controller, audit, suite, prompt, briefs, worker-phase, diagnostics, and contract files beside it. A prior `launch.json` prevents replacing the prompt. |
| Launch | `python3 -B controller.py launch --run RUN [--grok-binary PATH] [--model MODEL] [--effort EFFORT]` (`EFFORT` is `low`, `medium`, or `high`.) | Starts only the Grok parent. It records `launch.json`, raw `stdout.jsonl`, `stderr.log`, parsed `observed.jsonl`, process result, and export results. Native host tools own child preparation, spawn, wait, and collection. |
| Probe | `python3 -B fixture.py probe --run RUN --worker ID --phase PHASE` (`PHASE` is `start` or `finish`.) | A child runs `start` before edits and `finish` after its owned edit, from its assigned prepared worktree. Each probe writes a per-worker record and reports checks plus errors. |
| Filesystem verification | `python3 -B controller.py verify --run RUN` | Requires valid `operator/process-result.json`, verifies frozen input hashes, and makes one fresh fixture verification attempt. It writes `post-exit-result.json`, which passes only when the parent exited zero, input integrity passes, and the fresh fixture report passes with verifier exit zero. The attempt is immutable, including failures. |
| Native audit | `python3 -B native_trace.py --run RUN` | Reads session-bound native updates and observation timestamps. It does not launch workers and does not treat child narrative as proof. It writes `operator/native-verification.json`, records the post-hoc auditor path/hash, and archives a different prior report under `operator/audit-history/`. |

The optional scripted setup/integration treatment uses
`python3 -B operator/operations.py prepare-batch --run RUN` once, then
`python3 -B operator/operations.py integrate-batch --run RUN --collected-worker ID`
with one repeated `--collected-worker` for every manifest worker. Those IDs are
parent assertions only; the native auditor owns lifecycle evidence.

### Compact treatment

The `compact` suite runs the production `ask_agent_task.py` interface through
the fixture harness. Its caller prompt invokes `operations.py prepare-batch
--compact` once, then `briefs.py --compact` once. Preparation retains each full
production result and binding on disk. `briefs.py --emit-worker ID` prints only
that worker's bounded native argument object, which the parent passes unchanged
to the native spawn tool. It does not print all worker prompts in one Bash
result.

Each emitted worker prompt is derived from the production task script prompt.
Its start and finish wrappers each invoke the production `worker-start` or
`worker-finish` exactly once with the same retained `--binding` file, while
recording the fixture context checks and probes. The worker must not separately
repeat those production commands. After the parent collects every actual native
result, it runs `operations.py verify-return --worker ID` once per worker and
only then calls the existing guarded `integrate-batch`. The integration gate
requires every retained compact verify-return record to bind the same task,
package, workspace, and receipt.

Native qualification checks each parent emission and spawn against the retained
per-worker assignment. It also requires each native child transcript to show
its exact start and finish wrapper invocations and the matching successful raw
production command records. A probe file or parent-created command record alone
cannot satisfy that gate. Compact trials seed a dirty `.gitignore`, an ignored
root `.claspignore`, and an unrelated ignored file; child snapshots must retain
the root control and omit the unrelated ignored input without changing caller
state. These trials compare the compact API plus fixture instrumentation and
do not establish a pure production speed improvement. Fresh compact v2
treatment prompts use fixture.py verify --summary and require one complete,
untruncated summary JSON object with exit zero, passed true, and no errors.
The full verification.json remains unchanged for controller and auditor use.

The suite records each exact argv and exit code in `suite-result.json`. It stops
on the first unsuccessful phase, preserves the run, and does not retry it. It
pre-records each selected case as `NOT_RUN` before the campaign, then marks
only the active case `RUNNING`. If launch returns nonzero but left a
`process-result.json`, the suite still attempts post-exit verification and the
native audit so those diagnostics can explain the failed launch. Any nonzero
phase exit prevents campaign success, even when a later report looks clean.
`suite.py --list` and the default `harness` suite are offline. Live execution
requires `--live`, `--output NEW_DIRECTORY`, and an explicit live suite name.

### Fixture manifest and report

The manifest records `run_id`, mode, worker count, hold duration, task
assignments, package tree hash, primary/caller snapshots, and all run paths.
Worker IDs are the strings `1` through `N`; the assigned file for worker `i` is
`src/step_i.py`. The required formula is `(i+1)*x + i*i`. Each worker inherits
the caller's dirty state, including staged, unstaged, untracked, and deleted
inputs. Only the assigned task modules may change in the caller after patch
integration.

`fixture.py verify` writes a JSON object with `schema_version: 1`, a boolean
`passed`, a `checks` object whose values are booleans, and a list of `errors`.
The fixture gate is `passed is true` and every required `checks` value is the
boolean `true`. A process exit of zero without that report does not prove a
pass. The default verify command prints the full report. Optional
verify --summary changes stdout only: it emits schema
ask-agent-fixture-verification-summary/v1 with the run ID, exact pass state
and errors, check count, sorted failed-check names, absolute report path, exact
saved-byte count, and SHA-256 of verification.json. It never truncates errors.
The full verification.json is retained unchanged in either mode, and the
process exit status is still determined by the full report. Fresh compact v2
and baseline/batched v5 parent prompts use summary-v1 in a separate native
tool call; fresh packet/scripted v4 records use verification_output=legacy.
Historical compact v1 and baseline v4 records remain legacy.
Probe and verification reports also have adjacent
`*.diagnostics.jsonl` records. Operational fixture errors emit a diagnostic to
stderr and exit 2. The fixture CLI still uses argparse for malformed argument
syntax, with its normal usage text and exit status 2.

### Native report

`native_trace.py` writes schema `ask-agent-native-verification/v1`. Its top
level includes `status`, `passed`, `native_status`, `native_passed`,
`combined_classification`, `checks`, metrics, evidence, and limitations. Each
native check is an object with a `status`, explanatory `detail`, and zero or
more evidence locators. Check statuses are `PASS`, `FAIL`, `INCOMPLETE`, or
`UNKNOWN`. Missing evidence is incomplete; inaccessible typed fields are
unknown. Neither is a pass.

The standalone HTML report also requires a passing nonempty integrity record and
the controller post-exit gate, consistent with the process exit and fresh file
report. Earlier runs lacking that controller record are incomplete under this
current rule; the report retains their native and original suite classifications.

An unqualified live suite pass requires zero exit codes for every required
phase, `post-exit-result.json` with `passed: true`, and the final native report
with `status: "PASS"`, `passed: true`, `native_status: "PASS"`, and
`native_passed: true`. Native success does not override a failed or incomplete
filesystem verifier, and filesystem success does not establish native
launch/collection behavior. The `auditor_implementation` SHA identifies the
post-hoc auditor used for the report; it does not establish which implementation
ran at launch. If a later audit produces different bytes, the previous report is
copied to `operator/audit-history/` under its content hash before replacement.

## Pass gates

The gates are evidence checks, not confidence scores:

1. The frozen package, manifest, prompt, controller, and copied apparatus hashes
   still match where the run recorded them.
2. Every worker has a unique real Git worktree and index, with the expected
   common directory and the exact inherited dirty inputs.
3. Start and finish probes bind each worker, its run ID, its actual root, and
   its sole owned task path. The same ignored marker path with distinct values
   is a filesystem separation probe.
4. Each worker's implementation passes its independent task oracle. The
   integrated bytes match the worker outputs, all integrated task oracles pass,
   and the composed pipeline matches the independent expected values.
5. The caller retains its frozen HEAD, semantic index, staged and unstaged
   content, untracked inputs, and all unrelated files. Only the permitted task
   paths may change.
6. The native trace binds one typed spawn to each manifest worker and prepared
   cwd, binds collection to the same parent session, records all required
   terminal child results, and shows a valid parent terminal event.
7. A `timing`, `optimization`, or `scripted` comparison keeps every case's
   mode, worker count, hold, prompt treatment, and model settings in its
   manifest and suite record. Hold intervals are instrumentation and are
   excluded from model throughput comparisons.

For a parallel case with a positive hold, every worker's hold interval must
overlap by at least 0.1 seconds. This establishes only overlap of the recorded
probe holds, not useful work overlap or CPU parallelism. A sequential case has
the corresponding sequential native launch/collection order gate: each previous
child must have a typed terminal collection result before the next launch. A
collection call beginning is insufficient. Unknown manifest modes cannot pass.

The native verifier maps only known check names to the diagnostic categories in
`diagnostics.py`. It does not turn an unmapped future check or free-form error
string into a generic failure claim. Keep the original report when extending
the check map.

## Proof precedence

Native audit records filesystem verification history separately. Its current
filesystem source is selected in this order:

1. `post-exit-verification.json`, when available;
2. otherwise `verification.json`;
3. otherwise `parent-verification.json`.

The controller writes `post-exit-result.json` as the immutable summary. Its
`passed` value requires parent exit code zero, successful frozen-input
integrity, a newly generated `post-exit-verification.json` with `passed: true`,
and verifier exit code zero. A missing or stale report cannot satisfy the
fresh-file condition. A nonzero parent exit does not make verification pass,
but when `process-result.json` exists the suite still runs verification and
native audit to retain their evidence.

The selected current report determines the current filesystem result. A
current failure remains `FAIL`. A current pass after any earlier recorded
failure is `RECOVERED`, which preserves the historical failure. If a prior
failure exists but no current report is available, the result is
`INCOMPLETE_AFTER_FAILURE`. The suite's unqualified pass gate accepts only
`PASS`; `RECOVERED` is informative evidence, not a clean trial pass. A
post-exit report does not replace, merge with, or cure a failed native
lifecycle audit.

## Diagnostic schema

`diagnostics.py` is a shared formatter and report-check mapper. The fixture,
controller, suite, and native-audit CLIs import it for operational and
acceptance diagnostics; the optional integration script can use the same helper
for its structured result. Malformed CLI arguments still use argparse's normal
usage message and exit status 2. The JSON object schema is
`ask-agent-diagnostic/v1`:

| Field | Meaning |
| --- | --- |
| `code` | Stable uppercase category identifier. |
| `severity` | `error` for a verified failed check or operational failure; `warning` for incomplete or unknown evidence. |
| `phase` | The command or lifecycle phase that observed the condition. |
| `expected` / `observed` | The exact mapped invariant and the verifier value or check object. |
| `rationale` | Why that invariant matters to this trial. |
| `rationale_ref` | A frozen link to one of this document's anchors. |
| `evidence` | Actual filesystem paths, precise JSON pointers or source line numbers, and a SHA-256 when a referenced path is an existing regular file no larger than 1 MiB. |
| `recovery` | Evidence-preserving next action. |
| `retry_safety` | Whether the attempted operation may be repeated. |

`evidence_reference(path, ...)` keeps the path even if it is missing. It adds
`sha256` only after reading a bounded regular file; `hash_status` explains why
no hash was produced. A report citation has a JSON Pointer to the exact check.
For nested native evidence, `report_pointer` points back to the locator inside
the report and `line` identifies the source event when the verifier supplied
one. A missing source path remains a missing citation; the helper does not
invent replacement evidence.

`report_check_diagnostics(report, report_path, phase=...)` maps known fixture
boolean failures, native `FAIL`/`INCOMPLETE`/`UNKNOWN` check records, and
operations `integrity_checks` records whose `passed` field is false. It
preserves the report's exact check value as `observed`. For an integration
check whose `failure.phase` matches, it also cites that failure's action path.
Unmapped checks produce no diagnostic until they have a specific rule. Callers
may pass an explicit rule map for a new, reviewed check; the helper will not
guess its meaning.

```python
from diagnostics import emit_diagnostics, report_check_diagnostics

records = report_check_diagnostics(report, verification_path, phase="verify")
emit_diagnostics(records, jsonl_path=operator_dir / "diagnostics.jsonl")
```

For an operations result whose structured failure was caused by a command
failure rather than an `integrity_checks` row, call
`operation_failure_diagnostic(result, result_path)`. It recognizes only the
stable failure codes currently emitted by `operations.py`; unknown codes remain
raw evidence for a future rule.

For an operational error that is not represented by a report check, the caller
supplies an explicit expected value, observed value, evidence locator,
rationale, recovery, and retry policy:

```python
from diagnostics import evidence_reference, exit_with_diagnostic, make_diagnostic

record = make_diagnostic(
    code="PATCH_CONFLICT",
    severity="error",
    phase="patch-check-2",
    expected="git apply --check exits zero",
    observed={"exit_code": 1, "stderr": conflict_text},
    rationale="The immutable worker patch does not apply to the current caller state.",
    rationale_ref="CONTRACT.md#retry-safety",
    evidence=[evidence_reference(action_record_path)],
    recovery="Keep prior applied modules and inspect the conflict record and patch.",
    retry_safety="Do not rerun integration; reconcile the retained partial state first.",
)
exit_with_diagnostic(record, jsonl_path=operator_dir / "diagnostics.jsonl")
```

`exit_with_diagnostic` emits one JSON line to stderr and exits with status 2.
The standard `argparse` syntax/usage errors may continue to use
`ArgumentParser.error`, which also exits 2. Operational errors after argument
parsing should use the shared helper so their expected/observed values and
evidence survive in the run record.

## Evidence references

Use only paths returned by the verifier, controller, fixture, or operation
record. A path to an absent file is still useful evidence of a missing record;
it must not be given a digest. An event line number is evidence only when the
source verifier supplied it. JSON pointers use RFC 6901 escaping (`~` becomes
`~0`, `/` becomes `~1`).

The JSONL target is optional and caller-selected. Current callers use
report-adjacent `*.diagnostics.jsonl` files for fixture and native reports,
`operator/controller-diagnostics.jsonl` for controller failures, and
`diagnostics.jsonl` at the suite output root. The helper appends one compact
JSON object per line and fsyncs the append. It expects one writer per run; it is
not a multi-writer coordination or tamper-proof log. Keep the source reports
and raw logs alongside it.

## Retry safety

Each live suite case and each parent launch has one evidence history. The
suite stops at the first unsuccessful command and retains later cases as not
run. A new attempt uses a new output directory; do not overwrite or silently
resume a failed case.

`controller.py verify` requires a completed parent process and refuses to
replace an existing post-exit report. Keep pre-exit, parent, and post-exit
reports as separate records. If the frozen inputs fail their hash check, stop
before interpreting a refreshed filesystem report as proof about the original
trial.

`operations.py integrate-batch` is test-only patch integration. It accepts
parent-supplied worker IDs as assertions and cannot prove native spawn, wait,
or collection. It applies immutable baseline-relative patches serially to the
caller after explicit returned-patch checks. It does not create a merge commit
or combine whole worker branches. If a later apply or check fails, preserve
receipts, immutable patch copies, call logs, and already applied modules. Do
not auto-rollback or rerun integration over that partial state. Inspect and
reconcile it, then use a fresh run if another attempt is needed.

## Ambient hooks

`--seed-feedback-backlog` is an explicit fixture variant. It seeds a tracked
backlog file in the primary baseline for a selected treatment. It does not
disable or neutralize Grok hooks, plugins, extensions, or `SessionEnd` behavior.
If `grok inspect --json` returns usable data, `controller.py` retains selected
host-profile fields, including hooks and plugins. If it fails or returns
unparseable output, that absence is evidence to preserve; it is not evidence
that no ambient hooks ran. Attribute an observed side effect only when the
retained event evidence supports that attribution.

## Integration boundary

The experiment tests a small deterministic file task and filesystem
separation. The relative marker collision intentionally probes worktree
isolation; it does not test hostile path access. The helper-managed child
worktrees share Git common data by design. No result supports a production
security claim, broad feature-development speedup, or a true merge/commit
integration claim.

## Script-generated packet arm

`briefs.py --run RUN` validates prepared bindings, repeats prepared-state inspection
against each current child, and saves the exact launch arguments in an exclusive
`operator/dispatch-packet.json` before emitting them. It never launches a model.
The native auditor compares the actual launch fields to that retained packet;
missing or mismatched evidence blocks a pass. It also binds the retained packet
to the typed script-output event so rewriting the packet later cannot hide a
changed launch. For the observed Grok output truncation, the auditor requires
the exact root-session terminal log, matching byte count and captured head/tail,
and an immutable retained copy; missing full output remains incomplete. The parent must send those arguments
through its native tool and collect actual terminal results. This arm reads the
selected skill card, then uses the frozen scripts for managed-route mechanics
instead of rereading route appendices. It is an explicit experimental workflow
substitution; comparisons must identify that change.

This Grok-specific packet publisher enforces a 20,000-byte complete-output
budget, based on the retained 1.0.46 truncation event. An oversized packet fails
before publication or dispatch with `DISPATCH_PACKET_TOO_LARGE`, the expected
limit, actual serialized byte count, and manifest/setup evidence. This is a
transport qualification limit, not a universal model context limit. Use a new
run with shorter paths or a separately tested transport revision after diagnosis.

`worker_phase.py --run RUN --worker ID --phase start|finish` is a worker-side
mechanical wrapper, introduced in treatment version 4 to keep generated briefs
below the host's observed tool-output limit. It requires the actual current Git
root to equal the assigned child root and preserves one attempt per phase.
Start verifies helper context and records the existing start probe. After the
native worker edits its one owned file, finish runs its oracle, records the
finish probe, and inspects returned patch delivery. Exact commands, output,
failures and contribution references are retained per worker and phase. It
never implements task code, launches models, stages, commits or integrates.
The native worker remains responsible for its edit and inline handoff.

`briefs.py --run RUN --parent-oracle` writes the independent expected composition
outside the caller. It runs only after native dispatch. It does not implement
or execute child source modules. This artifact is supporting parent work, not
an acceptance oracle that could replace the fixture's independent checks.

The integration CLI emits a compact summary after persisting the complete
`integration-result.json`; full call output, checks, failures and partial apply
state remain in that record. A compact response requires both `INTEGRATED` and
passing fixture verification. Native lifecycle qualification remains separate.

## Compact packet transport and result index

Compact treatment version 4 binds each production packet to its expected digest
in the native wrapper command, underlying worker start/finish commands and the
parent return check. The prepared raw binding is retained outside repositories.
The worker start response carries the validated task and mode-specific rules.
Consumers use structured commands; exact prose substitution is not an interface.
File digests detect mismatches, not malicious-process access or native identity.
A generated v4 prompt requires matching treatment metadata before launch.
Retained v4 setup or result-index markers also require that metadata during the
native audit; deleting it cannot downgrade the run to older, weaker gates.
Missing or contradictory metadata prevents qualification.

The parent supplies actual native handles to `operations.py write-parent-result`
with repeated `--worker-handle ID=HANDLE` arguments, preserving duplicate IDs
for rejection. It also supplies the successful fixture summary's
`--verification-sha256` and integration/finalization summary's
`--integration-sha256`. The writer accepts only the complete expected worker set
and matching successful evidence from this run. It does not perform native
collection, semantic acceptance, task execution or a second integration.

Result creation is exclusive. Each retained record has a concrete locator and
content hash; verification distinguishes the checked `verification.json` from
its later controller archive `parent-verification.json`. The writer must not
present that future archive as already created. The native audit checks the
actual launch handles and original verification hash after controller archival,
and detects replaced indexed records. Indexed handles remain parent assertions
until that independent check. A failed writer or audit preserves existing
files, caller contributions and worker scratch for diagnosis; no automatic retry,
overwrite, cleanup or claim of success is permitted.


## Claude native evidence

`claude_suite.py --suite delivery-qualification --live --output NEW_DIRECTORY`
selects a separate Claude host adapter. The five phases are shared fixture
preparation, Claude prompt preparation, Claude launch and transcript capture,
shared post-exit verification, and the frozen Claude native auditor. Live
cases preserve the same `commit3-a`, `commit5-a`, and `ephemeral3-a` semantics.
Offline Claude adapter tests and `--list` must never launch a model.

The controller starts one parent process, never worker model processes. It
records requested model/effort, CLI identity, prompt and apparatus hashes,
native stream observations, process status, session-bound hook payloads, and
exact copies of native parent/child transcripts with provenance. Capture uses
paths supplied by the matching native session hooks, not a global transcript
search. An absent, duplicate, conflicting, stale, or unreadable required
capture is an error. No previous launch, capture, or audit may be overwritten.
Session settings disable forked subagents and unrelated MCP configuration;
they do not alter persistent user settings. The run uses existing subscription
authentication, not an API-key fallback.

The Claude dispatch adapter retains the original compact assignment and its
hash, and a deterministic translated native argument object with its hash.
Its generated prompt preserves the complete common assignment and adds the
host's explicit shell/file path rules. Only actual native Agent arguments are
passed: fresh general-purpose, native background, and exact prompt. The nonempty
`description` is a display label, not worker identity; preserve its actual value
in the native evidence but do not reject punctuation changes. The allowed
argument keys remain exact. No invented `cwd`, resume, fork, or second native
worktree is allowed. Child Bash
commands must enter the assigned helper worktree for every call; file-tool
paths must be absolute and scoped. Root correctness requires the production
context check and fixture probe evidence, not inherited transcript cwd text.

The native audit must correlate parent Agent calls, started task identities,
child start/stop evidence, child tool calls/results, and successful native
completion notifications before parent return verification and integration.
Automatically backgrounded shell tasks are excluded only when typed `local_bash`
start and completion events correlate with a real native Bash call; they are
never counted as workers. Unknown or incomplete task identities remain errors.
A parent assertion, filesystem artifact, or final narrative cannot substitute
for a missing native lifecycle event. Every child must execute its one start
and one finish wrapper with the exact binding. The shared artifact gates
remain mandatory, including delivery-mode-specific commit or ephemeral
semantics, parent dirty/index/HEAD preservation, and package integrity.

The successful verification summary, final result writer, and native terminal
response retain the compact terminal boundary. Report requested and served
model identities separately. Native stdout may contain multiple init/result
messages while background completion notifications trigger parent turns;
that is not multiple independent parents. An unrecognized or incomplete
format must fail qualification rather than be guessed into a success.

A campaign passes only when all five phase exits are integer zero and every
selected case has an exact `PASS`, `passed: true` Claude verdict. Independent
post-exit filesystem and frozen-input checks are required. Retain failures and
worktrees; do not automatically delete, retry, or promote an audit-only replay
to a new live trial. Timing intervals are observed host lifetimes, not CPU
concurrency or causal model-speed claims.
