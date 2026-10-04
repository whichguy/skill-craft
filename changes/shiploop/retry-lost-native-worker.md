---
bump: minor
---
A run resumed after its host session was lost can recover its chain without a person. When a worker's handle can no longer be looked up, `chain retry` accepts `confirmed_stopped: false` with `native_status: "unavailable"`; the old workspace is kept as evidence, its late callbacks are refused, and the step gets a fresh worker. Previously the run paused to ask whether it could retry.
