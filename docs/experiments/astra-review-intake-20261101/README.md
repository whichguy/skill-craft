# Astra's max-effort review of ShipLoop's prompt enrichment (2026-11-01)

Consumer: the owner, who asked "Ask Astra with max thinking to review the prompt enrichments and see if there are any recommendations it would have on what to improve"; and
whoever next changes intake item 9 or designs the next intake study. I read "the prompt enrichments" as ShipLoop's intake enrichment (duty 9: the catalog K1 to K12, the key-question
ledger, its routes and the look-it-up sentence) and the study behind it ([../../shiploop-intake-question-bank-journal.md](../../shiploop-intake-question-bank-journal.md)).

## Setup

`ask.sh astra ask --json --effort max --profile consult --cwd <checkout of main>`: model `gpt-6-astra`, effort `max`, sandbox read-only (it could read the repository and run read-only commands, not
write), no fallback to another model, about 13 minutes. `brief.txt` is exactly what it was given (the sources to read, my summary to check, and what to return); `review.md` is its answer, verbatim.

## Its five recommendations (its ranking; none adopted yet)

1. Measure K12's effect on delivered behaviour with requests that actually need a lookup; keep the shipped design meanwhile (a screen of about 10 live runs: `hello` unchanged as a negative control,
   `shared-expenses` and `user-listing` with references into supplied project documentation).
2. Carry intake's evidence, defaults and open questions forward by Q-ID, so that a provisional default cannot silently become a requirement (wording for intake, discovery's "Answer each intake open question"
   duty and spec's basis; test it with an X2b-style cold-context exercise that includes a later contradiction).
3. Make term resolution context-sensitive: a matching installed-skill name is a candidate meaning, not proof of intent (three contrast pairs, 12 intake calls).
4. Clarify relevance, applicability and person routing: a question only for an unresolved distinction that changes named work; `applies: no` means the concern cannot affect the outcome; `person` records a dependency and
   does not itself stop the run; no word caps.
5. A decision-relevant evaluation contract for future studies: discovery, transfer and delivery reported separately; request-blocked comparisons; whole-pipeline cost; predeclared branches (reanalysis of saved scores, no model calls).

Its "do not change" list: the catalog and model-written ledger, K12, unattended operation, unrestricted answers, K1/K9/K10/K11, no K13 or compulsory probes, scripts own state, and no proof-order gate as an intake improvement.

## What I checked against the repository

| Its claim | Result |
|---|---|
| The shape check requires, per question, only a unique `Q` id, a nonempty question and an allowed route; `category`, `changes`, `default`, `blocks` are asked for but unchecked, and the error text lists more than is checked | Verified (`_check_intake_questions`, `QUESTION_ROW`, shiploop_navigator.py). Consistent with the lesson of `e7e0bc3c0e347845e8ee4f99ee318175d280c9db`; no stricter gate is recommended by anyone. |
| Journal section 0 credits the shipped ledger with the live A/B's drop in proof-order send-backs (0 of 6 against 4 of 6) | **Right, and my error.** That A/B tested the proof-order refusal and the ledger together (`45f9752eee7d4fe3450b9ac88843cc1da0fbb980`); the refusal refused exactly the 4 control plans that went on to the send-back and fired 3 times in the treatment arm. The ledger's own downstream effect is unmeasured. Corrected in the journal. |
| Journal section 0 says an attended intake asked "one question per output, the same one every time" | **Right, an overstatement.** README QB4: person-routed rows Bp 1, 1, 1, 1 and Qp 1, 1, 0, 0, all six the weekly report's window: six of eight outputs. Corrected in the journal. |
| QB5's registered test pooled 15 against 15 outputs in one unrestricted permutation test | Verified (`qb5.py`, `p_higher`, `permutation_p`). Its paired sign-flip sensitivity (items right p 0.000122; silent assertions 0.125; a three-request sign-flip cannot go below 0.125) is **its recomputation, not mine**. |
| Discovery's duty is "Answer each intake open question in `summary` with a source, or keep it unknown with an owner" | Verified (shiploop_prompts.py, discovery duty 14). |
| Test strategy reads spec and research, not intake | Verified (shiploop_stage_spec.py, the `test-strategy` stage's `reads`). |
| `run.py --prompt` makes a custom case that does not inherit a named case's fixture or quality metadata | Verified (run.py, `load_case`/`case_quality` branches on `custom`). |
| Intake has no blanket prohibition on reading; the journal's "real intake leaves repository reading to discovery" is too strong | Consistent with the intake duty text (no prohibition found); the stage division should be worded as "broad baseline discovery belongs to later stages". |
| The QB5 means, +8.1% output tokens, +16.3% uncached input, silent assertions 0.667 to 0.200, the judge's 2.64 and 4.72 point shifts, QB1's 0.935 and 0.958, the `meter` partial credit, the seat-reservations read-contract miss | **Not rechecked by me.** The journal agrees on +8% tokens and the 2.6 to 4.8 point drift. |

## What changed in the repository because of it

Only the journal: dated corrections at the two overstated sentences in section 0 and a log entry with findings F50 to F54. No prompt, skill or default changed.

## My reading of the recommendations (assessment, not decisions)

- Worth doing first: **1**, because both live studies say that fully specified requests cannot show K12's benefit and this is the only one of the five that can; and **5**, which costs no model calls.
- Hold for the owner: **2**, **3** and **4** change prompt text that every run reads, so each needs its small experiment before a change; 3 is the cheapest (12 intake calls).
- Attribution correction (F50) and the QB4 count (F51) are applied.
