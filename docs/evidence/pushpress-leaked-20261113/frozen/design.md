# P25: can the description load the card for a leaked PushPress key? Design, frozen before the first run

Journal Round 13, 2026-11-13. The owner answered "Add leaked trigger (P25)" to "What should happen next with this branch?", which lifts the gate for a change to the
description of `skills/pushpress/SKILL.md`, its test and a pending note, and nothing else. A push, a merge, a release and everything on the live tenant still wait.
This file, the harness, the scorer, the candidates, the dev prompts and the author brief were hashed (`frozen-dev-manifest.txt`) before the first run of any kind. The
held-out prompts and the choice of candidate are added after the dev stage and hashed again (`frozen-manifest.txt`) before the first confirmation run.

## Question

Round 12 (journal F13, F15): with C4, the description now at the head of the branch, 22 of 22 runs on eleven held-out announcements loaded the card, but a PushPress key
pushed to a public repository (HP11) did not, in 2 of 2 runs, while two other after-the-fact prompts did (4 of 4). The card does cover a leaked key: Rule 6 says a key that has
reached a transcript is burned and the user rotates it, and `references/settings-and-admin.md` §2 names the page where a leaked key is replaced. Can a change to the key sentence of the
description, inside the cap of 1024 characters, make the card load when a PushPress key or webhook secret has leaked (pushed, posted, shown, sent), without loading it for other products'
leaked keys and without losing the announcements and Round 9's prompts?

## Arms and harness

Unchanged from Round 12 (`run_trigger.py` and `make_candidate.py` are byte-identical copies of its files; `claude -p --restricted --strict-mcp-config --plugin-dir <absolute payload> --tools Skill
--max-turns 1 --max-budget-usd 0.3 --no-session-persistence --output-format stream-json --verbose --model sonnet "<prompt>"`, from a scratch directory outside every repository, stdin from /dev/null,
`SHIPLOOP_KEEPALIVE=off`; Claude Code 2.1.323, model `claude-sonnet-5-5` at default effort; 48 skills visible; a run **fires** when the stream holds a Skill call that names `skill-craft:pushpress`;
a run is invalid without a result event or without the pushpress skill in its init list). Nothing but the skill names called, the init list hash, cost and turn counts is stored; no answer text.

- **C4 arm**: the published payload (skill-craft 2.35.10, `git archive ffbc1cb8 plugins/skill-craft`) with only the description block replaced by `candidates/C4.txt`. Its `SKILL.md` must hash to the
  value that Round 12's run files record (`payload_pushpress_skill_sha256`), which proves the arm is Round 12's.
- **C5 arm**: the same payload with the description block of the chosen candidate (C5a or C5b), made by the same script.

Positive control: the dev stage's control prompt DC1 (Round 9's E1) must fire on each candidate's payload; the regression's explicit prompts are the control for the confirmation runs. A negative result
counts only next to a control that fired in the same session and the same harness (journal F16).

## Candidates (`candidates/`; written and hashed before any run)

Both change only the description block. Word changes are inserted plus deleted words against C4 (`difflib`, whitespace tokens).

- **C4** (1018 characters): the current description.
- **C5a** (1022): the P25 text. The verb list reads "pasted, saved, created, tested or leaked" and "versus" becomes "vs" in the last sentence to stay under the cap. 7 words changed.
- **C5b** (1023): an explicit after-the-fact clause. The key sentence reads "..., even if the user only says they are about to paste one, and AFTER one has leaked: it says where a key may go, what to
  say if one reaches the chat and where a leaked one is replaced." To fit the cap it drops ", through the owner's signed-in browser" from the first sentence and "payments," from its list of areas
  (the later list of questions still holds failed or upcoming payments, deposits and payouts), and "versus" becomes "vs". 29 words changed.

Everything else is C4 character for character. "Use whenever the user mentions PushPress", "even if the user only says they are about to paste one", "what to say if one reaches the chat" (C5a),
"sign-in through the host's approved credential flow (never a typed password)" and "safety rules for member data, money and outbound messages" stay.

## Dev stage (not held out; chooses a candidate; lines fixed here, before it runs)

`prompts/dev-prompts.json`: four leak prompts that should fire (DL1 is HP11, the observed miss; DL2 to DL4 are mine: a screenshot in Slack, a signing secret in a public repository, a key in deploy logs),
three other-product leak prompts that should not (DLN1 is HP11 with Stripe's key, DLN2 is DL2 with Mindbody's, DLN3 an AWS key in a public gist) and the control DC1. Per candidate: the four leak
prompts two runs each, the three negatives and the control one run each: 12 runs (about 0.4 USD).

**Selection rule.** C5a runs first. A candidate **passes dev** if (i) DC1 fires, (ii) at least 6 of its 8 leak runs fire and DL1 fires in at least 1 of its 2 runs, and (iii) none of its 3 negative runs
fires. If C5a passes it is the candidate (it changes fewer words than C5b). If it fails, C5b runs the same dev set under the same lines; if it passes it is the candidate. If neither passes, stop: no
confirmation run, no change, and the dev results are the finding. If DC1 does not fire, stop and diagnose before reading any other result of that candidate.

