Write the spec **this once** from `{{PROMPT_PATH}}` (and the bound repo if present). This is not c-plan. Do not follow a DevLoop overlay.

Write:

- `{{SPEC_MD}}` with a labeled line `done_sentence: <exact sentence>`
- `{{SPEC_JSON}}` with keys `done_sentence` (string), `checkable` (bool), optional `verify_hint`, optional `ask_user`

Derive a machine-checkable `done_sentence`. Do not invent pytest, a path, or a cwd.

If not checkable: set `checkable` false, set `ask_user` to the question, then `/shiploop complete --blocked --resume-to validate-spec --reason <ask_user>`.
