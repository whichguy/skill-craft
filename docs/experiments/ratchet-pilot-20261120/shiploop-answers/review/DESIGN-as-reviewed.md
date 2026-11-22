# A candidate ShipLoop change: the requester's answer to a default reaches the specification before the plan is fixed

Status: a design for review, written 2026-11-22 before any code. A candidate branch; not for `main` until the owner
accepts it.

Owner's word, 2026-11-22 07:37, to "Release the list now, and then build the answer route as a candidate?": "Yes,
both". The list is released (ShipLoop 2.6.0). This is the second half.

## 1. What is wrong today, measured

ShipLoop 2.6.0 makes the spec stage record each choice it made where the request does not say (`defaults`), and
shows the list to the requester. It does nothing with what the requester then says.

- With the requester's answer written into the specification, builds pass 8 of 8 held-out checks three times of
  three; without it, 3 of 8 three times (the Ratchet program, on the `ticket-due-times` case).
- A one-sentence answer sent as a plain owner note right after the spec changed the build in 2 deliveries of 4, was
  confirmed in 1, and was ignored in 1, where the script recorded the note as delivered all the same.
- With nobody answering, the wrong choice stands: 4 of 8 Sol deliveries with the list chose the answer the owner
  ruled wrong, as 5 of 12 did before the list, and each fails the same five held-out checks.
- The mechanisms as they are (`route-map.md`, facts read from the code): an owner note is free text bound to no
  requirement; it is "delivered" when the step that showed it is accepted, whatever the step did. No gate reads what
  changed. Planning stages after the spec may reword a requirement (only a dropped ID is refused); `implement` and
  `document` may only add marked lines. No route reruns the spec for a note. The plan binds the build when the
  `plan` result is accepted.

So the cheapest place where an answer can take effect with a script check is between the acceptance of the spec
and the acceptance of the plan: the stages `test-strategy` and `plan`, and their reviews.

## 2. The change

One sentence: the requester can answer a listed default by its number; if the answer arrives before the plan is
accepted, the stage then current must rewrite that requirement and prove it to the script; an answer that arrives
later is said to be held for a new run, in the packet, the done packet and the report.

ShipLoop stays unattended: nothing asks, nothing waits, no stage pauses, no loop gets a limit. An answer is
something the requester may send, never something a run needs.

### 2.1 Recording an answer

`shiploop note --run-dir RUN --default N --text "<the requester's words>"` (or `--file`). It is an owner note with
one more field, so the one inbox, its quoting, its hold and its delivery record stay as they are:

    {id: "N3", written_at, text, default: {row: 3, requirement: "R-3", question, recorded, entry_sha256}}

`row` is the number the list shows; `requirement`, `question` and `recorded` (the default as the spec recorded it)
are copied from that row, so the note stays readable if a later spec result changes the list; `entry_sha256` is the
hash of the requirement's entry in `KNOWLEDGE/spec.md`, whitespace-normalised, when the note is written.

Refused, with nothing written: no accepted spec result with a `defaults` list yet; N outside the list; and the
refusals a note already has (empty or too long text, a run that is done or halted). For a finished run the refusal
adds the sentence the done packet already gives: start a new run on the project with a sentence that says what you
want instead.

### 2.2 In time, or late

An answer is **in time** when the stage that is current at the next accepting callback is `test-strategy` or `plan`
(their stage results, or the import of their reviews). It is **late** in every other stage. This is decided when
the callback is evaluated, not when the note is written, so a note written while the plan's result is being
accepted cannot be half applied.

### 2.3 What the stage is told (a required block, right after the owner notes, only when an answer is open)

For in-time answers, in `test-strategy` and `plan`:

    Answers from the requester to defaults (each is the user's decision; apply it before this stage's own work):
      N3 answers default 3 (R-3: <question>). The spec chose: <recorded>. The requester's words are note N3 above.
    Rewrite each named requirement's entry in KNOWLEDGE/spec.md so that its acceptance lines state what the
    requester wants and nothing the answer replaces. Keep the ID and say in the entry that the requester decided it.
    This stage's output follows the rewritten entry. In this result return `answers`: one {note, requirement, line}
    for each, `line` being one acceptance line of the rewritten entry, word for word. ShipLoop refuses done while a
    named entry reads as it did when the answer arrived.

In `plan` one more line: the test strategy was accepted before this answer; where it describes the old behaviour,
the rewritten requirement governs, and the plan's items say so.

For late answers, in whatever stage is current:

      N4 answers default 3 (R-3) and arrived after the plan was accepted. ShipLoop applies no answer after that
      point in this run: leave the requirement as it is and say in the summary that N4 is held for a new run.

### 2.4 The gate (at `check` and `complete`, when a review's result is imported, and before an earlier check's yes is reused: the three places the `defaults` gate already sits)

