# The Harbor bench: specification

Experiment apparatus of `docs/platform-knowledge-journal.md` (section 10 registers the runs). Nothing here is
ShipLoop product behaviour, and none of it goes to `main` as it is.

## Why an invented platform

The question is whether a platform fact reaches a model's plan, and then its product, by a given route. With a
real platform a model may already know the fact, so a good plan proves nothing about the route. "Harbor" is a
hosting platform that does not exist. Its five rules below are written nowhere but in its platform card, so a plan
or a product that follows one got it from the route under test. Every reading is made by a script.

The rules are of the kinds a real platform has: a manifest entry without which code never runs, a call that
silently returns part of the data, storage that does not outlive a run, a repeat start, and a setting that must be
declared.

## The product (the fixture)

A git-ready tree at `test/shiploop_e2e/fixtures/harbor-stockroom/` (the harness reads fixtures there). Python 3.9
or later, standard library only, no network, no listening port.

```
README.md              what the service is, that it "runs on Harbor", how to run the tests. No job rules.
harbor.toml            the deployment manifest: [app] name and runtime; [actions.recount] run = "stockroom.actions:recount"
stockroom/__init__.py
stockroom/items.py     the Item record (sku, name, quantity) and a small helper or two
stockroom/actions.py   one existing on-demand action, recount(request): reads and writes ONE record by sku
harbor/__init__.py     the local stand-in for the Harbor SDK (see below)
harbor/local.py        `python -m harbor.local run-action <name> [json]`: runs an action through the manifest
tests/test_actions.py  unittest tests of the existing action (they pass)
docs/shiploop/         spec.md, environment.md, architecture.md: the project's knowledge home, as an earlier
                       ShipLoop run would have left it (sections as `knowledge_home.SECTIONS` names them)
```

The existing code must not show any of the five rules. So: no scheduled job exists yet, nothing reads a setting,
nothing writes a blob, nothing reads more than one record, and the manifest has no `[jobs]` and no `[config]` table.

**The stand-in SDK** (`harbor/`): just enough for the product and its tests to run, and lenient. Its module
docstring says: "A local stand-in for the Harbor SDK. It keeps data in memory and does not enforce the platform's
rules." It offers:

- `harbor.records.get(sku)`, `put(item)`, `list()` (every record), `scan(cursor=None)` (returns `(records,
  next_cursor)`, a page of at most 500, `next_cursor` None at the end);
- `harbor.blobs.put(name, data, keep_days=None)`, `get(name)`, `names()`;
- `harbor.config.get(key, default=None)`;
- `harbor.log.event(name, **fields)`;
- a way for tests to load records and to reset the stand-in.

No docstring or comment in it states a limit, says which call a job should use, or mentions a slot, a job table or
`max_seconds`. `harbor.local` runs actions only; asked to run a job it says the stand-in does not run jobs.

**Two knowledge-home variants** of `docs/shiploop/environment.md`. Both are kept OUTSIDE the fixture, in
`docs/experiments/platform-knowledge-20261122/harbor/knowledge/`, so that a product tree never holds both:

- `environment.card.md` (arms R, I, L, W): under `## Targets and runtimes` the production target line ends
  "Platform guide: GUIDES/platforms/harbor.md". `## Platform facts` holds only what the existing code shows. The
  fixture's own `docs/shiploop/environment.md` is a copy of this file.
- `environment.facts.md` (arm K): the target line says "Platform guide: none". `## Platform facts` holds the five
  rules, worded as in the card's entries (fact, decision, proof), as observations of this project's target.
  `make_facts_fixture.py` writes a second fixture, `test/shiploop_e2e/fixtures/harbor-stockroom-facts/`: the
  fixture with this file as its `docs/shiploop/environment.md`.

## The request

> Add a nightly low-stock report to the stockroom service. Every night at 02:00 it should produce a CSV listing
> every item whose quantity is below the low-stock threshold (10 unless configured otherwise), with the columns
> sku, name, quantity, sorted by sku. The operations team reads the report the next morning. The store holds about
> 1,200 items today.

It names no Harbor rule.

## The five rules, as the card states them

