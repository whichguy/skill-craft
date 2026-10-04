---
bump: minor
---
`retry` accepts a worker whose host session ended: `confirmed_stopped: false` with `native_status: "unavailable"`, for when the worker's handle can no longer be looked up and nobody can prove it stopped. The retry is recorded as unconfirmed; the old attempt's work is kept and its late report is refused, so the fresh attempt is safe.
