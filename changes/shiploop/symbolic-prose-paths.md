---
bump: minor
---
Prose paths in a packet print as the References block's symbols. The block gains a fourth symbol, `GUIDES` (this skill's
references directory), defined once with its absolute value, and its heading reads "References (symbols expand to these
absolute paths; commands stay literal):". A line that names a file as prose prints `RUN/notes/x.md`, `GUIDES/navigator.md#anchor`,
`HOME/spec.md` or `WORKTREE/SHIPLOOP.md` where it printed the absolute path: the pass-log line, the work-queue and planning-source
lines, the previous-result lines of a replan or revise, the Run rules' State and knowledge-index line, the guide and policy lines,
the test rerun, floors and inherited-learnings lines, the "Excerpt only" pointer and the evidence bullets. The Improve handoff
file does the same (it carries the same block).
- Always literal, because hooks and the loop runtime read them: the callback and every command line, the Keepalive marker, the
  "Full packet:" line, the Progress view link, the `evidence_refs` example, the `/until-loop` argument block, the
  `/improve ShipLoop Improve: ...` line and the index pointer. The list of lines that become symbols is closed (a new line that
  prints a path stays literal until it is named), and a packet without the block (done, halted, the Improve packet) is unchanged.
- On the 24 whole renders of the node-fix-bug case the change is -4,507 characters (-2.9%); on the live Salesforce chess packet
  files it is -3.4% (the live run's long plugin-cache and run paths repeat more).
