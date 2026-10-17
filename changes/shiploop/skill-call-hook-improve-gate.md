---
bump: minor
---
On Claude Code, ShipLoop now enforces that the improve skill is invoked at every Improve stage, instead of asking for it in
the packet. In the 2.1.0 live run 3 of 4 Improve reviews were written by a script that reported to the runtime directly, and in
the 2.4.0 live slice the skill was invoked for 1 of 4 stages; changing the packet's wording did not move either.
- A new hook, `scripts/shiploop-skill-call` (`PostToolUse` on the Skill tool, declared as `after-skill` in
  `host-hooks.json` for Claude only; `shiploop-hook install --host claude` adds the same entry), appends each Skill call
  of a session the keepalive hooks bound to a run to the run's `skill-calls.jsonl`: time, skill (`skill-craft:improve`
  and `improve` are one), argument, tool-use id, session and, for a subagent, its id. It never blocks the call and writes
  only inside the bound run directory.
- `complete --action=<improve id>` refuses until the record holds a call to the improve skill made after that Improve
  stage started whose argument carries the stage's handoff path or action id. The refusal's first line names the Skill
  call to make and the command to run after it.
- Where no record can exist (Grok, Codex, Cursor, OpenCode, no hooks, hooks turned off with `SHIPLOOP_KEEPALIVE=off`,
  hooks installed before this one, or `delegation: ask-agent`, where a fresh worker runs the review) nothing is enforced,
  and `complete` says so once per run when it accepts the import.
- The hook generator accepts the new `after-skill` event (Claude only) and refuses it for any other host.