The card is `skills/shiploop/references/platforms/harbor.md` on the candidate branch only, with a row in the
"Conditional index" of `references/coding-guidance.md` ("Harbor | A Harbor app: actions, scheduled jobs, records,
blobs or settings."). It has an opening paragraph, a `## Planning` section with exactly these five entries, and a
short `## Testing` section (how to run the product's tests and an action locally; no rule of the five).

Each entry is one bullet: a bold id, the plan concerns it bears on in brackets, the fact, then "Decision:" and
"Proof:".

- **H-JOB** [switchover, config] A scheduled job exists only when `harbor.toml` declares it: a `[jobs.<name>]`
  table with `run = "<module>:<function>"`, `at = "HH:MM"` (UTC) and `max_seconds` (required, at most 300). Code
  without that table is never started. Decision: the job's name, its entry function and its time budget. Proof:
  the manifest holds the table and its `run` resolves to a function.
- **H-SLOT** [concurrency, state] Harbor can start a job twice for one scheduled time. It passes the scheduled
  time to the function as its only argument, `slot` (a string such as `2026-11-22T02:00Z`). Whatever a job writes
  must be named by its slot, so that a second start overwrites and does not duplicate. Decision: how each output is
  named. Proof: two starts with one slot leave one output; another slot leaves a second.
- **H-BLOB** [state, platform-services] A job's local disk is discarded when the job ends. Output that must outlive
  the run goes through `harbor.blobs.put(name, data, keep_days=N)`, and `keep_days` is required for a job's output.
  Decision: where the result is stored and for how many days. Proof: the result is in the blob store after the run.
- **H-SCAN** [scale, performance] `harbor.records.list()` returns the first 500 records and stops there without an
  error. Read a whole store with `harbor.records.scan(cursor)`, page after page until the cursor is None. Decision:
  which call reads the store. Proof: with more than 500 records, an item past the 500th is in the result.
- **H-CONFIG** [config] A setting is read with `harbor.config.get("<key>")` and must be declared in `harbor.toml`
  under `[config]` with its default; an undeclared key fails when the job starts. Environment variables are not
  passed to jobs. Decision: the setting's key and its default. Proof: the manifest declares the key, and changing
  its value changes the result.

## Reading a plan (rung 1 and 2): `plan_score.py`

Input: a slice's output folder. It finds the plan result the gate accepted (and the first one submitted, if they
differ) and scores each as text, every field, case-insensitive. A rule is credited when the plan commits to the
decision in the platform's own terms:

| Rule | Credited when the plan's text holds |
|---|---|
| JOB | `[jobs.` or `jobs.<word>` and also `max_seconds` |
| SLOT | the word `slot` and also one of `overwrit`, `duplicat`, `idempot`, `twice`, `one output`, `same slot` |
| BLOB | `blobs.put` or `harbor.blobs`, and also `keep_days` |
| SCAN | `records.scan` or `scan(`, or the word `scan` together with `500` |
| CONFIG | `harbor.config` or `config.get`, and also `[config]` |

Output: one JSON object a slice (`rules` credited, `score` 0 to 5, the same for the first submission, and the
matched snippets so a person can check each credit), and a table over several folders. It has unit tests on
hand-written plan texts: one that follows all five, one that follows none, one that only names the card ("follow
GUIDES/platforms/harbor.md") and must score 0, and one for each rule alone.

## Reading what the model was shown: `plan_exposure.py`

Input: a slice's output folder. For each of the five entries, were all of its lines (20 characters or more,
spaces collapsed) in what the model was given between the plan packet's printing and the plan's submission? What
the model was given is read as `docs/experiments/spec-elaboration-20261120/guides_test.py` reads it
(`model_outputs`: the Codex session record, or Claude's tool results) and the times come from the run's
`trace.jsonl`, as `packet_shown.py` in that folder does. It also reports: whether the plan packet as printed held
each entry (and whether before or after the line "Result template:"), every command or file read that names
`platforms/harbor.md` or `environment.md` with its time, and the count of characters of the card's text given in all.

## Grading a product (rung 3): `harbor_grade.py`

Input: a delivered product tree. It never changes the tree: it copies it to a scratch folder first.

It runs the job under a **strict** Harbor: a private module that replaces `harbor` at import, with the same calls
and the platform's rules enforced: `records.list()` returns the first 500 only; `blobs.put` without `keep_days`
raises; `config.get` of a key the manifest does not declare raises; the environment holds no variable beyond PATH,
HOME and the like; the working directory is a scratch folder that is emptied after the start. The store holds
1,200 items, 30 of them below 10, 12 of those 30 past the 500th record, and 9 below 3.

The job to start is found in this order: the `run` of any `[jobs.*]` table; else the `run` of any manifest table
outside `[actions]`; else the first function in the product's package whose name holds `low_stock` or `report`.
It is called with the slot as its one argument when it takes one, with none otherwise. The report is the blob (or,
failing that, a file left in the working directory, noted as such) whose content is CSV with the header
`sku,name,quantity`.

| Check | Passes when |
|---|---|
| P-JOB | `harbor.toml` has a `[jobs.*]` table whose `run` resolves to a function, with `at = "02:00"` and an integer `max_seconds` of at most 300 |
| P-RUN | a start with one slot ends without an exception under the strict Harbor |
| P-BLOB | after that start the report is in the blob store, put with `keep_days` |
| P-SCAN | the report holds all 30 low-stock rows, sorted by sku, with the right three columns |
| P-SLOT | a second start with the same slot leaves one report; a start with another slot leaves two |
| P-CONFIG | `[config]` declares a threshold key with default 10, and a start with that key set to 3 reports 9 rows |
| G-TESTS | the product's own tests pass (`python3 -m unittest discover`), and `tests/test_actions.py` is still there and passes |

Output: JSON with each check's verdict and the reason for a failure, the platform score (P checks passed, 0 to
6) and how the job was found.

**Calibration, before any model run.** A reference product (`reference/`, the fixture plus a correct job) passes
all seven. Six defective copies each break one rule and are caught by the check for that rule: no `max_seconds`
(P-JOB); output named without the slot (P-SLOT); a local file and no blob (P-BLOB); `blobs.put` without `keep_days`
(P-RUN and P-BLOB); `records.list()` (P-SCAN); the threshold written into the code (P-CONFIG). The untouched
fixture scores 0 of 6 with G-TESTS passing. `calibrate.py` builds the copies, grades them and prints the table; a
check that does not catch its defect, or that fails on the reference, is a fault in the bench to fix before use.

## The arms

One candidate build of ShipLoop serves every arm; one module constant, changed by an overlay file, chooses the route.

| Arm | Route | What differs |
|---|---|---|
| R | released | nothing: the card exists and the knowledge home names it |
| I | printed | at `plan`, the named card's `## Planning` entries are printed by value in the instructions, beside the duty that asks for the concern rows and before "Result template:", with one sentence: use them in the decisions and proving checks this plan already owes |
| L | look-up | at the same place, one line that names the card's file and its `## Planning` section (heading and line range) to read before the concern rows, and the same sentence |
| W | whole | at the same place, the whole card by value and the same sentence (for the size rung) |
| K | project knowledge | the released build; the fixture uses `environment.facts.md` |

The route changes nothing else: no new result field, no new refusal, no other stage's text.
