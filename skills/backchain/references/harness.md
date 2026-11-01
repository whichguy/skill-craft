# Backchain development checkout: harness, benchmarks and maintenance

Planning logic lives in **prompts**, and a native run's bookkeeping in the shipped
`scripts/backchain.py`. The harness, `fixtures/`, `samples/`, `schema/plan.schema.json` and the
benchmarks below live in the separate Backchain development checkout and are not shipped with
this skill; use these commands only in that checkout. The native procedure on the skill card
needs none of them.

## Whole-skill completion boundary

The native skill runs the selected actual Until Loop through `references/convergence.md`.
Direct harness commands generate or package candidates only; they do not perform the review
loop. Within a Backchain invocation, feed their output back into that loop. A CLI success or
`completionStatus=complete` cannot stand in for an actual Until Loop terminal receipt and
planning evidence. The harness does not bundle or invoke a second review controller; Backchain
reuses the selected Until Loop runtime.

## Product labels

| Label | How | Claim |
|-------|-----|--------|
| **native** | Session model plans; `scripts/backchain.py` checks, packages and records; Until Loop reviews | Validated plan JSON with its convergence record |
| **script-packaged** | `bash harness/run-prompt.sh --package-only <enriched.json>` | Schema/DAG/waves validated, plus the checkout's reports |
| **full-harness** | `bash harness/run-prompt.sh --prompt …` or `--from-draft …` | Router generator; router or configured alternate elaborator |
| **nbq-experiment** | same + `--nbq` | External EVSI → `dependency-context.*`; requires Ollama chat URL |

The checkout's `harness/lib.js` is the arbiter of the structural check; the shipped
`scripts/backchain_graph.py` ports it and reproduces its recorded verdicts
(`test/fixtures/backchain-check` in Skill Craft).

## One-shot candidate packaging (`run-prompt.sh`)

The commands below do not run Until Loop or semantic convergence. A direct CLI exit 0
proves only its documented structural result. The scripts and benchmark prompts remain
one-pass primitives; bind their resulting candidate to the selected Until Loop separately.

```sh
bash harness/run-prompt.sh --prompt samples/oauth-login-tests.prompt.md
# defaults: elaborator TRACE on; relationship learnings on stderr
# options: --report compact|full · --no-trace · --quiet · --model sonnet · --from-draft · --package-only
# opt-in:  --nbq | --next-best-deps  (dependency-scoped next-best-questions before elaborate)
```

This generates a draft, elaborates it, **persists** recomputed `parallel_groups`, and validates
structure. It always saves **`compact-report.md`** and the exhaustive **`full-report.txt`**.
Stdout defaults to `--report compact`: a `Step | Work | Needs | Conditions` table with unique
direct supplier IDs, initial/unresolved count notes, initial facts and unresolved descriptions,
dependency-only parallel candidates, and validation/completion/advisory summaries. `--report full`
prints the exhaustive backchain: every statement, produce, input relation/need/match detail, wave,
chain, edge, and fidelity walk. `--quiet` silences progressive learnings only; it does not
suppress the final selected report. Artifacts under `results/run-prompt-*/` include
**`packaged.json`**, **`validation.json`**, **`handoff.json`**, both report files, and `run.json`
(`artifacts.compact_report` and `artifacts.full_report`). The canonical JSON contract is unchanged.
Exit `0` only when structure is valid; inv-7-only failures exit `1` with diagnostics (no silent fix).

**Alternate elaborator backends:** `BACKCHAIN_ELAB_BACKEND` accepts `router` (default),
`ollama`, `ask-ollama`, or `cmd`. Use `BACKCHAIN_ELAB_MODEL` to pin the alternate model;
`cmd` also requires `BACKCHAIN_ELAB_CMD` and executes an executable path through its shebang.
Only the elaborator changes: a full `--prompt` run still needs the router for generation, while
`--from-draft` can use an alternate backend without a Claude-compatible runner. Audit identity in
`run.json`: `stages.elaborator.requested_model` is the requested pin and
`stages.elaborator.served_model` is the backend-reported model (with `served_models` retaining the
full list). Treat a missing served identity as unknown; the legacy top-level `model` is not proof
of which alternate model produced the elaboration.

