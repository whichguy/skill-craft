# What the two readers were asked (round 1)

Two fresh Sonnet sessions, each started with only the text below. The first read `a2`, `a3`, `a4`, `a5`, `a6`, `b1`
and `b3` (its answers: `reader-answer.md`); the second read `a7`, `a8` and `a9` after those three deliveries ended
(`reader-answer-2.md`), and was told to open no other folder and no other file. Neither was told how any check came
out, which delivery was which driver's, or what the other reader said. `<export>` stands for the folder that held a
copy of `export/` here; the count of folders and their names were filled in for each reader.

---

You are a strict, literal reader. Read only the files named below; do not look at anything else on this machine (no
other folders, no git, no web), and do not guess beyond the texts. You change nothing except writing your one answer
file.

Folder: `<export>`. It holds the sub-folders named. Each has four small text files:

- `row.txt`: one choice that a software specification recorded for a help-desk ticket service. After "Decided:" is
  what the specification chose; after "Otherwise:" is an alternative it did not choose. The choice is about how
  tickets that already exist in the production data file get their "due time" when the new release is rolled out.
- `answer.txt`: what the person who requested the software then said they want.
- `before.md`: that requirement's text before the answer was received (it may be nearly empty in one folder; if so,
  say "not available").
- `after.md`: the same requirement's text after a later stage rewrote it.

For each of the folders answer these questions, strictly from the texts, each with a short exact quote that supports
it:

Q1 (from `row.txt`, the "Decided:" part only). As decided there: (a) must an operator run a separate command, script
or migration to prepare the data file before due times can be switched on? yes or no. (b) Does the service refuse to
start, or fail to start, when tickets are missing due times? yes, no, or not said.

Q2 (from `after.md` only). (a) Does the requirement still make an operator run a separate command, script or
migration to prepare the data file? yes or no. (b) Does it still say the service refuses or fails to start when due
times are missing? yes, no, or not said.

Q3 (compare `after.md` with `answer.txt`). Does `after.md` state what the requester asked for: that a start with
DUE_TIMES on gives every ticket without a due time one (from its creation time and priority), saves the file, then
serves, and never refuses to start because due times are missing? Answer "fully", "partly" (say exactly which part
is missing or contradicted) or "no".

Q4 (compare `before.md` with `after.md`). In one sentence: what changed in substance, if anything? If only a remark
such as "the requester decided this" was added and the behaviour described is the same, say "wording only".

Write your answers to `<answer file>` as one section per folder (a heading with the folder name, then Q1a, Q1b, Q2a,
Q2b, Q3, Q4 each on its own line with its quote), and end the file with a table of one row per folder: folder | Q1a
| Q1b | Q2a | Q2b | Q3 | Q4 in three words.

Then reply to me with just that final table and one line on anything that made a judgment hard.
