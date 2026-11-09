# Report template (normative)

Machine-written by `emit-report.py`. Agent pastes `chat-card.md` verbatim.

## On-disk layout

```text
<run root>/<repo-slug>/<UTC-ts>-<rand>/   # run root: $TEST_HARNESS_RUN_ROOT, else ${XDG_STATE_HOME:-$HOME/.local/state}/test-harness/runs
                                          # repo-slug: the sanitized basename of --repo
  manifest.json       # init-run.py
  terminal.json       # optional: { "stop": "no_progress", "detail": "…", "round": N }
  report.json         # source of truth
  results.md
  chat-card.md
  invoke-baseline/
  round-N/
    pre/ post/ delta.json
    stdout.log stderr.log meta.json
    side-effects.json   # classifier only (per-round; no top-level copy)
    restore.json        # fail path; safe restores + dirty-pre preservations
    tmp/
  worktree/ | fixes.patch   # fix-loop / agent only
```

## manifest.json (init-run.py)

Required fields: `repo`, `repo_slug`, `cmd`, `profile`, `source`, `mode`, `rounds_max`, `run_dir`, plus `schema_version`, `assume_fast`, `flags`, `started_at`.

## RESULT tokens (observation only)

| Token | Meaning |
|---|---|
| PASS_CLEAN | suite 0 ∧ side ok ∧ fs_scope full |
| PASS_CLEAN_SCOPED | suite 0 ∧ side ok ∧ scoped fs |
| FAIL_SUITE | suite ≠0 ∧ side ok |
| FAIL_SIDE_EFFECTS | suite 0 ∧ side fail≥1 |
| FAIL_BOTH | suite ≠0 ∧ side fail≥1 |
| STOPPED_MAX_ROUNDS | fix-loop exhausted rounds_max without PASS |
| STOPPED_SAME_ERROR | last 3 error_sig identical and ≠ none |
| STOPPED_NO_PROGRESS | terminal.json stop=no_progress |
| STOPPED_TIMEOUT_BUDGET | harness-wide wall-clock budget exhausted before the next round |
| INCOMPLETE_RUN | missing manifest or classifier after meta |

Mode limits (`once`, profile unknown) → `annotations` + `next_steps`, **not** RESULT tokens.

Greppable line:

```text
test-harness RESULT=<TOKEN> repo=<basename of --repo> suite=<exit> side_fail=<n> side_note=<m> rounds=<k>/<max> dur_ms=<n> run=<basename>
```

## Suite output the report understands

Case lines are recognised by shape: `PASS name` / `FAIL name` / `SKIP name`, two-space indented `PASS  name`, TAP
(`ok 1 - name`), `✓ name` / `× name`, rows with one label per suite padded to a fixed width and then `✓`, `✗` or
`SKIP`, and mocha-style `1) name` failures. Lines such as `PASS 15 foo tests` are module rollups, not cases. A suite
rollup line (`✓ 2/2 suites passed`) makes the top-level stdout authoritative and treats a replay on stderr as diagnostics.
A runner may also print one summary line, `RESULT_JSON {"total": N, "failures": N, "errors": N, "skipped": N}`;
the report then takes its totals from it when it is at least as informative as the parsed case list. Tagged
control lines (`[tag] text`) that dominate stderr on a passing run are reported as a control channel, not as noise.
Nothing else is assumed about a runner: without any of these the report relies on exit code, logs and the audit.

## report.json

See `emit-report.py` envelope: `schema_version`, `result`, repo/cmd/profile/mode, `suite`, `repo_fs`, `side_effects.{fail,note,summary}`, `next_steps`, `annotations`, `result_line`, `verdict_narrative`.

## chat-card.md

Paste **verbatim** into chat. Sections (in order):

1. **Final result** — RESULT token, command, scope, counts, paths  
2. **What ran & was verified** — real case counts (rollups filtered), group table with the claim each group's name supports, case inventory by group (name + humanized claim)  
3. **Conclusion (supervisor)** — a short verdict on whether the expected path held  
4. **What was attempted** — the command, case counts and header cues from stdout  
5. **Unintended consequences** — blocking, suspicious and informational signals from stdout, stderr, the filesystem audit and control policy  
6. **Worked well (hygiene)** — exit/channels/FS audit (not a substitute for case inventory)  
7. **Struggles** — fails + non-blocking notes  
8. **Control channel** — redacted policy findings / stderr sample  
9. **Dive in** — report.html / results.md / raw logs  

**No BASELINE paths.** Module summary lines (`PASS 15 foo tests`) are rollups, not cases.

## results.md

Deep dive sections (in order):

1. Final result + command/scope  
2. Conclusion (supervisor), What was attempted, Unintended consequences (detail)  
3. **What ran & was verified** — groups + full case inventory (same content as chat-card, non-compact)  
4. Worked well (hygiene) / Struggles  
5. Dive-in commands  
6. Summary (machine fields)  
7. Blocking findings / Notes / Baseline context  
8. **Control channels (stdout / stderr)** — bytes, lines, status, evaluation, previews  
9. **Test cases (flat table)** — all parsed lines incl. rollups (kind, claim, observation)  
10. Suite evidence excerpts + paths to raw logs  
11. Operator next steps  

`report.json` → `suite.case_inventory` is the machine form of the inventory.

## Driver

`run-harness.sh` runs both modes: `--mode once` (the default: audit-only, no worktree) and `--mode fix-loop` (a disposable
worktree with restore-on-fail rounds; product and test fixes stay with the agent, who edits the worktree and re-invokes).
Discovery: `--cmd`, then `.test-harness.yml`, then tiers 2–5 (see `discovery-matrix.md`).
