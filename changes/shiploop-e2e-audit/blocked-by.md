---
bump: patch
---
Synthetic blocked results in the DAG replay now carry `blocked_by`, which
ShipLoop requires on every new blocked result.
