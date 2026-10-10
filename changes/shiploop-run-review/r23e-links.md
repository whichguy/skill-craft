---
bump: patch
---
The Run Review page now turns references in Claude's review text into links: an existing finding or option id jumps to its card,
a repo path, a commit and a spec clause S-n open on GitHub, and an https URL opens itself. The address is
`config/page.repoUrl` (in the defaults; `--check` refuses a non-https one; with none the repo references stay text). Run content
such as stage summaries and packets is never linked: those paths are files on the machine that ran the case.
