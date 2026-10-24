---
bump: minor
---
- **Proof:** a step's command, which ShipLoop runs at the step's done, is now `steps[].proof`; it was `check`. The
  step-plan duty, template, refusals, Step block and references say `proof`.
- **Settle:** an open item's and an unverified outcome's way to be settled is now `settle`: open `assumptions[].settle`
  and `unverified[].settle`. A probed assumption keeps `check`, because its probe is a command.
- **Check, defined:** `check` now means only a command judged by its exit code: an expectation's check, a probed
  assumption's probe, the service-is-back check and the `check` rows of the recorded commands. The glossary records
  it.
- **State version 9:** a run saved at version 8 is refused with the reason and the fresh-run route.
