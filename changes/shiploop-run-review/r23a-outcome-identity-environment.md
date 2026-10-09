---
bump: patch
---
The Run Review export and page now show four more records the E2E harness writes. How the harness classed the ending (PASS, FAILED,
BLOCKED or STOPPED, with its grounds) is a line under the run header, as a record and never coloured as a verdict. The build under test
(plugin hash, prompt hash, host build) is another line, with the harness's reason for any it could not measure. An Environment card
shows the tools, the browser and the other runs that shared the machine while this one ran, and a chip in the header says so, since
minutes measured beside another run are not clean. A run that did not pass shows, as information only, how many of its checks pass in
the worktree it never returned and what each failing check printed. All four are absent for a run exported before the harness wrote them.
