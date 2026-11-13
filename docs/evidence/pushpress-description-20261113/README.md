# P1(b): a description that loads the pushpress card before a key is pasted (journal Round 12)

Does a change to the description of `skills/pushpress/SKILL.md` make the card load when a user only announces that they will paste a PushPress API key or webhook
secret, without loading it for other products' keys and without losing the prompts it loads today? The published description loaded it for 0 of 6 announcements (journal
F8). Nothing here touches a PushPress tenant: a run is one `claude -p` call with one tool (Skill), one turn and the whole skill-craft plugin visible, and the only thing
recorded is which skill the model called first.

## Layout

- `frozen/` is the design, frozen by hash before the confirmation runs (11 files): `design.md` (the question, the arms, the dev stage with its results and the selection
  rule, the order of the runs, the pass lines and the claim limit), `run_trigger.py` (the harness), `make_candidate.py` (builds a plugin payload that differs from the
  published one only in the description block), `score_trigger.py` (the scorer), `candidates/` (the three description texts tried), `prompts/` (the dev prompts; the held-out
  prompts as the author agent wrote them, in two batches, and in the harness format). Check it: `cd frozen && shasum -a 256 -c frozen-manifest.txt` (11 lines, all OK).
  Round 9's prompts (`../pushpress-validation-20261108/trigger/prompts.json`, sha256 `ce269ffa...`) are referenced, not copied.
- `outputs/` holds the confirmation runs (`regression-C4.json`, `heldout-C4-pos.json`, `heldout-C4-neg.json`, `heldout-published-announce.json`), the frozen scorer's output
  (`summary.json`, `scorer-output.txt`), two post-hoc diagnostics that are not in the frozen design (`diagnostic-*.json`), and `dev/`, the dev stage's runs (used to choose a
  candidate, not held out).

## How the runs were made

Two plugin payloads: the published skill-craft 2.35.10 (`git archive ffbc1cb852ccde469743c5d312d95603fd27d56a plugins/skill-craft`) and the same tree with the description block of
`skills/pushpress/SKILL.md` replaced by `frozen/candidates/C4.txt` (419 files in each, one differs). Each run, from a scratch directory outside every repository:

    claude -p --restricted --strict-mcp-config --plugin-dir <payload> --tools Skill --max-turns 1 --max-budget-usd 0.3 --no-session-persistence \
        --output-format stream-json --verbose --model sonnet "<prompt>" < /dev/null

Claude Code 2.1.323, model `claude-sonnet-5-5` (alias `sonnet`), default effort, 48 skills visible (25 `skill-craft:*` and 23 bundled), the same list in both arms. The harness
(`frozen/run_trigger.py`) calls a run valid only when its init event lists `skill-craft:pushpress`. Re-score without a model, from this folder:

    python3 -B -I frozen/score_trigger.py --regression outputs/regression-C4.json --regression-prompts ../pushpress-validation-20261108/trigger/prompts.json \
        --heldout-prompts frozen/prompts/heldout-prompts.json --pub-announce outputs/heldout-published-announce.json \
        --c4-pos outputs/heldout-C4-pos.json --c4-neg outputs/heldout-C4-neg.json --out outputs/summary.json

## What was not kept

- Answer text: the harness stores only the skill names called, the skill-list hash, the model named by the init event, cost and turn counts.
- Two invalid first runs (14 runs, 0.28 USD). The first version of the harness passed a relative plugin path that resolved against the run's directory, so no plugin loaded and nothing
  fired; a positive control (Round 9's E1, E3 and I1, which must fire, and its sport80 prompt, which must call sport80) showed it before anything was counted. The harness now makes
  the paths absolute and checks the init list. A one-run sanity check and one debug run (0.09 USD) are not kept either.
- The author agent's own cost: two requests to a fresh `sonnet` agent (its usage was reported as 126,392 tokens after the first request and 156,749 after the second), not metered in USD here.
