# Context-reset production validation summary

> Historical experiment: ShipLoop no longer contains model transports or the
> `drive` controller. The former Claude probe is retired. These observations
> describe that older implementation and are not current execution instructions.

This document records what the bounded local host trials established without
publishing raw host output. It is a findings summary, not a public execution
receipt and not a claim about a hosted or deployed application.

## Local observations

Each host trial used a harmless seeded canary, a retained-session recall, a
reopened/resumed retained-session recall, a fresh-session recall using the same
question, and a benign local Python continuation command. Local trials observed
the following for Codex, Grok, and Claude:

| Behavior | Result |
| --- | --- |
| Retained and resumed sessions recalled the canary | Passed locally |
| Fresh sessions returned `UNKNOWN` to the identical recall question | Passed locally |
| The fresh session ran the continuation command | Passed locally |

The Codex fresh prompt repeated the recall question and appended a continuation
command. Claude and Grok used byte-identical prompts for isolated recall.

The Grok trial needed isolated native ACP operation with `--no-leader` and
`GROK_MEMORY=0`; otherwise cross-session memory could contaminate the fresh
context condition. This is a child-process control only. It does not delete
stored memory, bypass permissions, or change global host configuration.

The historical source included a small Claude local probe, now removed with
the model adapters. Its generated result, other live receipts, host identifiers,
and raw transcripts are intentionally absent from this source extraction.

## What this does not establish

- No full live multi-item ShipLoop run crossed an actual Improve campaign and
  then delivered a product outcome.
- The checks do not establish lower cost, lower subscription usage, or a
  universal token reduction.
- Native host permissions, configured tools, and available integrations remain
  host-specific. The Grok and Claude adapters do not claim a Codex-equivalent
  writable-root or network sandbox.

A preliminary local Codex comparison reported 28.31% lower continuation input in
one synthetic fresh-context comparison, but uncached input increased. Treat that as a
reason to run paired measurements, not as a savings claim.

## Hermetic companion coverage

The former controller and adapter tests covered protocol wiring and recovery
without model calls. The current aggregate instead verifies that ShipLoop has no
model-launching path. Those checks do not replace the historical observations
above or establish current live product behavior.
