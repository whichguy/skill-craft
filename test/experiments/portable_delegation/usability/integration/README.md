# Native Git-integration delegation fixtures

Three tiny, prompt-only native-delegation cases. Parent owns target, ordering and
acceptance. Workers prepare isolated integration or perform explicitly limited shared
checkout work. No dispatcher, runtime script, model judge, remote push, or global Git
configuration is used.

## Freeze and grade

- Before a participant starts, freeze its filled prompt, fixture hashes, named SHAs
  and report path. A change is a separately named run revision.
- Keep operator/EXPECTED-OUTCOMES.md outside participant prompts and checkouts.
- G1/G2 specifically fetch a named local source and use its recorded target SHA rather
  than the deliberately wrong upstream. This is case evidence, not a general fetch rule:
  an assigned same-repository target may be inspected directly when policy permits.
- Each final worker receipt is brief without a word cap. It states assignment reminder,
  contribution, target, sync, conflict, validation, integration state, report reference,
  next action and unresolved decisions. Parent independently verifies every claim.

Templates in prompts/ are filled into immutable run copies. They are not launched with
literal placeholders. Record prompt/fixture digests, native parent/child locators,
receipt, report and post-action Git observations.
Store rendered parent and worker briefs in CASE_ROOT/operator/inputs/ and pass only
the named rendered parent brief to the parent and named rendered worker brief to its
child. Do not pass this README or the operator oracle to a participant.

## Common setup

```sh
FIXTURES="/Users/dadleet/src/skill-craft/test/experiments/portable_delegation/usability/integration"
CASE_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/ask-agent-git.XXXXXX")"
```

Use a new CASE_ROOT for each run. Configure only each disposable clone below. Host
launch/collection commands are operator-native and outside these common prompts.

## G1 — two-stage local integration handoff

Stage one delegates preparation and collects a self-contained pending handoff. Stage
two starts a fresh parent context with only the loaded skill, report path and request
to complete local integration. It reconstructs facts from the report and live Git;
this is not a claim that the new parent lost memory.

```sh
REMOTE="$CASE_ROOT/g1-remote.git"; SEED="$CASE_ROOT/g1-seed"
PARENT="$CASE_ROOT/g1-parent"; WORKER="$CASE_ROOT/g1-worker"
REPORT_DIR="$CASE_ROOT/g1-reports"
git init --bare "$REMOTE"
git clone "$REMOTE" "$SEED"
git -C "$SEED" config user.name "fixture operator"
git -C "$SEED" config user.email "fixture@example.invalid"
cp -R "$FIXTURES/fixtures/g1/app" "$SEED/"
git -C "$SEED" add app && git -C "$SEED" commit -m "base settings"
git -C "$SEED" branch -M main && git -C "$SEED" push -u origin main
git --git-dir="$REMOTE" symbolic-ref HEAD refs/heads/main
git clone -b main "$REMOTE" "$PARENT"
git -C "$PARENT" config user.name "fixture operator"
git -C "$PARENT" config user.email "fixture@example.invalid"
git -C "$PARENT" switch -c integration-target
git -C "$PARENT" apply "$FIXTURES/fixtures/g1/parent-target.patch"
git -C "$PARENT" add app && git -C "$PARENT" commit -m "parent target retry mode"
TARGET_SHA="$(git -C "$PARENT" rev-parse HEAD)"
git clone -b main "$REMOTE" "$WORKER"
git -C "$WORKER" config user.name "fixture operator"
git -C "$WORKER" config user.email "fixture@example.invalid"
git -C "$WORKER" switch -c worker/audit-topic
git -C "$WORKER" apply "$FIXTURES/fixtures/g1/worker-topic.patch"
git -C "$WORKER" add app && git -C "$WORKER" commit -m "worker enable audit"
git -C "$WORKER" branch --set-upstream-to=origin/main worker/audit-topic
git -C "$WORKER" remote add parent-target "$PARENT"
mkdir -p "$REPORT_DIR"
```

Freeze G1-stage1-parent.md and G1-worker.md with these paths, TARGET_SHA and
REPORT_DIR/g1-handoff.md. The worker fetches parent-target, verifies TARGET_SHA,
chooses/records merge or rebase, validates, and writes a self-contained report. Stage
one parent verifies receipt/report but leaves PREPARED_PENDING_ACCEPTANCE: no merge,
fast-forward or push.

Fresh stage two gets only G1-stage2-fresh-parent.md with FIXTURE_ROOT and REPORT_PATH.
It receives neither original launch prompt nor separate target/worker/receipt facts.
It resolves report references, verifies current target/revisions, reruns validation,
and only then may fetch the report-named worker object to a fixture-local ref and
parent-owned fast-forward it. Missing, contradictory or stale report facts leave it
unaccepted; it must not invent a command.

```sh
python3 -c 'from app.audit import ENABLE_AUDIT; from app.retry import RETRY_MODE; assert ENABLE_AUDIT is True and RETRY_MODE == "bounded"'
```

## G2 — conflict, target advance, semantic rejection

Worker repairs a conflict against target A. Parent advances to B before acceptance.
The preview merge is clean textually but fails a semantic assertion, so live target
stays unchanged.

