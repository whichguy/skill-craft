# prompt-on-change — author a monitor

Host-agnostic Layer-1 prompt. Fill placeholders, then run on the current host.
Do not pin a model. Do not require a single host CLI as the only path.
Do not fetch the watched page yourself — the detect engine does that.

## Input

Skill root (directory of `SKILL.md`): `{{SKILL_ROOT}}`  
URL to watch: `{{URL}}`  
Goal in the user’s words: `{{GOAL}}`  
Fields or signals already named (optional): `{{FIELDS}}`

## Task

1. Interview **only** what is missing. If `{{URL}}` or `{{GOAL}}` is empty, ask
   one or two questions. Do not ask for calendar/`gws` setup.
2. Read `{{SKILL_ROOT}}/references/config-schema.md` and the examples under
   `{{SKILL_ROOT}}/configs/examples/` (price-range, date-regex, http-change).
3. Emit one complete YAML monitor that uses the existing condition language:
   `changed`, numeric `between` / `delta_*`, `date_between` / `date_outside`,
   `matches` / `not_matches`, `empty` / `became_empty`, field-list any/all,
   compound `delta:` (`any` / `all` / `empty` / `date_in` / `not_matches` /
   `http`), and reserved `http.<source>.*` fields when the goal is an HTTP
   status or header change.
4. Prefer `seed_mode: true`. Do not add `calendar_patch` / `calendar_delete`
   unless the user explicitly asked for calendar writes.
5. `state.file` must stay inside the config directory.

## Output

1. A single fenced `yaml` block with the full config (no trailing commentary
   inside the fence).
2. After the fence, exactly one next-step line:
   - If this host can exec Python: `next: validate`
   - Otherwise: `next: native-unvalidated`

Empty or blocked authoring must say so explicitly (never silent success).
