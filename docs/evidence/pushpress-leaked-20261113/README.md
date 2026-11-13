# P25: would "leaked" in the description's key sentence load the pushpress card more often? (journal Round 13)

Does adding "leaked" to the key sentence of the description of `skills/pushpress/SKILL.md` make the card load when a PushPress API key or webhook secret has already got out (pushed to a repository,
posted, sent), without loading it for other products' keys and without losing the announcements of Round 12 and Round 9's prompts? **Result: no gain was shown, in two rounds, and the description stays
C4 (the description Round 12 committed).** Nothing here touches a PushPress tenant: a run is one `claude -p` call with one tool (Skill), one turn and the whole skill-craft plugin visible, and the only thing
recorded is which skill the model called first.

| | round a (`frozen/`, `outputs/`) | round b (`round-b/`) |
|---|---|---|
| held-out set | 12 leak reports that carry the gym's own context, from the first author agent | 12 short generic leak reports (at most 45 words), from a second author agent |
| C5a ("... created, tested or leaked ...") fired on | 12 of 12 | 12 of 12 |
| C4 (the description at the head) fired on | 12 of 12 | 11 of 12 |
| gain line (at least 4 more than C4) | 0, fails | 1, fails |

Because the gain line failed, nothing after it ran, as fixed in advance: no quiet prompts, no regression, no announcements, no description change. 78 runs, 2.53 USD.

## Layout

- `frozen/` is round a's design. `frozen-dev-manifest.txt` hashes the 11 files that existed before the first run of any kind (design, harness, scorer, candidates, dev prompts, author brief, Round 9's and
  Round 12's prompt files); `frozen-manifest.txt` hashes all 15 files (adds `after-dev.md`, `make_leak_prompts.py`, the agent's batch as it wrote it and the harness file made from it), taken after the dev
  stage and the batch and before the first confirmation run. Check them: `cd frozen && shasum -a 256 -c frozen-manifest.txt`. `design.md` has the question, the arms, the candidates, the dev stage with its
  selection rule, the order of runs, the pass lines, the budget and the claim limit; `score_p25.py` is the scorer; `run_trigger.py` and `make_candidate.py` are Round 12's, byte for byte; `candidates/` holds
  C4, C5a and C5b (C5b was never run).
- `outputs/` holds round a's runs (`leak-pos-C5.json`, `leak-pos-C4.json`), the scorer's output (`summary.json`, `scorer-output.txt`), `dev/` (the dev stage, used to choose C5a, not held out), the post-hoc
  diagnostic (`diagnostic-*.json`, `diagnostic-note.md`: not in the frozen design, it decided nothing) and `logs/` (the harness's own summaries).
- `round-b/` is the second round: `frozen/` (`design-b.md`, `prompts/author-brief-b.md`, `make_leak_prompts_b.py`, the second agent's batch and the harness file; `frozen-b1-manifest.txt` before the agent was asked,
  `frozen-manifest.txt` before the first run) and `outputs/` (its runs, scorer output and logs). It reuses round a's harness, payloads and scorer unchanged.

## How the runs were made

Three plugin payloads built from the published skill-craft 2.35.10 (`git archive ffbc1cb852ccde469743c5d312d95603fd27d56a plugins/skill-craft`, 419 files each) that differ only in the description block of
`skills/pushpress/SKILL.md` (`frozen/make_candidate.py`): C4 (its `SKILL.md` hashes to the value Round 12 recorded), C5a and C5b. Each run, from a scratch directory outside every repository:

    claude -p --restricted --strict-mcp-config --plugin-dir <payload> --tools Skill --max-turns 1 --max-budget-usd 0.3 --no-session-persistence \
        --output-format stream-json --verbose --model sonnet "<prompt>" < /dev/null

Claude Code 2.1.323, model `claude-sonnet-5-5` (alias `sonnet`), default effort, 48 skills visible (25 `skill-craft:*` and 23 bundled), the same list in every arm and every run. The harness calls a run valid
only when its init event lists `skill-craft:pushpress`; no run had an error. Re-score without a model: the commands are in the first lines of `outputs/scorer-output.txt` and
`round-b/outputs/scorer-output.txt`.

## What was not kept

- Answer text: the harness stores only the skill names called, the skill-list hash, the model named by the init event, cost and turn counts.
- The two author agents' own cost: one request each to a fresh `sonnet` agent (137,306 and 145,570 tokens by the harness's count), not metered in USD here. Each made one Write of its JSON and the harness's hand-back, and no other tool call (checked in its transcript).
