---
bump: patch
---
The text-search classifier behind the focused-search refusal and the executed-criterion check now reads quoting as the
shell does. A search whose quoted pattern holds `;` or `|` is one command, so the refusal now catches it; it used to
read the text after the `;` as a second program. A command whose quotes do not close is no longer treated as a search.
