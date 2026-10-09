---
bump: patch
---
The Run Review export and page now show how ShipLoop was carried in a run. A new Fidelity card reads the harness's fidelity block: how each accepted
stage's exit was evidenced (a script record, an Improve review, a cited file, notes, the model's sentence alone), what ShipLoop's script checks
recorded, the model's edits of ShipLoop's own files and its refusals by stage, each heuristic list printed with the harness's own limits text.
The exporter now scores the Improve child's packets for Goal, Done when, Checked by, Output and Recovery, shown on the Improve card next to the
run's release (Goal and Done when are printed from skill-craft 1.25.0, so an earlier release reads 0 for them by design). A run without these
records exports and renders as before, and says why they are not measured.
