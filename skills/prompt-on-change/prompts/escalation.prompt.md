# prompt-on-change — escalation handler

Host-agnostic Layer-1 prompt. Fill placeholders, then run on the current host.
Do not pin a model. Do not require a single host CLI as the only path.

**Same-turn default:** if the detect CLI just printed `LLM_ESCALATION: <path>`,
claim and reason in this turn. Do not wait for a Hermes cron (or any other
host scheduler). `scripts/prompt-on-change claim` is an equivalent claim step
only when this prompt still has an unsubstituted evidence-file placeholder.

## Input

Escalation directory: `{{ESCALATION_DIR}}`  
Evidence files (reserved list when the wrapper filled this prompt):

```
{{EVIDENCE_FILES}}
```

Matches (when filled; `previous_value` / `new_value` may be null):

```json
{{MATCHES_JSON}}
```

Each evidence JSON was written by the detect engine after a condition matched
or an action/fetch failed. Layer-0 (the engine) already executed any configured
actions. This prompt is reasoning and reporting only.

## Task

**Reserved-path mode** — if `{{EVIDENCE_FILES}}` lists one or more real paths
(the placeholder was replaced): operate on **exactly those files**. Do not
scan `{{ESCALATION_DIR}}`. Do not move or claim files. Do not reply `[SILENT]`
because a directory scan was empty. Read the reserved JSON and reason.

**Native scan mode** — if `{{EVIDENCE_FILES}}` is empty or still the literal
placeholder: if there are no pending `{{ESCALATION_DIR}}/*.json` files
(ignore `.tmp`), reply with exactly `[SILENT]`. Otherwise, for each top-level
`*.json` file:

1. **Claim first**, before reading: move
   `{{ESCALATION_DIR}}/<filename>`
   to
   `{{ESCALATION_DIR}}/processed/<filename>`.
   If the move fails because the file is gone, another run already claimed it;
   skip it. A crash after the claim leaves the file in `processed/` instead of
   re-firing it.

Then, for each reserved or claimed file:

2. Read the file. Use these fields as ground truth:
   - `config_name`, `condition_id`, `match_reason`
   - `previous_value` → `new_value` (and `numeric_delta` when present; both
     may be null on multi-field / `delta` matches)
   - `previous_state` / `current_state` / `delta` / `changed_fields` / `http`
   - `actions_taken` (already done — never redo or retry them)
   - `prompt` (engine-rendered instruction)
3. Decide what the change means. Call out whether the delta is a range move,
   a date inside/outside a window, a regex match or non-match, an HTTP
   status/header change, an emptying, a compound any/all match, or a failure
   (`escalation_type`).
4. Report in plain language. Do **not** patch calendars, send mail, or mutate
   the watched system. Do **not** write a new detect config unless the user
   later asks. Do **not** fetch the watched URL.

## Output

Markdown with one section per reserved or claimed file:

- What changed (`previous` → `new`, plus numeric delta when it exists)
- Why the condition fired
- What the engine already did
- Residual risk or recommended human follow-up

If every file was skipped as already-claimed in native scan mode, reply
`[SILENT]`. Do not use `[SILENT]` in reserved-path mode.

## Outcome

After the human report (or instead of it when silent), emit **one** fenced block
whose info string is `json outcome` (not a model pin — a log contract):

```json outcome
{
  "silent": false,
  "claimed": [],
  "condition_id": "",
  "previous_value": "",
  "new_value": "",
  "residual": ""
}
```

Set `silent` true when the reply is `[SILENT]`. `claimed` is the processed
path(s) you moved or replayed; leave it empty in reserved-path mode. Leave
values empty when unknown. This fence is how hosts debug prompt execution.
