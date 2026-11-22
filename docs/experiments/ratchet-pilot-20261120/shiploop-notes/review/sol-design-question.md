Review a design before any code is written. Be adversarial and concrete; read the code in this folder rather than trusting the design's description of it.

THE FOLDER (your working directory) holds:
- `DESIGN.md`: the design under review: "an owner note is settled by a row in a result, never by a print". Sections 1 (what is wrong, measured), 2 (the change), 3 (known ways round), 4 (how it will be judged).
- `maps/mechanism-map-notes.md` and `maps/mechanism-map.md`: two maps of how the engine behaves today, written by reading it. Treat them as claims to verify, not as facts.
- `evidence/`: what real deliveries showed (`earlier-plain-notes.md`, `given-round3.txt`, `given-round1.txt`, and `answers-DESIGN.md`, the design and results of an earlier candidate whose tests led here; its sections 7 to 11 hold the measurements the new design cites).
- `engine/`: the engine as released, the code the design would change (`skills/shiploop/scripts/*.py`), with `references/` (the texts stages are pointed at) and `tests/` (the suites that pin today's behaviour of owner notes, packets and gates).

BACKGROUND IN FIVE LINES. ShipLoop is a script-driven delivery harness: a model session does one stage at a time, reads a "packet" the script prints, and calls back with `check` (a dry run of the gates) and `complete` (submit the stage's result). The script owns navigation and gates; the model does one step. It runs unattended: nothing may ask, wait or pause, and no loop gets a limit. The run owner can write an "owner note" into a run in flight. Today a note counts as delivered when a step is accepted whose packet text held it; real deliveries showed that on one host the model is never given the note's words, and that nobody is told.

WHAT I WANT FROM YOU.
1. A verdict in one line: "Build as designed", "Change first" or "Do not build", then your reasons.
2. Findings, most serious first, numbered. For each: what is wrong or risky, the code that shows it (file and symbol), and what you would do instead. Say for each whether you verified it in the code here or are inferring.
3. Answers to these specific questions:
   a. Section 2.5 removes the hold, the record of what a print showed, and the delivery record. Find every reader of them (engine, trace, references, tests) and say what breaks or must change with them. Is anything they did still needed, for example on a host that does read packets whole?
   b. Section 2.4 puts one validator at three places. Check each against the code: `_evaluate`, the reuse of an earlier check's yes in `dispatch`, and the import of a review. What about a producer's replay of its parked result, a paused or blocked producer that resumes, and a note written between the read and the save (the note command takes no lock)?
   c. Section 2.2 reads where a note stands from the current accepted results. Walk through reconcile, an inner send-back, an outer send-back, `add-work` (which reopens outer stages already accepted) and a `blocked` result that reissues the stage: after each, which rows still count, which notes are owed again, and by which stage? Is there a case where a settled note is silently reopened in a way that stalls a run, or an open note is never owed by anyone?
   d. The carry table of 2.2: for each stage, is the target right given what that stage and its target can actually change in the code today (the living spec, the queue)? What about stages a run leaves out or the script records without a packet, `prepare`, the first stage of a run, and the last?
   e. Section 2.3: are the `item` checks at `plan` and `carry-forward` right, and is the rule for a queue replacement that drops a note's item enough? How do they meet a review's `final_result` that lists the whole queue, and `primary.check_queue`?
   f. The new result key: what exactly must be registered so that a result with `notes` is accepted, a non-done result with it is refused, stored results reload on the next command, and a run with no notes is byte-for-byte unchanged in what it prints and stores? Name the functions.
   g. The refusal text of 2.4: given that a host may pass its model only the first sentence of a refused command (see `evidence/earlier-plain-notes.md`, delivery d4), will a model be able to act? What is printed on stdout and what on stderr for `check` and `complete` today, and should that change?
   h. Does anything in the design make a stage ask, wait or pause, or let a run stall for good? What does a model that keeps submitting without the row meet?
   i. Packet room: which packets are close to a size limit, which tier the notes block must be in, and whether quoting carried notes again at the settling stage fits.
   j. Section 4: is the plan able to show what it claims? What is missing, what would you cut, and what result would make you say the design is wrong?
   k. Is there a smaller change that fixes what section 1 measured: for example keeping the hold and adding only the row, or only closing the `check` and `next` paths? Say what each smaller change would leave broken.
4. A list of what you could not verify from this folder.

Write for a reader who will decide what to change in the design from your answer alone. No preamble.
