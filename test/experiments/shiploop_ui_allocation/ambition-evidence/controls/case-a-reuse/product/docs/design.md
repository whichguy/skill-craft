# Accepted UI and previous environment
## UI identity
Keep the native account selector, note list, stable textarea editor, save/cancel/back controls; preserve focus, keyboard/touch behavior, narrow layout, reading position and draft text. Navy #15324f, amber #c08722, white cards, system body and Georgia display type. No approved framework migration. Local in-memory editing is separate from server-confirmed notes.
## Previous environment assumption
The earlier fieldnotes-embedded-v1 target allowed account-scoped persistent browser storage. This historical observation supported a proposed reload recovery design but no draft persistence is implemented. Revalidate when target or policy changes. Current target observation is obtained with scripts/probe_environment.py.
