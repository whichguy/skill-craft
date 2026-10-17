---
bump: patch
---
The audit recognises a validate-existing stage that ShipLoop recorded itself by the opening words of its summary, so it
accepts both the shorter sentence the engine now writes ("... and each matched its state.") and the longer one an
earlier ShipLoop wrote ("...; validate-existing was recorded without running it. Records: <path>"); before, only the
longer one counted and a run of the newer engine was reported as missing a callback for that stage.
