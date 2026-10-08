---
bump: patch
---
ShipLoop now creates the run's `notes/` directory beside `scratch/` when it prints a packet, so the pass log every packet names can be written (and an `evidence_refs` entry for it resolved) without a `mkdir` first. The log itself is still the model's to create.
