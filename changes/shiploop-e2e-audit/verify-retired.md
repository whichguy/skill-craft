---
bump: patch
---
The mock DAG replay walks ShipLoop's 23 stages: verify is retired, and an item's carry-forward follows its last document stage.
The behaviour capture keeps verify among its stage names only for captures of runs recorded before it retired.
