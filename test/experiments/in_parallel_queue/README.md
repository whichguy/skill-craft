# In Parallel native queue experiment

This apparatus creates a prompt-led synthetic queue case and audits its
retained output offline. It does not launch a model or create native agents.
The case prompt asks one coordinator to discover and report every deterministic
module through the selected `in-parallel` and `plan-dispatcher` skills. The
expected values stay in a separate parent-side `expected.json`, outside the
synthetic Git checkout; the coordinator prompt expressly forbids reading it.
The file is not access-controlled from the coordinator, however, so this is an
instruction rather than a security boundary. Neither the apparatus nor the
audit proves that the coordinator left the oracle unread or reasoned without
seeing it.

Preparation pins the fixture's Git HEAD, index bytes, all non-`.git` fixture
file bytes, and porcelain worktree status, along with the selected
`in-parallel`, `ask-agent`, and `plan-dispatcher` package trees. It does not
check every item under `.git` (for example, config, refs, reflogs, or hooks).
Each case and audit output path must be new and external to the selected skill
checkout. Use a new case directory for each attempt; a prepared case is never
overwritten. Preserve failed cases as found; do not restore or clean a drifted
fixture before audit. The prompt directs every generated task to inspect with
AST and run any Python probe using `python3 -B`, `PYTHONDONTWRITEBYTECODE=1`, or
`sys.dont_write_bytecode = True`, with evidence outside the fixture.

```sh
python3 test/experiments/in_parallel_queue/experiment.py prepare \
  --case /tmp/in-parallel-cap2 \
  --skill-root /absolute/path/to/skills \
  --tasks 7 --capacity 2

# Omitted capacity uses the selected skill default (currently five, capped by
# the task count); choose a different new case directory for this attempt.
python3 test/experiments/in_parallel_queue/experiment.py prepare \
  --case /tmp/in-parallel-default \
  --skill-root /absolute/path/to/skills \
  --tasks 7

python3 test/experiments/in_parallel_queue/experiment.py audit \
  --case /tmp/in-parallel-cap2 \
  --coordinator-rollout /absolute/path/to/coordinator.jsonl \
  --aggregate /tmp/in-parallel-cap2/coordinator/aggregate.json \
  --output /tmp/in-parallel-cap2-audit.json
```

The prompt requires a finite queue plan, one fresh native context per item,
bounded refill through a single Dispatcher, report-only/current execution, and
a table plus aggregate totals. New cases pin
`result_evidence_role=coordinator-response` in `case.json` and the prompt. The
aggregate records the actual task IDs and
attempts, each module's formula and results at 0 and 4, the observed native
handle, and locators/hashes for the harness packet, collected record, verified
record, and coordinator-preserved raw worker result. The Dispatcher inbox
separately pins its accepted result under `dispatcher/artifacts/`. The final run
path is the harness run root containing `run.json`, `result.json`, and
`dispatcher/`.

For prior v1 cases without that configuration field, the auditor resolves the
result role from the exact contract wording in the hash-verified prompt. It
accepts the legacy `dispatcher-artifact` role only when the prompt directs
`raw_result_path` to the exact attempt's Dispatcher result; the audit report
labels that artifact as a Dispatcher result rather than a raw worker response.
Diagnostic artifacts must have pinned paths and hashes; summaries are retained
when provided. Unknown or conflicting prompt wording fails closed.

Audit output includes a `proof_scope` object with the oracle, Git metadata, and
native-overlap limitations. Audit is offline. It checks the actual harness JSON
artifacts as well as the aggregate wrapper, compares every row and total to the
parent-side oracle, and rechecks fixture and selected-skill source pins. Source
preservation reports list added, missing, and changed fixture paths, with
expected and observed SHA-256 values where applicable. For native concurrency it
parses only the specified coordinator Codex JSONL: typed child start/completion
events must join the corresponding `spawn_agent` call IDs and child paths, and
the peak active interval must fit the case capacity. Spawn arguments are read
only for `task_name` and `fork_turns`; message content is not retained. The
report keeps only minimal event locators and the consumed journal hash. This
proves recorded native lifecycle overlap within the observed coordinator
journal; it does not establish CPU-level parallelism or speedup.

The offline tests use constructed JSONL and temporary artifact trees. They
exercise parser and aggregate rejection paths; they are simulated authoring
checks, not evidence of live native concurrency or a live experiment result.

```sh
python3 -B test/experiments/in_parallel_queue/test_experiment.py
```
