---
bump: patch
---
The run-file catalog (`references/state-files.md`) now lists every file ShipLoop writes into a run directory: the run lock and the save journal `transaction.md`, `context-index.md`, `reference.md`, `scratch/`, `backchain/`, the run baseline pair, the Improve bind result and notes files, and the send-back marker. Its `timeline.json`, `callback-attempts` and lint pending-journal rows now state the real file formats.
