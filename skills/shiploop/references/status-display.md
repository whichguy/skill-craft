# Status display

ShipLoop renders one fixed **status block** from saved run state, and at
milestones a **run narrative** that tells the story of the run. The model writes
neither; in a terminal CLI a hook can show them to the user directly.

```text
=== ShipLoop status ===
Where:     Work items > W2 "Add --version flag" (2 of 4) > Tests first > test-author
Run:       Preparation ✓ | Work items 1/4 ▶ | Release ·
Item:      Plan ✓ | Tests first ▶ | Build · | Check · | Integrate ·
Done:      W2 baseline: existing suite 142/142 passing; no --version coverage yet.
Next:      test-author: write the tests the item's test spec calls for
Item plan: Add --version to cli.py argparse; tests in test_cli.py.
Completed: 1 item; W1 "Config loader refactor": loader split, 12 tests added
=== end ShipLoop status ===
```

`✓` is accepted done, `▶` is current, `·` is pending.

| Line | Content |
|---|---|
| Where | Phase, then item (N of M) and its stage group, then the stage. `(Improve review)` while an Improve child owns the step. |
| Run | Preparation, work items (completed/total) and Release. |
| Item / Stages | During a work item, its 18 stages in five groups: Plan, Tests first, Build, Check, Integrate. In preparation and release, each stage. |
| Done | The latest accepted result's first sentence, marked when Improve reviewed it or the outcome was repeat, blocked, replan or reconcile. While a child is parked, the result it is reviewing. |
| Next / Stopped | The current stage and its one-line purpose, or the Improve review in progress. A paused, blocked or halted run shows its reason; the packet prints the resume command. |
| Item plan | The first sentence of the item's accepted `step-plan` summary, or of the item's `context` before that. Omitted when neither exists. |
| Completed | Completed items, the three most recent with the first sentence of their `carry-forward` summary. |

## Live HTML progress view

Open `<run>/progress.html` as an ordinary HTML file. After a successful `init`,
`next`, `resume`, callback, `pause`, or `halt`, the CLI ensures one read-only
background observer for that run. It samples about every two seconds and
publishes a complete page when recorded inputs change, plus a periodic heartbeat.
The open page reloads about every five seconds. No web server, browser file
permission, external asset, or model call is required.

The page shows the preparation/work/release outline, accepted items, the current
stage and blocker, recent recorded activity, and expandable spec, architecture,
plan and test-strategy previews. Before plan acceptance it says the work plan is
pending. Current repository documents are **saved drafts** with a path, content
hash and observation time. Accepted planning-result records appear separately;
an updated document or worker report does not itself accept work. The observer
cannot display unrecorded work or intermediate edits it did not sample. Each
file is checked for a stable read; several document previews do not represent
an atomic repository-wide snapshot.

Generated implementation steps have their own dependency diagram. Inline step
plans supply their recorded `deps` and accepted per-step progress. Each bound
execution graph supplies its nodes and prerequisite edges; saved dispatcher
state supplies their recorded status. The diagram is rebuilt when these inputs
change, even while the parent action stays the same. Graphs are labeled by work
item/action so identically named steps in separate plans remain distinct. A text
dependency list accompanies each diagram. Older step plans without explicit
`deps` can show their accepted tasks but label their dependencies unknown.
The preparation/work/release outline is separate from these generated steps.

Previews are embedded in the file so a saved copy remains useful offline. Source
links can become unavailable when a worktree is moved or removed. Selected
Markdown/text files are bounded, credential-screened and escaped; symlink,
hardlink, special-file and out-of-root references are refused. Missing or withheld
files have explicit placeholders. The existing privacy screen recognizes only
specific credential patterns, not every possible secret.

The page distinguishes last recorded activity from last successful observation.
Its stale indicator means observation may have stopped; a fresh observation is
not proof the agent is running. **Pause updates** affects only the browser, never
ShipLoop. Browser storage restrictions may prevent restoring reading position;
manual refresh and the full saved content remain available. Background-tab
throttling and busy run locks can delay refresh, so timing is not a real-time
guarantee.

Use the same selected package's CLI and exact run directory:

```sh
python3 "$CLI" view --run-dir "$RUN_DIR"            # write one offline snapshot
python3 "$CLI" view --run-dir "$RUN_DIR" --start    # start or reuse background observer
python3 "$CLI" view --run-dir "$RUN_DIR" --watch    # watch in this foreground process
python3 "$CLI" view --run-dir "$RUN_DIR" --status   # process status, read-only
python3 "$CLI" view --run-dir "$RUN_DIR" --stop     # stop; disable automatic restarts
```

