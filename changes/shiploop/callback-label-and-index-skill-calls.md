---
bump: minor
---
Two fixes that the merge of the packet and loop changes needed.
- The docs no longer say a packet's callback is "the line after the header": the owner rule and the pointer to the run's
  `context-index.md` sit between them, and the Until Loop and pointer changes move more lines above it. The commands
  `shiploop-next` and `shiploop-complete`, the README and `references/navigator.md` name the callback by its label,
  `Callback for this stage` (an Improve child's packet labels it `Next command (` or `2. When the improve skill has
  completed, run:`).
- The run's `context-index.md` map lists `skill-calls.jsonl`, the record of the Skill-tool calls a Claude Code session made
  in the run (the Improve stage's gate reads it). Before, the map was missing a file every Claude run has.
