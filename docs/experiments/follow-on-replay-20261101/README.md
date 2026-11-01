---
Status: measured 2026-11-01; exploratory. Four readers (the first reader, Sol twice, Grok once) classified the same 32 rows; E2E cases only; no ShipLoop run was made and nothing in ShipLoop changed.
Consumer: the owner, deciding D1 to D4 of the follow-on design (docs/shiploop-follow-on-run-design-2026-10-31.md, sections 7 and 10). Later: whoever collects leftovers from the owner's own features and wants to know whether the classes hold.
Journal: docs/shiploop-follow-on-run-journal.md (Round 4).
---

# What other readers make of what runs leave open — 2026-11-01

The 2026-10-31 peek ([../follow-on-peek-20261031/README.md](../follow-on-peek-20261031/README.md)) read what finished runs leave under
`Open for the next run` and found no gap the system could close alone and three decisions in 122 runs. One reader made that
classification, the same model that wrote the design. This replay (design section 7, M1) asks whether other readers, blind to
those labels, classify the same texts alike. The plan, the rules and five predictions were committed before any reader was
called (journal, Round 4, Plan).

## 1. The answer

**The classes hold, and no gap appears.** 28 of the 32 rows get the same class from all four readers. The first reader agrees with the
other three on 28 to 30 rows (coarse groups: 28 to 30 of 32, kappa 0.83 to 0.91), and the three others agree with one another on 30 to 32.
No row is a confirmed gap: the first reader, Sol's main run and Grok labelled none; Sol's retest labelled two (F01, N1), Grok
did not, and each of those runs records a person as the owner of the open item and no authenticated browser as the reason. What is
left is the `decision` class, and it is smaller than the first reader said: two rows by majority (F08 csv-report numeric forms,
F22 the delivery route of `ticket.assigned`), three by the first reader alone, out of 166 finished runs now (1.2% to 1.8%; 3 of 122,
2.5%, at the snapshot). The third decision (F23) is read as `person` by all three other readers.

So the replay does not move the design's recommendation. Its rule N applies: with no gap, `decision` is the only live class, and the
recommendation stays not to build the follow-on list until runs of the owner's own features show more.

## 2. Method

- **The set** (`build_set.py`, `rows.json`): 32 rows, one per run. F01..F25 are the 25 strict rows of the peek, frozen. N1..N7 are the
  strict rows of runs outside the peek's snapshot: a scan of every `~/e2e-runs*` root found 44 runs finished since (166 now against
  122) and 7 with real text: `-hostonly` 2, `-multipass` 3, `-xr` 1, `~/e2e-runs` 1. Each row has its full text and its request as numbered
  sentences (17 distinct requests).
- **The first reader** (Claude Sonnet 5.5): `classification.json` for F01..F25; `first-reader-new-rows.json` for N1..N7, written before any
  other reader was called (sha256 a7e424970ed18602fc9fb2b00cff5bd8e2e105283e0adb7fefb6df64c2bd97a9).
- **The other readers** (`make_prompts.py`, `prompts/`): blind to every label, note and `arguable` flag, to case and run names, and to
  each other. Each prompt holds the seven class definitions of `classification.json` verbatim, the rows shuffled and renamed r01..r32, and
  the requests lettered by first appearance; the owner's home directory prefix is replaced by `~/` (one occurrence, in F19).
  - sol-a, the main second reader: Codex GPT-6.1 Sol (`gpt-6.1-sol`, fallback off), effort xhigh, read-only sandbox, web search disabled
    (the envelope says so), an empty working directory; classes in file order, seed 20261101.
  - sol-b, the retest: the same model and effort, classes in reverse order, seed 20261102.
  - grok, the third reader: Grok (`grok-4.7`, served model verified), effort xhigh, `--no-tools`, an empty working directory; file order, seed 20261103.
  Each reply is in `readers/NAME.raw.json` and, parsed, in `readers/NAME.parsed.json` (`parse_reader.py`). No reply needed a rerun. No tool
  or command use appears in a reader's log. The Codex CLI printed a warning that its version (0.166.0) differs from the runner's contract (0.144.5).
