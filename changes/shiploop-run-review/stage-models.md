---
bump: patch
---
A run is read with its own stage model: `runs.stageModel` is `v4` for the 17-stage inner loop (every run saved before
2026-10-10) or `v5` for the 8-stage one, and the page header says "17-stage run" or "8-stage run". A 17-stage run keeps its
own stage catalog, purposes, exit checks, reader counts, phases (Build, Prove, Integrate) and phase 3-5 expectations from the
frozen `defaults/stages-v4.json` (written to the page as `config/stages-v4` by `export.py --defaults`), its skill decision
from skill-assess and skill-validate, and test-red's "meant to fail" note; every saved run exports as it did before the
8-stage change, apart from the new field. A script-run card whose stage also has an Improve child now says so.
