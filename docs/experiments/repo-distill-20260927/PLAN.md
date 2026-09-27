# Repo distill and clean-room reproduction: plan (rev 3)

Owner request (2026-09-27): distill a specification from a real GitHub
repository, have ShipLoop rebuild it from that specification alone, compare
the rebuild with the original, and learn what to change: in ShipLoop **or in
the distillation**. Distilling a spec is also wanted on its own, for
understanding any repository we reference.

Start small, iterate often. Each revision reviewed unknowns, flow and error
conditions and pruned by KISS/YAGNI; the review tables at the bottom record
every item and its decision.

## Goal and exit criteria

The pilot is done when, for json-server, scripts show:

1. a distilled spec whose claims all cite evidence that resolves, with the
   original name absent (`spec_check.py`);
2. an admitted oracle: 100% pass on the original, twice (no flakes), and
   most checks fail on a stub; stub-passing checks listed (`oracle_run.py --admit`);
3. a baseline rebuild from the spec alone, oracle-scored (`rebuild.py`);
4. every failing check attributed to one fault location, with a spot-check
   of the verdicts by hand;
5. the json-server harness case built, and its first ShipLoop run (E4)
   scored and attributed.

Nothing else is in scope.

## Pipeline

```
repo ──distill──▶ spec.md (claims + evidence + pinned interface + unknowns)
repo ──port────▶ oracle/ (black-box node:test checks, run via $APP_CMD)
spec ──build───▶ rebuild (plain Grok session, then ShipLoop), repo never visible
oracle(rebuild) ──attribute (one Opus judge)──▶ distill fixes | builder fixes
```

- **Pinned interface, free internals.** The spec fixes what a user or client
  observes; the oracle checks only that, through the command line and HTTP.
- **Evidence per claim** (D-n with `path:line`); unknowns listed, not guessed.
- **Clean room.** The builder gets SPEC.md only, in an empty directory under a
  neutral path, product renamed (`tinyrest`), web search off. The run is void
  when the builder's tool calls reach the original's name or path, or its
  `package.json` depends on the original's published package (json-server is
  on npm; wrapping it would pass every check). The name in the builder's
  own reasoning is recognition, not access: recorded, not voiding.
