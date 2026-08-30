---
name: shiploop
description: >-
  Session harness: spec once, one backchain sequence plan, then walk ready
  steps by emitting a paste-ready /goal per running id in a per-step git
  worktree/branch. Use when the user says shiploop, ship the project,
  session harness, or what's the next step. After every increment invoke
  /shiploop complete — do not rely on chat memory. Lost context without
  completing → /shiploop next.
allowed-tools: all
version: 0.8.9
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
then the packet H2s. Successful `init` / `complete` / `update` print
`initialized …`, `updated -> …`, `completed <id>`, or `cleared <id>` first.
`next` prints `next — claimed <ids> (<phase>)` or `next — reprint (<phase>)`.
`complete-step` / `clear-step` / `inject-step` print no packet.

Banner:

```text
shiploop — session harness
```

`shiploop` owns session state. It does not implement the product. Planning
requires the sibling **backchain** skill (fail-closed via
`dep_roots.backchain`).

Reprint and closer live on this leaf (`/shiploop next`, `/shiploop complete`).
There are no sibling marketplace skills for those verbs.

Practices: skill-craft `docs/LOOP-ENGINEERING.md` (ShipLoop session track).
State files: [references/state-files.md](references/state-files.md).
Survey guide: [references/survey.md](references/survey.md).
Human overview: [README.md](README.md).

## When to use

- User says **shiploop** or wants an artifact-backed next step that ships
- A run already has `.shiploop/` and context may be gone
- Spec once → sequence plan once → walk via `/goal` → session residual

## When not to use

- Offline freeze/prove/stop → **`evidence-gates`**
- Packet reprint only → `/shiploop next` (same leaf)
- Increment finished, want the next packet → `/shiploop complete` (same leaf)
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
     the product tree. Then follow the new packet.
   - **state.json exists, same ask, phase is not `blocked`:** do not `init`
     again. Invoke `/shiploop next` (or `/shiploop complete` if an increment
     just finished) to reprint and continue.
   - **state.json exists, phase is `blocked`:** read `ask_user` /
     `blocked_reason` / `resume_to` from the packet, resolve whatever it
     asked, then invoke `/shiploop complete --reason "…"` to resume.
     Wrappers refuse `update`; do not type `update --to`.
4. Follow the whole packet. After every packet (`init` / `next` /
   `complete`), echo the printed `## You are here` block and the Diagnosis
   **now** / **pending** lines back to the user — do not summarize them
   away. That is the live session rail (`status --human` reprints it).
   Do only the **Next prompt** (first line is `Use this prompt as much as
   possible.`). On implement, paste the **Frozen session environment**
   block together with the stored prompt into `/goal`. Do not paste
   worktree, branch, or HOST FLAG. Implement steps name a per-step
   worktree and branch in **Look here** / **Diagnosis** — work there; do
   not edit the session checkout or reuse a prior worktree. Full workflow:
   [README.md](README.md). Git sequence (who runs which command):
   [README.md — Git sequence (harness vs host)](README.md#git-sequence-harness-vs-host).
5. When the increment is done: invoke **`/shiploop complete`**. That command
   owns the closer (commit + merge if this was a `/goal`, then harness
   `complete`, then the next packet). Do not type `complete-step --id` or
   `update --to` unless this card named an override (`--clear`,
   `--blocked --reason`, `--id` when several steps are running). Empty or
   unmerged branches are refused. ShipLoop does not auto-merge. See
   **Host flag — extra folder** before any implement `/goal`.
6. Repeat until the packet says stop. Lost context without completing
   anything → invoke **`/shiploop next`** (reprint / claim only).
7. Mid-implement, discovered intermediate work → `inject-step` (see
   [commands/shiploop-inject.md](commands/shiploop-inject.md) and
   [references/activities/implement.md](references/activities/implement.md)).
8. **Never** invoke `shiploop capture`.

## Host flag — extra folder (do not re-root)

ShipLoop creates another folder for implement `/goal`s. Work there. The
session checkout stays the merge dest. Do not re-root the host chat into
that folder or the product repo unless the user asked. Printed packets
repeat this block in **Progress** and the implement Next envelope
(stored `prompt`s stay verbatim):

```text
HOST FLAG — extra folder (do not re-root):
ShipLoop creates another folder: a per-step worktree under <repo>/.worktrees/shiploop/<run_id>/<id> on branch shiploop/<run_id>/<id>.
Implementation work happens IN that worktree, not in the session checkout.
Do not move_agent_to_root / re-root the host chat into that folder or the product repo unless the user asked.
The session checkout stays the merge dest; do not edit it during implement.
After /shiploop complete, the host merges the kept branch into session HEAD; the next packet names the next worktree.
```

## Closer (`/shiploop complete`)

This is not a reprint. Invoking it means the current increment finished (or
failed). Follow [commands/shiploop-complete.md](commands/shiploop-complete.md):

- **Success (default):** Next prompt is done. If that work was an implement
  `/goal`: commit on that worktree if it is not committed; merge the kept
  branch into the session checkout if it is not in `HEAD`. Do not skip the
  merge; the next worktree forks `HEAD`.
- **`/goal` failed**, session can continue: `--clear` (add `--id` only when
  several steps are running and cwd is not that worktree).
- **Hard stop:** `--blocked --reason <text>` (required). `--resume-to` only
  if the packet named it.

Then exec the leaf CLI (`complete`) and follow the whole packet that prints.

## CLI

```sh
CLI="$SKILL_ROOT/scripts/shiploop"
python3 "$CLI" init [--prompt TEXT] [--run-dir DIR] [--implementer host] [--force] [--bound-plan PATH] [--repo PATH]
python3 "$CLI" next [--run-dir DIR]
python3 "$CLI" complete [--id ID] [--run-dir DIR] [--clear] [--blocked --reason TEXT]
python3 "$CLI" update [--run-dir DIR] --to PHASE [--reason TEXT] [--resume-to PHASE]
python3 "$CLI" status [--run-dir DIR] [--human]
python3 "$CLI" start-step [--run-dir DIR] --id ID
python3 "$CLI" complete-step [--run-dir DIR] [--id ID]
python3 "$CLI" clear-step [--run-dir DIR] [--id ID]
python3 "$CLI" inject-step [--run-dir DIR] --statement TEXT --prompt TEXT --produces TEXT \
  [--id Sn] [--need NEED --from ID] [--before ID ...]
```

The host closer is **`/shiploop complete`** (it execs `complete`).
`complete` infers the unique running id or the happy-path `--to` from
`.shiploop/` files, then prints the next packet. `complete-step` /
`update --to` / `--id` are overrides.

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
