---
name: prompt-on-change
description: >-
  Detect URL/HTML/JSON field changes and promote a prompt event with previous
  and new state. Use when the user says watch this page, notify me when a
  price or status changes, or poll a CSS/JSONPath/regex/HTTP field. Native
  path authors YAML in-chat; the detect CLI is optional. Fires on change,
  numeric or date range, regex match/non-match, empty, HTTP status/headers,
  or compound delta. Calendar actions optional.
version: 2.1.0
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: script-backed
  hermes:
    category: software-development
    tags:
      - portable-skill
      - multi-host
      - change-detection
      - prompt-event
---

# prompt-on-change

Config-driven URL monitor. A harness that has loaded this skill can finish
“watch this URL / tell me when it changes” in-chat. Prompts author the
config and reason over evidence. A deterministic engine (optional) fetches,
extracts, and compares state. It stays silent when nothing matched. On a
match it writes evidence JSON and prints `LLM_ESCALATION: <path>`.

**Package leaf:** `prompt-on-change`  
**Native default:** `prompts/author.prompt.md` then, on match,
`prompts/escalation.prompt.md` in the **same turn**  
**Script optional:** `scripts/prompt-on-change` (one CLI family)  
**Honesty:** installing this skill is discovery. Runtime is the CLI when
Python deps resolve. Do not claim four-host install as proven runtime.
Calendar patch/delete needs a `gws` binary and is optional.

This skill does **not** mean the host model fetches the page itself. The
cheap engine does that. If this host cannot exec Python, hand back the YAML
and label it **native-unvalidated**.

## Triggers

- Watch this page / notify me when the price or status changes
- Poll an HTML field, JSON path, regex, or HTTP status/header
- Promote a prompt event with previous → new state
- Fire on a numeric range, a date range (inside or outside), a regex match
  or non-match, HTTP status/header change, empty / became-empty, or a
  compound delta (`any` / `all` / `empty` / `date_in` / `not_matches` / `http`)
- Watch flight status, prices, package tracking, status pages, advisories

## Not for

- Continuous LLM polling of an unchanged page (the engine is the cheap layer)
- Host-only “open Claude and…” as the sole procedure
- Claiming skill-dir install as proven runtime on every host
- Cursor Automations as the documented scheduler

## Procedure

Native default (any harness, including Grok):

1. Load `prompts/author.prompt.md`. Fill `{{URL}}`, `{{GOAL}}`, `{{FIELDS}}`,
   `{{SKILL_ROOT}}` (directory of this `SKILL.md`). Interview only what is
   missing. Emit a complete YAML config.
2. If this host **cannot** exec Python: stop. Hand back the YAML labeled
   **native-unvalidated**. That is a valid native outcome.
3. If this host **can** exec: optional `prompts/schedule.prompt.md` for
   host-local repeat (cron, launchd, or “run again when I ask”).
   First successful `run` on a `seed_mode` config prints `SEED_OK: <name>`.

Script optional (same Layer-0 contracts):

4. `scripts/prompt-on-change bootstrap` once (venv under `$POC_STATE_DIR`,
   never inside the skill tree).
5. `scripts/prompt-on-change validate --config PATH` then
   `scripts/prompt-on-change run --config PATH` (add `--exec` to run the
   issued prompt on Grok in the same command).
6. **No-change contract:** exit 0 and empty stdout. That is the documented
   empty outcome, not silent success.
7. **Match contract (the product):** write evidence, print `LLM_ESCALATION:`,
   then **issue the escalation prompt** (`PROMPT_ISSUED:`). That filled
   prompt is the point of the skill. `--exec` also runs it (`PROMPT_RUN:`).
   `--no-issue` is engine-only. Do **not** wait for a Hermes cron.
   Claim first, reason over previous/new/delta/http, **never re-act**.
8. **Debug:** `explain --config PATH` prints a read-only trigger trace (why a
   poll stayed silent). `status` lists pending/processed. `issue` / `issue --exec`
   re-issue a pending or `--last` processed event without re-fetching.

Package root is the directory that contains this `SKILL.md`. Runtime state
defaults to `$POC_STATE_DIR` or `$XDG_STATE_HOME/prompt-on-change` (fallback
`~/.local/state/prompt-on-change`). Do not hardcode `/opt/data`.

Host matrix: `references/host-matrix.md`.  
Schema: `references/config-schema.md`.  
Examples: `configs/examples/price-range-delta.yaml`,
`date-regex-delta.yaml`, `http-change-events.yaml`.

## CLI

One family. Do not document `detect_engine.py` as the invoke.

```sh
scripts/prompt-on-change bootstrap
scripts/prompt-on-change validate --config configs/examples/price-range-delta.yaml
scripts/prompt-on-change run --config configs/examples/price-range-delta.yaml
scripts/prompt-on-change run --config configs/examples/price-range-delta.yaml --exec
scripts/prompt-on-change explain --config configs/examples/price-range-delta.yaml
scripts/prompt-on-change status
scripts/prompt-on-change claim
scripts/prompt-on-change issue
scripts/prompt-on-change issue --last
scripts/prompt-on-change issue --exec
scripts/prompt-on-change self-check
```

Env: `SKILL_ROOT`, `POC_STATE_DIR`, `DETECT_DIR`, `DETECT_ENGINE_HEALTH_DIR`,
`DETECT_ENGINE_ESCALATION_DIR`, `DETECT_ENGINE_LOG_FILE`, `PYTHON`, `GROK_BIN`.

Grok plugin install is a git URL or local path to `plugins/prompt-on-change`,
never `name@marketplace`. Hermes adapter: set the env vars above; do not
clobber `~/.hermes/skills/productivity/prompt-on-change`.

## Promote conditions (prev → new)

Evidence always includes `previous_value`, `new_value`, `previous_state`,
`current_state`, `delta.fields`, `changed_fields`, and `http` (per-source
status/header envelope). Custom prompts may use `{{ previous_value }}`,
`{{ new_value }}`, `{{ delta }}`, `{{ changed_fields }}`, `{{ http }}`.

| Form | When it fires |
|------|----------------|
| `op: changed` | field differs from previous state |
| `op: between` + `min`/`max` | current numeric value in inclusive range |
| `op: delta_between` + `min`/`max` | `(new - prev)` in inclusive range |
| `op: delta_gt` / `delta_lt` | signed numeric delta vs `value` |
| `op: empty` / `became_empty` / `became_nonempty` | emptiness vs previous |
| `op: date_between` / `date_outside` + `min`/`max` | current date inside or outside inclusive range |
| `op: matches` / `not_matches` + `value` | regex search hits, or does not hit |
| `op: any_changed` / `all_changed` + `fields:` | compound field list |
| `field: http.<source>.status` / `.etag` / … | reserved HTTP envelope (auto-projected) |
| `delta.http: { status_changed, status_in, status_between, headers, header_matches, header_not_matches }` | AND of HTTP envelope clauses |

Groups still support `any:` / `all:` over named conditions. Nested `and` / `or`
/ `not` / `unless` are unchanged. Full schema: `references/config-schema.md`.
