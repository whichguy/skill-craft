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
  Deeply research those MCP servers and destination services (tool schemas,
  resources, prompts, official docs) for required or conventional syntax
  style, library, module format, or behavior. If the source says it overtly,
  record `references[{path, why}]`. **Reuse before add:** search bound
  `repo_root` **and** the destination for libraries and patterns already in
  use; do not duplicate, conflict with, or arbitrarily add a new library
  for the same job.
- **tools / mcp** — CLIs and MCP servers available **and in-bounds for this
  increment**. Inventory, do not install or catalog. In-bounds means dest-writes can succeed now through that name, or a `create` handle in this increment will enable them. `exclusive[].use` must still be an inventoried tools or mcp name. A failed enablement probe is an `ask` handle and dest blocked — do not omit the designated writer from these lists, and do not dest plan until `inspect`. Unauthenticated, deferred, or wrong-for-this-increment names belong in the brief, not these lists (Frozen asserts MCP in `mcp:` is in-bounds).
- **mcp_considered** — first matching read-capable session MCP tool, printed
  as `server(tool)`, or `none(reason)` when nothing matched. A single token,
  not a deferred-tools bucket.
- **exclusive** — exclusive writer for destination artifacts this increment
  creates or updates,
  each `{artifact, use, dont_use}`. `use` is the designated writer (a name)
  from `tools` or `mcp`). `dont_use` is overlapping tools that **mutate the
  same artifact** (conflicts, not as backups) and may be `[]`. `exclusive: []`
  when there is no such artifact (read-only inventory, local-only). Missing
  `exclusive` is unanswered — dest plan requires the key. When a designated
  writer fails: dest blocked; do not switch writers.
  Choose `use` by artifact, not familiarity. Name the destination artifact
  first. Scan each connected server's tool list once, descriptions only, no
  calls, for tools that mutate that artifact kind. Servers with none are one
  brief Don't-use line. If more than one mutates it, the others are
  `dont_use`, and the brief gives the reason for the choice in one sentence:
  it bootstraps the product tree, it owns publish, or the user named it.
  Deep-read and probe candidates only. When one source bootstraps the tree
  and another pushes, `use` is the pusher and Q2 follows the bootstrapper;
  cite both.
  `If the writer above fails, stop and invoke /shiploop complete --blocked --reason … — do not switch writers.`
  Frozen reprints that sentence; do not retype it into `environment.md`.
- **handles** — external resources this increment needs (credentials,
  hosted ids, service endpoints, **platform preconditions** the exclusive
  writer requires), each resolved as `list` (enumerate
  candidates), `inspect` (read a concrete value — empty for credentials),
  `ask` (must ask the user), or `create` (this increment provisions it).
  Any `list` or `ask` handle blocks `dest plan` — resolve it first, or use
  the `dest blocked` hatch below.

  `inspect` / `list` / `ask` / `create` classify **what was resolved**, not
  intent. If this session has a cheap read-only call (signed-in MCP list,
  `gh auth status`, a documented status endpoint, the dest writer's own
  status/setup tool), run it **once**, **before
  committing** the machine fence. `inspect` only when the required concrete
  value was obtained (non-credential: id in `value`; credential: `value`
  stays empty — never a token). Several matches → `ask`. Failure the user can
  relieve → `ask` and the dest-blocked hatch. No cheap call → `ask`. Never
  write the product tree to find out.

  When `exclusive` is nonempty, read the named writer's docs/status/setup
  for platform preconditions (APIs, OAuth scopes, billing, org allowlists,
  marketplace enablement). Each is a handle. Cheap probe: enabled →
  `inspect`; user must flip a console flag → `ask` + dest blocked; this
  increment can enable it via the writer's setup tool → `create`. If the
  writer needs none, say so in the brief. Do not invent a second map or
  a new initiation value. **Probe enablement before** an `initiation:
  needed` `create` handle that provisions the hosted project.
- **initiation** — `none` (nothing to create), `needed` (one-time project
  creation is part of this increment; requires at least one `create` handle),
  or `done` (already created in a prior increment). Deploy *readiness*
  (manifest, store listing, first publish) is a spec-expansion question,
  not a second initiation value — see `validate-spec.md`. Platform
  enablement is a handle, not a fourth initiation value.
- **ui / ui_craft** — `ui` is true when this increment ships any **human-facing surface** (product UI, CLI, operator/debug page a person uses, dest-facing page the user sees). `ui_craft` is the installed design/UX skill invoked for those surfaces (`none(reason)` when `ui` is false). Inventory is not design: listing `ui: true` does not plan the surface. Cite the craft skill as `references[{path, why}]` with `why` naming distinctive identity + interaction, not “inventory.” The brief lists each surface and the dest-writer conventions that bound it (helpers, HTML/CLI patterns already in the dest).

## Destination discovery

When `mcp` or `exclusive` is nonempty, answer the four dest-discovery questions and the evaluations in the printed validate-spec activity. `layout` / `routing` shape is in `state-files.md`. Nonempty `exclusive` requires all four answers and nonempty `references` before dest plan; `mcp` only requires Q1 and Q2, and Q3/Q4 may be `none`.

The evaluations (usability this turn, dest file identity, tracked bind files) live in the printed validate-spec activity; each may be the token `none` when inapplicable.

## Write it once

Write `environment.md`: a short prose brief, then a unique H2 titled exactly
`machine`, immediately followed by one fenced JSON object with the keys above.
Put dest notes (existing repo, migration, CI/CD, missing systems) in that
brief. Record unauthenticated, deferred, or wrong-for-this-increment MCP
servers in the brief too — they are later **Don't use** lines, not machine
keys. After inventory, **before the spec**, research applicable practices and fold
them into the same file (more prose + `references`). Deeply research
in-bounds MCP and destination services for style / library / behavior;
reuse before add on bound `repo_root` and the destination. When `exclusive` is
nonempty, that folded prose must cover the libraries, file/runtime layout,
and platform preconditions the named writer requires, and `references` must
be nonempty. Do not invent
a Writer playbook heading. Do not write `playbook.md`. Do not restate the
`exclusive` map in prose. `kind: brownfield`
requires `augment: true` and a nonempty `references` list (cite the bound-repo
README if it exists, plus any other files or URLs the increment depends on).
Those `references[].path` values later appear in every seed `prompt` together
with a `Tools:` block. This file becomes hashed and frozen at `dest plan`
(`environment_sha256`) — same discipline as the frozen spec. Editing it after
bind requires dest blocked → validate-spec; rewrite environment.md; → plan
(do not hand-edit backchain/plan.json). Do not write
`environment.json`. Do not add a second practices file. Do not add research
skills to `dep_roots`.
Do not freeze signed-in account addresses; write "signed in as the expected
account". Do not freeze live dest URLs.

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
