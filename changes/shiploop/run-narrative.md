---
bump: minor
---
Milestone packets now carry a script-rendered run narrative: the goal, a progress bar per phase, what has been achieved (each step's new one-line `headline`), what is happening now, what comes next, and the observed pace with a labelled forecast from `<run>/timeline.json`. Where the host shows hook messages (the Claude Code terminal CLI) the status hook shows it as plain text; everywhere else, including the Claude desktop app, the model pastes the Markdown narrative as written, once per milestone. Results accept an optional `headline` of at most 100 characters.