`--start` or an explicit `--watch` reenables observation after `--stop`. A one-shot
snapshot refuses to compete with an existing observer. `--interval` selects the
sampling interval (default two seconds); `--idle-timeout` defaults to 1800 seconds
without changed inputs. An idle observer exits and a later packet can restart
it. Set `SHIPLOOP_PROGRESS=off` in a command's environment to suppress automatic
startup, for example in a hermetic harness. It does not stop an existing observer
or disable explicit `view` commands.

Only the observer writes `progress.html`. It holds a separate singleton lock and
briefly takes the existing run lock for reading. It skips pending transactions
without recovering them, never writes authoritative state, and never accepts
results or launches workflow/model execution. Its heartbeat/process JSON is
display metadata, not another workflow record. A failed read or render retains
the last good page; a viewer failure cannot fail a ShipLoop transition.

On a terminal state the observer re-samples to reconcile selected documents and
workspace-return information, then freezes the page and exits. Unverified
delivery remains visibly unverified; a halted run remains unfinished. The
existing `report.html` stays the terminal report. An archived HTML snapshot has
no ongoing observation unless an observer still owns its original path.

## Where it appears

1. **Every packet**, after the progress snapshot. The block orients the
   owner, which does not reprint it: it tells the user at most one line per
   step and shows the whole block unchanged only when the user asks for the
   full status.
2. **`<run>/status.md`**, rewritten by every saved transition in the same
   journaled transaction as `state.md`, and **`shiploop status --run-dir=…`**,
   which prints the block read-only. `status` takes the run lock like `next`,
   so it first finishes any interrupted save. Only a direct read of
   `status.md` during an interrupted save can show the previous step.
