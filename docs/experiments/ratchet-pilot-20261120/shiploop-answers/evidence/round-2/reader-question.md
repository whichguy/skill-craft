# What the reader was asked (round 2, answers sent during the build)

One fresh Sonnet session, started with only the text below (`reader-answer.md` holds its answers). It was not told
how any check came out or which delivery was which driver's. `<export>` stands for the folder that held a copy of
`export/` here.

---

You are a strict, literal reader. Read only the files named below; do not look at anything else on this machine (no
other folders, no git, no web), and do not guess beyond the texts. You change nothing except writing your one answer
file.

Folder: `<export>`. It holds seven sub-folders: `e1`, `e2`, `e3`, `e4`, `e5`, `e6`, `f1`. Each has four small text
files:

- `row.txt`: one choice that a software specification recorded for a help-desk ticket service. After "Decided:" is
  what the specification chose; after "Otherwise:" is an alternative it did not choose. The choice is about how
  tickets that already exist in the production data file get their "due time" when the new release is rolled out.
- `answer.txt`: what the person who requested the software said they want. They said it later, while the software
  was already being built.
- `before.md`: that requirement's text at the moment the requester said it (its first line says what it is; if it
  is nearly empty in a folder, say "not available").
- `after.md`: the same requirement's text when the work ended.

For each of the seven folders answer these questions, strictly from the texts, each with a short exact quote that
supports it:

Q1 (from `row.txt`, the "Decided:" part only). As decided there: (a) must an operator run a separate command, script
or migration to prepare the data file before due times can be switched on? yes or no. (b) Does the service refuse to
start, or fail to start, when tickets are missing due times? yes, no, or not said.

Q2 (from `after.md` only). (a) Does the requirement make an operator run a separate command, script or migration to
prepare the data file? yes or no. (b) Does it say the service refuses or fails to start when due times are missing?
yes, no, or not said.

Q3 (compare `after.md` with `answer.txt`). Does `after.md` state what the requester asked for: that a start with
DUE_TIMES on gives every ticket without a due time one (from its creation time and priority), saves the file, then
serves, and never refuses to start because due times are missing? Answer "fully", "partly" (say exactly which part
is missing or contradicted) or "no".

Q4 (compare `before.md` with `after.md`, ignoring the first line of `before.md` that says what the file is). In one
sentence: what changed in substance, if anything? Answer "nothing" if the two texts are the same. If lines were only
added that name tests, files or work items and the behaviour described is the same, say "evidence lines only". If
the behaviour described changed, say what changed.

Write your answers to `<answer file>` as one section per folder (a heading with the folder name, then Q1a, Q1b, Q2a,
Q2b, Q3, Q4 each on its own line with its quote), and end the file with a seven-row table: folder | Q1a | Q1b | Q2a
| Q2b | Q3 | Q4 in three words.

Then reply to me with just that final table and one line on anything that made a judgment hard.
