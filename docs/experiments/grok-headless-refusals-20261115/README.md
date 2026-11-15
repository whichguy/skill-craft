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
- **Trigger** (probed on 1.0.77, 109 Grok sessions in all). The floor fires on three shapes, deterministically, in 0 to
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
  (release-plan 10, release-verify 7): 17 of them a `"$VAR"` write target, as in scripts that copy the candidate into
  `"$COPY"` or `"$SCRATCH"`, and 4 the backtick shape.
- **Rate.** Over the 267 recorded Grok runs (2026-10-05 to 11-14), 193 shell calls were refused, all under `auto`: 82 in 21
  of 27 deliveries, 96 in 41 of 139 planning slices, and 15 in 15 of 97 start-route probes. On 1.0.77 the rate is 1.28 per
  100 shell calls (28 of 2,186). Every refusal in a run that kept Grok's session store ended its turn (176 of 176). The 4
  runs under `bypassPermissions` had none in 1,292 shell calls.
- **Cost.** A refusal costs a session: a median 10.9 s from the refusal to the run's next permission decision more than
  half a second later, which is the resumed session's first decided call (90th percentile 36.8 s), and
  the resumed model re-reads its context (the four planning-points runs' medians were 122,000 to 187,000 tokens per resume).
  The resume prompt did not say why the session ended, and half the refusals (88 of 176) were followed by another refusal
  within the next 10 shell calls. That is how pp-3 was lost. After its first refusal at release-plan, each of the next seven
  sessions (38 s to 7 minutes long) ended on another `"$VAR"`-target script. `run.py`'s stall stop (3 resumes without
  progress) ended the run, then ended its `--resume-run` the same way. No other recorded run was lost to a refusal.
