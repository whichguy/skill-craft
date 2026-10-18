---
bump: minor
---
Packets name the knowledge files and the request by their files instead of quoting them whole (packet review 2026-10-17,
owner decisions D1 and D2; units U1 and U2).
- A packet lists each knowledge file it reads (`HOME/spec.md`, `environment.md`, `architecture.md`) by path, size and table
  of contents: every heading, with the R-<n> or AD-<n> entries under it (a run of list entries as `R-1..R-6`). It quotes by
  value only the requirement and decision entries the stage follows. On the recorded Salesforce run the whole quotes were
  53% of all packet text and sat where no print reached; the model reopened the files every time.
- The spec and architecture diff since the run began names a file that is new since the baseline (its diff is the whole
  file) with its size and contents instead of printing it, at every stage that reads the diff (release-verify printed
  35 KB of it on a first run). A file that existed at the baseline keeps its changed sections, uncut.
- The original request is quoted whole only at intake, spec and plan (and in the Improve handoff of spec and plan). Every
  other packet prints one line naming `RUN/request.md`, which holds it verbatim with its sentence index; the Improve
  handoff adds the delivery contract's exclusions line beside it when the run has one (a producer packet already prints
  it in its delivery block).
- The Improve handoff names the reviewed stage's packet (`RUN/packets/<action>.md`) and result (`RUN/inbox/<action>.md`)
  and the knowledge files with their sizes instead of quoting the producer's knowledge files and hand-offs again; it keeps
  by value the criteria the stage was handed, and on a revisited step plan it names the previous accepted result and the
  revise result. A long-home handoff falls from 42-60 KB to about 20 KB.
