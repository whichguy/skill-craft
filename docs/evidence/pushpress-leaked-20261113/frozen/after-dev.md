# After the dev stage (written before the held-out prompts were read)

Recorded 2026-11-13. The files under `outputs/dev/` are the runs; this note is hashed with the held-out prompts in `frozen-manifest.txt`.

## Dev result: C5a

Payload `payload-C5a` (SKILL.md sha256 `b00da1d6d083...`; C4's payload hashes to `19717fca6f7b...`, the value Round 12 recorded; every payload has 419 files). The init list of every run holds 48 skills with the
hash `67260e599d83c13c`, the same list as Round 12's runs, and the model is `claude-sonnet-5-5`. No run had an error.

| prompt | kind | fired |
|---|---|---|
| DL1 (HP11, the Round 12 miss) | leak, code | 2 of 2 |
| DL2 | leak, code | 2 of 2 |
| DL3 | leak, code | 2 of 2 |
| DL4 | leak, code | 2 of 2 |
| DLN1, DLN2, DLN3 | other-product leaks | 0 of 1 each |
| DC1 (Round 9's E1, the control) | explicit | 1 of 1 |

Lines of design.md: (i) the control fired; (ii) 8 of 8 leak runs fired (line: at least 6 of 8) and DL1 fired in 2 of 2 (line: at least 1 of 2); (iii) 0 of 3 negatives fired (line: none).
**C5a passes dev and is the candidate** (7 words changed against C4; C5b, 29 words, was not run, so it has no result). Cost of the dev stage: 0.415 USD (12 runs). C4 was not run on the dev prompts, so the dev stage
shows that C5a fires on them, not what C4 does on DL2 to DL4 (C4's 0 of 2 on DL1 = HP11 is Round 12's). The held-out prompts below were read after this choice.

## Held-out prompts: delivery

The fresh author agent (`sonnet`, no candidate and no result in its brief) received `prompts/author-brief.md` as written. The only addition outside the brief was a delivery note: its one tool call was a single Write
of the JSON object to a file in the scratch directory, so that the texts reach `prompts/leak-agent-output.json` byte for byte (copied with `cp`, compared with `cmp`) and are not retyped by me.
