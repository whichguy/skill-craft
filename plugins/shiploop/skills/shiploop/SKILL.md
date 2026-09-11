---
name: shiploop
description: >-
  Session harness: spec once, one backchain sequence plan, then walk ready
  steps by printing a parent until-loop per running id in a per-step git
  worktree/branch. Use when the user says shiploop, ship the project,
  session harness, or what's the next step. After every increment invoke
  /shiploop complete — do not rely on chat memory. Lost context without
  completing → /shiploop next. Issue this prompt — satisfy the printed
  precondition, exec When done exactly, until When done says stop
  (done / halted / blocked-ask).
allowed-tools: all
version: 0.8.36
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: script-backed
  hermes:
    category: software-development
    tags:
      - portable-skill
      - multi-host
      - session-sm
---

# ShipLoop (session harness)

**Package leaf:** `shiploop`

CLI stdout: an outcome line (when the command prints one), then the banner,
then the H2s, then a `Git ran:` trailer when the harness recorded
mutating git. Successful `init` / `complete` / `update` print
`initialized …`, `updated -> …`, `completed <id>`, or `cleared <id>` first.
`next` prints `next — claimed <ids> (<phase>)` or `next — reprint (<phase>)`.
`complete-step` / `clear-step` / `inject-step` print no H2s (Git ran
still follows when git ran). On git/merge/dirty refuse, the trailer is
on stderr with `error:`.

Banner:

```text
shiploop — session harness
```

`shiploop` owns session state. It does not implement the product. Planning
requires the sibling **backchain** skill (fail-closed via
`dep_roots.backchain`).

Reprint and closer live on this leaf (`/shiploop next`, `/shiploop complete`).
There are no sibling marketplace skills for those verbs.

**Issue this prompt. Satisfy the printed precondition, then exec When done
exactly.** — **Host loop** after every stdout, same turn, until stop.
Chat memory is not the SM.

Practices: skill-craft `docs/LOOP-ENGINEERING.md` (ShipLoop session track).
State files: [references/state-files.md](references/state-files.md).
Survey guide: [references/survey.md](references/survey.md).
Human overview: [README.md](README.md).

## When to use

- User says **shiploop** or wants an artifact-backed next step that ships
- A run already has `.shiploop/` and context may be gone
- Spec once → sequence plan once → walk via parent until-loop → session residual

## When not to use

- Offline freeze/prove/stop → **`evidence-gates`**
- Reprint only → `/shiploop next` (same leaf)
- This prompt is done, want the next stdout → exec the printed When done (`/shiploop complete`)
- Residual×2 engine alone → **`review-coverage`** / **`review-converge`**

## Procedure

1. Print the banner `shiploop — session harness`.
2. `SKILL_ROOT` = directory containing this `SKILL.md`.
3. **Three-branch init** — check for a live `.shiploop/state.json` first.
   `init --repo PATH` with no `--run-dir` writes `PATH/.shiploop` (not
   `$PWD/.shiploop`). Exec the CLI with process cwd = that repo (or the
   running step worktree), not `$HOME`.
   - **No state.json (fresh session):** run
     `python3 "$SKILL_ROOT/scripts/shiploop" init --prompt "…" --repo PATH`
     once. `--implementer host` is the only legal implementer.
   - **New ask on an existing run:** `init --force --prompt "…" --repo PATH`.
     Empty `--force` is refused before any wipe. `--force` does not delete
     the product tree. Then **Host loop** on the new stdout.
   - **state.json exists, same ask, phase is not `blocked`:** do not `init`
     again. Invoke `/shiploop next` (or `/shiploop complete` if an increment
     just finished) to reprint and continue.
   - **state.json exists, phase is `blocked`:** read `ask_user` /
     `blocked_reason` / `resume_to` from stdout, resolve whatever it
     asked, then invoke `/shiploop complete --reason "…"` to resume.
     Wrappers refuse `update`; do not type `update --to`.
