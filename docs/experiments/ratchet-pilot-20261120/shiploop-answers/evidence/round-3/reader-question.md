# What the reader was asked (round 3, test A: plain notes sent during the build)

One fresh Sonnet session, started with only the text below (`reader-answer.md` holds its answers). It was not told
how any check came out or which delivery was which driver's. `<export>` stands for the folder that held a copy of
`export/` here.

---

You are a strict, literal reader. Read only the files named below; do not look at anything else on this machine (no
other folders, no git, no web), and do not guess beyond the texts. You change nothing except writing your one answer
file.

Folder: `<export>`. It holds three sub-folders: `m1`, `n4`, `n5`. Each has four small text files:

- `row.txt`: one choice that a software specification recorded for a help-desk ticket service. After "Decided:" is
  what the specification chose; after "Otherwise:" is an alternative it did not choose. The choice is about how
  tickets that already exist in the production data file get their "due time" when the new release is rolled out.
- `answer.txt`: a note the person who requested the software sent later, while the software was already being
  built. It says what they want instead. It is not the same note in every folder.
- `before.md`: that requirement's text at about the moment the note was sent (its first line says what it is).
- `after.md`: the same requirement's text when the work ended.

For each of the three folders answer these questions, strictly from the texts, each with a short exact quote that
supports it:

Q1 (from `row.txt`, the "Decided:" part only). As decided there: (a) must an operator run a separate command, script
or migration to prepare the data file before due times can be switched on? yes or no. (b) Does the service refuse to
start, or fail to start, when tickets are missing due times? yes, no, or not said.

Q2 (from `answer.txt` only). What does the note ask for, in one sentence: that the service fills the due times in by
itself at a start and never refuses, or that an operator runs a separate command and the service refuses to start
until then?

Q3 (from `after.md` only; where it holds both a current text and text marked as superseded or history, judge the
current text). (a) Does the requirement make an operator run a separate command, script or migration to prepare the
data file? yes or no. (b) Does it say the service refuses or fails to start when due times are missing? yes, no, or
not said.

Q4 (compare `after.md` with `answer.txt`). Does the requirement at the end state what the note asks for? Answer
"fully", "partly" (say exactly which part is missing or contradicted) or "no" (say what it states instead).

Q5 (compare `before.md` with `after.md`, ignoring the first line of `before.md` that says what the file is). In one
sentence: what changed in substance, if anything? Answer "nothing" if the two texts are the same. If lines were only
added that name tests, files or work items and the behaviour described is the same, say "evidence lines only". If
the behaviour described changed, say what changed, and whether the text says why.

Write your answers to `<answer file>` as one section per folder (a heading with the folder name, then Q1a, Q1b, Q2,
Q3a, Q3b, Q4, Q5 each on its own line with its quote), and end the file with a three-row table: folder | Q1a | Q1b |
Q2 in three words | Q3a | Q3b | Q4 | Q5 in three words.

Then reply to me with just that final table and one line on anything that made a judgment hard.
