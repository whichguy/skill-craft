# prompt-on-change config schema

YAML consumed by `scripts/detect_engine.py`. This is the portable extract of
the original Hermes skill card, plus range / compound-delta promotion.

## Skeleton

```yaml
name: "My Monitor"
enabled: true
seed_mode: true          # first poll observes only
expires: "2026-12-31T00:00:00-08:00"
sources:
  - id: page
    url: "https://example.com"
    extract:
      - id: price
        type: css
        selector: ".price"
        transform: text
conditions:
  - id: price_changed
    field: price
    op: changed
groups:
  - name: notify
    any: [price_changed]
llm_escalation:
  trigger_groups: [notify]
  fire_once: true
  prompt: |
    {{ config_name }}: {{ condition_id }}
    {{ previous_value }} → {{ new_value }}
    Delta: {{ delta }}
state:
  file: "state/my_monitor.json"
  initial: {price: ""}
```

`state.file` must stay inside the config directory.

## Extraction types

| Type | Required | Notes |
|------|----------|--------|
| `jsonpath` | `path` | JSON body |
| `jsonpath_from_html` | `path` | JSON-LD `<script>` tags |
| `css` | `selector`, `transform` | `text`, `text\|upper`, `attr:href` |
| `regex` | `pattern` | optional `group` |
| `header` | `name` | header or `status_code` |

## Operators

| Operator | Required | Meaning |
|----------|----------|---------|
| `changed` | field | differs from previous state (or `baseline`) |
| `eq` / `ne` / `contains` | field + `value` | string compare |
| `exists` | field | not None, not whitespace-only |
| `empty` | field | None, whitespace, or empty collection |
| `became_empty` | field | previous nonempty, now empty |
| `became_nonempty` | field | previous empty, now nonempty |
| `gt` `gte` `lt` `lte` | field + `value` | numeric compare of **current** value |
| `between` | field + `min` + `max` | inclusive numeric band on **current** value |
| `date_between` | field + `min` + `max` | inclusive date/datetime window on **current** value |
| `date_outside` | field + `min` + `max` | current value strictly outside that same window |
| `delta_gt` `delta_gte` `delta_lt` `delta_lte` | field + `value` | signed `(new - prev)` vs threshold |
| `delta_between` | field + `min` + `max` | inclusive band on `(new - prev)` |
| `time_diff_gt` / `time_diff_lt` | field + `value` + `compared_to` | absolute minutes |
| `time_shift_gt` / `time_shift_lt` | field + `value` + `compared_to` | signed minutes |
| `matches` | field + `value` | regex **search** hits (input capped) |
| `not_matches` | field + `value` | regex search does **not** hit (empty counts as no-hit) |
| `any_changed` / `all_changed` | `fields` | compound change list |
| `any_empty` / `all_empty` | `fields` | current emptiness |
| `any_became_empty` / `all_became_empty` | `fields` | emptiness transitions |
| `any_became_nonempty` / `all_became_nonempty` | `fields` | appearance transitions |

`between` / `delta_between` swap bounds if `min > max`. Non-numeric operands
do not match (not a crash). Unavailable sources are **indeterminate**.

`date_between` / `date_outside` parse ISO datetimes plus date-only
(`YYYY-MM-DD`, `MM/DD/YYYY`) and common display dates (`Aug 15, 2026`).
Date-only `min` is start of that day; date-only `max` is end of that day.
Naive bounds inherit the actual value's timezone. Unparseable dates do not
match. `matches` / `not_matches` use Python `re.search` on a length-capped
input; invalid patterns fail closed (no promote).

## Compound `delta:` block

AND of the clauses you set. Use this when the promote rule is “any of these
fields moved, and that one became empty, and price dropped by $5–$50”:

```yaml
- id: meaningful
  delta:
    any: [status, gate]
    all: []                 # omit if unused
    empty: []               # currently empty
    nonempty: []
    became_empty: [headline]
    became_nonempty: []
    range: {field: price, min: -50, max: -5}
    date_in: {field: dep_time, min: "2026-08-01", max: "2026-08-31"}
    date_out: {field: expires, min: "2026-01-01", max: "2026-12-31"}
    matches: {field: status, pattern: "Delayed|Cancelled"}
    not_matches: {field: status, pattern: "On time"}
```

`delta.any` is OR across that list. `delta.all` / `empty` / `became_*` are AND
across their lists. `delta.range` is a numeric `(new-prev)` band. `delta.date_in`
/ `date_out` are the same windows as `date_between` / `date_outside`.
`delta.matches` / `not_matches` take `field` plus `pattern` (or `value`).

Groups:

```yaml
groups:
  - name: critical
    any: [cond_a, cond_b]   # XOR with all — both is a validation error
    actions: []             # optional calendar_patch / calendar_delete names
```

Nested `and` / `or` / `not` / `unless` / `for` / `refire_after` / `seed_mode`
behave as in the original engine. Nesting cap is 32.

## Evidence (prompt event)

On match the engine writes JSON under `DETECT_ENGINE_ESCALATION_DIR` and prints
`LLM_ESCALATION: <path>`. Payload always includes:

- `previous_value` / `new_value` / `numeric_delta` (leaf) or field maps (compound)
- `previous_state` / `current_state`
- `delta.fields.<name>.{previous,new,numeric_delta,became_empty,became_nonempty}`
- `changed_fields`
- `prompt` (rendered)

No-change: exit 0, empty stdout.

## Optional calendar

`actions.*.type`: `calendar_patch` | `calendar_delete`. Requires `gws` on
`PATH` (or `GWS_PATH`) and `GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE`. Missing
adapter fails the action closed and writes `action_failure` evidence. The
detect/escalate core does not import-crash without `gws`.

## Runtime binding

| Surface | Default |
|---------|---------|
| Package root | directory of `SKILL.md` (`SKILL_ROOT`) |
| Write-safe / state | `POC_STATE_DIR` or `$XDG_STATE_HOME/prompt-on-change` |
| Health | `DETECT_ENGINE_HEALTH_DIR` (default state dir) |
| Escalations | `DETECT_ENGINE_ESCALATION_DIR` (default `state/escalations`) |
| Config dir for runner | `DETECT_DIR` (default `$POC_STATE_DIR/configs`) |