4. **Host loop** (below). After every `init` / `next` / `complete` stdout,
   issue the printed Next; satisfy any printed precondition; exec When done
   exactly. Echo the printed `## You are here` block, Diagnosis **now** /
   **pending**, the full `## Next prompt`, and the full `## When done
   invoke` block (`status --human` reprints it). First line of Next is
   `Issue this prompt.` This skill **cannot invoke `/goal`**. `/shiploop next`
   reprints and claims; it does not advance Implement/Improve. On implement: Frozen, Implement git,
   **Implement** or **Improve** (one cycle; do not nest). Do not paste HOST FLAG
   (parent chat stays put; no re-root). Work in the named worktree; do not
   edit the session checkout or reuse a prior worktree.
   Full workflow: [README.md](README.md). Git sequence (who runs which command):
   [README.md — Git sequence (harness vs host)](README.md#git-sequence-harness-vs-host).
   When several ids are running, finish one id's Implement + Improve + merge
   before opening another, unless they are truly parallel; never use one
   parent Improve turn for two ids. Stored DAG prompts may start with `/goal`
   bytes (a label, not a slash to invoke). Intake, validate-spec, and plan
   are parent-chat writes on the session checkout: no Implement/Improve loop,
   no worktree.
5. When When done is the merge: leftover uncommitted
   work gets a pathspec commit (never `git add -A`) with `Key learnings:`
   / `See: <sha>`, then invoke **`/shiploop complete`**.
   Use `--inner-loop goal` only if this host actually ran `/goal` (override).
   Bare `complete` from Implement cannot merge. That command merges
   (`git -C <session-checkout> merge --no-ff --no-edit`), keeps the step
   branch, removes the worktree, and does not squash, so inner Key learnings
   stay reachable from session HEAD; it prints Git ran, dests residual when
   this was the last step, and prints the next stdout.
   Do not merge from the worktree cwd. If complete dies, read Git ran /
   stderr, fix, retry. Do not type `complete-step --id` or `update --to`
   unless this card named an override (`--clear`, `--blocked --reason`,
   `--id` when several steps are running). Empty, dirty, or conflicted
   complete is refused. See **Host flag — extra folder** before any
   implement until-loop. Stored DAG prompts may start with `/goal` bytes
   (a label, not a slash to invoke).
6. Stay in **Host loop** until When done says stop. Lost context without
   completing anything → invoke **`/shiploop next`** (reprint / claim only),
   then Host loop on that reprint.
7. Mid-implement, discovered intermediate work → `inject-step` (see
   [commands/shiploop-inject.md](commands/shiploop-inject.md) and
   [references/activities/implement.md](references/activities/implement.md)).

## Host loop

The script is the only SM. **Issue this prompt. Satisfy the printed
precondition, then exec When done exactly.** After every CLI stdout in
**this same turn**:

1. Echo the printed `## You are here` block, Diagnosis **now** /
   **pending**, the full `## Next prompt` (not only its first line), and
   the full `## When done invoke` block. Do not summarize them away. That
   paste is the live rail; remembered stdout is not.
2. **Issue** that **Next prompt** (do that work in this chat).
3. When When done names a precondition, satisfy it (produces true + tests
   green; Lint-after-write must have run (or none(<reason>)); or this Improve
   cycle was only-trivial), then exec the printed
   command with no flags beyond the ones it printed and the host-owned
   values it named (`--improve "<text>"`, `--reason <answer>`, `--id <sid>`).
   Several steps running: exec one labeled `--id` closer, discard the rest
   of that now-stale stdout, follow the new stdout.
4. The new stdout is the next prompt to issue. Do not invent a next step
   from chat. Uncertain whether a closer landed, or about to end the turn
   without stop → exec `next`, then this loop.

“No extra judgment” means **no command selection**, not “no evaluation.”
Evaluating produces/tests is work the step already requires.

Repeat 1–4 until **stop**:

- When done is `stop — no update` (phase `done` or `halted`), or
- phase `blocked` whose Next is ask the user.

A When done that names `complete` (including `--trivial`, `--id`,
`--clear`, `--reason`, `--improve`) is **not** a stop — exec it and issue
the new stdout. Do not end the turn by narrating the next step.

## Host flag — extra folder (do not re-root)

ShipLoop creates another folder for implement until-loops. Work there. The
session checkout stays the merge dest. Do not re-root the host chat into
that folder or the product repo unless the user asked. Printed stdout
repeats this block in **Progress** and the implement Next envelope
(stored `prompt`s stay verbatim):

```text
HOST FLAG — extra folder (do not re-root):
ShipLoop creates another folder: a per-step worktree under <repo>/.worktrees/shiploop/<run_id>/<id> on branch shiploop/<run_id>/<id>.
Implementation work happens IN that worktree, not in the session checkout.
Do not move_agent_to_root / re-root the host chat into that folder or the product repo unless the user asked.
The session checkout stays the merge dest; do not edit it during implement.
After a merge complete, the harness merges the kept branch into session HEAD and prints Git ran; the new stdout names the next worktree.
```

## Closer (`/shiploop complete`)

This is the exec of the printed When done. The script updates `.shiploop/`
and prints the next stdout — that is the next prompt to issue. Calling it
does not by itself mean the increment is finished. Follow
[commands/shiploop-complete.md](commands/shiploop-complete.md)
and **exactly** the printed When done command (no default independent of
that line — residual dest done requires `--improve`; several running ids
require `--id`):

- Exec `python3 "$SKILL_ROOT/scripts/shiploop" complete` plus only the flags
  When done printed. Use `--inner-loop goal` only if this host actually ran
  `/goal` (override). When When done is the merge and the worktree still has
  uncommitted files, leftover-commit first (`Key learnings:` / `See: <sha>`).
  If Improve already committed, do not invent a second finish commit. The
  harness merges (`git -C <session-checkout> merge --no-ff --no-edit <branch>`),
  keeps the step branch, removes the worktree, and does not squash, so inner
  Key learnings stay reachable from session HEAD; it prints Git ran and dests
  residual when this was the last step. Do not merge from the worktree cwd.
  If complete dies, read the Git ran transcript, fix, retry. Uncertain whether
  complete landed → `/shiploop next`.
- **Until-loop failed**, session can continue: `--clear` only when When done
  named it (add `--id` only when several steps are running and cwd is not
  that worktree).
- **Hard stop:** `--blocked --reason <text>` when When done named it.
  `--resume-to` only if stdout named it.

Then exec the leaf CLI (`complete`) and **Host loop** on the new stdout.

## CLI

```sh
CLI="$SKILL_ROOT/scripts/shiploop"
python3 "$CLI" init [--prompt TEXT] [--run-dir DIR] [--implementer host] [--force] [--bound-plan PATH] [--repo PATH]
python3 "$CLI" next [--run-dir DIR]
python3 "$CLI" complete [--id ID] [--run-dir DIR] [--trivial] [--tests TEXT] [--advance B --tests TEXT | --improve-cycle trivial|material | --inner-loop goal|parent] [--improve TEXT] [--clear] [--blocked --reason TEXT] [--resume-to PHASE]
python3 "$CLI" update [--run-dir DIR] --to PHASE [--reason TEXT] [--resume-to PHASE]
python3 "$CLI" status [--run-dir DIR] [--human]
python3 "$CLI" start-step [--run-dir DIR] --id ID
python3 "$CLI" complete-step [--run-dir DIR] [--id ID] [--inner-loop goal|parent] [--improve TEXT]
python3 "$CLI" clear-step [--run-dir DIR] [--id ID]
python3 "$CLI" inject-step [--run-dir DIR] --statement TEXT --prompt TEXT --produces TEXT \
  [--id Sn] [--need NEED --from ID] [--before ID ...]
```

The host closer is **`/shiploop complete`** (it execs `complete`).
`complete` infers the unique running id or the happy-path `--to` from
`.shiploop/` files, infers the step action, then prints the next stdout.
Flagless `complete` advances Implement → Improve, records one Improve cycle
(bare = material; `--trivial` = only-trivial), or merges after two
consecutive only-trivial. `--advance` / `--improve-cycle` / `--inner-loop`
are overrides. `complete-step` / `update --to` / `--id` are overrides.

| Exit | Meaning |
|------|---------|
| 0 | Success |
| 2 | Blocked (illegal transition, missing artifact, hash drift, unsupported implementer) |
| 64 | Usage |

State lives under the **run dir** (default: `<repo>/.shiploop` when `init`
was given `--repo`, otherwise walk from cwd to `.shiploop`), never
inside this package. `--to implement` and claiming a step require `repo_root`
to be a git repository with `HEAD` so each running id can get a unique
`shiploop/<run_id>/<id>` worktree under `<repo>/.worktrees/` (hidden via
`.git/info/exclude`, not a tracked `.gitignore`).

## Host matrix

See [references/host-matrix.md](references/host-matrix.md). Discovery ≠ execution.
