---
bump: patch
---
A run whose baseline is a HEAD pointer alone (saved before `run-starting-knowledge.json` existed) no longer gets a HEAD-relative spec diff: its packets say the diff is not computed, as for any run without a baseline. Only the starting-bytes snapshot supplies the diff.