- **The measures** (`compare.py`, fixed before the run): fine agreement (seven classes) and coarse agreement (five groups) for every pair, kappa on
  the coarse groups, the gap and decision analyses, the 2-of-3 majority of first, sol-a and grok. `extra_stats.py` holds the post-hoc
  statistics and is not pre-registered.
- **The reading** (journal, Round 4, Plan): rule G (a candidate gap from Sol is confirmed only if Grok agrees and the run's own record shows an
  unmet request sentence or a refuted assumption that needs no person), rule N (with no gap, `decision` is the only live class), rule D
  (`decision` is separable if Jaccard(first, sol-a) on the decision rows is at least 2/3).

## 3. Results

Agreement (`compare-output.txt`):

| pair | fine, 32 rows | coarse, 32 rows | kappa (coarse) |
|---|---:|---:|---:|
| first vs sol-a (main) | 28 | 30 | 0.91 |
| first vs sol-b | 28 | 28 | 0.83 |
| first vs grok | 30 | 30 | 0.91 |
| sol-a vs sol-b (Sol against itself) | 30 | 30 | 0.91 |
| sol-a vs grok | 30 | 32 | 1.00 |
| sol-b vs grok | 30 | 30 | 0.91 |

On the 25 frozen rows the first reader agrees with sol-a on 22 (coarse 23) and with grok on 23 (coarse 23); on the 7 new rows on 6 (coarse 7) and 7 (coarse 7).

Class totals (`extra-output.txt`):

| class | first | sol-a | sol-b | grok |
|---|---:|---:|---:|---:|
| decision | 3 | 2 | 2 | 2 |
| person | 7 | 7 | 7 | 9 |
| capability | 4 | 6 | 4 | 4 |
| extension | 6 | 5 | 5 | 5 |
| debt | 1 | 1 | 1 | 1 |
| note | 11 | 11 | 11 | 11 |
| gap | 0 | 0 | 2 | 0 |

`note`, `debt` and `capability` (as the first reader read it) are unanimous. The four rows on which any two readers differ:

| row | text starts | first | sol-a | sol-b | grok |
|---|---|---|---|---|---|
| F01 | Confirm rendering and click-through in an authenticated browser. | person | capability | **gap** | person |
| N1 | Observe the authenticated Lightning board in de and exercise play and restart… | person (arguable) | capability | **gap** | person |
| F18 | Optional: a test for the page's fetch-failure message… A node server.js… was still running; stop it by hand. | extension | person | person | person |
| F23 | At handoff: record the requesting user's answer to A1 (person-level delivery) and state where the post-release knowledge lives… | decision | person | person | person |

- **Gap (rule G).** Sol's retest, with the classes listed in reverse order, moved F01 and N1 from `capability` to `gap`; its own reason says a
  browser automation "could supply" the missing evidence. Grok called both `person` (alternative `capability`). The runs themselves record the open
  item with an owner who is a person and a reason that is a missing capability: F01 `owner: user`, "No authenticated browser session is available
  to this automation"; N1 `owner: release owner`, "No authenticated browser automation route is available" (`third-look.txt`). Neither is a gap. None is
  confirmed. The capability/gap line is where the readers' definitions are least stable: the same reader moved on it when the order of the definitions changed.
- **Decision (rule D).** The first reader's set is {F08, F22, F23}; sol-a, sol-b and grok each give {F08, F22}. Jaccard(first, sol-a) is 2 of 3, exactly
  the threshold, so the class passes the rule, by one row. The design's two test rows agree across all four readers: F22 `decision`, F11 `note`. The row that moves is F23,
  a handoff note that mixes an answer to record (decision), a place where knowledge lives (note) and a readiness check for operations (person); every
  other reader keyed on the whole and chose `person` (alternatives: decision, debt, decision).
- **The first reader's moves.** F18 is a mixed text: three optional items (extension) and an unconditional instruction to stop a leftover server by hand
  (person). All three other readers chose `person`; the first reader keyed on the leading "Optional:". On a second reading the majority is the better class.
