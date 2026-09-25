# Status display

ShipLoop renders one fixed **status block** from saved run state. The model
does not write it, and on Claude Code a hook can show it to the user directly.

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

## Where it appears

1. **Every packet**, after the progress snapshot. The owner shows the block to
   the user unchanged, unless a host status hook already showed it.
2. **`<run>/status.md`**, rewritten by every saved transition in the same
   journaled transaction as `state.md`, and **`shiploop status --run-dir=…`**,
   which prints the block read-only. `status` takes the run lock like `next`,
   so it first finishes any interrupted save. Only a direct read of
   `status.md` during an interrupted save can show the previous step.
3. **Host status hook**: `scripts/shiploop-status-hook` copies the block from a
   ShipLoop command's own stdout into the hook's `systemMessage`, which Claude
   Code and Codex show to the user. A marketplace install sets it up; see
   [host hooks](#host-hooks).

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

| Host | Package file | After installing | Shows the block to you |
|---|---|---|---|
| Claude Code | `hooks/hooks.json` | active once the plugin is enabled | yes |
| Codex | `hooks/codex.json` (manifest `hooks`) | review and trust it once in `/hooks` | yes, as a UI warning |
| Grok | `hooks/hooks.json` (Claude format) | install with `--trust` | no: Grok never shows a successful hook's output |
| Cursor | `hooks/cursor.json` (manifest `hooks`) | active in a trusted workspace | no: `afterShellExecution` has no output field |

On Grok and Cursor the hook recognizes the call and stays silent, so the
in-packet block and `status.md` remain the display there. OpenCode has no
marketplace; it uses the in-packet block and `status.md`.

### Skill-directory installs

`install.sh` never writes host settings. For a symlinked Claude Code install,
add the hook yourself to `~/.claude/settings.json` (adjust the path if the skill
is installed elsewhere). Do not also enable the plugin, or each block shows twice:

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
