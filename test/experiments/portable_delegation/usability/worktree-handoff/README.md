# U18 W1 worktree handoff fixture

A prompt-only native-parent case for U18 Git worktree delegation. It measures source
snapshot fidelity, worker-only contribution handling, report recovery and parent-owned
integration/removal separately. It creates no script, dispatcher, model restriction or
separate temporary result folder.

**Retired record.** This fixture exercises the caller-prepared worktree contract,
which current Ask-Agent no longer supports: the helper now prepares, inspects and
closes managed worktrees (see the
[managed-workspace apparatus](../../../ask_agent_managed_workspaces/README.md)).
The `verify-w1.py` operator helper and its offline regression suite were removed.
The table below describes what that helper checked, kept only so the
[U18 results](../WORKTREE-RESULTS.md) remain readable.

## Former operator checks

| Command | Operator responsibility it checked |
| --- | --- |
| `prepare` | Create a fresh owned primary repository and dirty linked feature checkout; save the baseline and paths. Parent still creates worker worktrees. |
| `snapshot` | Record checkout identity, index and working layers, untracked inputs, file modes/types and hashes. |
| `preflight` | Compare the intended native launch cwd/project arguments, frozen inputs and current source against the recorded baseline. |
| `public-opencode` | Read the supported installed OpenCode SQLite shape in read-only mode, selecting public text/tool fields without exporting raw sessions or private reasoning. |
| `complete` | Cross-check normalized native observations with actual source/inbox/worktree state. Missing returns, early finalization, extra source edits and lost reports must not pass. |

Render the parent prompt with the absolute paths planned for the fresh run, then
freeze the exact prompt, skill and reference inputs. Register the native launch
arguments and run preflight before launch. The registration is an operator
claim until the actual native session cwd/arguments are observed; a preflight
pass cannot prove that a later command honored the registration.

Keep diagnostics in the operator evidence area outside participant checkouts,
worker worktrees and the durable result inbox. Project only allowlisted public
fields at the database query boundary. Do not export an entire session and
filter it afterward, or provide diagnostic output to the running participant.
An unsupported host schema is a failed collection boundary, not an empty pass.

Completion checks require evidence of the parent final after both native returns,
retained result files before removal, worker terminal state and the intended Git
outcome. A message count, elapsed time, `finish=stop`, process exit or report file
alone is not the stop condition. The helper neither polls nor terminates a live
process. A successful check establishes consistency with the supplied public
observations; it cannot authenticate fabricated observations.
`COMPLETE` is a fixture lifecycle verdict. Score native dispatch conformance,
compact return reminders, real parent continuation, capabilities and observation
limits separately against the frozen oracle. A completed lifecycle can still
have those instruction-following failures, as the U18 results demonstrate.

No hermetic suite runs this fixture. Its redaction, ordering and archival
checks that still apply to current delegation are covered by
`test/ask-agent-managed-harness.test.py`. The frozen U18 W1 campaign predates
the removed helper; its checks never retroactively qualified invalid or
interrupted attempts.

## Source fixture before launch

Operator starts in a linked Git worktree on branch feature whose HEAD is one commit ahead
of primary main. The current feature checkout contains these dirty inputs:

- dual.txt has a staged layer plus a different unstaged layer.
- staged-add.txt is staged as a new file.
- deleted.txt is a tracked file deleted only in the working tree.
- unstaged.txt is a tracked file with an unstaged edit.
- notes.txt is an untracked input.
- pricing.json starts as `{"currency": "USD", "base_price": 100}`.

The intended code contribution is one new pricing.json field:
`"discount_rate": 0.10`. No inherited sentinel may be changed by either worker.

### Operator setup (disposable fixture)

Run these ordinary commands in an empty disposable parent directory. They create the primary
checkout and the current linked checkout; they do not create a worker or a result folder.