3. **Host status hook**: `scripts/shiploop-status-hook` reads the block from a
   ShipLoop command's own stdout and puts a two-line summary in the hook's
   `systemMessage`. Only the Claude Code terminal CLI shows it, in dim text
   after `PostToolUse:Bash says:`; the Claude desktop app, the VS Code panel
   and the Codex TUI (0.157.1) drop a PostToolUse `systemMessage`, and the
   model never sees it:

   ```text
   ShipLoop ▶ Work items > W2 "Add --version flag" (2 of 4) > Tests first > test-author
   Done: W2 baseline: existing suite 142/142 passing; no --version coverage yet. | Next: test-author: write the tests the item's test spec calls for
   ```

   The second line takes `Waiting on you` or `Stopped` in place of `Next` when
   the run waits or stops. The full block stays in `status.md` and `status`. A marketplace install sets it up; see
   [host hooks](#host-hooks). At a milestone the hook shows the narrative
   instead, with terminal bold in place of the Markdown.

## Run narrative

At milestones a packet carries a script-rendered narrative between
`=== ShipLoop narrative ===` and `=== end ShipLoop narrative ===`: the goal, a
progress bar per phase, what has been achieved, what is happening now, what
comes next and the run's observed pace. Milestones are the start of a run,
every accepted preparation and release stage, the end of each work-item stage
group (Plan, Tests first, Build, Check, Integrate), and every paused, blocked,
awaiting, halted or done packet. Other packets carry no narrative.

```markdown
#### 🚢 ShipLoop — Add a --version flag to the CLI.
`█████░░░░░░░` **Preparation 3/7** · Work items (set by plan) · Release (9 steps)

**✅ Achieved**
- **intake** — Scope: a --version flag that prints the package version and exits 0
- **discovery** — argparse lives in cli.py; 142 tests pass on a clean checkout
- **research** — importlib.metadata reads the installed version; no new dependency

**▶️ Now** — **spec**: define required behavior and acceptance criteria

**🔭 Ahead**
- **test-strategy** — map requirements to the checks that will prove them
- **plan** — build the dependency plan and the work-item queue
- **then prepare, the work items, release**

**⏱ Pace** — 3 steps in 11 min · about 15 min left in preparation at this run's pace (an estimate, not a promise)
```

- **Achieved** lists each accepted step's `headline`: one line of at most 100
  characters that the step writes for the user in its result. A result without
  one falls back to its summary's first sentence. During work items it lists
  the completed items with their `carry-forward` headline and the current
  item's latest step; during release, the accepted release stages.
- **Ahead** names the next stages with their purpose, then the remaining
  groups, work items and release.
- **Pace** reads `<run>/timeline.json`, a derived display file written in the
  same transaction as `status.md`: the run's start and when each step was
  accepted. The forecast appears after two accepted steps and is the observed
  average time per step times the steps left in the phase. The model never
  estimates time itself.

The section's first line tells the owner who shows it:

| Where the owner runs | First line | Who shows it |
|---|---|---|
| Claude Code terminal CLI (`CLAUDE_CODE_ENTRYPOINT=cli`) | the host's hook already shows it; do not repeat it | the status hook, as styled terminal text |
| every other host and surface, including the Claude desktop app, the VS Code panel, Codex, Grok, Cursor and OpenCode | show it exactly as written, as Markdown in your own message | the owner, once per milestone |

Pasting the narrative costs the owner its output tokens at each milestone,
roughly 200, and nothing between milestones.

## Host text is untrusted

Titles, summaries and reasons come from host results. The block cleans each
value: it drops control characters, collapses whitespace and turns any `===`
run into `==` so text cannot close the block early. It also caps each value:
IDs at 32 characters, titles at 60 (40 in Completed), and summaries and reasons
at 140 (60 in Completed). The block holds no commands or absolute paths, is at
most 11 lines, and stays under about 1,500 characters for any queue.

## Host hooks

`host-hooks.json` declares the hook, and the marketplace package carries one
generated hook file per host, so installing the ShipLoop plugin sets it up:

| Host | Package file | After installing | Shows the summary to you |
|---|---|---|---|
| Claude Code | `hooks/hooks.json` | active once the plugin is enabled | terminal CLI only; the desktop app and the VS Code panel drop hook messages |
| Codex | `hooks/codex.json` (manifest `hooks`) | review and trust it once in `/hooks` | no: the 0.157.1 TUI drops a PostToolUse `systemMessage` (measured 2026-09-27) |
| Grok | `hooks/hooks.json` (Claude format) | install with `--trust` | no: Grok never shows a successful hook's output |

On Grok, a same-named plugin from Claude's marketplace clone
(`~/.claude/plugins/marketplaces/<market>/plugins/shiploop`) outranks Grok's own
installs, and Grok never trusted that path, so its hooks stay inactive. Linking
the trusted install at `~/.grok/plugins/shiploop` makes it win; check with
`grok inspect --json`. Grok 1.0.41 also runs no plugin hooks in headless
`grok -p` sessions, only settings-file hooks, so verify there in an interactive
session. Grok sends the command's output as a list of byte values.
| Cursor | `hooks/cursor.json` (manifest `hooks`) | active in a trusted workspace | no: `afterShellExecution` has no output field |

On Grok and Cursor the hook recognizes the call and stays silent, so the
owner's one-line updates, `shiploop status` and `status.md` are the display
there. OpenCode has no marketplace and uses the same three.

### Skill-directory installs

`install.sh` never writes host settings. For a symlinked Claude Code install,
add the hook yourself to `~/.claude/settings.json` (adjust the path if the skill
is installed elsewhere). Do not also enable the plugin, or each summary shows twice:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "\"$HOME/.claude/skills/shiploop/scripts/shiploop-status-hook\""
          }
        ]
      }
    ]
  }
}
```

The hook stays silent, and always exits 0, unless every check passes:

- The Bash command directly invokes a ShipLoop entry point
  (`…/scripts/shiploop`, `…/scripts/shiploop-complete` or
  `…/scripts/shiploop-next`), optionally after `python3` or environment
  assignments. It uses a packet verb, `workspace start` or `status`.
- The command has no pipe, redirect, chain or background operator.
- Stdout begins with the packet header (after a known context prefix or
  wrapper line), or with the block itself for `status`.
- Stdout holds exactly one block, ending within its first 8,000 characters.
  Claude Code keeps the head of oversized Bash output, and the block ends by
  about character 4,000.

So `cat status.md`, a `grep` over fixtures or an `echo` of the markers never
shows anything. A backgrounded call has no stdout at hook time and stays
silent; ShipLoop callbacks are not backgrounded.

The script reads each host's payload shape: Claude Code and Codex
(`tool_name`, `tool_input.command`, `tool_response`), Grok (`toolName`,
`toolInput.command`, `toolResult.output_for_prompt`) and Cursor (`command`,
`output`). An unknown shape stays silent.
