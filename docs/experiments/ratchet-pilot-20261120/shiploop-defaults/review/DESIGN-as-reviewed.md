# A candidate ShipLoop change: the specification lists the answers it chose for the requester, and ShipLoop shows them

Status: a candidate on branch `shiploop-defaults-2c3d50`. Not on `main`, not released. The owner decides whether it is
accepted. Written 2026-11-21, 22:40, before any code of the candidate.

Owner's word, 2026-11-21, to "Do you want me to draft the first of the six suggested ShipLoop changes here (showing the
plan's decisions to the requester), as a candidate branch that stays out of main until you accept it?": "Yes".

## 1. What is wrong today, measured

A request never says everything. Where it does not say, a ShipLoop run chooses. Today the choice is written as if it
had been asked for, and nobody is told.

- **Eleven archived full deliveries** of the E2E case `ticket-due-times` on Codex with `gpt-6.2-sol` at medium
  (ShipLoop 2.4.0 and 2.4.1; the SDLC structure study's runs, read and not touched). The request says the tickets
  already in the data file get due times, and does not say who or what puts them there, nor what the service does
  when it is started switched on while some ticket has none. Four runs chose "an operator runs a separate command, and
  the service refuses to start until every ticket has a due time"; seven chose "the service fills them in itself when
  it starts". The owner ruled the second right (SDLC structure study, round 9). The held-out check `migrate` fails in
  exactly the four and passes in exactly the seven.
- In **all eleven** the choice stands in `docs/shiploop/spec.md` as a plain line of a requirement ("With a data file,
  enabled startup rejects missing deadlines until backfill finishes."). In **none** does the spec result, the
  specification or the final report say it was a choice, or name the other answer. The report's "Open items" has no
  row on it in any of the eleven (nine have no row at all).
  Evidence: `evidence/baseline-11.txt`, written by `baseline_read.py`.
- The stage's text already asks for a record. `STAGE_RULES`: "take the default that best fits the request and the
  recorded knowledge, record it as an assumption (the alternatives and why this one) in the result's `assumptions`
  list where its template has one, else in its summary". The spec template has no such list, so the rule sends a
  default to a free-text summary of two or three sentences. Spec duty 9 says the same ("record a default for an open
  choice as an assumption in `summary`").

What earlier work in this repository says about the remedy:

- A question put to a session as a bare instruction is not answered; the same question with a section or a field to
  fill is (this pilot's F39 and F43; amendments 12 to 14 of the journal).
- The owner's pattern for a judgement a script cannot make (commit `f9d1f4cf`, the spec's `primary` list): "a required
  result field per decision, a placeholder that states the bar, a CLI gate on the field, and downstream packets quoting
  it by value."
- A session cannot choose which one question matters (0 of 18, F50), but with a place to mark them it marks every
  point a request leaves out (12 of 12, F48). So: ask for the list, never for the one.
- Given the requester's answer, a run carries it through every stage to the build: 8 of 8 held-out checks three times
  against 3 of 8 three times (F52).
- A final report shows what a stage wrote down and only that (spec-elaboration journal, section 26: Sol's reports
  list a median of 0 assumptions, Sonnet's 6).
- Telling the spec stage to *take* a default for "a limit the request leaves to choice" made it invent limits nobody
  asked for (spec-elaboration, arm K: a waitlist cap three times in four). This candidate must not do that: it asks
  the stage to record what it chose, not to choose more.
- On Codex the part of a packet after "Result template:" often does not reach the model (median 15% at the spec
  stage); the instructions do (97%). A duty belongs in the instructions (F51).

## 2. The change

**One new list on the spec stage's done result, `defaults`,** checked by the script and shown to the requester.
Nothing pauses, nothing waits, no limit is added, and no test or build rule changes.

### 2.1 The list

`defaults` is a list; `[]` says the specification chose nothing of its own. Each entry is five texts:

| field | what it holds |
| --- | --- |
| `requirement` | the R-<n> in `KNOWLEDGE/spec.md` that carries the answer |
| `question` | what the request leaves open, as the requester would ask it |
| `default` | the answer this specification chose |
| `alternative` | the nearest other answer a requester might want, and what it would change for the people who use or run the product |
| `why` | what in the request or the product points to this one |

No `id` (the displays number the rows), no class, no rank: a session cannot say which entry matters (F50), so it is
not asked.

### 2.2 The instruction (spec duty 4 gains these sentences; duty 9's clause points here)

> Where the request does not say and you chose the answer yourself (how the product behaves, a rule or a limit it
> applies, a step someone who runs it must take), write the answer in its R-<n>, with its basis given as a default of
> this date and not the request, and list it in `defaults`: the `requirement` that carries it, the `question` the
> request leaves open, the `default` you chose, the nearest `alternative` a requester might want with what it would
> change for the people who use or run the product, and `why` this one. List only an answer a requester could
> reasonably want otherwise: what the request, the product's documents or its code settle is not a default. Add
> nothing in order to list it; `[]` when you chose none. ShipLoop shows the list to the requester, who changes any
> with one sentence, so write it in their words.

The sentence about an open gap in the same duty ("Mark each unresolved prerequisite or user decision as an open gap
under its R-<n>") stays as it is. The new text is conditioned on the stage having chosen; it does not tell it to
choose where it would have left a gap.

### 2.3 The gate (at `complete` and `check`, and when a stage review's result is imported)

Refused, each with a message that says what the list is and what to write: a done spec result without the list; a
list that is not a list; an entry without exactly the five texts; an empty text; a template placeholder left in; a
`requirement` that is not one R-<n>; a `requirement` with no current entry in `KNOWLEDGE/spec.md`.

Not judged, because a script cannot: whether an entry is true, whether the list is complete, whether `[]` is honest.
The stored shape is loose (a list of text mappings) so every saved run loads; a run saved before the list says "not
recorded", never "none".

### 2.4 Where the requester sees it

1. **The packet of the stage after the spec** (`test-strategy`) carries one required block: the rows, the line "tell
   the user these with this stage's progress line", and the command that carries the user's sentence to the run as an
   owner note. Nothing waits for an answer. This is the attended surface: the host session already tells the user one
   line per stage.
2. **The done packet** (what the host relays when the run ends): a count, the rows, and how to change one.
3. **The report** (`report.html`): a section "Decided for you" directly after "Original request", before the table of
   transitions: the rows as a table, or "none", or "not recorded".

A sentence from the requester travels by what ShipLoop already has: `shiploop note` during the run (the next packet
quotes it; the planning stages have their recorded correction route), a new run on the delivered project afterwards.

### 2.5 Not built, and why

- No pause or question to the requester (owner's rule: unattended by default, no clear pause).
- No change to what tests assert about a default. This pilot's builds did better where an open point was pinned in no
  test, but that is a product trade-off of its own and the owner's to decide.
- No list at the plan, step-plan or implement stages. A builder's own choices (the implement step's `decisions` note)
  stay in the step's commit message. If this list earns its place, gathering those is the next step.
- No change to the trace page, the status narrative or the progress page.
- `STAGE_RULES` (printed in every packet) is not edited: only the spec stage's own duty names the list, so no other
  stage's packet changes.

## 3. How it will be judged (registered before any run of the candidate)

Runs: real deliveries through the E2E harness, case `ticket-due-times`, Codex, `gpt-6.2-sol`, medium, built from the
candidate's commit. A stand-in requester watches each run: when the spec's accepted result lists an entry about the
start-up point, it sends the owner's ruling as one owner note, in the words of
`program/replies.json` ("Nobody prepares the data file by hand. When the service starts with DUE_TIMES set to on, it
gives every ticket that has no due time one, from that ticket's own creation time and priority, saves the file, and
then serves. It never refuses to start because due times are missing."). When no entry is about the point it sends
nothing. Whether an entry is about the point is decided by a rule fixed here: its `question`, `default` or
`alternative` names starting the service (start, boot, launch, restart) and names the tickets that have no due time
yet (backfill, migrate, existing or older tickets, missing, without). I read every list afterwards and report any
case where the rule and a reader disagree.

Wave 1 is three runs. The decision after it:

| reading | rule |
| --- | --- |
| R1, the choice is on record | the start-up point is an entry of `defaults` in at least 2 of 3 runs (archive: on record as a choice in 0 of 11). Below that, the wording is wrong: stop, reword, and say so. |
| R2, nothing invented | each entry is read against the request and the product: a real open point, a point the request or product settles, or behaviour nobody asked for. Any run with behaviour nobody asked for that the archive's specifications do not have is reported and counts against the wording. Also reported: entries per run, requirement count and words of the specification against the archive (4 to 6 requirements, 340 to 498 words). |
| R3, the product | the held-out check `migrate` in runs where the note was sent. Archive: 7 of 11 pass with no requester. Three runs cannot show a rate; what is read is whether a run that had chosen "refuse" delivers "fills in at start" after the note. A run that lists the point, gets the note and still fails `migrate` is a failure of the mechanism and is reported as one. |
| R4, the surfaces | the report has the section in its place, the done packet has the lines, the `test-strategy` packet printed the block, the note was delivered. Each is read from the run's own files. |
| R5, the cost | gate refusals on `defaults` before acceptance, session time and tokens against the archive (855 to 1,130 seconds). |

If wave 1 meets R1 and shows no invention, a second wave of three follows, and two runs on the Claude host with
Sonnet at medium, to see the list does not misbehave on the other driver. If it does not, the result is recorded as
it is and the wording is revisited once; a second miss ends the attempt.

What this cannot show: that a real requester reads the list; that the model lists every choice that matters (only
this one point has a ruling to check against); anything about other cases.