- **The oracle is a port**, because original tests are white-box and their
  toolchains rot (mitt's `esm` loader no longer runs on Node 25). Only Node
  built-ins; the program starts through `$APP_CMD`.
- **Ground truth is the original's observed behaviour**, not its tests or
  docs: original tests can be broken (json-server ships one). A check that
  fails on the original is not admitted; it is listed in `MAPPING.md` as
  excluded, with the reason.

## Fault attribution

| Location | Evidence |
|---|---|
| distill: omission | no spec claim covers the checked behaviour |
| distill: error | a claim covers it; the original contradicts the claim |
| distill: ambiguity | the claim also admits the rebuild's reading |
| build: intake / plan | (ShipLoop only) claim lost from the living spec / not planned or tested |
| build: implementation | covered (and planned), built wrong |
| oracle | the check depends on something the spec left free, or is flaky |
| unattributed | none holds; reported, never defaulted to the builder |

Change one side per comparison: iterate the distiller with the builder fixed,
and iterate ShipLoop on a fixed spec file.

## Case

**markedjs/marked @ef0704c** (37.2k stars, MIT): a Markdown parser and
compiler (TypeScript, 3,201 own lines, zero runtime dependencies) with a
library API (parse, lexer/parser/renderer, options, hooks, extensions) and a
CLI. Its 1,861 spec tests (CommonMark 0.31.2, GFM 0.29, marked's own
fixtures) and 192 unit tests pass on Node 25. Chosen as the first repository,
in descending star order, to pass every selection gate (below).

The pilot started on typicode/json-server; the owner switched away because
it fails the gate on size (733 own lines, 13 dependencies, one from the same
owner). Its round-1 E0/E1 results and learnings are kept in RESULTS.md.

## Selection gate: material value of its own

A case must carry material logic of its own, not be a thin layer that
composes other packages or its owner's other repositories: a rebuild of that
mostly re-composes the same packages and says little about the builder.
Serving static files or wrapping another product is too trivial (owner).

`scripts/select_repos.py` walks the most-starred JavaScript/TypeScript
repositories in descending order (owner: choose by stars) and takes the first
that passes, cheapest gate first: maintained (pushed within a year, not
archived or a fork); a rebuildable interface (`bin`: a CLI, or a server
started from one); not a monorepo; no git submodules and no runtime
dependency published from the same owner's other repositories; has tests;
material own code (`repo_value.py`: >= 1,000 own lines) and a feasible size
(<= 10,000). After distilling, `repo_value.py --spec` also reports the share
of spec evidence citing dependency code (starting bar <= 25%). The bars are
proposals the owner may reset.

Walk of 2026-09-27 (237+ repos): code-server fails (wraps VS Code as a
submodule), prettier (10 same-owner dependencies), hexo (7), json-server
(`lowdb`, and thin); **marked passes first**, then Modernizr and mocha.

## Replan 2026-09-27: Grok credits exhausted

Grok ran out mid-E3 (that run had also stalled: 4 tool calls in 25 min, a
thought loop talking to an imagined user). The most dire tests, in order:

- **T1 baseline rebuild on marked** — the first end-to-end rebuild → score →
  attribute; everything later assumes it works. Run on two builders in
  parallel, same spec: Claude Sonnet 5 (budget cap $15) and Codex
  `gpt-5.6-luna` at xhigh (owner has Codex credits), each isolated (Claude:
  project settings only; Codex: a CODEX_HOME holding only the sign-in).
- **T2 attribution** (one Opus 5.5 judge) on T1's failures, spot-checked.
- **T3 ShipLoop E2E on the mdkit case**, once, with the T1 builder that held
  up (the E2E harness needs a Codex host for Luna). The automatic Claude T3
  is held until both T1s score.

Owner, 14:35: move the builder to GPT-6 (Luna, `gpt-6-luna` at xhigh) instead
of Sonnet. The Sonnet T3 already running finishes as the matched pair of the
Sonnet T1; a GPT-6 Luna pair runs beside it on Codex credits: T1 rerun
(`rebuilds/l2`) and T3 through the harness's Codex host (`--host codex
--model gpt-6-luna --effort xhigh`; the host's own defaults are the stale
`gpt-5.6-luna`/`high`, so both are passed explicitly). Later rounds default
to GPT-6 Luna.

Owner, 15:11: GPT-6 Luna at `max` effort for everything. Defaults are `max`;
the initializer distills restarted at `max`; the xhigh Luna pair (T1
`rebuilds/l2`, T3 `mdkit-luna-1`) finishes as an xhigh datapoint while a
`max` pair runs beside it (T1 `rebuilds/l3`, T3 `mdkit-luna-max-1`).

Deferred: distill round 2, the second repository, repeats. Stall detector
(no tool call for N minutes = failed step) before any unattended run.

## Phase 2: prove distill as a spec initializer (owner, 15:00)

Intended use: initialize ShipLoop's spec for an existing repository that has
never run ShipLoop. The clean-room results prove only the tested surface of
one repository (marked: 2 of 307 rebuild failures traced to the spec), never
audit claims directly, and the clean-room prompt deliberately leaves
architecture out. Each repository is cloned into a temporary folder at a
pinned commit and distilled there; clones and specs are disposable.

- **A. Distill audit (no rebuilds):** 4 repositories of different shapes
  from the star-ordered walk; distill on GPT-6 Luna xhigh; measure accuracy
  (a judge verifies a random 40-claim sample against source), coverage (the
  repository's own test names mapped to claims), and architecture coverage
  (entry points, modules and responsibilities, data flow, key dependencies
  and why, configuration, errors, extension points, build and test).
- **B. Initializer mode** in `skills/repo-distill`: real names, evidence
  kept, an architecture-and-decisions section, written as ShipLoop's
  knowledge home (`docs/shiploop/README.md`, `spec.md` with stable `R-n`
  IDs, `environment.md`, `test-strategy.md`, per `skills/shiploop/references/project-knowledge.md`).
- **C. Proof of use:** one never-ShipLooped repository, one feature request,
  ShipLoop run cold vs after initialization (harness follow-on style);
  compare planning cost and turns, existing tests kept passing, feature
  checks, and whether ShipLoop reused the initialized spec. Only after A/B.

## Experiments

Execution Grok 4.7 medium; judge Opus 5.5 medium, one judge per round.

- **E0 oracle port** → admission gate. If the port cannot reach 100% on the
  original after one repair pass, the porter drops the failing checks and
  lists them in `MAPPING.md`.
- **E1 distill** → `spec_check.py`.
- **E3 baseline rebuild** → oracle → attribution (`attribute.py`: one Opus
  judge over the original, spec, rebuild, oracle and its TAP output). If
  distill faults appear, revise `prompts/distill.md`, redistill, rebuild: at most two rounds.
- **E4 = the harness case's first run.** Not a separate experiment path: build
  the case (below), run it once on the released ShipLoop with the last spec,
  then attribution. Compare with E3 descriptively only.

Round 1 of E0/E1 runs on the rev-1 prompts; the prompts now carry the plan's
later decisions (observed behaviour is the truth, `excluded` mapping rows,
positive checks, no wrapping the original). Round 1 is kept rather than
restarted: the admission gate and `spec_check.py` enforce those decisions
anyway, and any gap they show is a direct measure of what the prompt change
buys.

Every Grok step records turns, cost and wall time; a step that ends without
its output file is a failed step (inspect, fix the prompt, rerun), never
patched by hand.

## Then build (shape fixed by rev 2)

- **`skills/repo-distill/`**: the distill prompt (general repo → spec, with
  relationships and unknowns) plus an oracle-port mode, and `spec_check.py`.
  The attribution prompt stays in the harness; it is not part of distilling.
- **No new harness.** A json-server case in `test/shiploop_e2e/cases.json`:
  the prompt builds from a seeded `SPEC.md` (one new `seed` field copies it
  into the empty work directory), and the checks are the committed oracle
  (run via `$E2E_CHECKS`) plus the clean-room dependency check. Attribution
  is one post-run script over the run's work directory. The harness already
  provides runs, baselines, review and learnings. The oracle's run time is
  measured at admission; the harness's 180 s per-check timeout is raised for
  this case only if it needs more.

## Review of rev 1: unknowns and failure cases

| # | Unknown or failure case | Material? | Decision |
|---|---|---|---|
| 1 | Correct negative checks (e.g. unknown id → 404) pass on a 404 stub, so "no check passes on the stub" rejects a good oracle | yes, blocks admission | Admit on 100% original + most fail on stub; list stub-passers |
| 2 | Oracle flakiness (ports, file-watch timing) is read as build failures | yes, corrupts attribution | Run on the original twice; flaky checks dropped |
| 3 | Builder reads the original (it sits on the same disk) or recalls it | leak: yes; recall: no for the pilot | Transcript grep voids a leaking run; memorisation accepted, noted |
| 4 | Attribution judge is wrong | yes, it steers every fix | Spot-check verdicts by hand in the pilot; calibration by planted spec defects deferred until the loop runs repeatedly |
| 5 | Single runs are noisy, so E3 vs E4 differences may be chance | only for claims about ShipLoop vs baseline | Report descriptively; repeat only if a decision depends on it |
| 6 | E2 (a separate judge mapping oracle checks to claims) duplicates what attribution finds after a cheap baseline rebuild | no | **E2 removed** |
| 7 | A new `test/repo_oracle/` harness duplicates run, baseline and review machinery (S-12) | no | **Removed**: a case + seed field + oracle check instead |
| 8 | Later tiers (http-server, ni, less famous repos) | not yet | **Deferred** to after the pilot |
| 9 | Oracle files are derived from MIT-licensed tests | yes, if committed | Keep the copyright notice in the oracle directory |
| 10 | The rebuild needs a build step or a runtime other than Node | no for this case | Delivery contract pins `node <bin>`; revisit per case |
| 11 | "Relationships" section is unused by the rebuild | no, but the owner wants general use | Kept: one prompt section, no extra machinery |

## Review 2 (rev 3): what the first runs and E2E history add

| # | Unknown or failure case | Source | Material? | Decision |
|---|---|---|---|---|
| 12 | The builder installs the original's published package and wraps it | json-server is on npm (1.0.0-beta.15) | yes, voids the comparison silently | Dependency check in scoring and in the harness case |
| 13 | Distill and port are slow (8+ min, still reading at 48 file reads) | E0/E1 runs | only for iteration speed | Record time and cost per step; no change until a step exceeds ~20 min |
| 14 | A Grok step ends without writing its output (turn cap 150, or a summary instead of the file) | E2E history (cancelled sessions) | yes, else a missing file looks like an empty result | Missing output = failed step; rerun after a prompt fix |
| 15 | The oracle exceeds the harness's 180 s check timeout | harness `run_checks` | only if slow | Measure at admission, raise per case if needed |
| 16 | Spec and oracle both come from the same tests, so untested behaviour is neither specified well nor measured | E1 reads the tests | no: known coverage limit | Accepted; results state "tested surface only" |
| 17 | Distiller or porter edits the repository or leaves servers running | E1 runs the program | no: none observed (only my own lockfile; no orphan servers) | Nothing added; `git status` glance per run |
| 18 | E4 as a separate ShipLoop invocation duplicates the harness case | rev 2 | no | **Merged**: E4 is the case's first run |
| 19 | ShipLoop run cost/time ($25–35, ~1 h, sleep stalls) | E2E LEARNINGS runs 8b, P6 | once only | One run; harness already keeps the machine awake |
| 20 | Citation formats the checker cannot parse (ranges with en-dash, backticks) | spec_check regex | unknown until E1 lands | Fix the checker, not the prompt, if it misparses |

## Review 3 (until-loop pass 1)

| # | Unknown or failure case | Source | Material? | Decision |
|---|---|---|---|---|
| 21 | Original tests can be broken (json-server: 1 of 128 imports a missing path; upstream's glob never runs it) | E1 transcript, rerun by hand | yes, defines the oracle's truth | Ground truth = observed behaviour; failing original checks excluded and listed |
| 22 | Attribution had no runner and its prompt named a `failures.txt` nothing writes | flow check | yes, E3 could not complete | `scripts/attribute.py`; prompt reads `oracle.tap` |
| 23 | Distiller and porter probe the running original and write scratch files under `/tmp` | E0/E1 transcripts | no: grounding is good, scratch is harmless | Nothing added |
| 24 | Stub never exits, so CLI-error checks (bad file, bad option) wait out their start timeout against it | stub design | no: only slower admission (~10 s per such check) | Accepted |

## Review 4 (until-loop pass 2)

| # | Unknown or failure case | Source | Material? | Decision |
|---|---|---|---|---|
| 25 | Transcript-wide grep voids a run whenever the builder merely recognises the product (the name in its reasoning), conflating accepted memorisation with access | rebuild.py design vs item 3 | yes, would void most runs of a famous repo | Void only on tool calls reaching the name/path, or the dependency; record recognition separately |
| 26 | Builder writes no `package.json` bin, so the program cannot start | delivery contract | no: scored as a failed rebuild with the error recorded | Nothing added |
| 27 | npm installs in the isolated HOME start from an empty cache | grok_step design | no: slower only | Accepted |

## Review 5 (until-loop pass 3)

No new material unknown, flow gap or error condition; nothing further to
prune. Wording only: intro, case paragraph reflow, who drops failing checks.

## Review 6: learnings from E0/E1 round 1

| # | Unknown or failure case | Source | Material? | Decision |
|---|---|---|---|---|
| 28 | Against the stub, each oracle check retries startup (8 × 10 s, a good token-based readiness probe), so the stub run never finishes and admission crashed | E0 admission | yes, blocked admission | Stub run bounded (180 s); a check that never reported did not pass; leftover stub processes killed |
| 29 | Distiller cites dependency source without the `node_modules/@` prefix | E1 spec_check (10 of 141 citations) | checker only | Checker resolves dependency paths; not a distill fault |
| 30 | An observable value embeds the original's name (`$schema: ./node_modules/json-server/schema.json`); the distiller split the string to pass the leak check, and the porter asserted the exact value | E1 spec D-18, E0 normalized-adapter check | yes for the clean room (name recoverable); accepted for round 1 | Round-2 prompts: branded values are specified with the new name and asserted only by presence/shape |
| 31 | A candidate may be a thin composition of other packages, so a rebuild re-composes them and measures little | owner, 2026-09-27 | yes, for case selection | Selection gate (`repo_value.py`); json-server fails on size, kept as pilot; later cases must pass |
| 32 | Static file serving (http-server) passes the size gate but is still trivial; size alone does not measure material logic | owner | yes | Switched to star-ordered selection with aggregation gates; marked chosen |
| 33 | A repo can hide aggregation from the size gate: submodules (code-server wraps VS Code) or its owner's split-out packages (hexo, prettier, json-server's `lowdb`) | selection walk | yes | Gates for submodules and same-owner runtime dependencies |
| 34 | marked is mainly a library: its hooks/extensions API is reachable only by importing it, not through the CLI | case switch | yes | Oracle and build contract reach the program through `APP_CMD` and/or `APP_MODULE` (the package's import entry); stubs for both |
| 35 | A watcher's expiry killed the run it launched (json-server E3 died at 30 min) | E3 round 1 | yes | Chains run detached (new session); watchers only tail their logs |
| 36 | "marked" is an ordinary word, so grepping tool calls for it would void innocent runs | case switch | yes | Tool calls are checked for `markedjs` and paths; the package name is checked only as a dependency (`--forbid-dep`) |
| 37 | Evidence citations carry the original's name in file paths (`src/marked.ts`), so a spec that cites well leaks by construction | marked E1 | yes, clean room | Builder receives the evidence-stripped view; leak check runs on that view |
| 38 | A step can stall in a thought loop without failing (Grok E3: 4 tool calls in 25 min) | marked E3 on Grok | yes, for unattended runs | Stall detector before unattended runs; recorded |
| 39 | The builder host's global setup leaks into the clean room (Codex: global AGENTS.md, hooks, memories, browser/GitHub plugins) | Codex host | yes | Isolated CODEX_HOME with only the sign-in |
| 40 | A renamed product renames its public API (`Marked` → `Mdkit`), so an oracle admitted against the original fails every library check on a correct rebuild (35/1,759 raw) | T1 scoring | yes, it inverted the result | Scoring and the case check load the rebuild through an alias module from a rename map; the original still passes 100% through it |
| 41 | A sandboxed judge cannot read inputs linked from outside its directory | T2 | yes, attribution read nothing | Inputs copied in (without node_modules/.git) |
| 42 | `--max-budget-usd` is checked after the fact: the Opus judge cost $24.74 against a $15 cap | T2 | yes for spend planning | Budget judges at ~2x the cap; attribution grouped by root cause keeps it to one pass |