In `test-strategy` and `plan`, for each open answer-note, done is refused unless:

1. the result's `answers` has exactly one item for the note, naming the requirement the note is bound to;
2. that requirement's entry exists, is not retired, and its normalised text differs from `entry_sha256`;
3. `line` is, word for word after whitespace is normalised, a line of that entry.

Each refusal names the note, the requirement and what is missing. `answers` is a done-only result key, allowed only
at those two stages, stored loose (any list of text maps loads) so a saved run always loads; the exact checks are
at the gates. No new state key: the note's delivery record already names the action that took it, and that
action's accepted result holds the `answers` item or does not.

Nothing is checked for a late answer. Nothing stops a later stage from rewording the requirement on its own, as
today.

### 2.5 Where the requester sees it

- The list's block in the `test-strategy` packet gains one sentence for the host: if the user answers a default,
  record it at once with the note command and `--default`; this stage or the plan stage then applies it, and a
  later answer is held for a new run.
- The done packet and the report mark each answered row: `answered by the requester ("<words>"); applied at plan:
  <line>`, or `answered by the requester after the plan was accepted ("<words>"); not applied in this run`. A late
  answer also gets the sentence for a new run. The mark "changed after the spec stage" stays for a row a stage
  rewrote with no answer.
- A review of `test-strategy` or `plan` is told of the list of open answers the way it is told of the `defaults`
  list for a spec review.

### 2.6 Not built, and why

- **Applying a late answer in the same run.** It needs a route that reopens planning or adds a corrective work
  item with a requirement change in it; the first is the reconcile route, which exists only for a stopped plan
  review, and the second would change what `add-work` may carry. No delivery has shown either is needed; the
  measured effect is for answers before the build.
- **Starting the new run for a late answer.** The sentence is printed; chaining runs is a product decision.
- **Judging whether the rewritten entry says what the requester asked.** A script cannot. The gate proves that the
  entry changed and that the result quotes a line of it; the stage's review and the report, which shows the words
  and the line side by side, are what a wrong rewrite meets.
- **A way to confirm a default.** An answer that agrees with the default makes the stage say in the entry that the
  requester decided it, which changes the text and passes the gate.

## 3. Known ways round (for the loophole table, in the same commit)

| Way round | What happens |
| --- | --- |
| The entry is edited cosmetically and keeps the old behaviour; `line` quotes it | Passes. The review and the report are the only checks |
| The named requirement is rewritten and another requirement still states the old behaviour | Passes. Not looked for |
| The host never records the user's reply as an answer | Nothing happens; the reply is whatever the host makes of it |
| An answer arrives one stage too late | Not applied; said so in three places |

## 4. How it will be judged (to be fixed in a commit before any delivery runs)

Tests with no model, through the real CLI: an in-time answer is shown, refused unanswered, refused when the entry
is unchanged, refused when `line` is not in the entry, accepted when all three hold, at `test-strategy` and at
`plan` and through a review's import; a late answer is shown as late and gates nothing; the note refusals; the done
packet and the report for both kinds; a saved run without answers loads; packet sizes stay inside their budgets.

Real deliveries, read against the released product's own rate. On `ticket-due-times` with Sol at medium, about four
deliveries in ten choose the start-up answer the owner ruled wrong and then fail five of eight held-out checks
(9 of 20 on file fail them). A stand-in requester reads the list the `test-strategy` packet printed and always
answers the start-up row with the owner's ruling through `note --default`, whatever the spec chose. Proposed
readings, each stated before the runs:

- R1. In every delivery the answer was applied in time: the note is delivered by `test-strategy` or `plan`, and
  that result holds its `answers` item. (The gate makes this true or stops the stage; a delivery stopped there
  counts against the change.)
- R2. Of six Sol deliveries, at least five pass all eight held-out checks. Without answers 11 of 20 pass, so the
  chance of five or more of six is about one in six: six is a first rung and not a proof, and a second six would
  follow a pass.
- R3. No delivery passes the eight checks while its requirement still states the refusal (read by hand).
- Described: one delivery on Sonnet; one delivery whose answer is sent late on purpose (after the plan), to see
  the three places say so and the build stay as planned; the spec stage's and the planning stages' times.

## 5. Open questions for the review

1. Is `test-strategy` and `plan` the right window, or should it stop at `test-strategy` so that no accepted
   planning result is ever older than the requirement it plans for?
2. Is reusing the owner note (one inbox, a `--default` field) sounder than a verb and record of its own?
3. Does the gate's third check (`line` is a line of the entry) earn its place, or is "the entry changed" enough?
4. Is "late answers are not applied and the stage is told to leave the requirement alone" right, given nothing
   enforces the leaving alone?
5. What in the engine would this break that the map does not show (state validation on load, the review import,
   the hold of a callback for a note that arrives after its packet printed, packet head budgets)?
