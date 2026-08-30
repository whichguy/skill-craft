The spec is **frozen**. Read `{{SPEC_MD}}` (done sentence, checkable, and
the three placement answers) and `{{ENV_MD}}` (frozen survey). Do not
rewrite either.

Call the installed **backchain** skill **once** to write the sequence DAG.
Place work from those answers — do not invent a second spec or a second
copy of the same step:

- **prep** — if the spec named **deploy preparation before the walk**, that
  *is* the early prep step. If it said none, omit deploy-prep; still add
  other implied prep.
- **intermediate deploy** — if the spec named **deploy/publish** as
  **dag**, that *is* the deploy/publish sequence step. If it named
  **outer-loop**, do **not** put that publish in the DAG — residual owns
  it after the walk. If it said **none**, omit a deploy/publish step.
- **cleanup** — when implied, as a real DAG step (postcondition).
- A **quality `/goal` on outer-loop completion** is never a DAG step.

Include a **README create or revise** as a **late DAG successor** after the
feature work it documents — same grain as cleanup, not a new state-machine
phase. It must record what the app is, how to run it, and what this
increment changed; it must never contain machine JSON, handles, tokens, MCP
inventory, or session hashes (those stay in `{{ENV_MD}}`).

Call backchain with the frozen done sentence **and** the full `{{ENV_MD}}`
(machine JSON plus dest notes in the brief). Ask it once whether the goal
needs an existing repo, a data migration, a CI/CD gate, docs, or a system
that is not there yet. A real missing precondition becomes a seed step. An
unanswerable question is dest **blocked** with `--reason`. Never leave a
nonempty `unresolved` list.

**Purpose vs setup vs iterate vs conclude.** The original ask
(`{{PROMPT_PATH}}`) and frozen `done_sentence` are the **purpose of the
plan**. They are Reminder / Look-here context — not the body of every
seed `prompt`. Split work so one-time jobs run once:

- **Setup (once)** — already true in `initial_state`, or an **early**
  seed whose `produces` is that setup. Later `/goal`s must not repeat it.
- **Iterate** — middle seeds. Each `/goal` is only this step until its
  own `produces`. Assume suppliers and `initial_state`.
- **Conclude (once)** — late seed (README / cleanup) and/or residual
  (quality `/goal`, outer-loop publish). Not in middle steps.

Examples (instructive):

1. **New repo.** Ask: "in a new repo, add result.txt". If `initial_state`
   already has `repo exists`, later prompts must not create another repo.
2. **Database.** Ask: "stand up postgres and add the User table".
   Database exists is setup; the table is iterate.
3. **Deploy at the end.** Ask: "ship the feature and deploy". Deploy is
   conclude (late DAG if spec said **dag**, residual if **outer-loop**).

Every seed step must carry a nonempty `prompt` — the exact string the host
will paste (newlines allowed, no control chars other than newline). The
script prints it **verbatim** and does not compose it from `statement` /
`produces` / the original ask. `statement` stays the short diagnosis
label. Shape:

```text
/goal
Do this activity until these conditions are met:
- <this step's produces, one bullet each>

Assume already true (do not repeat): <initial_state and supplier produces>.
Purpose of the plan (do not re-execute as this step): <frozen done_sentence>.

Tools:
…
```

`dest implement` refuses a seed `prompt` that has no line starting with
`/goal`, that omits `Do this activity until these conditions are met:`,
or that omits any `produces` string. Every **seed** `prompt` must still
cite the practice references from `{{ENV_MD}}` (`references[].path`) and
end with a `Tools:` block. This session `plan.md` pointer must never
contain machine JSON, handles, tokens, or MCP inventory — those stay in
`{{ENV_MD}}`. Seed **prompts** must carry the frozen `mcp_considered`
token.

Label meanings (host judgment — the script does not check these words):

- **Watch with:** the exact frozen `mcp_considered` string, including `none(reason)`.
- **Use:** existing non-MCP tools this step runs. Destination writes follow
  the playbook's exclusive writer, including MCP named in `mcp:`.
- **Don't use:** conflicting writers of the same artifact (from
  `exclusive[].dont_use`), plus unauthenticated, deferred, or
  wrong-for-this-step tools/MCP.
- **Assume:** relevant frozen handles, initiation, and dest notes already in the brief — never newly invented facts.

```text
Tools:
Watch with: cursor-ide-browser(browser_snapshot)
Use: git
Don't use: Drive MCP (not signed in); browser MCP (later quality check)
Assume: git remote already exists; do not write a new test harness
```

When nothing matched:

```text
Tools:
Watch with: none(no read-capable session tool matched done-sentence)
Use: git
Don't use: none
Assume: this increment stays local
```

`dest implement` refuses a seed `prompt` that omits any researched path, that
has no line starting with `Tools:`, or that omits the frozen
`mcp_considered` token (even on README / omit-MCP steps). In-flight
pre-0.8.4 runs: dest **blocked** then dest **plan**, rewrite seed prompts
(do not hand-edit `backchain/plan.json`). `inject-step` discovered steps still
need `/goal` plus until-`produces` but are exempt from citation and the
Tools: gate; the implement envelope still reprints frozen tools/MCP for
those `/goal`s. See `{{IMPLEMENT_ACTIVITY}}`.

Persist the backchain document to `{{BACKCHAIN_JSON}}` (canonical). Then
write `{{PLAN_MD}}` with a labeled line `done_sentence: {{DONE_SENTENCE}}`
(must equal the spec). Do not write a `plan.json` wrapper — leftover
wrappers are inert (`init --force` still unlinks them).

Do not vendor backchain. Do not exec a live packager. Missing backchain root
is a Missing line — then `/shiploop complete --blocked --resume-to plan`.
