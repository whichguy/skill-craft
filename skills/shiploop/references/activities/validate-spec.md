**Survey, then practices, then spec.** This is not c-plan. Do not follow a
DevLoop overlay. State files: `{{SURVEY_GUIDE}}` and
`references/state-files.md`.

## 1. Survey (once)

Inventory this session against `{{SURVEY_GUIDE}}`: kind/augment, references
(read `{{REPO_ROOT}}/README.md` if it exists and cite it — do **not** write
or rewrite it here), tools, mcp, mcp_considered, handles, initiation,
ui/ui_craft. `kind` and `augment` must match (`greenfield`/`false`,
`brownfield`/`true`); brownfield `references` must be nonempty. Write `{{ENV_MD}}`: a prose brief, then a unique H2 titled
exactly `machine` with one fenced JSON object. Any handle resolved `list` or
`ask` will block `dest plan` later — resolve it now or use the blocked hatch
below.

## 2. Best-practice research (once, before the spec)

From `{{ENV_MD}}` (kind, tools, mcp, ui, initiation, handles) and
`{{PROMPT_PATH}}`, decide which practices apply. Pull concrete references
implement steps must use: URLs, in-repo paths, ADRs, official docs, skill
or reference files, MCP resource URIs. If an observed MCP server or its
tools describe how to use them (tool descriptions, resources, prompts, or
a query that returns practice guidance), record that text as a reference —
inventory alone is not enough. Write the findings **into** `{{ENV_MD}}`
(more prose plus `references[{path, why}]`; `path` may be a URL or repo
path). Do not invent a second SoT file. Do not persist secrets. Do not
write the product README. Do not add research skills to `dep_roots`. Those
references must later appear in each DAG step's stored `prompt`.

## 3. Spec (once)

Write `{{SPEC_MD}}` with a labeled line `done_sentence: <exact sentence>`
and a labeled line `checkable: true` or `checkable: false` (each exactly
once, outside fences/blockquotes). Derive a machine-checkable
`done_sentence`. Do not invent pytest, a path, or a cwd. The spec's final
product duty is a README create (if absent) or revise (if present) — tell
backchain to add that as a late DAG successor in `plan`, not here.

If not checkable, or a handle needs the user: set `checkable: false` and a
labeled `ask_user: <question>`, then `/shiploop complete --blocked
--resume-to validate-spec --reason <ask_user>`. This hatch does not require
`{{ENV_MD}}` to be finished first.
