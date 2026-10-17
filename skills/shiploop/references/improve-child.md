# The Improve child

Split from the ShipLoop skill card (`../SKILL.md`). Read when an Improve stage is current, and before running, recovering or restarting an Improve child.

## Running the child

Read the selected actual Improve
`SKILL.md` and let its bound Until Loop runtime own the improvement loop. For a new ephemeral
child use [Improve context ownership](improve-context.md). ShipLoop sets the child up
at the transition: it binds the recorded card, writes the four-section opening, freezes the child
contract with the binding line first in frozen `context.request`, and starts the ephemeral Until Loop with
`--receipt` set to the per-action receipt path, so a bound run already has an active
`packet.json`. The model writes no opening and starts no runtime. Under `delegation: inline`,
this parent conversation runs the selected card's ShipLoop whole-skill subcall itself in the
exact Child workspace, with no Ask Agent, native worker, extra worktree or `host-owner.md`: it
runs the improve skill on the handoff the packet names and continues the child from the receipt.
A later user decision in this conversation applies from the next review iteration; record it in
the review notes and handoff and leave the frozen launch context unchanged. PRELUDE and OUTER
Improve packets carry the same runtime lines without a context prefix. On the opt-in
`delegation: ask-agent` route, Ask Agent delegates one fresh executor with consumer-owned
workspace and in-place delivery. Either way, only the parent accepts the result and executes the
return. Use the packet's selected skill, candidate scope, commit policy and other authority
constraints, expected check state, and return route. Test creation/refinement checkpoints
include the tests, fixtures, repeatability and suite wiring in that actual Improve review. Do
not paste or imitate Improve's algorithm in ShipLoop, substitute a hand-written review loop for
the selected skill (the Improve stage's `complete` refuses a review that repeats another Improve
stage's), create a child phase graph/counter, or advance the parent while the child is active.
The runtime writes every packet to the receipt before printing it. The one temporary
`state_file` owns the child's live counters; the receipt retains its recovery command and final
review/check locators, and ShipLoop imports only a packet the runtime wrote there. Preserve
parent identity, scoped authority and return locators in frozen child `context`, and replace
`handoff` on each `done`. Execute one work iteration, submit its truthful classification and
assessments, then obey the returned instruction. A complete child deletes its state file after
the runtime has written its terminal packet to the receipt; then run the parent return and
import. Only the
ephemeral runtime is supported; a card or saved binding that names a durable Until Loop runtime
is refused.
On accepted success, run `complete --action=<improve id>` (it takes `--notes`, `--final-result`
and `--no-commit`, and no `--result`): ShipLoop imports the review's own `review-<n>.md` and
`checks.md` files and selects the next producer. A blocked or stopped child leaves the parent
incomplete; once the blocker is resolved or the user authorizes continuing, run
`improve-start --action <improve id> --restart-stopped`, which archives the stopped receipt and
its reviews and starts a new child from ShipLoop's own opening.
