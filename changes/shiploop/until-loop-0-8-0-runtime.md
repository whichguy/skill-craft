---
bump: patch
---
ShipLoop accepts terminal packets from the Until Loop 0.8.0 runtime (new keys `exit_checks`, `last_check_results`,
`check_repairs`, `verify_script`) in its loop and standalone Improve checks. ShipLoop keeps its own 16 KiB contract
budget as a ShipLoop policy; the runtime itself no longer limits state size.
