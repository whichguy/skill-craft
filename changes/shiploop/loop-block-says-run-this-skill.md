---
bump: minor
---
The Until Loop block of every inner-stage packet now says what to run, with what, and what the result is, so a model that
lost all context acts on it without opening the Until Loop card. Before, it said `INVOKE /until-loop NOW with the argument
below`, indented the argument's lines among prose, and sent every host but Claude to the 24 KB `ADAPTER.md` for the
command (the last live Grok run read that card 6 times and the Improve skill 7 times to learn it).
- `RUN the until-loop skill now, once, with exactly the lines between the two markers`: the argument sits between
  `----- BEGIN until-loop ARGUMENT -----` and `----- END until-loop ARGUMENT -----` and holds the Work, Exit when, Repeat,
  Contract and Receipt lines and nothing else (no indent, no prose between them).
- Claude Code: the Skill tool, skill `until-loop`, with that argument. Any other host: the literal start command, on its own
  line, `python3 <runtime script> start --receipt <receipt> < <contract>` with the real absolute paths (the command a failed
  `complete` already prints), then each packet it prints until the receipt says complete or stopped.
- The result: when the Receipt says status complete (stopped: report it), keep it in `evidence_refs` and run the Callback
  command; if that refuses because of the loop, run the start command again (an active receipt: its `next_argv` instead).
- A packet read after the loop started leads with the resume line (do not invoke it again) instead of the RUN line: the
  runtime does not refuse a second start for one receipt, so a literal start command must not sit under a RUN line then.
- The closing rule keeps its obligations and adds that the receipt is not to be edited; the old "start the loop again"
  sentence became the result line. The heading is `Until Loop (no iteration limit):`.
- To keep the step-plan head under the host's 20,000-character cut, the head's pointer sentence is shorter (same
  obligations) and `packets.py --offline` writes the loop contract before it renders, as `emit` does, so an offline
  packet no longer ends with "The loop contract is missing".
