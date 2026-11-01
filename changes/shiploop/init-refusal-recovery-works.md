---
bump: patch
---
The `init` refusal in an empty folder that is not a Git repository now points at a recovery that works. The `workspace start` command it prints repeats the options the refused `init` carried (`--improve-skill`, `--delivery-contract`, `--delegation`, `--lint`, `--backchain-passes`, `--planning-review`), so following it does not drop what was asked for. A folder that holds any entry, even an empty `.shiploop` made beforehand, is no longer refused: `workspace start` bootstraps only a folder with no entry at all, so for such a folder the printed command failed. Git's "not a git repository" diagnostic is now read under a neutral locale, so a translated message cannot let the wrong start through.