**Opt-in next-best deps (`--nbq`):** default **off**. When set, after `draft.json` exists and
**before** the elaborator, Backchain builds a dependency-scoped problem from the draft, runs the
external **next-best-questions** skill (`infogain.py --json`), writes `nbq-problem.txt`,
`nbq-deps.json`, `nbq-context.md`, and injects that context as `{{NBQ_CONTEXT}}` into the elaborator
prompt. The elaborator may use ranked questions as five-lens **interrogation aids** only — no new
plan schema fields. If `--nbq` is set and the skill/command fails, the runner **exits 5** (does not
silently skip). **Critical:** `OLLAMA_URL` must be the chat endpoint
`http://127.0.0.1:11434/api/chat` (bare host:port → HTTP 405 and empty buckets with zero model calls).
Backchain normalizes bare URLs when possible. For tests: `BACKCHAIN_NBQ_CMD` (args: problemPath
outJsonPath). Skill root: `BACKCHAIN_NBQ_SKILL_DIR`. Casebook:
`bash harness/casebook-run.sh --track A --cases oauth-seeded-user --nbq`.

**TRACE (default on):** elaborator TRACE_MODE writes non-empty `trace.txt` when the elaborator emits
a `<trace>` block (`--no-trace` for JSON-only). The generator never produces a trace. Operator
stderr gets only a deterministic **TRACE pointer** (not per-pop prose mirrors). Trace mode is for
offline/manual debugging only: `harness/bench.sh` always renders it as `off` and does not parse
trace-mode output.

**Three operator channels:** (1) **stderr status** = deterministic **deltas** (stage banners,
`+` insert / `→` new edge / `·` null / compact ids-only `∴` package line; subject chips,
word-safe trunc); (2) **`trace.txt`** = elaborator **audit** when TRACE on (Goal phase +
per-pop `kept`/`wired`/…); (3) **selected stdout report** = compact by default or exhaustive with
`--report full`; both durable report files are always written. NDJSON twin:
`relationship-events.ndjson`. Disable progressive status with `--quiet` or
`--no-relationship-status`. Spec: `docs/relationship-status-spec.md`.

**Health metrics (operator):** structural ok, `completionStatus`, inv-7 diagnostics, and
dependency-safe waves. Same-depth steps may start together (not resource- or file-aware). Do **not**
score plans by seed-step count or discovered-step (`D*`) count — both can vary across one-shot runs;
judge by closed needs, honest `unresolved`, and a usable handoff DAG. A rich seed draft with few or
no `D*` can be ideal. Prefer empty seed `inputs`; if inv-7 fires, re-run generation with verbatim
`initial_state` pastes rather than asking the elaborator to rewrite seed edges.

**Parallel agents:** paste `results/.../handoff.json` (precomputed `waves`, `edges`, `critical_path`,
`steps` with `produces`/`inputs`) into the orchestrator — do not re-derive schedule from path
letters. Waves are conservative barriers; edges allow eager starts when a step’s own suppliers
are done. Packaging also runs a **forward fidelity walk** (multi-root → multi-sink along depth waves): each
step’s inputs must be ready from earlier waves / `initial_state`, and each edge’s `need` must
exact-match a supplier `produces` or carry a sparse `match`. Results land on handoff as
`forward_fidelity` + optional **`edge_semantic_warnings`** — **advisory** relationship honesty after
backprop freeze, not structural failures. The compact report is a reading aid: its direct
dependencies do not establish executor assignment, worktree isolation, file/resource safety,
merge safety, or runtime completion. A native run hands Plan Dispatcher the shipped
`scripts/backchain.py export` graph instead.

**`completionStatus=complete` without `goal_needs`:** means structure is valid and `unresolved` is
empty — **not** that the goal sentence was separately proven covered. Optional `goal_needs` (when
hand/harness-supplied) is the goal-closure check.

## What the prompts do (manual multi-step)

