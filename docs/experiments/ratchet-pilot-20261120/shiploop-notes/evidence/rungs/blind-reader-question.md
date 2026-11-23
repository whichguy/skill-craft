# The blind reader's question (first rung; a Sonnet reader, one for g1 to g3 and one for k1)

The reader was given only the export folder (`export/<name>/row.txt`, `answer.txt`, `before.md`, `after.md`, written
by `read_notes.py --export`), told that the four files are about one software project's requirement for how existing
support tickets get their "due time" (`row.txt`: one decision the specification had recorded; `answer.txt`: a message
the person who asked for the software sent later; `before.md`: the requirement before that message; `after.md`: the
requirement at the end), and told to answer from the files only. Nothing named the mode, the checks or the outcome.

Questions, each to be answered yes or no with one quoted phrase:

1. Does `answer.txt` ask for something different from what `before.md` says? Say in one sentence what the
   difference is.
2. Does `after.md` state what `answer.txt` asks for (the same behaviour, even if in other words)?
3. Does `after.md` still state anything that contradicts `answer.txt`? If yes, quote it.
4. Does `after.md` say anywhere that it was changed because of a message, clarification or note from the person who
   asked? Quote it if so.

Then one line per delivery: "the final requirement DOES / DOES NOT / PARTLY state what the message asks".
