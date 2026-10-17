---
bump: minor
---
The bundled Until Loop runtime prints lean returns for a run started with `--receipt`. `start` and `done` print `status`, `state_file`, `receipt`, a short `instruction`, `conditions.exit`, `report_fields` (each report field with its allowed values), `next_argv`, `done_argv` and `verify_script`; the receipt keeps the full packet (work, both conditions, context, progress, the last report and its handoff, `report_schema`), and `next` prints it whole for recovery. On a live-shaped ShipLoop step-plan loop the start return falls from 11,515 to 2,733 characters, a non-terminal `done` from 22,709 to 2,778 and a terminal `done` from 13,447 to 1,580. A run without a receipt still prints the full packet every time, and the Python `start` and `done` functions still return it.
