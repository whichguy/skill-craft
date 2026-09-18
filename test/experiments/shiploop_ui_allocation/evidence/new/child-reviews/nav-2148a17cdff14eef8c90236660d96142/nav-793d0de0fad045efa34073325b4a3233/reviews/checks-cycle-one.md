# Specification Improve cycle-one checks

| Check | Result | Raw evidence |
| --- | --- | --- |
| Fresh seven-message history | Single reachable fixture commit read successfully. | `history-cycle-one.stdout.txt` |
| Current working-tree inventory | Only `.shiploop-improve/` is untracked. | `status-cycle-one.stdout.txt` |
| Source-contract integrity | README, platform, API, and host observation digests match the current fixture set. | `source-digests-cycle-one.stdout.txt` |
| Controlled target observation | Probe reports `archive-static-v1`, self-only script/style, no server runtime/WebSocket, and storage `not_assessed`. | `probe-cycle-one.stdout.txt` |
| Local runtime availability | Node `v25.9.0` and Python `3.14.7` exist locally; no dependency or harness was selected. | `node-cycle-one.stdout.txt`, `python-cycle-one.stdout.txt` |
| Candidate structure and source locators | R-01..R-09, AC-01..AC-09, the non-durable requirements-home limitation, authority limitation, API/consumer limits, parent route, active packet/state, and absent product requirements home all pass the corrected probe. | `locator-cycle-one-corrected.stdout.txt` |
| First locator-probe attempt | Failed only because its phrase matcher looked for a wording that the candidate did not use; the candidate itself still contained the correct authority statement. The raw failed output and corrected rerun are both retained. | `locator-cycle-one.stdout.txt`, `locator-cycle-one-corrected.stdout.txt` |

No executable client behavior exists yet, so these checks do not claim browser, live API, deployed target, or consumer validation.
