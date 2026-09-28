---
bump: minor
---
The long-lived `docs/shiploop/spec.md` is now the delivered baseline: a run writes only its change spec (`features/<slug>/spec.md`: add/modify/retire/preserve per requirement) during planning, and merges it into the long-lived spec at `release-verify`, which checks every added, modified and retired ID. `prepare` no longer requires the long-lived spec; a blank repository's first run creates it through the merge, and a paused or failed run leaves it unchanged.
