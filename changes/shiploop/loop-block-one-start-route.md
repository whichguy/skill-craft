---
bump: minor
---
The Until Loop block of every inner-stage packet has one start route on every host, and it leads with the command. This
replaces the Claude Code route that the earlier loop-block note describes (the Skill tool, skill `until-loop`): the recorded
Claude run called it, got `Unknown skill: until-loop`, searched `ADAPTER.md`, and wrote the stage's result before the loop
had run; no skill-craft install registers a skill of that name.
- The block now reads: heading `Until Loop (no iteration limit; the loop script counts the iterations):`; the RUN line (`RUN
  the Until Loop now, once, before any work, and do this stage's work only inside it`, with the foreground command rule and
  the active-receipt clause: if the receipt already exists and is active, run its `next_argv` instead, because a second start
  resets the loop); the literal start command, `python3 <runtime script> start --receipt <receipt> < <contract>`; the follow
  line (follow each packet it prints, run its `done_argv` as printed, until the receipt says complete or stopped; the argument
  is already in the Contract file, do not edit that file or the receipt); the argument between the two marker lines; the
  result line; and the exit-evidence sentence.
- The result line lists the five fields of the runtime's done report with their values (classification, exit_assessment,
  continuation_assessment, evidence, handoff), so the report is written once and not looked up in the runtime's output.
- A packet read after the loop started prints the resume line (`do not start it again (a second start resets it)`, then run
  the receipt's `next_argv`) in place of the RUN line and the start command, and its result line names `next_argv` alone: a
  literal start command under a read-again packet invited a second start (measured: it sent `action_number` 2 back to 1).
- The per-host line is gone (`shiploop_loops.HOST_LINE`). The three places outside the block that said `/until-loop` (the
  inner stage's done-when line, the test stage's where-and-floors line, the SKILL.md and README descriptions) say "the Until
  Loop argument"; SKILL.md "Stage Until Loops" no longer names a tool.
- The loop contract JSON, its hash and the Improve start contract are unchanged (checked for all eight stages).
- Each looped stage's printed head and whole text are 246 characters longer (245 for test); the journaled head table
  (`test/shiploop_e2e/head_table.json`) is raised by the same amounts.
