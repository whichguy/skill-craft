# P1(b): can the description load the card before a PushPress key is pasted? Design, frozen before the confirmation runs

Journal Round 12, 2026-11-13. The owner answered "Fix description (P1b)" to "Which follow-up should I do next?", which lifts the gate for a change to the
description of `skills/pushpress/SKILL.md` and its test and pending note. A push, a merge, a release and everything on the live tenant still wait.

## Question

Round 11 (journal F8): with the published description the card did not load when a user announces that they will paste a PushPress API key (q15 0 of 2, k1 0 of 4,
in the single-plugin eval), while prompts that ask for something (k2, k3) loaded it 8 of 8. A card that does not load cannot apply Rule 6. Can a change to the
description, inside the repository's cap of 1024 characters, make the card load before a key is pasted, without making it load for other products' keys and without
losing the prompts it loads for today?

## Arms and harness

- **published**: the payload of skill-craft 2.35.10 (`plugins/skill-craft` at `ffbc1cb852ccde469743c5d312d95603fd27d56a`: 25 skills; its `skills/pushpress/SKILL.md` is
  byte-identical to the source at that commit).
- **candidate**: the same payload with only the description block of `skills/pushpress/SKILL.md` replaced (`make_candidate.py`; 419 files in each tree, one differs).
- **run** (`run_trigger.py`): `claude -p --restricted --strict-mcp-config --plugin-dir <payload> --tools Skill --max-turns 1 --max-budget-usd 0.3 --no-session-persistence
  --output-format stream-json --verbose --model sonnet "<prompt>"`, from a scratch directory outside every repository, stdin from /dev/null, `SHIPLOOP_KEEPALIVE=off`.
  Claude Code 2.1.323, model `claude-sonnet-5-5` (alias `sonnet`), default effort. The user's settings, plugins and MCP servers are off; the model has one tool, Skill, and one
  turn. A run **fires** when the stream holds a Skill call that names `skill-craft:pushpress`. A run that calls a skill ends with `error_max_turns`, which is expected.
  Every run must list 48 skills (25 `skill-craft:*` and 23 bundled) including `skill-craft:pushpress`, the same list in both arms; a run without the skill in its init list is invalid.
- Nothing but the skill names called, the init skill-list hash, cost and turn counts is stored; no answer text.
- Positive control, run before any counted run: Round 9's E1, E3 and I1 fire 2 of 2 each on the published payload, and its sport80 prompt N6 fires `skill-craft:sport80`, not pushpress.
  The control found a defect in the first version of the harness (a relative plugin path resolved against the run's directory loaded no plugin, so 14 runs fired nothing; 0.28 USD,
  discarded): paths are absolute now and the init list is checked.

## Dev stage (not held out; used to choose a candidate)

`prompts/dev-prompts.json`: eight positives (D1 is k1, D2 is q15, D3 to D8 are my own phrasings; D1 to D4, D7 and D8 announce a paste or offer one, D5 and D6 ask for a task) and six
negatives (DN1 to DN6: other products' keys, one other gym product, one with no product). Two runs of each. Published: the six announce prompts fired 1 of 12 runs, D5 and D6
fired 4 of 4. Candidates (`candidates/`): C1b (the published text plus one sentence, a few cuts to fit the cap; 77 words changed), C2 (a rewrite that leads with the key clause; 110 words
changed) and C4 (the published text with its first sentence shortened, one sentence added and the tail kept; 67 words changed). All three fired in 12 of 12 runs of the six announce prompts;
false fires on the six negatives in 12 runs: C1b 1 (the Mindbody prompt), C2 0, C4 0; C4 also fired 4 of 4 on D5 and D6.

**Selection rule**, written before C4 was run (C1b and C2 had been run; the rule was not hashed then): among the candidates with at least 11 of 12 dev announce fires and at most 1 dev false fire
in 12, take the one that changes the fewest words of the published description. That is **C4**. The held-out prompts below were read after C4 had been chosen.

## Held-out set

`prompts/heldout-prompts.json`, written by a fresh `sonnet` agent that had seen no candidate description and no result, from a brief that described the situation and asked for four kinds of
PushPress key messages (announce, task, question, after) and three kinds of quiet messages (other service, other gym product, no product); texts are verbatim and ids are prefixed with H.
A second request to the same agent added eight more announce prompts, because the first batch had three. 20 positive prompts (11 announce: HP1 to HP3 and HP13 to HP20) and 12 quiet prompts (HN1 to HN12).

## Confirmation order (one run of each; no prompt, candidate text or line changes after a result)

1. **Regression** of C4 on Round 9's 24 prompts (`docs/evidence/pushpress-validation-20261108/trigger/prompts.json`, sha256 `ce269ffaa4c6958a2ffae939b2ba6a8b3a548f5a544c388a2a556bea3fa6fd0b`), two runs each.
   If a gate below fails, stop: no description change, and the held-out set is not run for C4.
2. **Held-out**: published on the 11 announce prompts, C4 on all 20 positive prompts and on the 12 quiet prompts, two runs each. If C4 has any false fire on a quiet prompt, published also runs the 12 quiet prompts.

## Pass lines

Gates (a change is committed only if all pass):
- **R1** explicit recall of C4 on Round 9's six explicit prompts: at least 11 of 12 runs.
- **R3** false fires of C4 on Round 9's twelve quiet prompts: at most 1 of 24 runs.
- **R4** Round 9's three sport80 prompts: no pushpress fire in 6 runs.
- **H1** C4 on the 11 announce prompts: at least 18 of 22 runs fire.
- **H3** C4 fires in at least 10 more of those 22 runs than published.
- **H4** C4 on the 12 quiet held-out prompts: at most 1 false fire in 24 runs; each is listed with its prompt.

Measurements, reported with each miss and not gates: **R2** implicit recall on Round 9's six implicit prompts (at least 8 of 12 in Round 9's lines); **H2** C4 on all 20 positive prompts
(34 of 40 would be a good result) and by type (announce, task, question, after); published on the quiet prompts if it was run.

Every counted run must be valid (a result event and the pushpress skill in the init list); the harness retries a run that has no result once, and an invalid run is reported, not hidden.

## Claim limit

One model at default effort, Claude Code `-p`, one tool and one turn, 48 skills visible, no project notes or files. It measures which skill the model calls first on a prompt. It does not show
that Rule 6 is applied afterwards (P8 measured that), that another model or host loads the card, or that the owner's project copy of the card, which has its own description, loads it. The held-out
prompts come from one agent; with 12 or 20 prompts the interval around a rate is wide (Round 9: 0.76 to 1.0 for 12 of 12), and two runs of a prompt are repeats, not independent prompts.
