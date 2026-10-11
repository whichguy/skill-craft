---
version: 0.1.0
---
Separate complete task decomposition from worker concurrency. Default new batches
to at most five concurrent workers, honor an explicit prompt-supplied cap, and
refill free slots with fresh agents until the full required queue is accepted.
Preserve unresolved outcomes and verify aggregate membership against the complete
goal. Add reusable queue tests for bounded refill, full coverage, terminal retry,
and uncertain-launch reservations; keep Dispatcher as the only queue authority.
Consume the planned backlog incrementally, preparing only yielded items and
starting a fresh agent for each, with no persistent worker pool or batch barrier.
Clarify bytecode-safe report-only inspection after a live trial exposed an
ignored cache file despite clean Git status; retain full fixture-file auditing.
