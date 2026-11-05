---
bump: minor
---

# Move the ownership model where a clear cannot lose it, and shrink the card

## The measurement

One archived run (`archive-live2`, 31 packets, 455,885 bytes of packets):

| Content | Before | Where it lived |
| --- | --- | --- |
| Ownership model (one node, one owner, one callback) | 14,606 B card section | **card only** |
| Card section overlap with any packet | 1% | - |
| Card section overlap with `RUN/reference.md` | 0% | - |

After a compaction the packet reprints and the card does not. The ownership model appeared in neither any packet nor
`RUN/reference.md`, so it survived a clear only if the model still remembered the card — which the card itself tells it
not to re-read.

## What changed

**`reference#owner`** (`shiploop_reference.py`): a new `SECTIONS` entry carrying the model, and the recovery block now
says to read `#rules` and `#owner` after a clear or compaction. `RUN/reference.md` grows about 700 B and is reachable
through the command every packet already prints.

**The card** (`SKILL.md`): the 14,606 B `## Follow the current packet` section becomes 2,143 B of binding summary plus the
pointer, keeping the stopping rule intact. Card: **30,109 -> 17,645 B**; headroom against the 30,500 budget
**383 -> 12,855 B**.

**One dead function**: `shiploop_context_index.stages_named` had no caller; removed with its now-unused `Iterable` import.

**One deferred import**: `shiploop_trace._plan` read `navigator.graph`, a three-line wrapper that only returns
`shiploop_prompts.PRELUDE/INNER/OUTER`. It now reads those directly, so that call no longer needs the navigator module.

## What was tried and rejected

**Printing the rules once and pointing at `reference#rules` after.** Measured 294 B saved per packet (6,174 B over the
archived run's 21 later packets), and it would have brought `test-spec` back under the 16,000 B print limit.

It does not hold up:

- `test/shiploop_e2e/packet_obligations.json` row `rules` records **six anchors** that must appear in a producer
  packet's printed text, with `surface: "head"`. Compressing the wording to keep all six cut the saving to **79 B**;
  dropping any of them broke the ledger, `shiploop-stage-spec`'s stuck-rule count, and `shiploop-run-review`'s recovery
  predicate, which requires the unattended sentence verbatim.
- A 79 B saving against a 45 B margin means the next rule added silently pushes `test-spec` back over the limit, with
  nothing to notice it. That is a worse outcome than leaving the rules repeated.

So the rules stay as they are. The repetition is real (11.7 KB per run) but it is not redundancy: every packet must
carry all six obligations, and the tests that say so are correct.

## What this does not do

It does not reduce the 17 of 31 packets that exceed the print limit, and it does not finish the import coupling — the
remaining deferred imports need `validate`, `_validate_current_state` and `lint_view` out of navigator, which is a
larger refactor than this change should carry.
