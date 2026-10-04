---
bump: patch
---
The protocol states the limit of `retry` with `native_status: "unavailable"`: it keeps the step's accepted result correct, but relies on the lost worker having ended with its host session. A step sharing a checkout, port, database or other external resource with its replacement waits for proof that the old worker stopped.
