# ShipLoop E2E harness: defects and fixes journal

Started 2026-10-29. Living record of defects found in the E2E harness itself (grading, measurement, monitors) and their
fixes, one entry each, newest last. Edit in place; mark superseded claims with the date and the reason rather than
deleting them.

This is not the round journal. `test/shiploop_e2e/LEARNINGS.md` holds the E2E rounds, and the release preflight reads
any commit that touches it after a ShipLoop commit as an E2E round for that commit. A harness fix is not a round, so its
entry lives here, and no entry here vouches for a ShipLoop change.

## A model that abandons its first ShipLoop run left the output ungradable: one rule now picks the live run (2026-10-29) — status: firm for the defect and the fix; the sticky recorded identity is an open edge

**What was seen.** The brownfield session's R1 run (`~/e2e-runs-brownfield/20261029/bf-ds-r1-ticket-assignment`, DeepSeek
flash) intaken a request that shell quoting had mangled (S8 to S10 were lost). The model paused its own first run
(`work-20261029-142617-dad502`, `status_reason`: "Run intaken with a shell-mangled request … replaced by a fresh run") and
started a second (`work-20261029-142643-b5c43b`). With two runs under `.shiploop-runs/`: `run.grade_shiploop` found two
runs and nothing to tell them apart, so the verdict was `ambiguous` and the run could never pass, whatever the product did;
`metrics.run_dir_of` returned None, so stage times, the planning window and refusals went unmeasured; and the progress
monitor, taking the first `state.md` in path order, read "paused, rev 1, intake" for the whole run. The brownfield session
reported it and worked around it by hand (`record_run_identity` then `--grade-only`).

**What changed.** `test/shiploop_e2e/run_choice.py` is the one rule: the run `shiploop-run.json` records while its state
is readable; else the only run that was not there before the invocation; else, among several, the runs not paused or halted
(done and blocked stay in play), one of which is the run, several told apart only by the one the host's `--run-dir`
commands named; when every run is paused or halted, the one whose `state.md` changed strictly last. Anything left is a tie:
the verdict is `ambiguous` and lists only the tied runs, `run_dir_of` returns None, the monitor and the card say
`ambiguous`. Nothing is picked at random, and a run that was already there when the invocation started is never a
candidate. A choice that follows the runs' statuses is made again at every reading and is not recorded, because a model can
resume a run it paused. The runs not chosen are listed as `other_runs`. The same rule now serves `grade_shiploop`,
`metrics.run_dir_of`, `progress.py`, the owner-note watcher, the Live Run Card (`status_card.build_e2e`) and
`packets.find_run_dir` (the flow viewer, the packet report and the owner page). A folder with exactly one run grades with
the same keys in the same order as before.

**Evidence.** 21 new tests in `MultipleRunsTest` (`test/shiploop-e2e.test.py`), each asking the readers: 19 of 27 failed on
the unfixed source (the verdict `ambiguous`, `run_dir_of` None, the monitor on the paused run, an arbitrary first-in-path
pick for two live runs) and all pass after; mutation checks (newest wins among live runs, halted not set aside, blocked set
aside, always recording an identity, taking the first of a tied newest moment, ignoring the recorded identity) were each
killed by at least one test. On a copy of the real example's two `state.md` files and its `shiploop-run.json` (nothing was
written to the live folder) the verdict chose `work-20261029-142643-b5c43b` with the paused run in `other_runs`, and the
monitor read "active, rev 8, stage plan". A review found the Live Run Card and `packets.find_run_dir` still taking the first
run in path order; both now use the rule. A second review's `~nobody/run` finding (`Path.expanduser` raises `RuntimeError`
on an unresolvable `--run-dir`, which would crash the verdict and now the monitor) was reproduced by a fail-first test and
fixed.

**Open edges.**
- A recorded identity is sticky by design: when the only run present at one grade is recorded and the model abandons it for
  a second run in a later resumed session, the recorded run keeps winning. If a real run shows it, treat an identity whose
  basis is "the only new run" as soft (superseded when that run is paused or halted and exactly one other new run is in
  play).
- Run Review's exporter (`skills/shiploop-run-review/scripts/export.py`) may not import from `test/`: it takes the run
  `result.json` names, which the verdict wrote from this rule. Nothing reads `other_runs` to flag a model that started
  several runs; surfacing it in Run Review is a skill change and needs a release.
- Two live runs, or a finished run beside a live one, stay `ambiguous` even when one is newer; the 2026-10-16 audit control
  requires it.

## Grok's headless refusals end sessions: a pre-classifier write check in Auto-review, measured over 267 Grok runs; the owner chose the hook and the resume note, both built (2026-11-15) — status: firm for the cause (Grok 1.0.77), the rate, the fix's unit and live checks and one short real delivery (4 refusals turned into in-turn denials, no session lost); interim for the size of the effect on long deliveries

