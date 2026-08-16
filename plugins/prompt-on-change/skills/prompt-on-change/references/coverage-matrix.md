# prompt-on-change — coverage matrix

Inventory of the **public 2.2.0 surface**: CLI verbs, tokens, HTTP pull
shapes, and delivery decisions. Engine operator units stay in
`tests/test_detect_engine.py` (~382 cases) and are not re-listed here.

Owner scripts live under repo `test/`. Gate `always` runs from
`test/prompt-on-change.test.sh` with `POC_E2E=0 POC_GROK_LIVE=0
POC_LIVE_SITE=0` (no public web, no live Grok, no live TUI).

Live token contract: [e2e-success.md](e2e-success.md).

## CLI verbs

| Surface | Owner | Gate | Tokens / assert | Waiver |
|---------|-------|------|-----------------|--------|
| `validate --config` | lifecycle + hermetic examples | always | rc=0 on shipped examples | |
| `validate` reject GET+form, HEAD+body, PUT, form+json | lifecycle | always | rc≠0 | |
| `run` seed / silent / promote | lifecycle, e2e offline | always | `SEED_OK:`, empty stdout, `LLM_ESCALATION:` | |
| `run --dry-run` | lifecycle | always | no state write, no `PROMPT_ISSUED` | |
| `run --no-issue` | lifecycle | always | `LLM_ESCALATION:` only | |
| `run --no-issue --to` | delivery | always | no `PROMPT_RUN` / no grok argv | |
| `run --to grok:<uuid>` this-poll bind | delivery, e2e | always / `POC_E2E=1` | two `LLM_ESCALATION:` + one `PROMPT_ISSUED:` + `PROMPT_RUN:` | |
| `explain` seed / would_escalate / fire_once | lifecycle | always | JSON `seed`, `would_escalate`, `gated_by` | |
| `status` pending / processed | lifecycle | always | `pending:`, `processed:`, `CLAIM_EMPTY` | |
| `claim` / empty claim | lifecycle + hermetic | always | `CLAIMED:`, `CLAIM_EMPTY`, `[SILENT]` | |
| `CLAIM_SKIP` | lifecycle | always | `CLAIM_SKIP:` when `mv` cannot reserve | |
| `issue` / empty issue | lifecycle | always | `PROMPT_ISSUED:`, `CLAIM_EMPTY` | |
| `issue --last` | lifecycle | always | replay “already in processed” | |
| `issue --last --to` | delivery, e2e `lifecycle-to` | always / `POC_E2E=1` | `PROMPT_RESUME:` + `event.prompt.md` | |
| `issue --exec` (no `--to`) | grok-native | `POC_GROK_LIVE=1` | `PROMPT_RUN:`, outcome fence | hermetic SKIP |
| `self-check` | hermetic | always | `example validate: ok` | |
| `bootstrap` refuse venv in skill | lifecycle | always | rc≠0, “refuse venv” | full pip install not in CI |
| usage: no args / unknown cmd / missing `--config` | lifecycle | always | exit 64 | |

## HTTP pull

| Surface | Owner | Gate | Tokens / assert | Waiver |
|---------|-------|------|-----------------|--------|
| GET local HTML extract | lifecycle, e2e offline | always | prev/new + `http` envelope | |
| POST `form:` through wrapper | lifecycle | always | seed → form echo change → one escalation | |
| POST `json:` / `body:` + Content-Type | `test_detect_engine.py` | always | Source validate + fetch units | no second wrapper fixture |
| HEAD / GET+body / PUT/PATCH reject | lifecycle validate + engine | always | rc≠0 | |
| `{{env:VAR}}` missing fail-closed | engine | always | unit | |
| time.is GET | live-site, e2e `external-multi` | `POC_LIVE_SITE=1` / `POC_E2E=1` | clock promote | hermetic SKIP |

## Delivery (`--to grok:<uuid>`)

| Surface | Owner | Gate | Tokens / assert | Waiver |
|---------|-------|------|-----------------|--------|
| parse `grok:<uuid>` / unknown host | delivery | always | helper + wrapper | |
| `cursor:<uuid>` unknown host | delivery | always | rc≠0 | |
| missing `--to` value | delivery | always | exit 64 | |
| uppercase UUID lowercased | delivery | always | dest stamp / `--session-id` | |
| new session: `--session-id`, dontAsk, no yolo, sandbox | delivery | always | argv | |
| resume idle local dir | delivery, e2e | always / `POC_E2E=1` | `PROMPT_RESUME:`, event prompt | |
| refuse live / stale+alive pid | delivery | always | issue file, no grok | |
| `--assume-idle` | delivery | always | resume despite live | |
| `--force-new` | delivery | always | new uuid, not resume | |
| `--cwd` disagrees with session dir | delivery | always | refuse, no grok argv | |
| two `condition_matched` → one issue | delivery, e2e | always | both ids, no leak | |
| fetch_failure-only: no `--to` | delivery | always | legacy `--yolo` exec | |
| `--to` without `--evidence` | delivery | always | rc≠0 | |
| per-target flock | delivery | always | second wait | |
| engine rc≠0 skips `--to` | delivery | always | missing config | |
| live `--to` new + resume | e2e `local-to` | `POC_E2E=1` | `PROMPT_RUN` then `PROMPT_RESUME` | hermetic SKIP |
| live time.is `all:` of four + `--to` | e2e `external-multi` | `POC_E2E=1` | 4 esc, 1 issue, run+resume | hermetic SKIP |
| chained wrapper verbs + `--to` | e2e `lifecycle-to` | `POC_E2E=1` | explain→seed→silent→`--to`→fire_once→status→claim→`--last --to` | hermetic SKIP |
| live TUI concurrent `--resume` | — | — | — | waived: refuse-if-live is the safety story; fake-bin covers live pid |
| Cursor / Claude / Hermes inject | — | — | — | waived: Grok `--to` only |
| Cursor Automations as scheduler | — | — | — | waived: forbidden |
| calendar / `gws` through wrapper | engine units only | always | — | leftover; not the 2.2.0 product |

## Polls

| Surface | Owner | Gate | Tokens / assert | Waiver |
|---------|-------|------|-----------------|--------|
| miss / hit / hold / leave / re-hit | poll-effectiveness | always | two escalations across sequence | optional `--exec` |