## Held-out set (made after the candidate is chosen)

`prompts/author-brief.md` is sent as written to a fresh `sonnet` agent that has seen no candidate, no result and no other prompt, and is told to use no tools. It returns 12 leak prompts (6 `code`: a repository,
a log, a screenshot or another public place; 6 `people`: email, chat, shared document, former contractor; at least six without the words leak, leaked or leaking, because HP11 did not use them) and 12 quiet
prompts (8 about other products' keys, 2 about a key with no product, 2 about something that is not a key; none names PushPress). Texts are kept verbatim in `prompts/leak-agent-output.json`; the harness
file `prompts/leak-prompts.json` has ids LP1 to LP12 (categories `leak-code`, `leak-people`) and LN1 to LN12 (`neg-other-product`, `neg-no-product`, `neg-not-a-key`). A batch that breaks the brief (counts,
a PushPress in a quiet prompt, no PushPress in a leak prompt, more than six leak prompts with the word leak, a duplicate) is sent back to the same agent once with the broken rule named, before any run.
The prompts are read only after the candidate is chosen.

## Confirmation order (one run of each prompt; no prompt, candidate text or line changes after a result)

1. **Stage 1, benefit.** The chosen candidate (C5) on the 12 leak prompts. If L1 or L1a fails, stop (no C4 arm, no stage 2). Otherwise C4 on the same 12 prompts, for L3; if L3 fails, stop (no stage 2).
2. **Stage 2, harm**, only if stage 1 passes, in this order: C5 on the 12 leak negatives (L2; if it fires on any, C4 also runs them, as a diagnostic); C5 on Round 9's 24 prompts
   (`prompts/round9-prompts.json`, sha256 `ce269ffaa4c6958a2ffae939b2ba6a8b3a548f5a544c388a2a556bea3fa6fd0b`) for R1, R3, R4 and the measure R2; C5 on the 11 held-out announcements of Round 12 for A1.
   A gate that fails stops the stage.

## Pass lines (the description is changed only if all pass and every file is complete)

- **L1** C5 fires on at least 10 of the 12 leak prompts.
- **L1a** C5 fires on at least 4 of the 6 `code` prompts (the kind HP11 belongs to, which C4 missed).
- **L3** C5 fires on at least 4 more of the 12 leak prompts than C4 does.
- **L2** C5 fires on at most 1 of the 12 leak negatives; each false fire is listed with its prompt.
- **R1** C5 fires on at least 5 of Round 9's 6 explicit prompts.
- **R3** C5 fires on at most 1 of Round 9's 12 quiet prompts.
- **R4** C5 fires on none of Round 9's 3 sport80 prompts.
- **A1** C5 fires on at least 9 of the 11 held-out announcements.

Measurements, reported with each miss and not gates: **R2** implicit recall on Round 9's six implicit prompts (C4 fired I4 4 of 6 and I6 3 of 6 runs in Round 12 and the other four 12 of 12); the per-class
recall of the leak prompts for both arms; C4 on the leak negatives if it ran. Every counted run must be valid (a result event, the pushpress skill in the init list); the harness retries a run without a result
once, and an invalid run after that makes its file incomplete, which blocks the decision and is reported, not hidden.

If every line passes, the description block of `skills/pushpress/SKILL.md` is replaced by the candidate (the same fold as `make_candidate.py`, so that the block equals the tested payload's), the pinned phrases of
`test_description_loads_the_card_before_a_key_is_pasted` follow it, and a patch note is added; the card body, the references, the extractor, the version line and the owner's project copy stay as they are.
If a line fails, the description stays C4 and the record says which line failed.

## Budget and stops

Plan: 12 dev runs (24 if C5b is needed), 12 + 12 stage 1, 12 + 24 + 11 stage 2: 83 runs, about 2.9 USD at the 0.035 USD a run of Round 12; contingencies 12 (C5b dev) and 12 (C4 on the leak negatives). Cap: **3.5 USD
of model runs in total** by the CLI's `total_cost_usd`, summed over every run file in `outputs/` including controls; nothing is discarded or left out of the sum. The author agent is not metered in USD
(tokens are noted). At the cap, stop and ask. A run error, an invalid run, a failed control or a stage that fails its lines also stops the work until I have read it.

## Claim limit

One model at default effort, Claude Code `-p`, one tool and one turn, 48 skills visible, no project notes or files; it measures which skill the model calls first. It does not show that Rule 6 is applied
afterwards (journal Round 11 measured that), that another model or host loads the card, or that the owner's project copy of the card, which has its own description, does. The leak prompts come from one author
agent: 12 prompts, one run each, so 10 of 12 has a 95% interval of roughly 0.55 to 0.95, and the gain over C4 is measured on one run of each arm. The lines are decision thresholds fixed in advance, not tests of
significance. Round 9's regression runs once per prompt here (Round 12: twice), so it detects a loss of recall or a new false fire only when it is large; the borderline implicit prompts (I4, I6) are a measurement, not a gate.
The payload is skill-craft 2.35.10 (25 skills), not the installed 2.36.1 (26).
