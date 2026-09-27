---
bump: minor
---
Every action now carries its exact `call`: the argv plus an input whose
`"<...>"` placeholders the caller fills. The settle call pre-fills the receipt
digest, and the claim and start responses carry the follow-up calls. A
completed run returns no `next_argv`.

`init` accepts an optional `capacity`. The claim action then offers only free
slots, and an over-capacity claim fails with `ECAPACITY`.

Planning-blocked steps are no longer offered for claim, and a claim for one is
refused. Cleaning up a rejected attempt's workspace or evidence no longer
breaks the run. Concurrent writers wait briefly for the lock instead of failing
with `ELOCKED`.
