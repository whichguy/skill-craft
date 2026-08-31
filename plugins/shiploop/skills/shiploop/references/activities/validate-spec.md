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

Deeply research those MCP servers and destination services. Read tool
schemas, resources, prompts, and official docs. Determine whether there
is a required or conventional syntax style, library, module format, or
behavior pattern. If the source says it overtly, record it as
`references[{path, why}]` plus brief prose in `{{ENV_MD}}`. `why` names
what implement must follow (style / library / behavior), not “inventory.”
Do not invent a house style. Do not bake a vendor name into the skill.

**Reuse before add.** Brownfield / existing dest: search the bound
`{{REPO_ROOT}}` **and** the destination (existing hosted project, package
lock, README, imports, layout) for libraries and patterns already in use.
Continue those. Do not duplicate, conflict with, or arbitrarily add a new
library that serves the same job. Greenfield: no tree to reuse; still
record what the MCP/dest source requires so implement does not guess.
Writer conflicts stay `exclusive` (do not switch). Library conflicts are
the same idea: one established stack per artifact; dest blocked if the
user must choose.

When `exclusive` is nonempty, fold the named
writer's libraries, file/runtime layout, and platform preconditions into the
same file and keep `references` nonempty. Do not invent a Writer playbook heading. Do not write
`playbook.md`. Do not restate the exclusive map in prose. Write the findings
**into** `{{ENV_MD}}`
(more prose plus `references[{path, why}]`; `path` may be a URL or repo
path). Do not invent a second SoT file. Do not persist secrets. Do not
write the product README. Do not add research skills to `dep_roots`. Those
references must later appear in each seed step's stored `prompt` together
with a `Tools:` block that carries the frozen `mcp_considered` token.
In-flight runs: dest blocked → validate-spec; rewrite environment.md; → plan
(do not hand-edit backchain/plan.json).

### 3. Spec (once)

Write `{{SPEC_MD}}` with a labeled line `done_sentence: <exact sentence>`
and a labeled line `checkable: true` or `checkable: false` (each exactly
once, outside fences/blockquotes). Derive a machine-checkable
`done_sentence`. Do not invent pytest, a path, or a cwd. The spec's final
product duty is a README create (if absent) or revise (if present) — tell
backchain to add that as a late DAG successor in `plan`, not here.

While expanding the spec, answer these three questions in `{{SPEC_MD}}`
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
   **none**.
3. **Quality test/fix on outer-loop completion?** After residual
   review-coverage, should the host run a `/goal` quality test-and-fix pass
   on the completed product before dest done? Record yes (and what to
   check) or no. Residual treats that answer as frozen: yes runs it, no
   skips it.

Do not run that `/goal` here. Do not publish here. Do not invent a new
state-machine phase. Ownership: Q1 and Q2=`dag` → `plan`; Q2=`outer-loop`
and Q3 → residual.

If not checkable, or a handle needs the user: set labeled `done_sentence:`
(provisional), `checkable: false`, and `ask_user: <question>`, then
`/shiploop complete --blocked --resume-to validate-spec --reason <ask_user>`.
This hatch does not require `{{ENV_MD}}` to be finished first.
