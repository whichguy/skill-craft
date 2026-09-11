---
name: shiploop
description: Markdown-authoritative SDLC session harness with action-bound evidence.
---

# ShipLoop

Load and follow the canonical ShipLoop skill at skills/shiploop/SKILL.md.
ShipLoop 0.9 prints one durable action at a time. Its Markdown records—not chat
memory and not a JSON sidecar—are authoritative.

- Start with shiploop init --repo <repo> [--run-dir <fresh-run>] --prompt <ask>.
- Reprint the current action with shiploop next; after a cold loss inspect
  shiploop context --section prompt first, then the active step or iteration.
- Run only the command and result schema printed for that action. Every
  completion is action-bound: shiploop complete --action <id> --result <md>.
- Each implementation and Improve iteration needs explicit lint and required
  tests through shiploop verify. Improve also reads Git history and writes one
  verbose learning-oriented primary commit.
- Two consecutive trivial-only Improve iterations still require final verify
  and broader-plan review. No maximum-cycle shortcut is success.
- Use pause/resume for recoverable blockers, repair for a newly discovered
  defect, halt for a terminal unfinished handoff, and migrate only for a legacy
  JSON run.

Do not use legacy bare complete, update, complete-step, start-step,
clear-step, or inject-step flows. Do not automatically change ShipLoop from
the generic proposal journal.
