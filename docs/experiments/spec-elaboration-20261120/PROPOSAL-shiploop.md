# A proposal for ShipLoop from the asking-later test

Status: a proposal, written 2026-11-22 for the owner to decide. It changes nothing under `skills/`. The session that
wrote it (Spec elaboration) does not change ShipLoop; a change would be made by the session that owns the list.
The account behind it is the journal's section 61 (`docs/spec-elaboration-journal.md`).

**Since this was written (2026-11-22, 07:20).** Two things changed, and the text below is left as it was.

- The owner asked "What should we do?" instead of answering the question below. The small test does not need his
  ruling, because its judges can apply the list's own rule, so it is registered and run under his standing approval
  for experiments: the journal's section 62. "A yes starts one small test" is overtaken.
- The Ratchet session's confirmation round added two Sol deliveries. One of them tells what going back loses and
  one does not. So on Sol a row tells it in 1 delivery of 8 (1 row of 29), not in none of 6; on Sonnet in 2 of 2.

## In short

- **ShipLoop should tell the requester what it decided for them, right after the specification. That is already
  built and accepted.** It is the Ratchet session's list `defaults`, shown in the report as "Decided for you". Its
  merge commit records the owner's "Yes, merge it" of 2026-11-22, 05:46, and it is in a confirmation round before
  its release.
- **The asking-later test supports that list where it is and as it is.** It gives no reason to build anything
  more in order to find the decision that matters.
- **Read together, the two studies show one gap.** On Sol the list leaves out the decision that a separate reader
  ranks first. Whether that matters is one question only the owner can answer. A yes starts one small test. A no
  ends this study's part.

## What the test says about the accepted list

| The list as accepted | What the test measured | So |
|---|---|---|
| Made at the end of the spec stage | The decision that mattered is on 9 of 9 lists right after the specification, 9 of 9 once the plan and test cases are written, and 9 of 9 after the tests ran | Keep it there. Asking later does not find it more often. |
| Rows carry no rank, and nobody is asked to pick one | Asked to put the costliest wrong guess first, a separate session puts that decision second to fifth after the specification (in the first three in 6 of 9) and first in none of 27 lists | Never cut the display to a top one or three. |
| It holds what the specification decided, not what the build decided later | Lists made after the tests are longer (a median of 28 decisions against 23), and what is added exists only once there is code | A second list at the end could only add to the report. Not proposed: nothing shows anyone needs it. |

## The gap the two studies show together

Two terms. The *author* is the session that writes the specification and fills `defaults`. A *separate reader* is
a new session that sees only the request, the repository and the work's records.

- **What a separate reader puts first.** In the asking-later test a separate reader was asked for every decision
  the work took on the requester's behalf. All 27 lists begin with the same one: what going back to the old
  release loses. Release 1.4.0 still reads the data file, its next save drops the due times, and an operator must
  have kept a copy.
- **What the author's list holds.** In the Ratchet session's six Sol deliveries with the list, the specification
  speaks of keeping or losing the due times on the way back in five, and none of the 21 rows of `defaults` tells
  it. Its own blind reader names it as missed in those five, once as "the largest unmentioned consequence for the
  requester". Its one Sonnet delivery does tell it, as row 5 of 6.
- **So:** on Sol the author's list tells the start-up choice 6 times of 6 (its strict reader scores 2 of them a
  full yes and 4 "partly") and leaves out, 6 times of 6, the decision a separate reader puts first. The
  instruction already covers such a line: it asks for each acceptance line "that states what the request does
  not, and that a person who uses or runs the product would notice (what they see, a step they must take,
  something refused)", and keeping a copy before going back is a step they must take. So this is about what the
  author picks, not about the wording.

What this does not show. The two counts come from different deliveries under different instructions. No held-out
check judges that loss. The owner has not said whether it matters. The Ratchet session checked the counts on its
own files by a word search and they stand; three more deliveries are running in its confirmation round, and it
will record whether a row names the way back in each.

## The one question for the owner

> In the due-times case, going back to release 1.4.0 loses the due times at its next save unless an operator kept
> a copy. Should ShipLoop have told you that before it built?

- **Yes:** the author's list misses something you wanted to hear. The small test below is registered and run.
- **No:** the short list is enough on this case, and this study adds nothing to build or to test.

## The test that would follow a yes (not started, not registered)

- **Question.** Shown the rows the requester already gets, does a separate reader add decisions worth telling,
  without flooding the list?
- **Material.** The Ratchet session's nine kept deliveries with the list, read only, each at its accepted
  specification: six of due times on Sol, one on Sonnet, and two of `hello`, a request that leaves little open.
- **The ask.** One new Sol session at medium for each delivery, three times: these rows are what the requester has
  been told; list what else the work decided for them, costliest first.
- **Read, by rules fixed before any session runs.** Is the loss on going back among the first three added on the
  six Sol deliveries? Is it left out on the Sonnet delivery, where a row already tells it? How many of the first
  five added are real open points, by two judges who do not know the delivery? How many does `hello` get?
- **Size.** 27 sessions on subscription, about one to two minutes each going by the 27 already run, and about a
  dollar of judging.
- **If it earns its place,** what would be put to the list's owner is one separate session after the
  specification is accepted, and at most five added rows under "Decided for you", marked as a second reader's.
  Nothing waits and nothing is asked. The Ratchet session has said that would be a change of its own, after the
  release the owner asked for.

## The half that changes what gets built

Telling is not correcting. The Ratchet session measured both halves:

- With the requester's answer written into the specification, builds pass 8 of 8 held-out checks three times,
  against 3 of 8 three times without it.
- Sent as a plain note right after the specification, the same answer changed the build in 2 runs of 4, was
  confirmed in 1 and was ignored in 1.

A route of ShipLoop's own for that answer is already the owner's open decision with the Ratchet session. The
asking-later test adds one fact to it: the decision is visible right after the specification, so the answer can be
taken before anything is built.

## Limits

- One case (due times), one decision known to matter, and one driver for the lists (Sol at medium).
- All three deliveries read in the asking-later test had guessed wrong. A delivery that guessed right was not read.
- The chain from the list to the answer to a corrected build has not been run end to end in ShipLoop.
- Nothing shows that a requester reads the list. The Ratchet session's count of choices no row has (four or five
  a specification) is an upper limit: its reader cannot see the starting product and counts some of its
  conventions.

## Evidence

- The asking-later test: the journal's sections 59 (the design, fixed first) and 60 (the result); the files under
  `evidence/ask-later/` in this folder; the tool `ask_later.py`.
- The list: `docs/experiments/ratchet-pilot-20261120/shiploop-defaults/DESIGN.md` with its `evidence/` folder, on
  the Ratchet session's branch `shiploop-defaults-2c3d50` until its release reaches `main`.
- The comparison of the two: `evidence/ask-later/cross-reading-defaults.txt`, written by `cross_reading.py`, which
  prints every line it matched; and the journal's section 61.
