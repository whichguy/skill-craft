---
bump: patch
---
- The exporter reads a Backchain 0.7.0 planning run (`run/backchain/<action>/run`: `run.json`, `loop/receipt.json`, `evidence.json`, `cycles/NN/`) as the stage's loop, with one pass per recorded cycle. Before, it found no loop there and filed the stage as "graph check only".
