# Environment lifecycle — W1 draft persistence assessment

Current controlled-fixture observation, obtained with `DEVELOPER_DIR=/Library/Developer/CommandLineTools python3 -B product/scripts/probe_environment.py`: target `fieldnotes-embedded-v2`; `client_persistent_storage=unavailable`; `draft_api=false`; `server_runtime=false`; `websocket=false`; `script_src` and `style_src` are `self`; observation SHA-256 `40a3900ae08cf109734f411f62c8a89dbd5fae84c5f04d127ff000ea3038c878`. This is not a live deployment receipt.

The selected W1 outcome needs either a target-supported account-scoped durable client store plus authoritative identity/logout lifecycle signal, or a same-origin account-scoped draft API with equivalent read/write/delete and lifecycle guarantees. Neither is evidenced. The current account selector is not an authenticated-subject/logout contract. No remote target read, deployment, configuration change, or write authority was exercised or granted.

Earliest gate: W1 baseline/implementation. Recheck condition: an owner supplies a concrete target-compatible persistence and identity/logout contract, then re-run the current/revised probe and the planned target browser checks. Detail, file plan, and local baseline observations: `../../evidence/step-plan-w1.md`.
