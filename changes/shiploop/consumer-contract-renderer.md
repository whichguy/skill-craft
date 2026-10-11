---
bump: minor
---
Packets print what the consumer contract hands each stage, by value and uncut.
- **Knowledge files read.** Each file `knowledge_home.READS` gives the stage is quoted whole after the status block,
  each line prefixed `  | `, or marked "not written yet". The References block names them in one line. This replaces
  the per-stage consult list of headings, because heading matching missed most saved homes (owner decision D1).
- **Hand-off values.** "Handed off by earlier stages" quotes each `CONSUMES` value from `handoff_sources`:
  - the follows IDs with their spec or architecture entries, marked when retired, or "no entry in HOME/<file>";
  - the criteria, focused commands and system commands;
  - the test cases with oracle, red and green;
  - not_covered;
  - the open items with check, reason, consumer, owner and producer;
  - the lessons;
  - the spec and architecture diff since the run baseline.

  A missing value prints "not recorded by <stage>".
- **Result-shape block.** It prints the shape of each hand-off field the gate requires and the template leaves out:
  - follows at step-plan;
  - test_cases at test-spec;
  - lessons at release-verify;
  - not_covered, optional, at implement;
  - assumptions at each open-item stage.

  A done result that follows the packet is no longer refused once per missing key.
- **Duty wording.** test-spec records its cases in `test_cases` and a due-later case as an open item; verify and
  system-test-author record later checks and unrunnable cases as open items in `assumptions`.
- **Working-tree return.** The handoff packet prints the lessons commit message for the user to commit, since a
  working-tree return makes no commit.
