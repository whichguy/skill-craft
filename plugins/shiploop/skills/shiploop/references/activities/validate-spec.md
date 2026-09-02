**Survey, then practices, then spec.** Write `environment.md` then `spec.md`.
State files: `{{SURVEY_GUIDE}}` and `{{STATE_FILES}}`.

### 1. Survey (once)

Inventory this session against `{{SURVEY_GUIDE}}`: kind/augment, references
(read `{{REPO_ROOT}}/README.md` if it exists and cite it — do **not** write
or rewrite it here), tools, mcp, mcp_considered, exclusive, handles, initiation,
ui/ui_craft. `kind` and `augment` must match (`greenfield`/`false`,
`brownfield`/`true`); brownfield `references` must be nonempty. `tools`/`mcp`
are available **and in-bounds** this increment (dest-writes can succeed now,
or a `create` handle will enable them). Cheap-probe the exclusive writer's
status/setup before dest plan or an `initiation: needed` create;
`exclusive[].use` stays inventoried. `exclusive` is the destination-writer
map (conflicts, not backups); `[]` when none; dest plan requires the key.
Write `{{ENV_MD}}`: a prose brief (dest notes and unauthenticated or deferred
MCP belong here, not in machine JSON), then a unique H2 titled
exactly `machine` with one fenced JSON object. Any handle resolved `list` or
`ask` will block `dest plan` later — resolve it now or use the blocked hatch
below.

Inventory required handles, then at most one bounded read-only attempt per
identified claim before finalizing the machine fence, per the survey guide.
When `exclusive` is nonempty, those claims include platform preconditions
from the named writer's docs/status/setup (APIs, scopes, billing, org
allowlists). Probe enablement **before** an `initiation: needed` create.
If `list` or `ask` remains, write `{{SPEC_MD}}` with labeled
`done_sentence:` (provisional), `checkable: false`, and `ask_user: <the
unresolved handle>`, then `/shiploop complete --blocked --resume-to
validate-spec --reason <ask_user>`. Do not dest blocked with no `spec.md`.
Do not re-exercise a handle already `inspect`. A handle first introduced
while writing the spec inherits this rule before leaving validate-spec.

### 2. Best-practice research (once, before the spec)

From `{{ENV_MD}}` (kind, tools, mcp, exclusive, ui, initiation, handles) and
`{{PROMPT_PATH}}`, decide which practices apply. Pull concrete references
implement steps must use: URLs, in-repo paths, ADRs, official docs, skill
or reference files, MCP resource URIs. If an observed MCP server or its
tools describe how to use them (tool descriptions, resources, prompts, or
a query that returns practice guidance), record that text as a reference —
inventory alone is not enough.

Deeply research those MCP servers and destination services before freezing
their implementation constraints.

### Dest MCP, libraries, and conventions (required when `mcp:` or `exclusive` is nonempty)

Inventory is not use. For **each** name in machine `mcp:`, and for each
`exclusive[].use` (if any), answer the four questions below from **that
server’s own** tool descriptions, resources, prompts, and published
guidance — including tools this increment will not call for create.
Record each answer as `references[{path, why}]` plus brief prose in
`{{ENV_MD}}`. `why` names the implement constraint, not “inventory.”
If a question does not apply, write `none` in the brief so implement
does not guess. Do not invent a house style. Do not bake a vendor,
platform, or folder name into this skill; the writer’s documents
supply those names.

1. **How to use this MCP / dest writer.** Which tool is for which job
   (read state vs mutate dest vs create vs publish)? What anti-patterns
   does the server itself name? Cheap probe: the writer’s documented
   status/list/setup **once**, read-only, before dest plan.

2. **Library / runtime systems it imposes.** Required module format,
   wrap/export style, helpers that already exist after create/bootstrap
   (or, brownfield, after listing dest files). **Reuse before add:**
   search bound `{{REPO_ROOT}}` **and** the destination; do not add a
   second library for the same job. Greenfield still records what the
   dest source requires. Do not duplicate, conflict with, or arbitrarily add
   a new library that serves the same job.

3. **Conventions — reserved vs product.** After create/bootstrap (or
   dest list), split paths:
   - **reserved:** files/trees the writer owns, bootstraps, or will
     overwrite. Product feature code must not land here.
   - **product:** trees where this increment’s new feature code belongs.
   Cheap probe: list files the writer placed at create/bootstrap vs
   files this increment will add. The bootstrap set is **reserved**
   unless the same source names a distinct product tree. If published
   guidance says “put all new files in the runtime dump,” treat that
   dump as reserved and put product code in the named product tree, or
   (if none is named) in a non-runtime path at repo root — then dest
   blocked if the user must choose. Product-in-reserved is a discovery
   miss even when the writer invited it.