```sh
mkdir w1-primary && cd w1-primary
git init -b main
git config user.name 'W1 fixture'
git config user.email 'w1-fixture@example.invalid'
printf 'base\n' > dual.txt
printf 'delete me\n' > deleted.txt
printf 'original\n' > unstaged.txt
printf '{"currency":"USD","base_price":100}\n' > pricing.json
git add dual.txt deleted.txt unstaged.txt pricing.json
git commit -m 'w1 baseline'
git worktree add -b feature ../w1-feature
cd ../w1-feature
printf 'feature parent commit\n' > feature.txt
git add feature.txt && git commit -m 'feature is ahead of main'
printf 'staged layer\n' > dual.txt && git add dual.txt
printf 'staged layer\nunstaged layer\n' > dual.txt
printf 'staged addition\n' > staged-add.txt && git add staged-add.txt
rm deleted.txt
printf 'changed but unstaged\n' > unstaged.txt
printf 'untracked input\n' > notes.txt
mkdir -p ../w1-inbox
```

`../w1-feature` is `<SOURCE_CHECKOUT>` and `../w1-inbox` is `<DURABLE_INBOX>` after
conversion to absolute paths. The local Git identity is fixture-local; do not set global
Git configuration. Parent, rather than this setup, chooses and prepares separate worker
worktrees from this current dirty state.

Before dispatch, operator records absolute current checkout path, Git root, branch, HEAD,
staged/unstaged/untracked snapshots and hashes, relevant Git status/diff evidence, and
the primary-main relationship. It provides the frozen U18 main/reference paths and an
absolute durable inbox path outside every worker worktree. Parent prepares each unique
worker worktree itself from the current dirty checkout, including both staged and
unstaged layers and untracked inputs. It must verify fidelity before native launch.

## W1 execution

Render parent.prompt.md with absolute values (and an effective model selector only where
the host requires one) and freeze its hash. Parent launches the
code worker after confirmed worktree preparation, records its handle and performs useful
analysis of the supplied source snapshot. While it remains pending, parent launches the
independent report worker when supported, using the same descriptive pricing-handoff
reviewer label but a distinct task/handle/worktree. Parent launches that report worker even
when the code worker has already completed; only the overlap predicate is then unobserved.
Do not force overlap.

Each worker receives its full assignment directly in its native launch prompt. Each writes
multiple useful result files inside its own worktree, including a handoff index and detailed
report. Reports are not a separate temporary-folder layer. Worker receipts state observed
cwd, Git root, baseline, worker-only contribution, validation, result files, state and
parent merge/removal recommendation.

Parent consumes reports through native notification/join, verifies their paths and current
state, copies the durable receipt/index and every required referenced result to the designated
inbox before deleting any owned worktree, and updates final links if a path changes, then:

- integrates only the worker-only pricing.json contribution after rechecking target and
  validation, leaving source sentinels intact; or
- removes report-only worktrees only after consuming retained reports; or
- retains a worktree for a named blocker, unresolved review or active consumer.

The source checkout remains unchanged except the intended final pricing.json integration.
No worker deletes a worktree.

## Evidence and boundaries

Capture source trace (current checkout, snapshot and sentinels), worker trace (native
dispatch schema/arguments, handle, observed cwd/root, baseline fidelity, actual tools,
worker-only diff/commit, report/index) and public parent trace (launch/return, useful
continuation, collection, validation, integration/removal/retention and final synthesis).
Do not export private reasoning.

Focused extensions, not covered by W1 unless separately registered and run: unsupported
or non-Git source, binary input, symlink, submodule, active writers during capture,
retry/fresh attempt, nested worker, unavailable second launch, and worker-path transport
failure. Record each as NOT-COVERED, UNSUPPORTED or BLOCKED as applicable; do not infer
coverage from the normal path.

No exact tool parity is required across hosts. A host must use its exposed native fresh
worker and worktree/cwd facilities or report the limitation. Do not replace isolated
worktrees with a shared checkout, default branch or HEAD-only copy.

## Teardown

Before parent removal, preserve durable inbox entries and any required referenced result
files, updating final references when files move. Record integration/retention state. Use
Git/native worktree removal only after users stop and all needed results are copied; do not
blindly delete directories. Keep blocked worktrees and recovery material.
