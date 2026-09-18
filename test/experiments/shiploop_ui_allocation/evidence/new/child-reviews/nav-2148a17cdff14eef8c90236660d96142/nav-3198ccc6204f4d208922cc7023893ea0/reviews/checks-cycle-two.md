# Intake Improve — cycle two checks

| Command / check | Observed result | Limit |
| --- | --- | --- |
| `DEVELOPER_DIR=/Library/Developer/CommandLineTools PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/opt/python@3.14/bin/python3.14 scripts/probe_environment.py` | Same controlled target observation as cycle one, including `client_persistent_storage: not_assessed`, no server runtime, no WebSocket, and same source observation hash. | Still not a live target/deployment check. |
| Read-only Git status/history and product source hashes | `main` remains at `ec3243d658e24304b306749bc361869154fc4660`; the supplied product source digests remain unchanged. The only untracked tree is `.shiploop-improve/`. | Does not validate a future UI. |
| Targeted decision-record locator review | The correction record names all four accepted findings and preserves the controlled-fixture boundary, no persistence/retry claim, and no deployment assertion. | Confirms written planning decision, not API behavior. |
| Exact runtime interpreter JSON parse of `packet.json` | Passed (`packet-json-valid`). | Confirms preservation/parsing of the active raw callback packet only. |
| Evidence-file and symlink inspection | Cycle-one record, correction record, and packet receipt exist; `find .shiploop-improve -type l` printed no symlink. | Does not prove content semantics beyond the review. |