The templates remain authoritative; this is a maintainer's map. A native fresh request is planned by
`prompts/direct.v1.md` (direct synthesis: backward from the requested end states, then a forward walk), its
dependency review, and `prompts/elaborator.v1.md` only when that review changes the graph; the generator below
serves the checkout's one-shot pipeline.

1. `prompts/generator.v1.md` takes the unedited request at `{{RAW_PROMPT}}` and returns a JSON-only
   draft. It derives the request's terminal observable conditions into `goal_needs` **before**
   drafting any step, then runs **environment probes once against those conditions** —
   repo/worktree state, existing user or data state needing transition, release gates,
   documentation, and systems that must be brought into existence. Probes are conditional and
   **fail to nothing**: an unfired probe adds no step. They run at spec level, never per step.
   Demo requests live under the checkout's `samples/*.prompt.md`.
2. `prompts/elaborator.v1.md` (with `{{TRACE_MODE}}` `off`) returns the JSON-only enriched plan. It
   runs a **five-lens back-check per step** (CLAIM / NEEDS / SUPPLY / PULL / RESOLVE): deep
   interrogation of what that step needs to run, what it claims when done, whole-graph supply scan
   up the chain, one-hop downstream pressure on its produces, then wire / enrich / insert `D*` /
   unresolved — never a shallow edge-only pass. Three disciplines live **inside** RESOLVE, not as
   extra lenses: **CARRIER** (a producer names the concrete artifact when its `produces` could
   cover more than one thing, and the consuming edge's existing optional `inputs[].artifact` names
   the same carrier); **HOIST** (a need shared by two or more steps is supplied **once**, at the
   **lowest common ancestor** of its consumers and never higher — hoisting to a shared root would
   serialize independent branches; prefer **widening an existing step** over inserting a redundant
   `D*`, and re-check acyclicity before committing); and **EVIDENCE** (a need is closed only by
   request/inspect evidence it already holds, or by a predecessor whose execution would produce
   inspectable evidence of it — never a raw assumption; unproducible evidence stays `unresolved`).
   These duties are cumulative with the in-place rewrite duty, not alternatives to it.