**What was seen.** The planning-points probe (E24, 909adf228e00254d293ddfcd76b8011ef296fd6c) had 28 refused shell commands in
four Grok 1.0.77 deliveries, each ending a host session as `cancelled`, and pp-3 was lost at release-plan. The same category
had been counted since 33bd1a186a293c128e6a351da3586cdb66cac424 (run 6's cancelled calls) and in the Battleship analysis
(118d6f7d2c1394a11f1d06aaea006193e3a5369d, which proposed a packet rule, F10, that was never built), but its rule and rate
were unknown.

**Cause.** `run.py` launches Grok with `--permission-mode auto` (Auto-review) and no user. Before its classifier, Auto-review
checks which files a shell command writes; when it cannot resolve a written path it raises a floor only a person can clear.
Headless, Grok refuses the call, ends the turn as `cancelled` (`permission_cancelled`, 176 of 176 paired refusals), and skips
the `Stop` hook, so ShipLoop's keepalive cannot hold the session. Probed on 1.0.77 (63 sessions through `hosts.GrokHost`: 59
exact commands and 4 small tasks), the floor fires on three shapes in 0 to 13 ms, with no classifier call: a file-writing program whose
target holds a shell expansion (`mkdir -p "$COPY"`, `cp a "$X/"`, `tee "$X/…"`); a relative write after a `cd` to a folder
other than the session's (`cd WT && mkdir -p fixtures`); and an empty backtick substitution (two adjacent backticks)
inside double quotes or an unquoted here-document (Python one-liners reading ShipLoop's ```` ```shiploop-state ````
blocks). Allow rules, even `--allow 'Bash(*)'`, do not lift it. E2E meets it
because ShipLoop's run folder and worktree sit beside the session's folder (`<run>/work`), not in it.

**Rate.** 193 refused shell calls in the 267 recorded Grok runs (2026-10-05 to 11-14), all under `auto`; none in 1,292 shell
calls under `bypassPermissions` (4 runs). 1.28 per 100 shell calls on 1.0.77; refusals in 21 of 27 deliveries. Each costs a
session (median 10.9 s to the next tool call, plus a 122,000 to 187,000-token context re-read per resume), and 88 of 176 were
followed by another within 10 shell calls, under a resume prompt that did not say why the session ended. One run in all
was lost outright: pp-3, whose seven later sessions each ended on another `"$VAR"`-target script until the stall stop ended it.

**Options and recommendation.** Detailed in docs/experiments/grok-headless-refusals-20261115/README.md, "Options". Allow
rules do nothing. `bypassPermissions` removes every refusal but also the classifier's 53 model-visible blocks (remote
Salesforce changes, discarded uncommitted work, non-scratch deletes), and breaks comparability with every earlier Grok run.
A ShipLoop packet rule is a product change on every host. Recommended for the owner's go: a Grok `PreToolUse` hook in the
harness's profile that denies the three shapes with the rewrite, so the model reads the refusal in the same turn (prototype:
2 of 2 in-turn recoveries on a task, 0 of 2 without it; the shapes flag 28 of 28 recorded 1.0.77 refusals and none of
the 2,155 other 1.0.77 calls, 2,154 allowed and 1 blocked by the classifier), plus a resume prompt that names a refusal
for whatever the hook misses.

