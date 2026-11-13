# P25, round b: does C5a load the card for the short, generic leak reports that C4 misses? Design, frozen before the author agent is asked and before any run of this round

Journal Round 13, 2026-11-13. The authorization is the owner's "Add leaked trigger (P25)" button, as for round a: a change to the description of `skills/pushpress/SKILL.md`, its test and a pending note, and nothing
else, and the budget was "about 3 USD". Round a (`../../frozen/design.md`, hashed before its first run) is unchanged and its decision stands.

## Why a second round

Round a ran its lines on 12 held-out leak prompts from the first author agent. C5a fired on 12 of 12 and so did C4 (12 of 12), so the gain line (L3: at least 4 more fires than C4) failed at 0 and, as fixed in advance,
stage 2 did not run and the description stays C4. The set could not have shown a gain: its prompts carry the gym's own context (a kiosk, a Zapier hookup, an MCP server, requests to look in a folder), and C4 loaded
all of them.

A post-hoc diagnostic (not in round a's design, run to explain HP11, the one miss of Round 12) then showed a difference on two short prompts in which PushPress is only the name of the key:
HP11 ("pushed to a public GitHub repo, rotate it first or clean up the history first?"): C4 2 of 8 runs (0 of 2 in Round 12, 2 of 6 in the diagnostic), C5a 8 of 8 (2 of 2 in dev, 6 of 6 in the diagnostic);
DL4 (a key in deploy logs, "is that bad?"): C4 0 of 2, C5a 2 of 2. DL2 and DL3 (a screenshot in a coaches' Slack; a signing secret in a public repository) loaded in both arms, 2 of 2 each.

**Hypothesis (exploratory, from that diagnostic).** C4 misses short, generic security-incident questions about a PushPress key (one or two sentences, the key is the only PushPress-specific thing, nothing asked of the
assistant but advice); C5a ("... created, tested or leaked ...") loads them, and does not load the same questions about other products' keys. Round b tests this on new prompts from a new agent.

It is a second attempt after a failed first one, aimed at the class that the first attempt's diagnostic singled out. The prompts of this round are constrained to that class, so a pass supports the clause for short
generic reports and says nothing about leak prompts in general (round a's set says C4 already loads rich ones).

## Arms, harness, scorer

Unchanged from round a: the same `run_trigger.py` and `make_candidate.py`, the same three payloads (C4 and C5a, `claude -p` with one tool and one turn, 48 skills visible), the same scorer
(`../../frozen/score_p25.py`, hashed in round a's manifests; its categories fit this round's prompt file). The candidate is C5a as chosen by round a's dev stage; C5b stays untested. Round a's files are verified against
`../../frozen/frozen-manifest.txt` before the first run of this round.

## Held-out set (round b)

`prompts/author-brief-b.md` is sent as written to a new fresh `sonnet` agent that has seen no candidate, no result, no other prompt and no earlier batch (its only addition is the same delivery note as in round a:
one Write of the JSON to a scratch file, copied with `cp` and compared with `cmp`). It returns 12 positives (`LS1` to `LS12`: 6 `code`, 6 `people`; at least six without the words leak, leaked, leaking) and 12 quiet prompts
(`LSN1` to `LSN12`: 8 other products' keys, 2 with no product, 2 about something that is not a key; none names PushPress), every message of one or two sentences and at most 45 words, with no request to the
assistant to look at or change anything. `make_leak_prompts_b.py` refuses a batch that breaks the brief (counts and classes, PushPress missing or present, fewer than six without the word leak, a duplicate,
a message over 50 words, more than 3 of the 24 with a setup word or a request); a refused batch is sent back to the same agent once with the broken rule named, before any run. The texts are read after the design
is hashed.

## Order of runs (one run of each prompt; no prompt, candidate text or line changes after a result)

1. C5a on the 12 positives. If L1 or L1a fails, stop (no C4 arm, no quiet prompts).
2. C4 on the same 12 positives. If L3 fails, stop.
3. C5a on the 12 quiet prompts (L2).

## Pass lines (the same numbers as round a)

- **L1** C5a fires on at least 10 of the 12 positives.
- **L1a** C5a fires on at least 4 of the 6 `code` positives.
- **L3** C5a fires on at least 4 more of the 12 positives than C4 does. This line can fail the new set the way round a's did, if C4 loads these prompts too.
- **L2** C5a fires on at most 1 of the 12 quiet prompts; each false fire is listed with its prompt.

If all four pass, the clause is supported on the class it was aimed at, and the description change waits for stage 2 of round a's design (A1: at least 9 of the 11 held-out announcements; R1, R3, R4 on Round 9's 24
prompts: 35 runs, about 1.2 USD), which takes the total over the 3 USD the owner named and so waits for the owner's yes. If any of the four fails, the description stays C4. A run error, an invalid run or a failed
control stops the work until it is read. Every counted run must be valid; the harness retries a run without a result once.

## Budget

12 + 12 + 12 runs, about 1.2 USD at 0.033 USD a run. Spent before this round: 1.77 USD (54 runs, all kept in `../outputs/`). Cap for this round 1.3 USD, so 3.07 USD in all; stop at 3.2 USD in all, whatever remains.
The author agent is not metered in USD (tokens are noted).

## Claim limit

As in round a (one model at default effort, Claude Code `-p`, one tool and one turn, 48 skills visible, no project notes; the payload is skill-craft 2.35.10 and not the installed 2.36.1; the owner's project copy of the
card is not tested). 12 prompts from one author agent, one run each: 10 of 12 has a 95% interval of roughly 0.55 to 0.95. The lines are decision thresholds fixed in advance, not tests of significance. The hypothesis was
formed after looking at the data of round a and its diagnostic, which is why round b exists and is held out; two prompts (HP11, DL4) carried it, and both were also the ones C4 missed.
