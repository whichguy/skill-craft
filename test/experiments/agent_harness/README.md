# In Parallel live experiment apparatus

The directory name and `agent-harness-experiment` schemas remain stable for
retained evidence; newly prepared cases select the public `in-parallel` skill.

This directory prepares a synthetic Git checkout, launches one authorized root
model CLI, and audits the production `in-parallel` lifecycle separately from
native host evidence. In the direct arm, the root model is the coordinator and
owns the native workers. The apparatus never starts worker model processes.
Nested Claude attempts are retained as diagnostic failure evidence; do not
prepare new nested trials while the pinned headless Claude host strategy is
deferred.

Each case has three or five independent module tasks and begins with a committed
synthetic baseline plus staged and unstaged changes in `context/brief.md`,
`.gitignore`, and `.claspignore`. Report-only seeds known formulas before the
baseline commit. Edit trials use helper-managed worktrees and the production
commit return route; report-only defaults to the current checkout; ephemeral
trials use worktrees with return-only delivery. Each ephemeral task names its
formula and exact `transform(0)` and `transform(4)` results. The filesystem
audit checks the retained findings note, unchanged source, and unchanged worker
HEAD. The baseline also includes the exact empty feedback-collector backlog
file so its create-only host hook does not create an unrelated path; later
changes to the file remain detectable. Prompts contain only synthetic fixture
data and selected skill instructions.

Prepare a new output directory for every attempt. Preparation records package
tree hashes for in-parallel, ask-agent, and plan-dispatcher, plus this
apparatus and the existing host capture utilities. Live launch requires the
exact recorded source-freeze hash and case UUID. Preserve failed or uncertain
attempts; use a fresh directory for a retry.

```sh
# From the repository root
APP=test/experiments/agent_harness/experiment.py

python3 -B "$APP" prepare --case /tmp/agent-harness-sonnet-direct3 \
  --provider claude --arm direct --workers 3 --mode edit
python3 -B "$APP" prepare --case /tmp/agent-harness-sonnet-direct5-ephemeral \
  --provider claude --arm direct --workers 5 --mode ephemeral
python3 -B "$APP" prepare --case /tmp/agent-harness-grok-direct3 \
  --provider grok --arm direct --workers 3 --mode edit
```

Copy a case's `case_id` and `freeze_sha256` from its JSON response, then launch
only the case selected for the live trial:

```sh
python3 -B "$APP" launch --case /tmp/agent-harness-sonnet-direct3 \
  --authorized-case CASE_UUID --expected-freeze-sha256 FREEZE_SHA256
```

Grok nested is outside this bounded apparatus. Grok root launch evidence is
retained by the existing external controller and native trace helpers.

After the root CLI exits, audit each attempt once. Audit output is exclusive and
immutable, including failed verdicts:

```sh
python3 -B "$APP" audit --case /tmp/agent-harness-sonnet-direct3
python3 -B "$APP" report \
  --cases /tmp/agent-harness-sonnet-direct3 /tmp/agent-harness-sonnet-direct5-ephemeral \
  --output /tmp/agent-harness-sonnet-pair-report.json
```

To re-evaluate retained native traces after an auditor correction, write a
separate diagnostic artifact with explicit provenance and a fresh output path:

```sh
python3 -B "$APP" reaudit --case /tmp/agent-harness-sonnet-direct3 \
  --output-dir /tmp/agent-harness-sonnet-direct3-audit-rev2 \
  --provenance 'Explain the auditor correction and evidence being checked.'
```

Re-audit always reports `DIAGNOSTIC_ONLY`; it records source-freeze drift and
does not replace the original audit or qualify a new live attempt.

Native tree assertions and Git/filesystem assertions are separate report
sections. Claude proof binds root `Agent` calls and `task_started` events to
session-scoped lifecycle hooks and retained child transcripts. The host's
`task_started.is_backgrounded` value is authoritative; the Agent input's
optional `run_in_background` value is recorded separately. Each worker
transcript must show the exact prepared `worker-start` and `worker-finish`
command with successful results. The instrumented fixture requires each phase
command in its own shell call, with at most an exact `cd` prefix. Compound
phase invocations remain unqualified by the auditor even when delivery succeeds. Nested Claude coordinator stop hooks are
checked individually; a coordinator stop before every worker's final terminal
hook fails encapsulation even if that coordinator later resumes. Grok proof
uses session-id-bound native update logs, spawn receipts, child logs, and
terminal finish updates with session-bound native journal timestamps, and parses each phase command's typed zero-exit Bash
result as JSON with the exact production success status. Missing or ambiguous
evidence fails.

Launch identity checks bind root argv, cwd, model, effort, prompt/request hashes,
manifest, and source freeze to the prepared case. The filesystem audit compares
parent HEAD, index entries, staged diff, and control-file bytes, then runs the
combined synthetic verifier for edit/apply cases. Elapsed time, worker start
spread, and peak worker overlap come from retained timing evidence. Root Claude
input, cache-read input, cache-creation input, and output tokens are reported
separately; total input is incomplete if either cache field is absent. Child
token totals are unavailable. Observed host-wall-clock overlap does not
establish CPU parallelism or speedup.

`test_audit.py` contains offline checks for direct/nested graph requirements,
resumed native invocation intervals, effective launch state, ephemeral findings
and no-commit controls, fixture modes, request normalization, frozen inputs,
and Grok phase-result parsing. Run the offline checks through `bash test/run-all.sh --group in-parallel`;
the group's separate queue tests exercise bounded refill and complete task coverage.
