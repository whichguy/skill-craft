---
name: prompt-on-change
description: >-
  Detect URL/HTML/JSON field changes and promote a prompt event with previous
  and new state. Use when polling a page or API, watching a CSS/JSONPath/regex
  field, firing on change, numeric or date range (inside/outside), regex
  match/non-match, empty, or compound delta (any/all/when empty). Script-backed
  detect engine; calendar actions optional.
version: 1.8.0
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

Config-driven URL monitor. A deterministic engine fetches, extracts, and
compares state. It stays silent when nothing matched. On a match it writes
evidence JSON (previous value, new value, full state delta) and prints
`LLM_ESCALATION: <path>` so any harness can promote a prompt event.

**Package leaf:** `prompt-on-change`  
**Primary interface:** YAML config + `scripts/detect_engine.py`  
**Honesty:** installing this skill is discovery. Runtime is the CLI (and
whatever scheduler the host uses). Calendar patch/delete needs a `gws` binary
and is optional.

## Triggers

- Poll an HTML field or JSON path and notify only when it changes
- Promote an agent prompt with previous → new state
- Fire on a numeric range, a date range (inside or outside), a regex match or
  non-match, a numeric delta range, empty / became-empty, or a compound delta
  (`any` / `all` / `empty` / `became_empty` / `date_in` / `not_matches`)
- Watch flight status, prices, package tracking, status pages, advisories

## Not for

- Continuous LLM polling of an unchanged page (the engine is the cheap layer)
- Host-only “open Claude and…” as the sole procedure
- Claiming four-host install as proven runtime on every host

## Procedure

1. Author a YAML config (see `references/config-schema.md` and
   `configs/examples/price-range-delta.yaml` /
   `configs/examples/date-regex-delta.yaml`).
2. Validate: `python3 scripts/detect_engine.py --config PATH --validate`
3. Dry-run: `python3 scripts/detect_engine.py --config PATH --dry-run`
4. Live run (or `scripts/detect_runner.sh` over a config directory).
5. **No-change contract:** exit 0 and empty stdout. That is the documented
   empty outcome, not silent success.
6. **Match contract:** write evidence JSON and print `LLM_ESCALATION: <abs-path>`.
7. Load `prompts/escalation.prompt.md`, claim the file first, reason over
   previous/new/delta, and **never re-act** on the world.

Package root is the directory that contains this `SKILL.md`. Runtime state
defaults to `$POC_STATE_DIR` or `$XDG_STATE_HOME/prompt-on-change` (fallback
`~/.local/state/prompt-on-change`). Do not hardcode `/opt/data`.

Host matrix: `references/host-matrix.md`.

## CLI

```sh
python3 scripts/detect_engine.py --config configs/examples/price-range-delta.yaml --validate
python3 scripts/detect_engine.py --config configs/examples/price-range-delta.yaml --dry-run
python3 scripts/detect_engine.py --config configs/examples/price-range-delta.yaml
bash scripts/detect_runner.sh --self-check
```

Env: `SKILL_ROOT`, `POC_STATE_DIR`, `DETECT_DIR`, `DETECT_ENGINE_HEALTH_DIR`,
`DETECT_ENGINE_ESCALATION_DIR`, `DETECT_ENGINE_LOG_FILE`, `PYTHON`, `ENGINE`.

Hermes adapter (existing 5m runner): set those env vars to the live config and
state dirs. Do not clobber `~/.hermes/skills/productivity/prompt-on-change`.

## Promote conditions (prev → new)

Evidence always includes `previous_value`, `new_value`, `previous_state`,
`current_state`, `delta.fields`, and `changed_fields`. Custom prompts may use
`{{ previous_value }}`, `{{ new_value }}`, `{{ delta }}`, `{{ changed_fields }}`.

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
| `delta: { any, all, empty, nonempty, became_empty, became_nonempty, range, date_in, date_out, matches, not_matches }` | AND of those clauses |

Groups still support `any:` / `all:` over named conditions. Nested `and` / `or`
/ `not` / `unless` are unchanged. Full schema: `references/config-schema.md`.
