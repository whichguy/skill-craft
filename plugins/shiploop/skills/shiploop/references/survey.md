# Survey (inside validate-spec)

Survey is a **required prefix inside `validate-spec`** — not a new state-machine
phase, not a new transition edge. It runs once, before the spec is written, and
its output is `environment.md` (Look here names the absolute path).

## What to inventory

- **kind** — `greenfield` (no product tree yet) or `brownfield` (a tree already
  exists at the bound repo root).
- **augment** — `true` only when this increment adds to an existing brownfield
  tree without replacing it. Greenfield is always `augment: false`.
- **references** — concrete paths **or URLs** that inform this increment,
  each with a one-line `why`. Include existing `README.md` (read it; do not
  rewrite it — see below), prior specs, ADRs, official docs, skill/reference
  files, and MCP resource URIs. After the first inventory, run **best-practice
  research** (validate-spec job 2) and append those findings here before
  writing the spec. If an observed MCP server or its tools document how to
  use them, that text is a reference — inventory alone is not enough.
- **tools / mcp** — CLIs and MCP servers actually available this session.
  Inventory, do not install or catalog.
- **mcp_considered** — first matching read-capable session MCP tool, printed
  as `server(tool)`, or `none(reason)` when nothing matched.
- **handles** — external resources this increment needs (credentials,
  hosted ids, service endpoints), each resolved as `list` (enumerate
  candidates), `inspect` (read a concrete value — empty for credentials),
  `ask` (must ask the user), or `create` (this increment provisions it).
  Any `list` or `ask` handle blocks `dest plan` — resolve it first, or use
  the `dest blocked` hatch below.

  `inspect` / `list` / `ask` / `create` classify **what was resolved**, not
  intent. If this session has a cheap read-only call (signed-in MCP list,
  `gh auth status`, a documented status endpoint), run it **once**, **before
  committing** the machine fence. `inspect` only when the required concrete
  value was obtained (non-credential: id in `value`; credential: `value`
  stays empty — never a token). Several matches → `ask`. Failure the user can
  relieve → `ask` and the dest-blocked hatch. No cheap call → `ask`. Never
  write the product tree to find out.
- **initiation** — `none` (nothing to create), `needed` (one-time project
  creation is part of this increment; requires at least one `create` handle),
  or `done` (already created in a prior increment). Deploy *readiness*
  (manifest, store listing, first publish) is a spec-expansion question,
  not a second initiation value — see `validate-spec.md`.
- **ui / ui_craft** — whether this increment touches user-facing surface, and
  if so, which design/UX skill was invoked (`none(reason)` when `ui` is
  false).

## Write it once

Write `environment.md`: a short prose brief, then a unique H2 titled exactly
`machine`, immediately followed by one fenced JSON object with the keys above.
Put dest notes (existing repo, migration, CI/CD, missing systems) in that
brief. Record unauthenticated, deferred, or wrong-for-this-increment MCP
servers in the brief too — they are later **Don't use** lines, not machine
keys. After inventory, **before the spec**, research applicable practices and fold
them into the same file (more prose + `references`). `kind: brownfield`
requires `augment: true` and a nonempty `references` list (cite the bound-repo
README if it exists, plus any other files or URLs the increment depends on).
Those `references[].path` values later appear in every seed `prompt` together
with a `Tools:` block. This file becomes hashed and frozen at `dest plan`
(`environment_sha256`) — same discipline as the frozen spec. Do not write
`environment.json`. Do not add a second practices file. Do not add research
skills to `dep_roots`.

## The `dest blocked` hatch

If a handle needs the user (`ask`) or a design/UX question can't be resolved
here, write `spec.md` with labeled `done_sentence:` (provisional),
`checkable: false`, and `ask_user: <question>`, then `/shiploop complete
--blocked --resume-to validate-spec --reason <ask_user>`. `dest blocked`
does not require `environment.md` to be written first — the survey can be
incomplete when you stop to ask.

## README is not survey's to write

Survey **reads** `README.md` if it exists (cite it in `references`) but must
**not** write or rewrite it. Mutating the product tree before the spec is
frozen is a spec-adjacent action, not a survey action. The README create (if
absent) or revise (if present) is the increment's **final product duty**,
written from `spec.md` and executed as a late DAG successor during
`plan`.
