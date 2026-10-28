# ShipLoop on an existing repository: the baseline (design, 2026-10-28)

Status: **proposal, revision 2** (after the experiments and Astra's max review). Execute: ask. Owner decisions:
section 9. Evidence: [the journal](shiploop-brownfield-baseline-journal.md) and
[docs/experiments/brownfield-baseline-20261028/](experiments/brownfield-baseline-20261028/).

## 0. The answer

**Reverse-engineer progressively, inside the stages that already read the code, and keep what they learn as
committed knowledge.** Don't add a whole-repository pass up front, or a separate heavy stage.

1. **Census (script, at run start, seconds).** A generic map of the repository: areas and their weight, tests,
   documentation, decision records found by content, instruction files, hot spots. Measured at 0.1 to 1.5 s, on
   repositories up to 1.16 million lines.
2. **Discovery's close writes the as-is account into the living files**, not into the disposable
   `RUN/notes/current-system-baseline.md`, where it lives today. The account covers:
   - in `spec.md`, the behaviour of the flows the request touches, as contract-level `R-<n>` with
     `Status: baseline`, a `Source` and a locator;
   - in `architecture.md`, the decisions those flows rest on, as `AD-<n> (inherited)`, with each team decision record
     linked rather than copied;
   - the open questions and conflicts the spec must settle, as `Q-<n>`. Later packets quote them by value and the
     spec answers each by ID: in the experiments, a baseline that only sat in the repository was not fully used.

   ShipLoop checks the locators, commits the account, and takes a **comparison snapshot**. The spec then writes, and
   ShipLoop measures, only the delta.
3. **The spec and the plan inherit.** The spec decides preserve, modify, retire or add against those entries. The
   plan records each existing decision it relies on and decides only what the request adds.
4. **One traceability rule, checked by script.** Silence preserves. Any entry that existed when the run began, if it
   changes, needs a basis of the right kind:
   - an **obligation** (a documented or accepted requirement, or a team decision record) needs a request sentence,
     `Basis: S<k>`;
   - a **default** (observed behaviour, or a decision read off the code) needs a request sentence or a recorded
     assumption;
   - an **evidence correction**, where behaviour is unchanged, needs `Corrected: <locator>`.

   The script checks only that the basis is there and well formed. Whether it really justifies the change stays with
   review and the preservation tests.
5. **Later runs re-verify only what a script says is stale, and deepen only flows nobody recorded.** Knowledge
   accumulates per flow over runs. The repository's own test suite remains the executable baseline for everything no
   run has touched.

Why this shape, and not the separate baseline stage of revision 1:

- **Accuracy is good.** Three Opus-judged baselines: 26/27, 47/48 and 39/42 sampled claims correct, 0 wrong,
  0 unsupported, every expected fact covered.
- **But a dedicated pass costs too much.** It took 15 to 30 minutes on Sonnet. A whole-repository pass took 50
  minutes and 273 KB. A later deepen pass cost more than the first, because it re-verified fresh entries.
- **And within one run, a strong planner did not need it.** Plans with and without a baseline made the same
  decisions on two repositories. The value is durability, traceable change and earlier open questions, so the cost
  must stay near zero over the reading the run does anyway.

## 1. What happens today on an existing repository

| Stage | What it writes (source) | What that means for an existing repository |
|---|---|---|
| intake | the request mapped to S1..Sn (`shiploop_prompts.DUTIES["intake"]`) | no step names the areas of the repository the request touches |
| discovery | `environment.md`, plus the as-is account in `RUN/notes/current-system-baseline.md` (`DUTIES["discovery"]` steps 10 and 13) | the recovered system lives in a **run note** the run directory discards |
| research | resolves unknowns; reopens that run note (`DUTIES["research"]` step 8) | |
| spec | `spec.md` R-<n> (`DUTIES["spec"]` step 1) | on a first run there is no committed spec, so `spec.md` holds the **new feature only** |
| test-strategy | harnesses in `environment.md`, real-boundary checks in `architecture.md` | preserved behaviour comes from the run note (step 2) |
| plan | AD-<n> in `architecture.md` (`DUTIES["plan"]` steps 7-9) | step 8: "**Decide** the interaction structure", with no notion of a decision the repository already made |
| prepare | close: the three files must exist (`shiploop_knowledge_home.CLOSES`) | they do, describing the feature, not the product |

Consequences, traced to code:

1. **The recovered system is not inherited.** A later run's knowledge home (`shiploop_knowledge_home.LIVING`) knows
   only what ShipLoop built.
2. **Existing behaviour is unprotected.** The retention check (`shiploop_knowledge_home.check`, `_RETAINED`)
   protects only IDs already committed.
3. **No inherited decisions.** Every AD-<n> is a decision some run made.
4. **The delta is unmeasurable.** `record_baseline` stores HEAD at `init` (`shiploop_protocol`), so on a first
   brownfield run `spec_diff` shows everything as new.
5. **Untested in practice.** The 2026-09-19 guidance ([current-system-baseline.md](../skills/shiploop/references/current-system-baseline.md))
   was validated by transport tests and fresh-reader smoke only ([plan](shiploop-current-system-baseline-plan-2026-09-19.md)).
   Of the 13 E2E cases, one is brownfield (`user-listing`, 149 lines), and it has never run live.

## 2. What the experiments showed

Subjects were Sonnet agents (exploratory) and judges were Opus 5.5. Everything ran read-only on pinned public
repositories. Full numbers are in [the journal](shiploop-brownfield-baseline-journal.md); costs are in
[cost-ledger.tsv](experiments/brownfield-baseline-20261028/results/cost-ledger.tsv).

| Question | Result | Status |
|---|---|---|
| Can a script map a repository cheaply and generically? | Yes: 0.1-1.5 s, 40-77 lines, instruction files surfaced. Decision records are found by content: 15 of log4brains' 19 real records, plus 16 fixture and template hits, so the census offers candidates and discovery decides; 58 on cosmos-sdk (one is its template) | firm |
| Is a model-written baseline accurate? | Yes on what it anchors: judged 26/27, 47/48, 39/42 correct, 0 wrong, 0 unsupported; every expected fact present; C1 resolves 100% of locators after two checker fixes | interim (n=1 per repository) |
| Does it find what a planner needs? | Yes: the `paginate` rounding defect behind the `floor-pages` calibration variant; a hidden stdout contract (`init` parses `adr list --raw`); retry side effects (SMS quota, group re-calls, test sends); a doc-versus-ADR conflict; an API throttle the docs promise and no code implements | interim |
| Does it reuse the team's records? | Yes: all 19 log4brains ADRs mapped to AD-<n>, the 2 superseded ones under Superseded, fixtures and templates excluded | interim |
| What does it cost? | Scoped: 870, 1,405 and 1,795 s (27-61 KB). Whole repository: 3,023 s and 273 KB, and its format drifted (51 entries unparseable). Deepen pass on a later request: 2,180 s, though every entry was still fresh | firm: too costly as a separate pass |
| Does a baseline change a strong planner's decisions? | No. node-base: all 4 plans found and fixed the rounding defect. healthchecks: T2 reused the existing API, T1 extended `sendalerts` and E1 made the requested Celery move, the same way in all three arms | interim (n=1-2 per cell) |
| What does it change? | With a baseline, every changed decision carries a basis the script can check (the two node-base runs changed the same 5 entries). Plans cost 6-45% more time. Fact coverage of the hardest request was not better: 31 of 41 facts handled with a baseline, against 32 (A0) and 34 (A0w) | interim |
| Was the baseline used? | Not fully: the baseline-arm plan missed two facts its own baseline states (an error longer than 200 characters blocks the retry; each retry spends paid SMS or call quota). A file in the repository is not consumed; a quoted, numbered question is | firm for this case |

Three things the experiments did not test:

- a weaker or faster subject, such as the E2E default DeepSeek flash, where a recorded baseline may matter more;
- reuse across the stages of one real run, where each packet starts with cleared context;
- a real second run that inherits a committed home.

## 3. The flow

```
 init ──► intake ──────► discovery ─────────────────────► research ──► spec ─────► test-strategy ──► plan ──────► prepare
 census   names the      environment, commands, the        conflicts    delta vs    delta + the       inherits     close
          areas and      baseline test run, AND the        and open     baseline;   preservation      AD-<n>;
          flows it       as-is account of the touched      questions    Basis on    set only          records the
          touches        flows in spec.md / architecture.md first       changes                       ones it
          (hypothesis)   ─► C1 check, commit, snapshot                                                relies on
```

- **Placement: discovery's close.** Discovery already does this recovery (`DUTIES["discovery"]` steps 10 and 13); the
  change is its output, not a new activity. A separate stage would break reconciliation
  (`shiploop_planning_revision.RECONCILIATION_TARGETS = PLANNING_STAGES[:4]` would drop test-strategy). It would also
  need skip dispositions, and it would add packets without adding planning time to spend.
- **Touches are a hypothesis.** Intake names candidate areas and flows from the census and the request, each with
  the sentence S<n> that touches it. Discovery validates them through the affected flow: entry point, callers and
  providers, persisted state, configuration, tests, cross-cutting boundaries. Plan and step-plan reconcile them with
  the declared `paths` and `expectations`; integrate reconciles them with the paths that actually changed.
- **Comparison snapshot.** `RUN_BASELINE` stays the run's start. Discovery's accepted close records a second marker,
  the commit of its knowledge, once. `spec_diff` measures from it. This one commit is fail-closed: research does not
  start until it exists (today `_knowledge_close` tolerates a failed commit and lets the next stage commit it).
- **Greenfield and current homes cost nothing.** A census with no code skips the account. Touched flows that are all
  recorded and `fresh` (check C3) skip re-verification.

## 4. What discovery's account holds

### 4.1 Scope and size

- **Only the touched flows, plus the cross-cutting rules that apply to them.** A concern that does not apply is one
  line in the overview (`Background work: none`), never an entry. On node-base, the revision-1 packet produced
  R-7 "Background work", R-8 "Identity and access" and R-9 "Privacy and security" for a repository with none of them.
- **Requirements only where the run touches behaviour or tests are missing.** The repository's own tests are its
  executable baseline. An R-<n> records the contract the change alters or must keep, at contract level. Public API
  identifiers are allowed, because they are the caller's contract.
- **Decision records are indexed broadly but materialized narrowly.** One table links every record, with its
  status. An AD-<n> is written only for a decision that constrains the touched flows.
- **History on a question only.** No routine hot-spot or history study.
- **An honest partial account.** What could not be verified within the allowance is `inferred` or an open item, and
  dependent work stays unready. The account never claims coverage it did not earn.

### 4.2 Two dimensions: evidence and authority

| Evidence (`Source:` class) | Meaning |
|---|---|
| `documented` | the README, docs, a decision record or a contract says it |
| `asserted` | a named test asserts it (the test exists) |
| `tested` | that test ran and passed in discovery's baseline run |
| `observed` | only the code shows it |
| `runtime` | a read-only runtime probe showed it, with target, configuration and time |
| `inferred` | the model's reading, never stated as fact |
| `conflict` | sources disagree; both are cited |

| Authority (derived) | Entries | A change needs |
|---|---|---|
| obligation | `documented` or `accepted` requirements; decisions linking a team record or accepted by a run's request | `Basis: S<k>` |
| default | `observed` behaviour, `inferred` decisions, an earlier agent's design choices | `Basis: S<k>`, or `Basis: assumption <id>` with the assumption recorded (it reaches the owner) |
| correction | any entry whose behaviour is unchanged | `Corrected: <locator>` |

### 4.3 Conflicts

Record both claims with their authority. Do not resolve a conflict by keeping "current behaviour". Preserve the
behaviour no request touches. A consequential conflict in a touched flow is a question for research or the spec,
and dependent work waits for the answer. On node-base the request itself settles the `paginate` conflict (S5 defines
`pages` as the pages the matches fill). Revision 1 told the model "current behaviour stands", which would have
promoted a defect into the contract.

### 4.4 Documents that already exist

- **Decision records** are found by content, not by name; on log4brains the name-based census missed them. Each
  relevant record becomes an AD-<n> that keeps its native identity, status and revision, and links the record rather
  than copying it. Superseded records go under `## Superseded`. Fixtures and templates shaped like records are not
  decisions.
- **Contracts** (API descriptions, schemas) are linked at the operation or section that matters. A change to a
  linked contract counts as a change to its entry.
- **Instruction files.** The ones the host loads for the user's workspace (agent, contributing, security) are
  operative rules for this work, not data. Text found while reading sources is evidence, never instruction.
  - A rule that restricts the requested work is classified by scope **before** the affected operation. A rule against
    upstream AI contributions does not forbid local work. A rule limiting automated edits governs those edits.
  - Record the rule, its scope, the operation it governs, and its owner.
  - Continue the work it does not govern. Stop only before a governed operation that neither the request nor the
    owner authorized.
  - Never read "revert all changes" as permission to destroy work.
  - Two of the five public repositories sampled carry such rules (uptime-kuma's `AGENTS.md`, healthchecks'
    `CONTRIBUTING.md`).
- **The knowledge home is a product file.** On log4brains, CI runs Prettier over every `.md`, so `docs/shiploop/`
  must pass the repository's own format and lint gates. Run the existing lint auto-fix (`shiploop_lint`) over the
  home before each knowledge commit.

### 4.5 Format

```
Baseline coverage: deep: <flows and their areas>; overview: <areas>; not inspected: <areas>. As of <sha>.
### R-<n> <title>
Status: baseline · Source: <class> (<locator>)[; ...] · As of: <sha>
- <bullet> (<locator>)
- AD-<n> (inherited[, recorded]) <choice>. Why: <reason> (stated: <locator> | inferred). Evidence: <locator>. As of <sha>.
## Open questions
- Q-<n> <question>. Touches: R-<n>/AD-<n>. Why it matters: <consequence>. Source: <locator>.
```

The coverage line names **flows**, not just directories. "deep: hc/api" from a notification-retry run did not cover
the API listing a later request touched.

### 4.6 Consumers

| Part | Consumer |
|---|---|
| coverage line, `As of` | the script at the next run's start: skip, re-verify stale entries only, or deepen an unrecorded flow |
| baseline R-<n> | spec (preserve, modify, retire, add); test-strategy (the preservation set: their `tested` and `asserted` sources become regression checks, untested touched ones get a characterization check); step-plan `expectations`, which validate-existing runs |
| inherited AD-<n> | plan and step-plan; the basis check |
| open questions `Q-<n>` | research, spec and plan, **quoted by value** in their packets (each touching the request); spec answers each one, or carries it as an assumption with its owner; a script checks that every quoted `Q-<n>` is answered by ID |

**Consumer scope (Astra F1).** Test-strategy and plan cover "every criterion" today. They must read the run's
delta (the spec changes since the comparison snapshot) plus the preservation set, never the whole recorded
catalog. Otherwise one adoption creates work for the entire product.

## 5. The scripts (prototypes, 13 tests)

[census.py](experiments/brownfield-baseline-20261028/census.py) and
[baseline_check.py](experiments/brownfield-baseline-20261028/baseline_check.py)
([tests](experiments/brownfield-baseline-20261028/test_baseline_check.py)) reuse ShipLoop's own parsers
(`shiploop_item_scope.classify`, `shiploop_knowledge_home._entries`, `shiploop_request.sentences`/`index`/`cited`).

- **C1 sources** (discovery's close; locator validation only). The files exist, each entry has a Status and a
  Source of known classes, and no ID starts twice. Every locator resolves: the path exists, the quoted symbol or
  test name is in that file, and a `path:line` is in range. Evidence is demanded only of found entries; a new
  `(accepted)` decision has no code yet.
- **C2 basis** (every stage that edits the home; traceability only). This is the table in 4.2:
  - `S<k>` must be in 1..N, counted from the request's canonical index;
  - an assumption must name a recorded one;
  - an `As of` refresh is no change;
  - `step_spec_refusal` keeps governing what implement may add.
- **C3 freshness** (a notice at run start). Each entry is `fresh`, `stale` or `unknown` against its own evidence
  commit: its `As of`, or the commit before the one that wrote it.
  - It is `stale` when a cited file changed, was deleted, or has uncommitted edits.
  - It is `unknown` without usable evidence.
  - Only `fresh` lets a run skip re-verification. The packet quotes the stale and unknown entries, so the model
    re-verifies those and nothing else. On the deepen run, C3 rated all 69 entries fresh in seconds, and the model
    spent 36 minutes anyway.

Both checkers needed fixes that the experiments forced:

- **C1:** dotted symbols mistaken for paths; a prose line starting with an ID that shadows the real entry.
- **C2 and C3:** Astra's negative cases.

## 6. Changes, by file and stage

| Where | Change |
|---|---|
| new `shiploop_census.py` | the census; `init` and `workspace start` save `RUN/census.md` and `RUN/census.json`; a filesystem walk when there is no Git, because a project with no local code is not necessarily new (remote systems) |
| `DUTIES["intake"]` | quote the census; a `touches` field: candidate areas and flows, each with its S<n> |
| `DUTIES["discovery"]`, `STAGE_FILES["discovery"]` | steps 10 and 13 write the account into `spec.md` and `architecture.md` (scope rules 4.1, format 4.5, policy rule 4.4); `STAGE_FILES["discovery"]` gains both files; C1 at its done; the comparison snapshot after its commit |
| `shiploop_knowledge_home` | C1 and C2 inside `check`; C3 at init; the snapshot marker beside `RUN_BASELINE`; `spec_diff` from the snapshot; `_entries` prefers a list item or heading start over a prose line that begins with an ID |
| `DUTIES["research"]` | conflicts and consequential `inferred` entries become research questions; the open questions `Q-<n>` are quoted by value |
| `DUTIES["spec"]` | start from the baseline R-<n>; Basis or Corrected on every changed entry; answer every quoted `Q-<n>` (or carry it as an assumption), checked by ID; settle each consequential conflict |
| `DUTIES["test-strategy"]`, `DUTIES["plan"]` and their done-when lines | read the delta plus the preservation set; plan step 8 keeps existing placement, channels and background work, records each inherited decision it relies on, and decides only what the request adds |
| step-plan | each `works` expectation cites the R-<n> or AD-<n> it relies on |
| carry-forward, document | entries an item changed become `(accepted)` or gain the new test as a `tested` source; the coverage line gains the flows built |
| knowledge commit | the repository's lint auto-fix over `docs/shiploop/` first |
| `references/current-system-baseline.md`, `project-knowledge.md` | rewritten to this account; the run-note route removed (one supported version) |
| E2E | run `user-listing` live; add a medium brownfield case with a follow-on request on the same repository |

## 7. Large repositories

- The census is whole-repository and nearly free. Its JSON keeps the full directory inventory (cosmos-sdk: 206
  directories against 30 map rows); the Markdown map is a display, never the coverage universe.
- Depth follows the request's flows, not directories, and accumulates across runs.
- C3 makes revisits cheap. The cost that remains is deepening a flow no run has recorded, roughly what a planner
  spends reading that flow anyway (13-27 minutes per plan probe on healthchecks with no baseline).
- A whole-repository account is available as an explicit request ("record this repository's baseline") through
  the same duties. The measurements argue against it as a default: 50 minutes, 273 KB, and format drift on a
  60,000-line repository.

## 8. Alternatives considered

| Alternative | Verdict and evidence |
|---|---|
| Separate baseline stage after discovery (revision 1) | Deferred. It breaks reconciliation as wired, needs skip dispositions, and the planning allowance is shared. Revisit only if a controlled comparison (same duties, outputs and budget, cold restart) shows a gain. |
| One-time adopt run | Optional later entry point, with the same duties. It delays the feature and still needs refresh and deepening per request. |
| Whole-repository initializer (repo-distill, 2026-09-27) | Not the default: 3,023 s and 273 KB against 1,795 s and 61 KB scoped on the same repository, and its format drifted. The scoped-versus-whole comparison is in the journal. |
| Packet wording only (the plan inherits, with no recorded baseline) | Takes most of the single-run benefit for free. A0w plans kept every decision, as A0 and A1 did. It is part of this design, but it leaves nothing for the next run. |
| Keep the run note, copy it to the home at carry-forward | Too late: the spec cannot measure a delta against it, and the plan cannot inherit from it. |

## 9. Decisions for the owner

| # | Decision | Recommendation |
|---|---|---|
| D1 | Placement: discovery's close, a separate stage, or an adopt run | discovery's close now; a separate stage only after a controlled comparison |
| D2 | The traceability rule covers every entry that existed at the run's start, with obligation, default and correction tiers | yes |
| D3 | Conflicts are resolved before dependent work, never by "current behaviour stands" | yes |
| D4 | When a repository keeps decision records, should ShipLoop also write its new decisions in the team's format (a product file written at `document`)? | yes, linked from AD-<n> |
| D5 | An instruction-file rule that restricts the work: classify its scope, continue ungoverned work, stop before a governed operation | yes; stop only before the governed operation |
| D6 | Charge discovery's account to the 30-minute planning window | yes; bound it by the remaining allowance |
| D7 | The E2E evidence needed before building: `user-listing` live, plus a medium brownfield case with a follow-on run, on the E2E subject | yes; this is the measure of cross-run value |
| D8 | Fix the `_entries` shadowing edge now (independent of this design) | yes, a small fix with a test |
| D9 | Open questions as `Q-<n>` in the knowledge home, quoted by value into research, spec and plan, each answered by ID (script-checked). This is also the "key questions anchored" step of the planning research loop the owner listed on 2026-10-11 | yes; it is the one change the experiments show a recorded baseline needs before it adds value |

## 10. Smallest first build

1. Discovery writes the touched-flow account into `spec.md` and `architecture.md` (4.1-4.5); C1 at its close; the
   comparison snapshot; `spec_diff` from it.
2. Spec, test-strategy and plan wording: delta plus preservation set; the plan inherits; Basis or Corrected on
   changes; C2 as traceability; the open questions `Q-<n>` quoted by value, and answered by ID at spec.
3. C3 as a notice that the packet quotes; nothing skips on `unknown`.
4. Validate on node-base with two follow-on requests (one revisiting the same flow, one touching an unrecorded flow
   in the same directory). Include a cold restart, a commit-failure retry, and a baseline correction after the
   spec. Then run the medium case on the E2E subject.
