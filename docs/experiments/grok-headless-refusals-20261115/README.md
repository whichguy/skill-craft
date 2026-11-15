# Grok's headless refusals in ShipLoop E2E runs (2026-11-15)

Status: **firm** for the cause on Grok 1.0.77 and for the measured rate; the owner chose options E and D the same day
and both are built ([Decision and fix](#decision-and-fix-2026-11-15)); **interim** for their effect on a whole delivery,
which no E2E round has measured yet. The first version of this page (ded345978767587e07c6fffe60aa3f7e785c668b) said no
fix was built; that line is superseded.

## The question

On 2026-11-14 the planning-points probe (E24, results in 909adf228e00254d293ddfcd76b8011ef296fd6c) ran four long
deliveries on the E2E default subject, Grok `grok-4.6` at `xhigh` (Grok 1.0.77, `run.py --source marketplace`). Grok
refused 28 of the model's own shell commands (pp-1 11, pp-2 5, pp-3 8, pp-4 4). Each refusal ended a host session as
`cancelled`, and pp-3 was lost at release-plan ($74.62, about 4.5 hours). This study asks which rule refuses these
commands, how often it happens across the recorded Grok runs, and what would fix it. It is about the E2E apparatus.

## The answer in brief

- **Mechanism.** `run.py` launches Grok with `--permission-mode auto` (Grok's "Auto-review") and no user. Before Auto-review
  asks its classifier (a model that reviews each command, which takes 1.8 to 8 s), Grok checks which files a shell command
  writes. When it cannot resolve a written path, it raises what its binary calls a confirmation floor: only a person can
  clear it. A headless run has no person, so Grok refuses the call, prints `permission required: Execute … was not run, as a
  headless run cannot ask for approval`, marks the call `User cancelled the execution`, and ends the turn as `cancelled`
  (`permission_cancelled`). Grok skips the `Stop` hook for a cancelled turn, so ShipLoop's keepalive hook never sees it, and
  `run.py`'s resume loop starts the session again.
- **Trigger** (probed on 1.0.77, 81 Grok sessions in all). The floor fires on three shapes, deterministically, in 0 to
  13 ms, without the classifier:
  1. a write target that holds a shell expansion, where the target is every operand of `mkdir`, `touch` or `rm`, the
     destination of `cp`, `mv` or `ln`, or a file of `tee`: `mkdir -p "$COPY"`, `rm -rf "$X"`, `cp a "$X/"`,
     `tee "$X/t.txt"`, `mkdir -p "${TMPDIR:-/tmp}/x"`, `mkdir -p "$(dirname …)"`, even when the variable was set to a
     literal path a line earlier. (Corrected later the same day: the first version listed `tar -C` among these programs.
     The batches `writers-1077` and `writers2-1077` found `tar -x -C "$X"`, `tar -czf "$X/a.tgz"` and `rsync … "$X/"`
     allowed by the classifier, and a variable in a `cp` source only allowed too.)
  2. a relative write after a `cd` to a folder other than the session's own: `cd WT && mkdir -p fixtures`,
     `cd WT && git show … > fixtures.txt`, `(cd WT && mkdir -p x)`, `cd WT && cp README.md copy.md`, `cd WT && rm -f x`;
  3. two adjacent backticks inside a double-quoted word, an empty command substitution: ```` python3 -c "… r'```x\n(.*)\n```' …" ````,
     which is how the model reads ShipLoop's ```` ```shiploop-state ```` blocks in one-liners.

  The same commands with a literal absolute target, with no `cd`, with a `cd` to the session's own folder, in single
  quotes, or with a real command between the backticks (`` "a `date` b" ``) go to the classifier and are allowed. A shell
  redirect to a variable target (`> "$X/out.txt"`) is not floored either. Allow rules cannot lift the floor: with
  `--allow 'Bash(mkdir *)'`, `'Bash(cd *)'`, `'Bash(python3 *)'`, and even `--allow 'Bash(*)'`, all three shapes were
  refused again (6 of 6).
- **Why E2E runs meet it.** E2E launches Grok in `<run>/work` (`--cwd`), and ShipLoop keeps its run folder and worktree
  beside it in `<run>/.shiploop-runs/…`, outside the session's folder. The model's checks therefore `cd` into the worktree
  and keep the long paths in variables. On 1.0.77, 21 of the 28 refusals came at the release and acceptance stages
  (release-plan 10, release-verify 7), from scripts that copy the candidate into `"$COPY"` or `"$SCRATCH"`.
- **Rate.** Over the 267 recorded Grok runs (2026-10-05 to 11-14), 193 shell calls were refused, all under `auto`: 82 in 21
  of 27 deliveries, 96 in 41 of 139 planning slices, and 15 in 15 of 97 start-route probes. On 1.0.77 the rate is 1.28 per
  100 shell calls (28 of 2,186). Every refusal in a run that kept Grok's session store ended its turn (176 of 176). The 4
  runs under `bypassPermissions` had none in 1,292 shell calls.
- **Cost.** A refusal costs a session: a median 10.9 s to the next session's first tool call (90th percentile 36.8 s), and
  the resumed model re-reads its context (the four planning-points runs' medians were 122,000 to 187,000 tokens per resume).
  The resumed model is not told why its session ended, so half the refusals (88 of 176) were followed by another refusal
  within the next 10 shell calls. That is how pp-3 was lost. After its first refusal at release-plan, each of the next seven
  sessions (38 s to 7 minutes long) ended on another `"$VAR"`-target script. `run.py`'s stall stop (3 resumes without
  progress) ended the run, then ended its `--resume-run` the same way. No other recorded run was lost to a refusal.
- **Recommendation** (for the owner). Keep `auto` and add two apparatus-only changes: a Grok `PreToolUse` hook in the
  profile the harness builds, which denies the three floored shapes with a reason the model reads (a prototype recovered
  in the same turn 2 of 2 times, against 0 of 2 without it), and a resume prompt that names a refusal and the rewrite. The
  alternative, `bypassPermissions`, removes every refusal but also the classifier's 53 recorded blocks, and breaks
  comparability with every earlier Grok run. Details and costs are in [Options](#options).

## Method

1. **Read the setup.** `test/shiploop_e2e/hosts.py` (`GrokHost.argv`, `grok_keepalive`), `run.py` (`--permission-mode`
   default `auto`, a case's `platform.host_allow` passed as `--allow`, `resume_prompt`, the `RESUME_STALL` stop),
   `slice.py` (also `auto`), ShipLoop's keepalive (`skills/shiploop/scripts/shiploop_keepalive.py`: `PostToolUse`, `Stop`,
   `SessionEnd`), and Grok 1.0.77's own guides (`~/.grok/docs/user-guide/22-permissions-and-safety.md`, `10-hooks.md`,
   `14-headless-mode.md`). The audit harness's adapter (`skills/shiploop-e2e-audit/harness/grok_adapter.py`) is not on
   this path: it launches with `--permission-mode default` unless told otherwise, and nothing here touches it or its pins.
2. **Pair every shell call with Grok's own decision** ([analyze.py](analyze.py)). Each isolated Grok profile keeps a session
   store (`home/.grok/sessions/<folder>/<session>/events.jsonl`) with one `permission_resolved` event per tool call
   (`decision`, `wait_ms`), but without the command. The run's `events.jsonl` has each command. The script pairs the n-th
   shell decision with the n-th shell call, and keeps a pairing only when both counts match and every `cancelled` decision
   falls on a call the stream marks cancelled: 168 of the 170 runs with a store paired. The host and permission mode come
   from each launch's `invocation*.json` (Codex streams are translated into Grok's shape, so the stream alone does not name
   the host). The Grok build comes from `result.json` or the profile's own log (`ver`). The stage of a refusal is the
   ShipLoop stage in progress at its time (`state.md` history and `timeline.json`).
3. **Read the decision source.** The 1.0.77 binary names its permission routes (`auto mode: fast-path allow`, `classifier
   route completed`, `classifier timed out … prompting user`, `bash_request_floor`, and floor reasons such as
   `unresolved_argument` and `file_write`), but its logs record only the classifier route, at any `RUST_LOG` level. So the
   floor was found by timing (0 to 13 ms, against 1.8 to 8 s for the classifier) and by probes.
4. **Probe** ([probe.py](probe.py)). One fresh Grok 1.0.77 session per command, launched through `hosts.GrokHost` exactly as
   the harness launches it, with a layout like an E2E run (`work/` as the session folder, `.shiploop-runs/<name>/{run,worktree}`
   beside it), outside any temporary folder, under `~/e2e-runs-refusal-probe/20261115/`. Of the 59 sessions that asked for
   one exact command, 56 ran it character for character and 3 added or dropped only a final newline; the other 4 sessions
   gave the model a small task. Batches: `replay-1077` (eight refused commands from pp-1 to pp-4, their run root swapped),
   `pairs-1077` and `pairs2-1077` (minimal pairs, one feature changed at a time), `allow-1077` and `allowall-1077` (allow
   rules), `hook-1077` and `task-1077`/`task-hook-1077` (the prototype hook of
   ded345978767587e07c6fffe60aa3f7e785c668b), `trace-1077` (a log-level attempt), then, while building the fix,
   `writers-1077` and `writers2-1077` (each writing program with a variable or a post-`cd` target) and `live-hook-1077`
   and `live-task-hook-1077` (the harness's own installed hook). Model `grok-4.6` at `low`: the permission decision is not
   the model's. The 81 sessions cost $2.00, and every one was answered by Grok 1.0.77 (each profile's log names its build).
5. **Check the rule against the record.** The rule is code in one place, `test/shiploop_e2e/grok_preempt.floor_shapes`,
   which the harness's hook applies and `analyze.py` imports. It agrees with all 60 exact-command probes, and on the
   recorded runs it flags every 1.0.77 refusal (28 of 28) and no allowed 1.0.77 call (0 of 2,155). The first version's own
   copy of the rule (in analyze.py) flagged the same calls; it was replaced by the import.
6. **Summarize** ([summarize.py](summarize.py)) and export the probe sessions ([export_probes.py](export_probes.py)) into
   [evidence/](evidence/). Paths are written with `~`; nothing from the probes' debug logs is kept except the classifier
   verdict lines, because those logs also hold the account's sign-in response.

## The rule, by probe

| Command shape (1.0.77, `auto`, headless) | Decision | Wait |
|---|---|---|
| `COPY=…` then `mkdir -p "$COPY"` | refused, turn cancelled | 0 ms |
| `X=…` then `cp a "$X/"`; `X=…` then `echo hi \| tee "$X/t.txt"` | refused | 0 ms |
| `mkdir -p "${TMPDIR:-/tmp}/x"`; `mkdir -p "$(dirname …)"` | refused | 0 ms |
| `X=…` then `rm -rf "$X"`, `mv a "$X/m.md"`, `touch "$X/t.txt"`, `ln -s a "$X/l.md"`, `cp a "$X"` | refused | 0 to 6 ms |
| `cd WT && cp README.md copy.md`; `cd WT && rm -f copy.md`; `cd WT && touch t.txt` | refused | 0 to 1 ms |
| `cd WT && mkdir -p fixtures`; `cd WT && git show HEAD:README.md > fixtures.txt`; `(cd WT && mkdir -p x)` | refused | 0 to 1 ms |
| ```` python3 -c "… r'```x\n(.*?)\n```' …" ```` (backticks in double quotes) | refused | 0 ms |
| the eight refused commands of pp-1 to pp-4, replayed in fresh sessions | refused (8 of 8) | 0 to 9 ms |
| the three refused shapes with `--allow` rules, or with `--allow 'Bash(*)'` | refused (6 of 6) | 0 to 7 ms |
| `mkdir -p "<literal absolute path>"`, `cd WT && git status`, `cd <session folder> && mkdir -p fixtures`, multi-line read-only, `set -e` | fast-path allow | 0 ms |
| `rm -rf "<literal path>"`, `git -C WT archive HEAD \| tar -x -C "<literal path>"`, `git -C WT show … > WT/fixtures.txt`, `cd WT && node --version > <absolute path>` | classifier, allowed | 2.5 to 3.4 s |
| `X=…` then `cat "$X/a.md"`, `git -C "$WT" status`, `echo "$COPY"`, `node --version > "$X/out.txt"`, `cat > "$X/a.txt" <<'EOF'` | classifier, allowed | 2.2 to 3.4 s |
| the backtick command with `~~~` instead, or in single quotes; `` echo "a `date` b" ``; `echo HEAD $(git … rev-parse HEAD)` | classifier, allowed | 2.2 to 3.8 s |
| `python3 <run>/scratch/probe.py` (a script file run as one command) | classifier, allowed | 3.9 s |
| `X=…` then `rsync -a <dir>/ "$X/"`, `tar -czf "$X/a.tgz" …`, `git -C WT archive HEAD \| tar -x -C "$X"`, `cp "$X/a.md" <literal path>` | classifier, allowed | 3.3 to 7.1 s |

Earlier builds differed. 1.0.46 (runs from 2026-10-05 to 10-09) had no floor: 20 calls of these shapes were all allowed, and
its 3 refusals were classifier timeouts and escalations. 1.0.70 (runs from 2026-10-24 to 11-01) refused more: the three shapes
match 110 of its 125 floor refusals, and 12 of the other 15 hold ```` ``` ```` inside single quotes or a quoted
here-document, which 1.0.77 parses correctly.

## The rate

| Grok build | Mode | Runs | Shell calls | Refused | Per 100 calls | Runs with a refusal | Floor | Classifier timeout (~30 s) | Other |
|---|---|---|---|---|---|---|---|---|---|
| 1.0.46 | auto | 5 | 690 | 3 | 0.43 | 2 | 0 | 2 | 1 |
| 1.0.62 | auto | 3 | 1,348 | 11 | 0.82 | 3 | 5 | 5 | 1 |
| 1.0.70 | auto | 250 | 8,171 | 151 | 1.85 | 68 | 125 | 5 | 21 (17 counted from the stream only) |
| 1.0.77 | auto | 5 | 2,186 | 28 | 1.28 | 4 | 28 | 0 | 0 |
| 1.0.62 and 1.0.70 | bypassPermissions | 4 | 1,292 | 0 | 0 | 0 | 0 | 0 | 0 |

The four planning-points runs had 4 to 11 refusals each. By stage, over the delivery runs: research 13, test-strategy 11,
release-plan 10, release-verify 10, discovery 8, system-test-author 6, test 4, and 20 more over 11 other stages. The
slices concentrate at test-strategy and step-plan because they were seeded there. The start-route probes' 15 refusals were all
the model's first `mkdir -p "$(dirname "$RUN_DIR")"` before `init`.

Every table is in [evidence/summary.md](evidence/summary.md) ([summary.json](evidence/summary.json)). Each refused call, with
its stage, wait, shape and command head, is in [evidence/refusals.jsonl](evidence/refusals.jsonl); each probe session is in
[evidence/probes.jsonl](evidence/probes.jsonl).

## What the classifier blocks

Auto-review's classifier also blocks commands itself, 53 times in these runs. Those blocks are reported to the model
(`Tool run_terminal_command was not executed: Auto mode blocked this action (…)`) and the turn goes on, so they do not cost a
session. They stopped commands whose payload it could not see (20, for example a `bash -c` of a file's contents or an argv
read from a JSON packet), changes to the remote Salesforce org `de` (14: deploys, deletes, anonymous Apex, and a query of a
named person's user record), `git checkout --` and other reverts that would discard uncommitted work (11), deletion of
non-scratch files and folders (6), automation of the live Safari (1) and a fast-forward of `main` (1). Any fix that turns
Auto-review off gives these up.

## Options

| Option | Expected effect, with its evidence | Cost to comparability with earlier evidence | Other costs and risks |
|---|---|---|---|
| **A.** `--permission-mode bypassPermissions` for the Grok subject (a host default) | No floor, timeout or classifier refusal: 0 in 1,292 shell calls over 4 runs. Grok's guide recommends always-approve for automation. | Breaks it. Every Grok baseline and earlier Grok run used `auto`. Sessions, turns, time and cost fall, and the 53 classifier blocks disappear, so behaviour where a block steered the model changes. | No command review at all in a run that can reach the owner's filesystem, network, and any platform a case wires in. Deny rules would bring back a refusal class: with a Bash deny rule, a headless run denies every command Grok cannot check. |
| **B.** Allow rules (`--allow`, a case's `platform.host_allow`) | None: the floor defers every allow rule, even `Bash(*)` (6 of 6 refused). | None | It looks like a fix and is not one. |
| **C.** A ShipLoop packet rule for scratch and check scripts, as F10 of the 2026-10-18 Battleship analysis proposed (118d6f7d2c1394a11f1d06aaea006193e3a5369d; never built) | Partial: depends on the model following it in long contexts, untested. | Changes ShipLoop on every host. Needs an E2E round, and every later baseline on every host differs. | A Grok 1.0.77 detail in every packet on every host. A product change, outside this apparatus task. |
| **D.** `run.py`'s resume prompt says that the last command was refused by Grok's check, quotes its head, and gives the rewrite | Does not prevent a refusal. It targets the repeats: 88 of 176 refusals were followed by another within 10 calls, and each of pp-3's seven later sessions repeated the shape. | Small: only resumes that follow a refusal change. | Each first refusal still costs a session (median 10.9 s plus a context re-read). |
| **E.** A Grok `PreToolUse` hook in the profile the harness builds, beside the keepalive hooks, that denies the three shapes with the rewrite (built: [grok_preempt.py](../../../test/shiploop_e2e/grok_preempt.py)) | Turns a session-ending refusal into a refusal the model reads in the same turn. Probes: 3 of 3 shapes completed instead of cancelling; a task that invites a `"$VAR"` write recovered in the same turn 2 of 2 times, rewriting to literal paths, against 0 of 2 without the hook. On the record, the shapes flag 28 of 28 refusals and 0 of 2,155 allowed calls on 1.0.77. | Moderate. Auto-review and its classifier stay, so quality evidence stays comparable. Session counts and time fall in runs that met refusals. | Calibrated on 1.0.77: a new build can move the floor (1.0.70's was broader), so the hook needs a pin, like the adapter's verb pin. A false flag costs the model one rewrite, not a session; a missed shape costs what it costs today. It denies only what Grok would refuse; it does not rewrite or approve anything. |

Rejected outright: rewriting a floored command into a script file inside the hook (`updatedInput`). Grok would then review a
command that hides what the floor exists to see; if the owner wants the check off, option A says so openly.

**Recommendation: E with D.** E removes the session losses of the three known shapes on the current build. D covers what E
cannot: classifier timeouts (12 recorded, none on 1.0.77), escalations, and any shape a new build adds. Both stay inside the
E2E apparatus; neither changes ShipLoop, the subject model or the permission mode. Building them needs the owner's go,
because they change what the harness measures in Grok runs that meet a refusal. The owner gave it the same day; see
[Decision and fix](#decision-and-fix-2026-11-15).

## Decision and fix (2026-11-15)

The owner chose E with D ("Hook + resume note"), and both are built in the E2E harness. No ShipLoop file, host permission
mode, subject model or baseline row changed.

- **E, the hook.** `test/shiploop_e2e/grok_preempt.py` is the rule, the hook and its installer. `GrokHost.preempt_install`
  copies the module into the run's throwaway profile (`home/.grok/hooks/refusal-preempt.py`) and registers it as a
  PreToolUse hook with the matcher `run_terminal_command`, before each Grok session; a profile that has it keeps it, so a
  resumed run keeps the hook it started with, and a regrade only reads it. Each denial is logged in the run's state
  folder. `result.json` records `preempt` (installed, kept, the script's sha256, `calibrated_on`, and the denials), and
  the baseline row `preempted_tool_calls`. Claude and Codex get no hook.
- **D, the resume note.** When the last Grok session ended on a refused shell call, run.py's resume prompt (the resume
  loop's, and `--resume-run`'s opening) adds a note: the refused command's first 200 characters, not to run it again as
  written, and the hook's rewrite.
- **Live check** (Grok 1.0.77, the real install): the matcher fires; the three refused shapes were denied and each turn
  completed (3 of 3, batch `live-hook-1077`); the task that invites a `"$VAR"` write recovered in the same turn 2 of 2
  times, each with one logged denial and the copied file in place (`live-task-hook-1077`).
- **Pin.** `grok_preempt.CALIBRATED_BUILD` is 1.0.77. A hermetic test checks the rule against every exact-command probe
  in [evidence/probes.jsonl](evidence/probes.jsonl) and that each was answered by that build. When Grok updates, rerun
  `probe.py`'s cases on the new build, export them, and move the constant only when the test passes again.

## Unknowns

- Whether E's in-turn recovery holds across a whole long delivery: the probes test single commands and one small task.
- How the next Grok build moves the floor. 1.0.77 is the build every current E2E run uses (installed 2026-11-06).
- The Claude host also runs with `--permission-mode auto`. Its refusals are not measured: `cancelled_tool_calls` is a
  Grok-only signal (1a35bc503e07c75675527efabbfdb79f791f0343). Codex runs with approval_policy never.
- Real ShipLoop users who run Grok headless meet the same floor, because ShipLoop's run folder sits outside the session's
  folder for them too. Only a ShipLoop change would help them (for example, the keepalive installer adding the same hook);
  that is a product question for the owner.
- The 15 start-route probe trials refused at their first command (2026-11-01) lost that session before their route was
  recorded; whether that moved the start-route study's counts was not checked.

## Files

- [analyze.py](analyze.py): pairs every Grok shell call with Grok's decision; its shapes come from the harness's rule.
- [summarize.py](summarize.py): the rate tables and the compact evidence.
- [probe.py](probe.py): one-command Grok sessions through `hosts.GrokHost`; options for allow rules and the harness's hook.
- [export_probes.py](export_probes.py): the probe sessions into `evidence/probes.jsonl`, redacted, with the build that answered.
- The hook itself is [test/shiploop_e2e/grok_preempt.py](../../../test/shiploop_e2e/grok_preempt.py). The prototype this
  page first linked (`preempt_hook.py`) is in ded345978767587e07c6fffe60aa3f7e785c668b and was removed when the harness
  module replaced it.
- [evidence/](evidence/): `summary.md`, `summary.json`, `refusals.jsonl`, `probes.jsonl`.

To reproduce: `python3 -I analyze.py OUT` over `~/e2e-runs*` (about 50 s), then `python3 -I summarize.py OUT evidence`.
The probe sessions are under `~/e2e-runs-refusal-probe/20261115/`, outside the repository.
