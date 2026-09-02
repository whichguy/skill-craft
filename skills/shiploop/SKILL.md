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
version: 0.8.18
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
then the packet H2s, then a `Git ran:` trailer when the harness recorded
mutating git. Successful `init` / `complete` / `update` print
`initialized …`, `updated -> …`, `completed <id>`, or `cleared <id>` first.
`next` prints `next — claimed <ids> (<phase>)` or `next — reprint (<phase>)`.
`complete-step` / `clear-step` / `inject-step` print no packet (Git ran
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
   possible.`). On implement, open host **`/goal` A**: paste **Frozen**,
   **Implement git**, **Goal until**, and the stored prompt (that stored
   prompt **is** `/goal` A until produces — do not wrap a second `/goal`;
   do not work in the parent chat without until). When produces is true,
   close A. Open **`/goal` B** = Frozen + Implement git + **Improve**
   (do not nest B inside A). Improve until two consecutive only-trivial
   cycles (max 12, then leftover + complete). Do not paste HOST FLAG
   (parent chat stays put; no re-root). Work in the named worktree; do
   not edit the session checkout or reuse a prior worktree. Full workflow:
   [README.md](README.md). Git sequence (who runs which command):
   [README.md — Git sequence (harness vs host)](README.md#git-sequence-harness-vs-host).
5. When `/goal` A and Improve `/goal` B are done: leftover uncommitted
   work gets a pathspec commit (never `git add -A`) with `Key learnings:`
   / `See: <sha>`, then invoke **`/shiploop complete --inner-loop goal|parent`**.
   Choose `goal` after the `/goal` inner loop, or `parent` after the equivalent
   host-native until-produces + Improve two-clean loop. That command merges
   (`git -C <session-checkout> merge --no-ff --no-edit`), prints Git ran,
   dests residual when this was the last step, and prints the next packet.
   Do not merge from the worktree cwd. If complete dies, read Git ran /
   stderr, fix, retry. Do not type `complete-step --id` or `update --to`
   unless this card named an override (`--clear`, `--blocked --reason`,
   `--id` when several steps are running). Empty, dirty, or conflicted
   complete is refused. See **Host flag — extra folder** before any
   implement `/goal`.
6. Repeat until the packet says stop. Lost context without completing
   anything → invoke **`/shiploop next`** (reprint / claim only).
7. Mid-implement, discovered intermediate work → `inject-step` (see
   [commands/shiploop-inject.md](commands/shiploop-inject.md) and
   [references/activities/implement.md](references/activities/implement.md)).

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
After /shiploop complete, the harness merges the kept branch into session HEAD and prints Git ran; the next packet names the next worktree.
```

## Closer (`/shiploop complete`)

This is not a reprint. Invoking it means the current increment finished (or
failed). Follow [commands/shiploop-complete.md](commands/shiploop-complete.md):

- **Success (default):** `/goal` A (until produces) and Improve `/goal` B
  (two consecutive only-trivial, max 12) are done. If the worktree still
  has uncommitted files, `git -C <worktree>
  log -10 --format=full`, then pathspec add (never `git add -A`) and
  commit with a verbose body, `Key learnings:`, and `See: <full sha>
  <subject>` for prior lesson commits. If B already committed, do
  not invent a second finish commit. Then exec complete with
  `--inner-loop goal` (or `--inner-loop parent` for the equivalent
  host-native loop) — the harness
  merges (`git -C <session-checkout> merge --no-ff --no-edit <branch>`),
  prints Git ran, and dests residual when this was the last step. Do not
  merge from the worktree cwd. If complete dies, read the Git ran
  transcript, fix, retry.
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
python3 "$CLI" complete [--id ID] [--run-dir DIR] [--inner-loop goal|parent] [--clear] [--blocked --reason TEXT]
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
`.shiploop/` files, then prints the next packet. Completing a running
implement step requires `--inner-loop goal|parent`; it is recorded on that
receipt. `complete-step` /
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
