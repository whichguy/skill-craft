# Durable ShipLoop locator

Repository: /private/var/folders/_n/cth41tgs171367b_gghs0kgm0000gn/T/shiploop-entry-recovery-0xu0me0t/trial/fixture
CLI: /Users/dadleet/src/skill-craft-driver-entry/skills/shiploop/scripts/shiploop
Run directory: /private/var/folders/_n/cth41tgs171367b_gghs0kgm0000gn/T/shiploop-entry-recovery-0xu0me0t/trial/run
Authoritative state: /private/var/folders/_n/cth41tgs171367b_gghs0kgm0000gn/T/shiploop-entry-recovery-0xu0me0t/trial/run/state.md

Recover the current task from the saved run:

```sh
python3 /Users/dadleet/src/skill-craft-driver-entry/skills/shiploop/scripts/shiploop next --run-dir=/private/var/folders/_n/cth41tgs171367b_gghs0kgm0000gn/T/shiploop-entry-recovery-0xu0me0t/trial/run
```

This locator records no graph position. Execute only the recovered current action, reconcile actual effects, submit its current callback, then stop.