3. Package with the shipped `scripts/backchain.py package` (or the checkout's `run-prompt.sh
   --package-only`) before using the plan; never hand-edit `parallel_groups`.
4. A complete Backchain planning invocation then runs `references/convergence.md` over the
   candidate. Every review/fix/check cycle rechecks implementable chunk boundaries, splitting
   authorized oversized work into serial, parallel, or mixed dependencies while preserving
   outcomes and verification. `prompts/rubric-judge.md` and `prompts/compare-judge.md` in the
   checkout assess benchmark candidates; neither substitutes for the planning reviews the gate
   requires (by default until the first trivial review; one cycle with `Backchain passes: one`;
   two consecutive trivial reviews with `Backchain passes: converge`).

## More commands

```sh
# Structural only (no model)
bash harness/run-prompt.sh --package-only path/to/enriched.json --out-dir results/…

# From frozen draft (Claude-compatible runner)
bash harness/run-prompt.sh --from-draft fixtures/oauth-tests-gap.draft.json --trace

# Preserve original intent and selected specs across generator and elaborator
bash harness/run-prompt.sh --prompt request.md --source spec.md --source api-contract.md
bash harness/run-prompt.sh --from-draft draft.json --original-request request.md --source spec.md

# Optional EVSI dependency context
export OLLAMA_URL=http://127.0.0.1:11434/api/chat   # must include /api/chat
bash harness/run-prompt.sh --from-draft fixtures/oauth-tests-gap.draft.json --nbq --trace

# A/B measurements and the scored benchmark (optional residual, not RESULT)
bash harness/casebook-ab-backchain.sh   # raw draft vs elaborator
bash harness/casebook-ab-nbq.sh         # elaborator vs elaborator+EVSI
bash harness/bench.sh --run --label <name>
bash harness/bench.sh --compare <labelA> <labelB>
```

`--source` accepts repeatable UTF-8 text references (no NUL; at most 16 sources,
256 KiB per file and 1 MiB total including the original request). Rendered source
JSON is also bounded to 1 MiB; each final model prompt is limited to 120 KiB to
stay within the router's single-argument transport. Select relevant excerpts for
larger documents rather than relying on truncation.
Sources are captured once before a model call; `source-context.json` retains the
exact text, selected/resolved locators, and SHA-256. Generation and elaboration
consume these snapshots, so a source changing mid-run does not silently change
their inputs. Selected symlinks to regular files are supported and retain both
locators. Source contents are data, not permission to override the planner.
The source text is retained in local snapshots and prompts and sent to the
selected model. New snapshot and rendered-prompt files are created with owner-only
permissions; their existence or hashes do not establish source authority.

`run.json.source_context` records transport provenance and
`source_review: not_performed`. These flags do not execute the separate native
caller audit/revise operations or certify source completeness. A from-draft run
without `--original-request` explicitly records the original request as
unavailable. Package-only remains structural and rejects source inputs.

## Env

| Var | Meaning |
|-----|---------|
| `BACKCHAIN_MODEL` | Model pin for Claude-compatible runner |
| `BACKCHAIN_ELAB_BACKEND` | Elaborator backend: `router` (default), `ollama`, `ask-ollama`, or `cmd` |
| `BACKCHAIN_ELAB_MODEL` | Requested alternate elaborator model |
| `BACKCHAIN_ELAB_CMD` | Injectable executable or command for `cmd`; executable paths honor their shebang |
| `OLLAMA_URL` | EVSI only; normalize to `…/api/chat` |
| `OLLAMA_HOST` | Ollama elaborator base URL; the adapter appends `/api/chat` |
| `BACKCHAIN_NBQ_SKILL_DIR` / `BACKCHAIN_NBQ_CMD` | External NBQ |
| `BACKCHAIN_NBQ_*_MODEL` | Optional infogain model overrides |

For model provenance, inspect `run.json` stage records. In particular,
`stages.elaborator.requested_model` records the requested pin and
`stages.elaborator.served_model` records the backend envelope identity; `served_models` retains
all identities reported through a router envelope. Do not use the legacy top-level `model` as
served-model evidence for alternate backends.

## Exit codes (`run-prompt.sh`)

0 structure valid · 1 invalid · 2 usage · 3 model fail · 4 parse fail · 5 NBQ fail

Casebook/intent wrappers may use different codes; read `intent.json` / `health.json` for semantics.

## Layout and the maintainers' gate

| Path (development checkout) | Purpose |
| --- | --- |
| `prompts/` | Generator, elaborator, rubric-judge, compare-judge templates |
| `schema/plan.schema.json` | Plan document schema |
| `fixtures/` | Adversarial draft-plan cases for benchmarks |
| `samples/` | Natural-language requests for generator demos |
| `harness/` | Structural validation + `bench.sh` scoring |

When changing the checkout with a `test-harness` skill installed, its contract is
`<test-harness>/references/gate-snippet.md` + `local-change-gate.md`, for example:

```bash
bash "<test-harness>/scripts/run-harness.sh" \
  --repo "$(git rev-parse --show-toplevel)"
```

Require `PASS_CLEAN` or `PASS_CLEAN_SCOPED` and paste `chat-card.md`; a bare suite exit 0 is not
sufficient. Inner suite: `make test-fast`. The LLM bench and casebook are residual evidence, not
RESULT. The skill itself is maintained in Skill Craft (`skills/backchain`), whose own tests run with
`bash test/run-all.sh`.

## Habitat matrix

| Habitat | Skill path | Notes |
| --- | --- | --- |
| Plugin hosts (Claude, Codex, Grok, Cursor) | the installed `skill-craft` plugin | `skill-craft@whichguy`; invoke `/skill-craft:backchain` |
| OpenCode | `${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills/backchain` | `./install.sh --skill backchain` from a Skill Craft checkout |
| Hermes Docker container | `/opt/data/skills/software-development/backchain` | Same files as the host when `~/.hermes` is bind-mounted at `/opt/data` |

The generator and elaborator templates ship with the skill; the schema and the `make test-fast`
harness live only in the development checkout and are not assumed to be mounted into a Hermes
container. Skill-only operators follow the procedure and plan contract on the card.
