# A candidate ShipLoop change: the specification records the choices it made for the requester, and ShipLoop shows them

Status: a candidate on branch `shiploop-defaults-2c3d50`. Not on `main`, not released. The owner decides whether it is
accepted.

Owner's word, 2026-11-21, to "Do you want me to draft the first of the six suggested ShipLoop changes here (showing the
plan's decisions to the requester), as a candidate branch that stays out of main until you accept it?": "Yes".

How this note came to be: sections 1 to 3 were first written at about 22:20 on 2026-11-21, before any code
(`review/DESIGN-as-reviewed.md` is that text). The latest Sol at maximum effort then reviewed it (22:34; question and
answer word for word in `review/`). Section 4 lists what the review changed. Sections 2 and 3 below are the design and
the test plan as they stand after it. No run of the candidate had been made when this was written (22:45).

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
  row on it in any of the eleven (nine have no row at all; the two rows that exist are about the old release reading
  the new file).
  Evidence: `evidence/baseline-11.txt`, written by `baseline_read.py`; `evidence/archive-sol-medium-checks.txt`.
- The stage's text already asks for a record, in prose. The packet's rule: "Unattended: take the best default and
  record it as an assumption". Its long form in the run reference: "in the result's `assumptions` list where its
  template has one, else in its summary". The spec template has no such list, so a default goes to a free-text summary
  of two or three sentences, and spec duty 9 says the same ("record a default for an open choice as an assumption in
  `summary`").

What earlier work in this repository says about the remedy:

- A question put to a session as a bare instruction is answered inside the clauses, if at all; the same question
  with a section or a field to fill gets a separate answer (this pilot's F39 and F43). The same amendments warn (F45)
  that a second place to write can draw a requirement out of its clause: each entry must name the clause that states
  it.
- The owner's pattern for a judgement a script cannot make (commit `f9d1f4cf`, the spec's `primary` list): "a required
  result field per decision, a placeholder that states the bar, a CLI gate on the field, and downstream packets quoting
  it by value."
- A session cannot choose which one question matters (0 of 18, F50), but with a place to mark them it marks every
  point a request leaves out (12 of 12, F48). So: ask for the list, never for the one.
- Given the requester's answer before the plan, a run carries it to the build: 8 of 8 held-out checks three times
  against 3 of 8 three times (F52). That was this pilot's own bench, where the answer was applied by a step that
  rewrites the specification.
- A final report shows what a stage wrote down and only that (spec-elaboration journal, section 26).
- Telling the spec stage to *take* a default for "a limit the request leaves to choice" made it invent limits nobody
  asked for (spec-elaboration, arm K: a waitlist cap three times in four). This candidate asks the stage to record
  what it chose, not to choose more.
- On Codex the part of a packet after "Result template:" often does not reach the model (median 15% at the spec
  stage); the instructions do (97%). A duty belongs in the instructions (F51).

## 2. The change

**One new list on the spec stage's done result, `defaults`,** checked by the script and shown to the requester.
Nothing pauses, nothing waits, no limit is added, and no test or build rule changes. It is disclosure: it does not
give the requester a way to change a default inside the run (section 4, change 1).

### 2.1 The list

`defaults` is a list; `[]` says no choice of the specification qualifies. Each entry is five texts:

| field | what it holds |
| --- | --- |
| `requirement` | the R-<n> in `KNOWLEDGE/spec.md` whose clause states the choice |
| `question` | what the request leaves open, as the requester would ask it |
| `default` | what happens, for the person who uses or runs the product |
| `alternative` | one workable other answer, and what it would change for that person |
| `why` | what in the request or the product points to this one, or that nothing does |

No `id` (the displays number the rows), no class, no rank: a session cannot say which entry matters (F50), so it is
not asked. Two choices under one requirement are two entries.

### 2.2 The instruction (in the spec stage's duties, where every host reads it)

Duty 4 gains, after its sentence on `primary`:

> Before you submit, compare the acceptance lines you wrote with the request and with what the product already does.
> For each choice this spec made that the request does not settle and that changes what a person who uses or runs
> the product sees or must do, say in that clause that it is a default of this date, and record it once in
> `defaults`: its `requirement` (R-<n>), the `question` the request leaves open, the `default` chosen, one workable
> `alternative` with what it would change for that person, and `why` this one. Say what happens for that person, not
> the mechanism. This list is the spec's record of the defaults it took (RULES). Add no behaviour to fill it; `[]` if
> none qualifies. ShipLoop shows the list to the requester.

Around it, so the stage has one home for a default: duty 9's clause now reads "record a default for an open choice in
`defaults` (duty 4)", and the spec template's `summary` hint says "a default goes in `defaults`". The sentence on an
open gap in duty 4, duty 5's sentence on a clause's basis and the packet's shared rule are not edited: a gap is what
still needs evidence, a prerequisite or a person; a default is a choice made, and the list is where the spec records
it. The packet of the spec's own stage review gains one line: a review that changes, adds or removes such a choice
returns the list changed to match.

### 2.3 The gate (at `check` and `complete`, when a stage review's result is imported, and before an earlier check's yes is reused)

Refused, each with a message that says what the list is and what to write: a done spec result without the list; a
list that is not a list; an entry without exactly the five texts; an empty text; one of the template's own texts left
in; a `requirement` that is not one R-<n>; a `requirement` with no current entry in `KNOWLEDGE/spec.md`.

Not judged, because a script cannot: whether an entry is true, whether its clause really states the choice, whether
the list is complete, whether `[]` is honest. The stored shape is loose (a list of text mappings) so every saved run
loads; a run saved before the list says "not recorded", never "none".

### 2.4 Where the requester sees it

1. **The packet of the stage after the spec** (`test-strategy`) carries one required block: where the list is, the
   rows (those that fit 2,400 characters; a longer list names the run file that holds every row), and one
   instruction to the host: in this stage's progress line tell the user how many there are and name each in a few
   words; ask nothing and wait for no answer.
2. **The done packet**: a count, the rows, and "To change one, start a new run on this project with a sentence that
   says what you want instead."
3. **The report** (`report.html`): a section "Decided for you" directly after "Original request", before the table of
   transitions: the rows as a table with the reason for each, the spec action that recorded them, that a later
   stage's change to a requirement is not shown there, and the same way to change one. Or "none", or "not recorded".

### 2.5 Not built, and why

- No pause or question to the requester (owner's rule: unattended by default, no clear pause).
- **No route by which a sentence from the requester changes a default inside the run.** ShipLoop has owner notes,
  and a note reaches the next packet; but no script route replaces an accepted specification and what was planned
  from it (section 4, change 1). Building one is a product decision of its own.
- No change to what tests assert about a default. This pilot's builds did better where an open point was pinned in no
  test, but that is a product trade-off and the owner's to decide.
- No list at the plan, step-plan or implement stages. The review's strongest alternative is the plan stage: where a
  specification leaves a point open, the plan is where it gets decided. In the archive the start-up choice is already
  in the specification, so the candidate starts there; reading R6 below counts what the plan and the build chose
  that the list does not have.
- No change to the trace page, the status narrative or the progress page.
- The packet's shared rules are not edited, so no other stage's packet changes.

## 3. How it will be judged (fixed before any run of the candidate)

Runs: real deliveries through the E2E harness, built from the candidate's commit, on Codex with `gpt-6.2-sol` at
medium, as the archive's were. Wave 1 is a smoke test: three deliveries of `ticket-due-times` and one of `hello`, a
request that leaves little open. Three runs can show whether the row is understood, the gate usable and the surfaces
there. They cannot show a rate, and they can all pass `migrate` by chance (about one time in four at the archive's
7 of 11).

A stand-in requester (`requester.py`) watches each due-times run. It reads the block the `test-strategy` packet
printed, which is what a requester would be shown, and not the run's state. In two of the three runs it replies: when
a printed row is about the start-up point it sends the owner's ruling as one owner note, in the words of
`program/replies.json`. That reply uses ShipLoop's existing note route, which the candidate does not change and
promises nothing about; it is sent to observe what a run does with it (O1). In the third run it sends nothing.
During a run a keyword rule decides whether a row is about the point (it names the tickets already there, or names
starting the service together with a due time that is absent). That rule is a trigger, not the score.

**The score for R1 is a reader's**, given each run's specification and printed rows and not its build or its checks,
answering one question fixed here: *does a row tell the requester who or what gives the old tickets their due times,
and what the service does when it is started switched on while some have none, and name another answer?* Yes, partly
(the choice is named without its consequence or without an alternative), or no.

| reading | rule |
| --- | --- |
| R1, the choice is on record | "yes" in at least 2 of the 3 due-times runs (archive: 0 of 11). Fewer calls for rewording or for moving the list to another stage; it is then reworded once, and a second miss ends the attempt. |
| R2, nothing invented, nothing lost | each row and each specification is read against the request and the product. Stop the wave for: behaviour nobody asked for that the archive's specifications do not have (a cap, a refusal, an operator control); a request sentence that is in a row and not in a clause; a row whose requirement does not state the choice. Reported: rows per run, requirements and words of the specification against the archive (4 to 6 requirements; 260 to 498 words, median 377). |
| R3, the empty case | the `hello` run: its list, read the same way. An invented choice there counts against the wording. |
| R4, the surfaces | from each run's own files: the `test-strategy` packet printed the block; the host's own message at that stage named the defaults (from the transcript: this is what a user would have read); the done packet has the lines; the report has the section in its place. A row shown as current that the delivered product contradicts is reported as a stale row. |
| R5, the cost | refusals of the `defaults` gate before acceptance (the harness's gate count, which gains this gate's row), and the spec stage's time and tokens against the archive's. Whole-run time is reported and not compared: one extra stage review can swamp it. |
| R6, what the list misses | the delivered product is read for choices of the same kind that no row has (how the hours are set, what an invalid setting does, an upper bound on hours), and where each was made: the specification, the plan or the build. Described, no rule. |
| O1, the reply (an observation of the existing note route, not a reading of the candidate) | for each run that got the reply: the choice before it, the stage the note reached, whether a clause of `spec.md` changed and by which stage, whether the list then contradicts the product, and all eight held-out checks. |

What this cannot show: that a real requester reads the list; that the list holds every choice that matters (one point
has a ruling to check against); anything about other cases or the other driver. If wave 1 meets R1 with no stop, a
second wave follows: three more, and two on the Claude host with Sonnet at medium, where the released stage already
records defaults in prose and the thing to watch is a default that disappears from where later stages read it.

## 4. The review, and what it changed

The latest Sol at maximum effort read sections 1 to 3 as first written, with the scripts, the baseline and the two
journals (`review/sol-design-question.md`, `review/sol-design-answer.md`). Its verdict: build, as a disclosure pilot,
with changes. Each change, and what was done:

1. **Do not promise that a sentence changes the running delivery.** As first written, the `test-strategy` block
   printed the `note` command and every surface said "one sentence changes it". The review traced the route: a note
   is quoted by the next packet and marked delivered when that step is accepted, and nothing checks that a
   requirement changed; with stage reviews on, a note can first surface a stage later; the one route that reopens
   the specification (`improve-reconcile`) needs a stopped review of the plan and exists only before the build;
   after that a send-back reaches a step plan, not the specification; and `note` refuses a finished run. I checked
   three of those in the code (the refusal of a finished run in `shiploop_owner_notes.main`; "reconcile requires
   improve-reconcile, never finish_improve" in the navigator; `spec.md` belongs to the spec stage in
   `shiploop_knowledge_home.STAGE_FILES`) and take the rest as the review's reading. Done: the command and the
   promise are gone from every surface; the report and the done packet name the route that holds, a new run; the
   module and the documents say what is not built. The reply is kept in the test plan as an observation (O1).
2. **The instruction invited invention and asked the model to guess the requester's priorities.** First wording:
   "Where the request does not say and you chose the answer yourself (how the product behaves, a rule or a limit it
   applies, a step someone who runs it must take) ... List only an answer a requester could reasonably want
   otherwise". The review: every silence sounds like work; "reasonably want otherwise" is the judgement F50 shows a
   session cannot make; and `[]` was too easy to copy. Done: the instruction is now a comparison made on the finished
   clauses, the test is an observable difference for a person who uses or runs the product, and the clause itself
   says it is a default (section 2.2). Not taken: the review's wording also replaced duty 4's sentence on gaps and
   its instruction to list the domain rules a request leaves out; those are left as released, so the candidate
   changes one thing.
3. **One home for a default.** The review found three texts sending a spec default to the summary (duty 9, the
   template's summary hint, and the long form of the shared rule). Done for the first two. The shared rule is left
   alone because every packet prints it. The review also asked that duty 5 name a dated default as a clause's basis;
   I made that edit and took it back, because `shiploop-knowledge` pins duty 5's words to an earlier decision and
   duty 4's new sentence already has the clause say it is a default of this date.
4. **A placeholder is the template's own text.** The first check refused any text wrapped in angle brackets, which
   refuses "<details> opens on a click on its <summary>". Done: a text is a placeholder when it equals one of the
   template row's texts.
5. **Every route into the gate.** The stage review's import already ran the check; the reuse of an earlier check's
   yes did not. Done, with a test of the import route, and the review's own point that a reviewer who changes a
   clause must return the rows changed too is now a line of the spec review's packet (nothing checks it beyond the
   requirement's ID). The review also notes that the shared reader of `spec.md`
   takes `### R-12draft` as R-12 and can pick a retired entry when an active one of the same ID follows it; that
   reader is shared with `primary` and is not changed here.
6. **One job for each surface.** Done in part: the `test-strategy` block no longer asks the host to relay every row,
   only to name them in its one line; the report names the spec action and says a later change is not shown. Not
   taken: the review would rename the section "Defaults recorded in the specification" and drop the rows from the
   done packet. The heading stays "Decided for you", with "Nobody was asked" in its first line, because it is the
   requester who reads it; the done packet keeps the rows because it is the last thing the host relays.
7. **The test plan.** Three runs are a smoke test (said so now); the keyword rule is a trigger and a reader scores
   R1; the stand-in reads the printed block; a request with nothing open is in wave 1; readings for a lost
   requirement, a stale row, first-pass acceptance and the spec stage's own cost were added. The review's experiment
   for a correction route (two deliveries from one accepted specification that requires the refusal, the reply sent
   to one) is not run here: it tests a route this candidate does not build.

Two figures of section 1 as first written were wrong and are corrected above: the archive's specifications run from
260 words, not 340; and the long sentence about where an assumption is recorded is the run reference's, not the
packet's.

## 5. Wave 1, and the one rewording (written 23:32, before wave 2)

Four real deliveries built from commit 31e53d718113fb517c2939ea014a6850925a8950, 23:10 to 23:29, on Codex with
`gpt-6.2-sol` at medium. Evidence: `evidence/wave-1/` (for each run the specification as the spec stage left it, the
rows its packet printed, the blind reader's answer, the product reader's answer, the stand-in's record; `wave-1.txt`
and `wave-1.json` hold every reading of `read_wave.py`).

| | d1 | d2 | d3 | h1 (hello) |
| --- | --- | --- | --- | --- |
| rows the spec recorded | 4 | 3 | 3 | 1 |
| the start-up choice it took | the service fills them in at its first start | an operator's migration command first; an enabled start refuses without it | an operator's backfill first; an enabled start fails without it | |
| a row on that choice, with another answer | row 4 | row 3 | row 3 | |
| the blind reader's score (R1) | partly | partly | partly | |
| rows the reader calls a real open point that the named clause states | 4 of 4 | 3 of 3 | 3 of 3 | |
| choices in the specification that no row has (the reader's count) | 5 | 7 | 7 | |
| the stand-in's reply | sent | sent | not sent | |
| held-out checks passed | 8 of 8 | 8 of 8 | 3 of 8 | 2 of 2 |
| seconds; the spec stage; output tokens | 759; 53; 26,968 | 868; 52; 31,570 | 1,103; 56; 39,624 | 460; 48; 15,184 |
| refusals of the `defaults` gate | 0 | 0 | 0 | 0 |

**R1, the choice is on record: not met by its rule.** The rule asked for "yes" in two of three; the reader gave
"partly" three times. In all three the start-up choice is a row with another answer beside it, where none of the
eleven archived runs says anything. But no row tells the person who runs the service what they will meet: d2's says
"Run one offline migration command, then enable the switch" and its specification says, in a line no row has, "The
enabled service refuses to start on an incomplete existing file"; and each row leans on the builder's words
("backfill", "the flag", "before listening"). The reader was told to be strict and literal; d1's row ("The first new
startup fills missing values before listening, even with the flag off") could be read as answering both halves, and
it stays "partly" because the score is the reader's.

**R2, nothing invented, nothing lost: met.** All ten rows are real open points whose clause states them; none is
settled by the request or the product, none is behaviour nobody asked for, none says what its clause does not. The
specifications as accepted have 348, 358 and 451 words and 4, 5 and 6 requirements (archive: 260 to 498; 4 to 6).

**R3, the empty case.** `hello` recorded one row: whether the greeting ends with a newline. It is a real choice
(the request says `prints exactly "Hello, world!"`) and a small one.

**R4, the surfaces.** The block was printed in four of four `test-strategy` packets and the section stands in its
place in four of four reports. What the host then told the user: in d3 its message at that stage names all three
choices as choices ("The rollout plan uses one hours setting per priority and an explicit backfill before
activation. A ticket becomes overdue immediately after its deadline. I'll verify those choices ..."); in d1 it names
the three topics; in d2 it does neither. The done packet carried the rows in four of four, and no final message
presented them as choices. One stale row: d2's row 3 says "Run one offline migration command" under "Decided" while
the delivered service fills the due times in at start (below); that run's host said so itself in its last message
("The ShipLoop report retains an early offline-migration proposal. The delivered release backfills automatically at
startup.").

**R5, the cost.** No submission was refused by the new gate in any of the four runs. The spec stage took 52 to 56
seconds (archive 17 to 61, median 43). The deliveries took 759 to 1,103 seconds (archive 820 to 1,248) and 26,968
to 39,624 output tokens (archive 27,158 to 34,865; d3 is above it, and d3 also took four more accepted steps than
the other two, 34 against 30).

**R6, what the list misses** (the product readers, `product-reader-answer.md`). In three of three, no row says what
an invalid hours setting does (the service refuses to start; each specification has the line) and no row has the
largest number of hours the product accepts (2.4, 2.5 and 2.4 billion; no specification has it, so the build chose
it, as in twelve of twelve archived Sol products). In d3 no row has the refusal to start. A list written at the
spec stage cannot hold what the build decides, and it holds a third of what the specification decides.

**O1, the reply (the existing note route, not the candidate).** The two runs that chose the answer the owner ruled
wrong are a pair. In d2 the stand-in's one sentence arrived as note N1 while `test-strategy` was current. That stage
held its callback once, then rewrote the requirement ("N1 supersedes offline preparation and startup rejection.
Updated R-3, architecture and test strategy"), the plan called the note "binding", the service was built to fill the
due times in at start, and all eight held-out checks pass. In d3 nothing was sent, the service refuses to start, and
the five checks fail that fail in the archive's four. In d1, whose choice was already the ruled one, the next stage
wrote "N1 confirmed" and the plan added to the clause that no file needs preparing. One pair is not a rate. It does
show what the review doubted: a plain owner note sent right after the specification did change the requirement and
everything built from it, on this model, with stage reviews on. What stays true from the review: nothing in the
script checks it, and the recorded row went stale.

### The one rewording (R1's rule), and two repairs wave 1 asked for

1. **The instruction.** The rows described the mechanism and left out the consequence, and they covered a third of
   the choices. Duty 4's sentences now make the unit the acceptance line and ask for the consequence:

   > Before you submit, read your acceptance lines one at a time against the request and what the product already
   > does. Each line that states what the request does not, and that a person who uses or runs the product would
   > notice (what they see, a step they must take, something refused), is a choice this spec made: say in the line
   > that it is a default of this date, and record it in `defaults`: its `requirement` (R-<n>), the `question` the
   > request leaves open, the `default` as what that person sees or must do and what happens if they do not, one
   > workable `alternative` with what it changes for them, and `why` this one. This list is the spec's record of the
   > defaults it took (RULES). Add no behaviour to fill it; `[]` if no line qualifies. The requester reads the list:
   > write it for someone who does not know the code.

   The template's `default` placeholder says the same ("what that person sees or must do, and what happens if they
   do not"). The spec packet is now 19,934 characters at the reference install, 66 under the 20,000 a Grok host
   prints whole.
2. **A row a later stage overtook is marked.** The done packet and the report now compare each row's requirement
   with the specification as the spec stage's own commit holds it. A requirement one of whose lines is gone is
   marked "changed after the spec stage"; a line added, or a heading moved a level, is not a rewrite (the build's
   stages add lines to the requirements they serve). Run over wave 1's finished runs it marks R-3 in d2 (rewritten)
   and R-3 in d1 (extended by the plan after the note), and nothing in `hello`. Where the comparison cannot be made
   the displays say so.
3. **The done packet tells the host to say it.** Its first line is now an instruction ("In your last message tell
   the user each, as a choice made for them, and that the report lists them first ..."), because the rows were
   printed there four times and relayed as choices never.

### Wave 2, fixed before it runs

Three deliveries of `ticket-due-times` and one of `hello`, same driver, built from the commit that holds this
section; the stand-in replies in two and is silent in one, as in wave 1. The same reader, the same brief, the same
"strict and literal" instruction.

| reading | rule |
| --- | --- |
| R1 again | "yes" in at least 2 of 3. Otherwise the attempt to get the row to say the consequence ends here, and the candidate is reported as it stands: the choice is shown with an alternative, in the builder's words. |
| R2 again | the same stop: any row that is behaviour nobody asked for, a request sentence out of its clause, or a row its clause does not state. A line-by-line instruction can over-list; rows the reader calls `settled` are counted against it. |
| what the rewording moved (described) | rows per run (wave 1: 4, 3, 3) and the reader's count of unlisted choices (5, 7, 7); the `hello` list (1 row). |
| the done packet (described) | whether each final message tells the user the choices as choices (wave 1: 0 of 3). |
| the mark (described) | in a run whose reply changes the requirement: the row is marked in the done packet and the report. |