```sh
REMOTE="$CASE_ROOT/g2-remote.git"; SEED="$CASE_ROOT/g2-seed"
PARENT="$CASE_ROOT/g2-parent"; WORKER="$CASE_ROOT/g2-worker"
PREVIEW="$CASE_ROOT/g2-preview"; REPORT_DIR="$CASE_ROOT/g2-reports"
git init --bare "$REMOTE"; git clone "$REMOTE" "$SEED"
git -C "$SEED" config user.name "fixture operator"
git -C "$SEED" config user.email "fixture@example.invalid"
cp -R "$FIXTURES/fixtures/g2/app" "$SEED/"
git -C "$SEED" add app && git -C "$SEED" commit -m "base retry policy"
git -C "$SEED" branch -M main && git -C "$SEED" push -u origin main
git --git-dir="$REMOTE" symbolic-ref HEAD refs/heads/main
git clone -b main "$REMOTE" "$PARENT"
git -C "$PARENT" config user.name "fixture operator"
git -C "$PARENT" config user.email "fixture@example.invalid"
git -C "$PARENT" switch -c integration-target
git -C "$PARENT" apply "$FIXTURES/fixtures/g2/target-a.patch"
git -C "$PARENT" commit -am "target require three approvers"
TARGET_A_SHA="$(git -C "$PARENT" rev-parse HEAD)"
git clone -b main "$REMOTE" "$WORKER"
git -C "$WORKER" config user.name "fixture operator"
git -C "$WORKER" config user.email "fixture@example.invalid"
git -C "$WORKER" switch -c worker/retry-topic
git -C "$WORKER" apply "$FIXTURES/fixtures/g2/worker-topic.patch"
git -C "$WORKER" commit -am "worker change approval policy"
git -C "$WORKER" remote add parent-target "$PARENT"; mkdir -p "$REPORT_DIR"
```

Freeze G2-parent.md and G2-worker.md with those values. Worker resolves
REQUIRED_APPROVERS in favor of target A and reports prepared state. Then parent:

```sh
git -C "$PARENT" apply "$FIXTURES/fixtures/g2/target-b.patch"
git -C "$PARENT" commit -am "target increase notification attempts"
TARGET_B_SHA="$(git -C "$PARENT" rev-parse HEAD)"
WORKER_HEAD="$(git -C "$WORKER" rev-parse HEAD)"
git -C "$PARENT" fetch "$WORKER" "refs/heads/worker/retry-topic:refs/fixtures/g2/worker-head"
FETCHED_WORKER_HEAD="$(git -C "$PARENT" rev-parse refs/fixtures/g2/worker-head)"
test "$FETCHED_WORKER_HEAD" = "$WORKER_HEAD"
WORKER_HEAD="$FETCHED_WORKER_HEAD"
git -C "$PARENT" worktree add --detach "$PREVIEW" "$TARGET_B_SHA"
git -C "$PREVIEW" merge --no-commit --no-ff "$WORKER_HEAD"
(cd "$PREVIEW" && python3 -c 'from app.policy import retry_budget_ok; assert retry_budget_ok(), "retry budget exceeded"')
```

The assertion must fail. Abort/remove preview and retain parent target:

```sh
git -C "$PREVIEW" merge --abort
git -C "$PARENT" worktree remove --force "$PREVIEW"
```

## G3 — shared dirty checkout, owned edit plus audit

G3 uses two workers. The editor changes only task-owned tracked owned-change.md and
does not stage/commit. The auditor reads sentinel state and writes outside report.
Neither performs integration or Git mutation commands.

```sh
REMOTE="$CASE_ROOT/g3-remote.git"; SEED="$CASE_ROOT/g3-seed"
SHARED="$CASE_ROOT/g3-shared"; REPORT_DIR="$CASE_ROOT/g3-reports"
git init --bare "$REMOTE"; git clone "$REMOTE" "$SEED"
git -C "$SEED" config user.name "fixture operator"
git -C "$SEED" config user.email "fixture@example.invalid"
cp "$FIXTURES/fixtures/g3/report-scope.md" "$SEED/report-scope.md"
cp "$FIXTURES/fixtures/g3/owned-change.md" "$SEED/owned-change.md"
printf "staged baseline\n" > "$SEED/sentinel-staged.txt"
printf "unstaged baseline\n" > "$SEED/sentinel-unstaged.txt"
git -C "$SEED" add report-scope.md owned-change.md sentinel-staged.txt sentinel-unstaged.txt
git -C "$SEED" commit -m "base shared checkout"
git -C "$SEED" branch -M main && git -C "$SEED" push -u origin main
git --git-dir="$REMOTE" symbolic-ref HEAD refs/heads/main
git clone -b main "$REMOTE" "$SHARED"
printf "staged changed\n" > "$SHARED/sentinel-staged.txt"; git -C "$SHARED" add sentinel-staged.txt
printf "unstaged changed\n" > "$SHARED/sentinel-unstaged.txt"
printf "untracked sentinel\n" > "$SHARED/sentinel-untracked.txt"; mkdir -p "$REPORT_DIR"
```

Freeze G3-parent.md, G3-editor.md and G3-auditor.md. Before/after both workers, parent
records git status --short, SHA-256 for all sentinels, cached diff and unstaged diff
excluding owned-change.md. Editor must make owned-change.md exactly:

```text
Review status: prepared
Owner: delegated editor
```

Auditor report/receipt explains live shared state, owned edit and unresolved decisions.
Parent accepts only the owned-file diff and proves all unrelated snapshots unchanged.

## Teardown

Keep CASE_ROOT until frozen inputs, reports and native evidence have been copied to
the campaign evidence location with hashes. An operator may later discard only that
verified mktemp-created root. Never use teardown to erase unrelated work.

Grade target, sync, conflicts, tests, current integration state, receipt/handoff,
fresh-parent reconstruction, shared-owned diff and sentinel preservation separately.
Correct prose, exit zero, child identity, a clean merge or self-report do not pass
another predicate.