**Fix (owner's choice, the same day: "Hook + resume note").** `test/shiploop_e2e/grok_preempt.py` holds the rule, the
hook and its installer; `GrokHost.preempt_install` puts it in each Grok run's throwaway profile before the session, as a
PreToolUse hook on `run_terminal_command`, and run.py records `preempt` in result.json and `preempted_tool_calls` in the
baseline row. When a Grok session still ends on a refusal, the resume prompt names the refused command and the rewrite.
While building it, more probes corrected the rule: `rm`, `mv`, `touch` and `ln` targets are floored like `mkdir`'s, while
`tar -C`, `rsync` and a variable in a `cp` source are not (the first version had listed `tar -C`). The rule then agreed
with all 60 exact-command probes (81 after the review below) and still flagged 28 of 28 recorded 1.0.77 refusals and none
of the 2,155 other calls. Live, with
the real install on Grok 1.0.77, the matcher fires, the three shapes are denied in the turn (3 of 3), and the `"$VAR"`
task recovers in the same turn (2 of 2). Replaying the 28 commands Grok refused in pp-1 to pp-4 through the installed hook
denied all 28 in the turn, with no Grok refusal ($1.41). A whole `ticket-due-times` delivery was started as a further check
and stopped after 5 minutes, because the owner judged a 6-hour run excessive when the replay and the record check answer
the question; the next Grok E2E round records its sessions, time, denials and remaining refusals (`preempt`), and a
saving needs a comparison with runs like it. Hermetic tests
in test/shiploop-e2e-hosts.test.py (GrokPreemptTest and two
GrokResumeTest cases with a new `refused` fake-Grok mode); SPEC "A Grok refusal the harness can foresee is made in the
turn" and "A resume says when Grok's check ended the session".

**Review and rework (the same day).** Before concluding, Astra (`gpt-6-astra`, max effort) reviewed the hook, the note,
the tests and the write-ups: 14 findings, verdict "ship after the listed fixes". Each parser finding was probed on Grok
before the rule changed (batch `edges-1077`, 21 commands, no hook). The old rule disagreed with Grok on 15 of them. It
missed 7 that Grok refuses (a quoted program name, a write after a here-document with a hyphenated delimiter, a
here-string after a `"$X"` target, `>|` after a `cd`, `if cd …; then mkdir …`, and the `env` and `timeout` wrappers) and
denied 8 that Grok allows (`$` in single quotes, after a backslash or in a comment, adjacent non-empty backtick
substitutions, a `<<\EOF` body, a here-string operand, an attached `"$X…"` redirect, and an escaped `\>` after a `cd`).
On the other 6 it already agreed with Grok, and the review's proposed change would have broken that: Grok never forgets
a `cd` (a relative write after `popd`, a subshell's `cd`, `cd .` or a return to the session's folder is still refused),
counts `touch -r`'s value as a target, and allows `cp -t"$X"`. The rule became one lexer that abstains on a command it cannot read; the hook stands down outside
`auto` (batch `payload-1077`: the event's `permissionMode` is `auto` or `bypassPermissions`), run.py installs it only for
an `auto` launch, and its command ends in `|| true`, because a script that cannot start exits 2, which Grok reads as a
deny of every shell call. The note now reads only the last launch's events, only on Grok, only Grok's exact refusal text,
and not when that call later completed. Results: 81 of 81 exact probes agree; 28 of 28 recorded 1.0.77 refusals flagged
and none of the 2,155 other calls; 1.0.70's 2 false flags fall to 0; live, 3 of 3 shapes denied in the turn and 2 of 2
task recoveries (batches `live2-hook-1077`, `live2-task-hook-1077`). Corrected in this entry the same day, each for
overstating the evidence: "0 of 2,155 allowed calls" (one of them was a classifier block), "two adjacent backticks inside
double quotes" (an empty substitution, also in an unquoted here-document), "63 one-command sessions" (59 commands and 4
tasks), "because the resume prompt does not say why" (a co-occurrence, not a measured cause), "1.0.46 had none" (none was
observed) and "measures the session and time effect" (it records them; a saving needs a comparison).

**A short real delivery (the same day; the owner's choice, "Short real run first").** `hello`, seeded at step-plan,
through run.py on Grok 1.0.77 (grok-4.6 at xhigh, skill-craft 2.40.0 and ShipLoop 1.36.0 from the marketplace, the hook as
pushed in 4426c14db9d303fbc9ff625299fff610fe05bd69, so the pre-review copy;
`~/e2e-runs-refusal-probe/20261115/hello-seeded-hook-1`): PASS in one session with no resume, 112 minutes, $31.93, 201
shell calls, no Grok refusal. The hook denied 4 calls in the turn: a step-plan scratch probe with `"$PROBE"` targets and
a `cd` into it, then the model's first rewrite, which kept the `"$PROBE"` targets, and two `python3 -c "…```shiploop-state…"`
checks (carry-forward, handoff). Each time the model's next command came in the same turn: its second rewrite was a
Python script with a literal path, and after the other two it moved on. Replayed without the hook, laid out like the run
(batch `replay-hello-1077`, $0.10), Grok refused all 4 in 0 to 1 ms and each ended its session, so each, as written,
would have cost a session. The reworked rule flags the same 4 of the 201 calls. No earlier Grok 1.0.77 `hello` delivery
exists to compare time or cost with. This run vouches for the harness's hook, not for a ShipLoop change, so it is
recorded here and not in test/shiploop_e2e/LEARNINGS.md, whose latest touch the release preflight reads as an E2E round
covering every earlier ShipLoop commit.

**Evidence.** docs/experiments/grok-headless-refusals-20261115/ (analyze.py, summarize.py, probe.py, export_probes.py,
record_payload.py; evidence/summary.md, summary.json, refusals.jsonl, probes.jsonl, payloads.jsonl; the prototype
preempt_hook.py is in ded345978767587e07c6fffe60aa3f7e785c668b). Probe sessions under `~/e2e-runs-refusal-probe/20261115/`, outside the
repository.

**Open edges.**
- ~~No change is built.~~ Superseded the same day: the owner chose the hook and the resume note, and both are built.
  They change what the harness measures in Grok runs that meet a refusal (fewer sessions, `preempted_tool_calls`), so a
  Grok run before 2026-11-15 and one after differ there. One short seeded delivery has run with the hook (above: 4
  denials, no session lost); the size of the effect on a long delivery is not measured yet (the `ticket-due-times`
  verification was stopped at 5 minutes by the owner's call), and the next Grok E2E round records it.
- slice.py (the planning-slice experiments) installs neither the keepalive nor this hook, so a slice still loses its
  session to a refusal; adding the hook there would change those experiments' comparability and was left out.
- The floor is build-specific: no floor refusal was observed on 1.0.46, and 1.0.70 refused more (12 of its 15 refusals outside the three shapes hold
  ```` ``` ```` in single quotes or a quoted here-document). Any hook needs a per-build pin.
- The Claude host also runs `--permission-mode auto`; its refusals are not measured (a Grok-only signal, 1a35bc50).