4. **How a user actually hits the dest artifact.** Default dest
   entrypoint (bare URL, default route, first-responder) vs documented
   product path/query/route. Routes the writer keeps. How to run a
   **routing-level probe** of that entrypoint (not a library/module
   helper that bypasses the dispatcher). This probe is **not** a
   browser play-through. Cheap probe after create+push (or equivalent):
   hit the dest default entrypoint **and** the documented product path;
   record both. If they differ, `done_sentence` must not claim the
   product is served at the default entrypoint. A sink that genuinely
   needs a play-through must say so in `produces` and is a **live
   acceptance** step, not this probe.

When `exclusive` is nonempty, all four answers are required before dest
plan (and `references` stays nonempty). When `mcp:` is nonempty but
`exclusive` is `[]`, still record (1) and (2); (3) and (4) may be `none`
if there is no dest artifact. When both are empty, skip this block.

If official platform docs are also in `references`, and they conflict
with writer-published dest-write rules, **writer wins**. Record both:
writer path with `why` = the dest-write constraint; platform docs with
`why` = “platform default; dest writer overrides <X>.”

When `exclusive` is nonempty, keep `references` nonempty. Do not invent a
Writer playbook heading. Do not write `playbook.md`. Do not restate the
exclusive map in prose. Do not invent a second SoT file. Do not persist
secrets. Do not write the product README. Do not add research skills to
`dep_roots`. Those references must later appear in each seed step's stored
`prompt` together with a `Tools:` block that carries the frozen
`mcp_considered` token. In-flight runs: dest blocked → validate-spec;
rewrite environment.md; → plan (do not hand-edit backchain/plan.json).

### Surfaces (required when `ui` is true)

Inventory is not design. When machine `ui` is true, for **each** human-facing
surface this increment ships (product UI, CLI, operator/debug page a person
uses, dest-facing page):

1. Cite the frozen `ui_craft` skill as `references[{path, why}]`. `why` names
   distinctive identity and interaction, not “inventory.” The `ui_craft`
   token must appear in that `path`.
2. Record dest-writer conventions that bound the surface (helpers and
   interaction patterns already in the dest). Reuse those. Do not add a
   second UI/CLI stack for the same job.
3. Default quality bar unless the frozen spec says otherwise: as **highly
   interactive and distinctive** as those conventions allow — live feedback,
   in-surface state, keyboard where it fits, empty/error/success as designed
   moments. Not a generic template. Not a static form if the dest can do
   motion or in-page interaction.

When `ui` is false, skip this block.

### 3. Spec (once)

Write `{{SPEC_MD}}` with a labeled line `done_sentence: <exact sentence>`
and a labeled line `checkable: true` or `checkable: false` (each exactly
once, outside fences/blockquotes). Derive a machine-checkable
`done_sentence`. Do not invent pytest, a path, or a cwd. The spec's final
product duty is a README create (if absent) or revise (if present) — tell
backchain to add that as a late DAG successor in `plan`, not here.
If dest-hit found a reserved default entrypoint, `done_sentence` names the
**user** entrypoint, not the default dest URL.

While expanding the spec, answer these four questions in `{{SPEC_MD}}`
(prose is enough; do not invent new required labels). Survey already owns
`initiation` / `create` handles — question 1 is deploy *readiness*, not a
second project-create survey.

1. **Deploy preparation before the walk?** Does this increment need
   credentials, store listing, web-app manifest, or other deploy config
   *before* the feature steps? If yes, say what. If no, say deploy
   preparation is none. `plan` turns a yes into the early **prep** DAG
   step (not a second unnamed prep).
2. **Deploy / publish after the walk?** Once the feature work is done, does
   someone still need to deploy or publish? Record one of: **outer-loop**
   (residual, after review-coverage — not a DAG step), **dag** (one
   sequence step; that *is* the plan's intermediate/late deploy), or
   **none**. Residual re-reads live dest URLs and composes them onto frozen
   routing; it does not rewrite this answer unless dest-blocked to
   validate-spec.
3. **Quality test/fix on outer-loop completion?** After residual
   review-coverage, should the host run a `/goal` quality test-and-fix pass
   on the completed product before dest done? Record yes (and what to
   check) or no. If dest-hit differs from the default dest entrypoint, what
   to check names the **user** entrypoint. Any watch MCP for that check
   goes in machine `mcp:`/`tools` now (brief-only is Don't-use). Residual
   treats that answer as frozen: yes runs it, no skips it.
4. **Human-facing surfaces?** If survey `ui` is true, name each surface and
   say it is **designed** (distinctive, highly interactive within dest
   conventions) before it is built. If `ui` is false, say none.

Do not run that `/goal` here. Do not publish here. Do not invent a new
state-machine phase. Ownership: Q1, Q2=`dag`, and Q4 → `plan`; Q2=`outer-loop`
and Q3 → residual.

If not checkable, or a handle needs the user: set labeled `done_sentence:`
(provisional), `checkable: false`, and `ask_user: <question>`, then
`/shiploop complete --blocked --resume-to validate-spec --reason <ask_user>`.
This hatch does not require `{{ENV_MD}}` to be finished first.
