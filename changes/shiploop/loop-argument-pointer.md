---
bump: minor
---
- **Loop argument in the loop's packets (decision 20):** an inner stage's packet no longer prints the Until Loop
  argument (Work, the numbered exit conditions, Repeat). It prints the start command and one
  `Contract: <abs> · Receipt: <abs>` line, and its "Done when" points at the exit conditions the loop states in every
  packet it prints. The runtime prints the contract's Work, Exit and Repeat on start, next and each active done, and a
  test pins that. The test stage keeps the argument, because its command floors are numbered by it. Inner heads lose
  750-1,300 characters, so their lookups fit.