- **Recommendation** (for the owner). Keep `auto` and add two apparatus-only changes: a Grok `PreToolUse` hook in the
  profile the harness builds, which denies the three floored shapes with a reason the model reads (a prototype recovered
  in the same turn 2 of 2 times, against 0 of 2 without it), and a resume prompt that names a refusal and the rewrite. The
  alternative, `bypassPermissions`, removes every refusal but also the classifier's 53 recorded blocks, and breaks
  comparability with every earlier Grok run. Details and costs are in [Options](#options). The owner chose the hook and
  the resume note the same day; see [Decision and fix](#decision-and-fix-2026-11-15).

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
   the model's. Then `replay-hook-1077` (the 28 real refused commands with the hook; see Decision and fix). The 109
   sessions cost $3.41, and every one was answered by Grok 1.0.77 (each profile's log names its build).
5. **Check the rule against the record.** The rule is code in one place, `test/shiploop_e2e/grok_preempt.floor_shapes`,
   which the harness's hook applies and `analyze.py` imports. It agrees with all 60 exact-command probes (no hook, no
   allow rule), and on the recorded runs it flags every 1.0.77 refusal (28 of 28) and none of the 2,155 other 1.0.77 shell
   calls (2,154 allowed, 1 blocked by the classifier). The first version's own
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

Earlier builds differed. No floor refusal was observed on 1.0.46 (runs from 2026-10-05 to 10-09): 20 calls of these shapes
were all allowed, and
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
a `mkdir -p` before `init` whose target held an expansion (8 `"$RUN_DIR"`, 6 `"$(dirname "$RUN_DIR")"`, 1 `"$PARENT"`).

Every table is in [evidence/summary.md](evidence/summary.md) ([summary.json](evidence/summary.json)). Each refused call, with
its stage, wait, shape and command head, is in [evidence/refusals.jsonl](evidence/refusals.jsonl); each probe session is in
[evidence/probes.jsonl](evidence/probes.jsonl).

## What the classifier blocks

Auto-review's classifier also blocks commands itself: 53 blocks attributable to a call in the paired runs (56 block decisions
in all, 3 of them in runs whose calls could not be paired). Those blocks are reported to the model
(`Tool run_terminal_command was not executed: Auto mode blocked this action (…)`) and the turn goes on, so they do not cost a
session. They stopped commands whose payload it could not see (20, for example a `bash -c` of a file's contents or an argv
read from a JSON packet), changes to the remote Salesforce org `de` (14: deploys, deletes, anonymous Apex, and a query of a
named person's user record), `git checkout --` and other reverts that would discard uncommitted work (11), deletion of
non-scratch files and folders (6), automation of the live Safari (1) and a fast-forward of `main` (1). Any fix that turns
Auto-review off gives these up.

## Options

| Option | Expected effect, with its evidence | Cost to comparability with earlier evidence | Other costs and risks |
|---|---|---|---|
| **A.** `--permission-mode bypassPermissions` for the Grok subject (a host default) | No floor, timeout or classifier refusal: 0 in 1,292 shell calls over 4 runs. Grok's guide recommends always-approve for automation. | Breaks it. Every Grok baseline and every earlier Grok run but the 4 above used `auto`. Sessions, turns, time and cost fall, and the 53 classifier blocks disappear, so behaviour where a block steered the model changes. | No command review at all in a run that can reach the owner's filesystem, network, and any platform a case wires in. Deny rules would bring back a refusal class: with a Bash deny rule, a headless run denies every command Grok cannot check. |
| **B.** Allow rules (`--allow`, a case's `platform.host_allow`) | None: the floor defers every allow rule, even `Bash(*)` (6 of 6 refused). | None | It looks like a fix and is not one. |
| **C.** A ShipLoop packet rule for scratch and check scripts, as F10 of the 2026-10-18 Battleship analysis proposed (118d6f7d2c1394a11f1d06aaea006193e3a5369d; never built) | Partial: depends on the model following it in long contexts, untested. | Changes ShipLoop on every host. Needs an E2E round, and every later baseline on every host differs. | A Grok 1.0.77 detail in every packet on every host. A product change, outside this apparatus task. |
| **D.** `run.py`'s resume prompt says that the last command was refused by Grok's check, quotes its head, and gives the rewrite | Does not prevent a refusal. It targets the repeats: 88 of 176 refusals were followed by another within 10 calls, and each of pp-3's seven later sessions repeated the shape. | Small: only resumes that follow a refusal change. | Each first refusal still costs a session (median 10.9 s plus a context re-read). |
| **E.** A Grok `PreToolUse` hook in the profile the harness builds, beside the keepalive hooks, that denies the three shapes with the rewrite (built: [grok_preempt.py](../../../test/shiploop_e2e/grok_preempt.py)) | Turns a session-ending refusal into a refusal the model reads in the same turn. Probes: 3 of 3 shapes completed instead of cancelling; a task that invites a `"$VAR"` write recovered in the same turn 2 of 2 times, rewriting to literal paths, against 0 of 2 without the hook. On the record, the shapes flag 28 of 28 refusals and none of the 2,155 other calls on 1.0.77. | Moderate. Auto-review and its classifier stay; how changed trajectories affect quality is not measured. Session counts and time should fall in runs that met refusals. | Calibrated on 1.0.77: a new build can move the floor (1.0.70's was broader), so the hook needs a pin, like the adapter's verb pin. A false flag costs the model at least one rewrite instead of a session (not measured); a missed shape costs what it costs today. It denies what its rule, calibrated on 1.0.77's probes and record, predicts Grok refuses; outside that corpus that is unverified. It returns a deny or no opinion and never replaces a call's input. |

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
- **Replay of the real refusals** (batch `replay-hook-1077`, $1.41): the 28 commands Grok refused in pp-1 to pp-4, each in a
  fresh session laid out like its run, with the harness's hook installed. The hook denied 28 of 28 in the turn (one logged
  denial each), Grok refused none, and every turn completed. With the record check above (no false flag in the 2,155 other
  calls of the same runs), this verifies the deny for these 28 recorded refusals and the rule's agreement on the record's
  other calls; it does not test the model's rewrite in a long context.
- **No whole-delivery round.** A `ticket-due-times` verification run (`~/e2e-runs-refusal-probe/20261115/tdt-hook-1`) was
  started and stopped after 5 minutes at discovery: the owner judged a 6-hour run excessive for this check, and the replay
  above answers the correctness question for about a dollar. Its record shows the hook in a real run (installed,
  `build_matches` true, no denial yet); it can be continued with `--resume-run`. The effect on sessions and time over a
  whole delivery is left to the next Grok E2E round, which records it at no extra cost (`preempt` in result.json,
  `preempted_tool_calls` in the baseline row).
- **Pin.** `grok_preempt.CALIBRATED_BUILD` is 1.0.77. A hermetic test checks the rule against every exact-command probe of
  that build in [evidence/probes.jsonl](evidence/probes.jsonl) without a hook or an allow rule (81 after the review below;
  each row names the build that answered it). When Grok updates, rerun `probe.py`'s cases on the new build, export them
  beside the old rows, and move the constant only when the test passes for the new build. An installed copy keeps its own
  constant, so a resumed run's record names the build its hook was calibrated on.

## Review and rework (2026-11-15)

Before concluding, Astra (`gpt-6-astra`, max effort) reviewed the hook, the resume note, the tests and these write-ups. Its
verdict was "ship after the listed fixes", with 14 findings. Each was checked against the code, and the parser findings
against Grok itself, before anything changed:

- **Calibration batch `edges-1077`** (21 probes, no hook): Grok 1.0.77 allows `$` in single quotes or after a backslash, a
  `$` in a comment, adjacent non-empty backtick substitutions, a here-string operand (`<<< "$X"`), an attached redirect to
  `"$X…"`, an escaped `\>` after a `cd`, `<<\EOF` bodies, and `cp -t"$X"`. It refuses a quoted program name (`"mkdir"`), a
  write after a here-document with a hyphenated delimiter, `cp … "$X" <<< text`, `>|` after a `cd`, `if cd …; then mkdir …`,
  the `env` and `timeout` wrappers, and `touch -r "$X"`. It also refuses a relative write after a return to the session's
  folder, after a subshell's `cd`, after `cd .` and after `popd`: Grok never forgets a `cd`. The old rule disagreed with
  Grok on 15 of these 21: it missed 7 (every refusal above but `touch -r` and the four `cd` cases) and denied 8 (every
  allowed case but `cp -t"$X"`). On the other 6 it already agreed with Grok, and the change the review proposed for them
  (forgetting a `cd` at a scope's end, no target in `touch -r`'s value, reading an attached `-t`) would have broken that.
- **Batch `payload-1077`** (2 sessions): the hook event says `permissionMode` `auto` under `--permission-mode auto` and
  `bypassPermissions` under bypass.
- **What changed.** One lexer replaces the five scanners: it reads quotes, escapes, comments, operators, redirects with
  their operands, here-documents (any delimiter spelling, exact terminators, quoted with `\` too) and substitutions, and
  abstains on a command it cannot read to its end. The hook stands down outside `auto`, and run.py installs it only for an
  `auto` launch. The registered command ends in `|| true`: a script that cannot start would otherwise exit 2, which Grok
  reads as a deny of every shell call. The resume note reads only the last launch's events (from sessions.jsonl), only for
  a Grok launch, only an update whose whole text is Grok's refusal, and not when the call later completed or the session
  ended normally. Logging needs an absolute XDG_STATE_HOME (the harness's profile), the denial record never raises and
  counts unreadable rows, and an installed copy's record reads that copy's own calibration.
- **Results.** The rule agrees with all 81 exact-command probes of 1.0.77. On the recorded runs it still flags 28 of 28
  1.0.77 refusals and none of the 2,155 other calls, and 1.0.70's 2 false flags fall to 0 (110 of 125 refusals flagged).
  Live with the reworked install (batches `live2-hook-1077` and `live2-task-hook-1077`): 3 of 3 shapes denied in the turn
  and 2 of 2 task recoveries, one logged denial each. On pp-1's real stream the bounded reader finds the refused command in
  exactly the 11 of 12 sessions a refusal ended, and the review's case of a later session that wrote no end event reads as
  no refusal.
- **Corrected wording.** Several numbers and claims on this page, the SPEC rules and the journal entry overstated the
  evidence (the 2,155 calls include one classifier block; 53 blocks are the call-attributable ones of 56; the start-route
  targets were not all `dirname`; "had no floor", "only what Grok would refuse", "covers both ways", "because the resumed
  model was not told", "quality stays comparable"); they now say what was measured.

## Unknowns

- Whether E's in-turn recovery holds across a whole long delivery: the probes test single commands and one small task.
- How the next Grok build moves the floor. 1.0.77 is the build every current E2E run uses (installed 2026-11-06).
- The Claude host also runs with `--permission-mode auto`. Its refusals are not measured: `cancelled_tool_calls` is a
  Grok-only signal (1a35bc503e07c75675527efabbfdb79f791f0343). Codex runs with approval_policy never.
- Real ShipLoop users who run Grok headless meet the same floor, because ShipLoop's run folder sits outside the session's
  folder for them too. Only a ShipLoop change would help them (for example, the keepalive installer adding the same hook);
  that is a product question for the owner.
- The 15 start-route probe trials refused before `init` (2026-11-01) lost that session before their route was
  recorded; whether that moved the start-route study's counts was not checked.

## Files

- [analyze.py](analyze.py): pairs every Grok shell call with Grok's decision; its shapes come from the harness's rule.
  `--until 2026-11-14` keeps the diagnosis's corpus, so later runs (with the hook) do not change the evidence.
- [summarize.py](summarize.py): the rate tables and the compact evidence.
- [probe.py](probe.py): one-command Grok sessions through `hosts.GrokHost`; options for allow rules (`--allow`), the
  harness's hook (`--preempt-hook`), a task instead of an exact command (`--prompt task`) and Grok's debug log
  (`--rust-log`). A case may give the folders a recorded run had, which is how the 28 refusals were replayed.
- [record_payload.py](record_payload.py): the hook that recorded what Grok's hook event says (batch `payload-1077`).
- [export_probes.py](export_probes.py): the probe sessions into `evidence/probes.jsonl`, redacted, with the build that
  answered, and the recorded hook events into `evidence/payloads.jsonl`.
- The hook itself is [test/shiploop_e2e/grok_preempt.py](../../../test/shiploop_e2e/grok_preempt.py). The prototype this
  page first linked (`preempt_hook.py`) is in ded345978767587e07c6fffe60aa3f7e785c668b and was removed when the harness
  module replaced it.
- [evidence/](evidence/): `summary.md`, `summary.json`, `refusals.jsonl`, `probes.jsonl`, `payloads.jsonl`.

To reproduce: `python3 -I analyze.py OUT --until 2026-11-14` over `~/e2e-runs*` (1 to 2 minutes), then
`python3 -I summarize.py OUT evidence`, and `python3 -I export_probes.py ~/e2e-runs-refusal-probe/20261115 evidence`.
The probe sessions are under `~/e2e-runs-refusal-probe/20261115/`, outside the repository.