- **Majority** (first, sol-a, grok): no row is unresolved. Final classes: decision 2, person 9, capability 4, extension 5, debt 1, note 11, gap 0.

Predictions (`compare.py`; probabilities written before the run): P1 sol-a labels no row gap, 70%: held. P2 coarse agreement first vs sol-a at least 26 of 32, 65%:
held (30). P3 Jaccard on decision at least 0.67, 55%: held (0.67, at the threshold). P4 at least half of the fine disagreements fall on rows the first reader
marked arguable, 60%: missed (1 of 4: N1). P5 sol-a and sol-b agree on at least 28 of 32, 60%: held (30).

## 4. What this does and does not show

- It shows that the first reader's classes are not an artefact of one reader on these rows: three other readings, from two vendors, reproduce them on 28 of 32 rows
  and agree on the two decisions that matter (F08, F22) and on the absence of a gap.
- It shows where the classes are soft: a text that mixes items of different classes (F18, F23), and the line between `person`, `capability` and `gap`,
  which moved with the order of the definitions. The first reader's `arguable` flags did not predict where readers differ: they differed on three rows
  the first reader had not flagged.
- It does not show that the classes are right. Every reader had the first reader's definitions, so some agreement is the definitions agreeing with themselves.
- It does not show the value of a follow-on run. The corpus is small, E2E-only and saturated (every completed brownfield run passes its held-out checks, 593b4b44cfc0a166e01fe3a61e301ba85833c8a8), so a gap may simply not be in it.
- It says nothing about the owner's own features: none of the 32 rows comes from one.

## 5. Limits and unknowns

- 32 rows and seven classes: one row moves the decision overlap from 2/3 to 1 (F23 read as decision), to 1/2 or to 1/3. The threshold of 2/3 was met exactly; a
  threshold of 0.7 would have failed it. The new rows come from the same few ticket cases and are not independent.
- The 2-of-3 majority includes the first reader's own vote. Without it, sol-a and grok agree on all 32 rows at the coarse level and on 30 at the fine level.
- The replay classifies whole `Open for the next run` texts, one class per text. The design's follow-on list would classify entries one by one, so the mixed texts
  (F18, F23) would not arise there; whether the readers would then agree is not measured.
- Sol and Grok are not deterministic. Sol's retest differs from its main run on two rows (the gap labels); Grok ran once.
- The Sol model identity is the requested wire id (`gpt-6.1-sol`, fallback off); Grok's served model was verified. The Codex CLI version differs from the runner's contract.
- The runs' archives are outside the repository (`~/e2e-runs*`); `build_set.py` reproduces only on the owner's machine. `rows.json` holds the texts, so everything after it reproduces
  from the repository, apart from the model calls.
- The set excludes runs whose lessons say "none": a run that should have listed something and did not is outside what a leftover text can show (design section 5).

## 6. Reproduce

```sh
python3 -B docs/experiments/follow-on-replay-20261101/build_set.py        # needs the archives (owner's machine)
python3 -B docs/experiments/follow-on-replay-20261101/make_prompts.py
# one call per reader, from an empty working directory (E):
#   ask.sh sol  --json --effort xhigh --profile ask --cwd E "$(cat prompts/sol-a.txt)"   > sol-a.json   (likewise sol-b)
#   ask.sh grok --json --no-tools --cwd E "$(cat prompts/grok.txt)"                      > grok.json
python3 -B docs/experiments/follow-on-replay-20261101/parse_reader.py sol-a sol-a.json   # likewise sol-b, grok
python3 -B docs/experiments/follow-on-replay-20261101/compare.py
```

Files: `build_set.py`, `make_prompts.py`, `parse_reader.py`, `compare.py` (pre-registered), `extra_stats.py` (post hoc), `rows.json`, `first-reader-new-rows.json`, `prompts/`
(the three prompts and their row maps), `readers/` (raw and parsed replies), `compare-output.txt`, `extra-output.txt`, `third-look.txt`.
