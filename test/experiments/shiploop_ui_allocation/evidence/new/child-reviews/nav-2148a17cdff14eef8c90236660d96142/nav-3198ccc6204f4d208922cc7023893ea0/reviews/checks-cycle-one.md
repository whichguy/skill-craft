# Intake Improve — cycle one checks

Candidate scope: `<study>/new/run/notes/intake.md` and its parent result. The only product-tree write at this point is the authorized `.shiploop-improve/` review-record tree.

| Command / check | Observed result | Limit |
| --- | --- | --- |
| `DEVELOPER_DIR=/Library/Developer/CommandLineTools PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe_environment.py` | Returned `archive-static-v1`, self-only scripts/styles, no server runtime, no WebSocket, `draft_api: false`, and `client_persistent_storage: not_assessed`; observation SHA-256 `4234ca2a0b1535bab72aa9388b97f8d6140d7363ac0215a30858c77c415d2699`. | Controlled fixture evidence only; it does not prove a live deployment. |
| `python3 -m json.tool host-observation.json` | Parsed the controlled host observation as JSON. | Structural parse only. |
| Read-only Git status/history and SHA-256 command from the product root | `main` remains at `ec3243d658e24304b306749bc361869154fc4660`; product-source digests match intake. `?? .shiploop-improve/` is the intentional child evidence tree. | Does not test a future UI. |
| Locator regular-file checks | Intake note, parent result, parent return note, and child raw packet receipt existed as non-symlink regular files. | Existence does not prove semantic correctness. |
| First packet JSON parse attempt after the locator loop | The shell reported `zsh:2: command not found: python3`; no packet conclusion was drawn from that attempt. | This was an invocation-environment failure, not a source failure. |
| `/opt/homebrew/opt/python@3.14/bin/python3.14 -m json.tool .../packet.json` | Passed (`packet-json-valid`). | Verifies only JSON shape/parsing of the preserved start packet. |

No UI, browser, build, or test harness exists in the fixture, so no product behavior test was claimed or substituted for one.
