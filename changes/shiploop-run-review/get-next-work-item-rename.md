---
bump: patch
---
The Run Review exporter and page follow the engine's rename of the stage `select-work` to `get-next-work-item`: the phase table, the page's stage flow, the stage catalog (`defaults/stages.json`, regenerated) and the stage card name it `get-next-work-item` ("Get next work item"). The old name stays in one alias table, in the exporter and the page, so exports of runs of ShipLoop 1.22.0 and earlier, the committed evidence and the page's database still render, in the same phase and with the same catalog entry. Merge this change together with the engine's rename: against an engine that still names the stage `select-work`, the catalog and phase-table tests fail by design.
