# Run Review data contract

The Run Review page is a **static template**. It holds no run data and no content defaults: everything it shows
lives in the artifact's database (capability `db`) as the collections below, and is exported to the repository as JSON.
To show a new run, write documents. Do not edit or republish the template for data.

| Piece | Where | Changes when |
| --- | --- | --- |
| Template | `template/index.html`, one file, published once with `capabilities: {db: {}}` | the page's behaviour changes (republish, note it in the journal) |
| Defaults | `defaults/*.json`: starting phases, groups, criteria, prompt settings | an expectation changes (in the repo, with a revs entry); written over the page's replicas by `export.py --defaults --live` |
| Contract | this file | a field is added, renamed or removed (change the template, exporter and tests together) |
| Data | the `db` collections below | every iteration |
| Exporter | `scripts/export.py`: a run output directory in, documents out; `--check` and `--docs` read a review bundle | the run layout changes |

Anything not in this contract is ignored by the page. A missing optional field hides its panel.

## Collections

**`expectations/<key>`** (what we expect; the page only reads them. Changing one is an option the owner ticks and a prompt applies from the repo)

| Field | Type | Notes |
| --- | --- | --- |
| `kind` | `phase` \| `group` \| `criterion` | required |
| `order` | number | sort key: phases `0..N-1`, groups, criteria within their group |
| `title` | string | phases, groups, criteria |
| `short` | string | phases only: the chevron subtitle |
| `text` | string | the expectation wording; for a group, a one-line blurb |
| `group` | string | criteria only: key of a `group` doc; none means "Other" |
| `clauses` | array of string | criteria only: the `S-n` clauses of `test/shiploop_e2e/SPEC.md` it serves (empty when none does) |
| `revs` | array of `{at, from, to, reason, obs?, option?}` | appended when an expectation is revised (by the prompt, from the repo); `option` names the option that asked for it; never rewritten |
| `updatedAt` | ISO string | |

Keys: `phase-<order>`, `group-<name>`, a short id for a criterion (`P1`, `B1`). The number of `phase` docs sets
the number of columns in the flow; `Observed` states in a run's `phases` array align with their `order`. A database
that still holds `iter-<id>` documents or an `iterations` collection from the earlier page keeps them (the committed
snapshot preserves them); nothing reads them. An expectation has **no status**: how it stands for a run is derived by the
page (the chip in step 2) from the run's open findings and its review, so it cannot disagree with them. The worst `effect`
among the open findings that apply to the run wins (`broken`, then `bent`); an open finding with no `effect` reads "not
rated"; with no open finding it reads "holds" only when the run's review gives a one-line `basis` for the criterion,
otherwise "not examined". Findings that are fixed, accepted or re-expected do not count.

**`runs/<key>`** (one document per run output directory)

| Field | Type | Notes |
| --- | --- | --- |
| `key`, `name` | string | required |
| `order` | number | required; sort key |
| `release` | string | required: the plugin and ShipLoop version under test |
| `phases` | array of `done` \| `running` \| `blocked` \| `none` | required; aligned with the phase docs |
| `time`, `imp` | string | required: short text shown in the run header |
| `refusals`, `glue` | number | optional: omitted, never 0, when the harness names the counter unmeasured (`shiploop_failures`, `model_glue`: a host whose events cannot show it, such as Claude's). The header reads "refusals not measured" |
| `unmeasured` | map of string | the reason for each measure that is absent: the harness's reason for each counter it could not measure (`metrics.json` `unmeasured`), and one under the run field's own name for each measure below that is missing (`calls`, `contextPeak`, `contextWindow`, `compactions`, `improvePasses`, `improveMin`, `visitContext`; the harness names the first and third `model_calls` and `window_tokens`, and a peak with no reason of its own takes the calls' reason). `{}` when everything was measured. A `metrics.json` without the key is refused: regrade the finished run first |
| `improvePasses` | number | optional: Improve review passes over every `improve/<action>/` child, from each child's `terminal.json` `progress.action_number`. Absent, with a reason in `unmeasured`, when any child has none (a sum over an unknown part is unknown). `0` when the run has no Improve child |
| `improveMin` | number | optional: minutes spent in Improve, the sum over children of `improve/<action>-bind.md` to `improve/<action>/receipt.md` by file time. Absent, with a reason, when any child lacks either file or its times run backwards. A child still running when the run stopped has no receipt, and the run's `improveMin` is then unknown |
| `calls` | number | optional: model calls of the main thread (unique assistant messages for Claude, usage events for Grok, rollout calls for Codex), from `metrics.json` `model_calls`. Chain workers and Improve agents report elsewhere and are not in it |
| `contextPeak`, `contextWindow` | number | optional: the largest context one call held, and the model's context window (tokens). Both main thread. The peak is **not the same quantity on every host**: Claude's is the call's input side (input, cache reads and cache writes); Codex's is a call's total tokens (input plus that call's own output), so for the same context it reads higher by the output share (about 3% for Luna). Compare a peak within a host. Absent, with a reason, when the host did not report it |
| `compactions` | number | optional: context compactions of the main thread. Claude's events carry none, so it is absent there with the harness's reason; `0` is a measurement |
| `wallMin` | number | wall minutes so far or in total |
| `host`, `model`, `effort`, `case` | string | |
| `status` | `done` \| `active` \| `paused` \| `blocked` \| `failed` | the ShipLoop run status; a stopped (paused) run is `paused`, not `active` |
| `startedAt`, `endedAt` | ISO string | |
| `verdicts` | object of booleans | invoked, plugin, process, shiploop, committed, checks |
| `stages` | array of `{stage, outcome, min?, turns?, packetBytes?, resultBytes?, action?, skipped?, seeded?, improve?, context?}` | one row per accepted visit, in `state.md` history order; `min` is the accept-to-accept delta from `timeline.json`, never the harness's stage metric. `min` is **null** (the page shows "n/a") when the visit has no accept stamp, the visit before it has none (its start is then unknown), its stamp is earlier than the one before it (stamps running backwards: unknown, neither negative nor clamped), or the harness seeded the visit; never 0. Fields below |
| `stages[].action` | string | optional: the action id of the visit (`state.md` history). The Improve child and the packet file carry the same id |
| `stages[].skipped` | `true` | present only when true: `packets/` holds files and none is `<action>.md`, so the engine skipped the visit ("Not applicable to this item") and issued no packet. No summary text is read; a model-authored "Not applicable:" visit has a packet and is work. Absent when `packets/` is empty or missing (unknown) |
| `stages[].seeded` | `true` | present only when true: the E2E harness recorded the visit itself (`--seed-at`) without doing it. They are the first `len(seeded.skipped)` history rows, taken from `result.json` `seeded` and used only when their stage names match `seeded.skipped` in order (else none is marked and `facts.md` says why). A seeded visit has `min` null and is neither work nor `skipped` |
| `stages[].improve` | map `{passes?, min?}` | present when the visit started an Improve child: `passes` from `terminal.json` `progress.action_number`, `min` from `improve/<action>-bind.md` to `improve/<action>/receipt.md` by file time. A member is omitted when unknown (`min` when either file is missing or the times run backwards), never 0 |
| `stages[].context` | map `{calls?, peak?, peakPct?, compactions?}` | present only where the harness measured that visit's context: the main thread's calls, the largest call's tokens (`peak`, a call's total tokens on Codex, see `contextPeak`), `peakPct` of the window, and compactions inside the visit. Today only a Codex run with rollouts has it. The harness's stage rows carry no action id, so they are matched to the visits by position in the history and used only when their count and every stage and outcome agree; else no visit has a context. When no visit has one, `unmeasured.visitContext` says why |
| `knowledge` | object `{fileName: bytes}` | sizes of the planning documents the run committed (spec, test strategy, plan, ...) |
| `failures` | array of `{verb, line}` | ShipLoop commands that exited non-zero; omitted with `refusals` when unmeasured |
| `evidence` | string | path of the output directory (local, not durable) |

**`backchain/<id>`** (a loop ledger; id `<runKey>-<loop>`; none is written when a run has no loop; none is written for a run without a loop)

`run`, `loop` (the owning stage name such as `plan`, `step-plan` or `carry-forward`, or `none`), `phase` (order), `order`, `title`, `stageMin` (number or null),
`segments` (array of `{label, min, kind, note, pass?, change?, streak?}`), `facts` (array of `{k, v}`).
`kind` is `added`, `wasted`, `insurance`, `unclear` or `neutral`. A pass segment has `pass` (1-based), `change` (what the
pass changed, from candidate digests) and `streak` (the clean streak after it). When `stageMin` is set the segments' minutes
sum to it. A hand-set verdict is interim; the default for an unjudged pass is `unclear`.

**`observations/<id>`** (the page calls them findings; the collection name stays)

| Field | Type | Notes |
| --- | --- | --- |
| `phase` | number | a phase `order`; with the run's stage rows it draws the "where" strip on the card (no authored picture needed) |
| `criterion` | string | an expectation key |
| `kind` | `defect` \| `recovered` \| `decision` \| `noise` \| `added` \| `wasted` | |
| `run` | string | a run key or `any` |
| `runs` | array of string | optional: the run keys it applies to; overrides `run` (`any` in the list means every run) |
| `status` | `open` \| `fixed` \| `accepted` \| `reexpected` | a missing status reads as open |
| `title`, `expected`, `observed`, `evidence` | string | `expected` and `observed` carry the measured numbers; `evidence` is a path or commit |
| `effect` | `broken` \| `bent` | optional: how an OPEN finding hits its expectation. An open finding with no effect is "not rated" |
| `advice` | string | optional: Claude's recommendation, one to three sentences; an inference is marked "Inferred:" |
| `figure` | object | optional illustration of expected versus seen numbers (below) |
| `createdAt` | ISO string | orders the list |

`figure` is a small structured spec the page draws, never markup: `{kind: "bars", items: [{label, value, unit?,
lowerBound?, tone?}]}` with 1 to 6 items. `value` is a non-negative number (a measured 0 draws a stub); `lowerBound:
true` prints a leading `>=` and an open bar end (the number is a floor, not a measurement); `tone` is `expected`,
`saw` or `limit`; labels are plain text, escaped on render (the first 22 characters show; keep them short). An unknown `kind`, an unknown field, a negative value or
more than 6 items is rejected by the validator and not drawn. A figure decorates the evidence; the expected, saw and
evidence text stays on the card.

**`actions/<id>`** (the page calls them options)

| Field | Type | Notes |
| --- | --- | --- |
| `title`, `why`, `goal`, `criterion` | string | `goal` is the self-contained instruction: `Do: ... Files and symbols: ... Test: ... Done when: ...`, no line numbers, no status narrative |
| `status` | `open` \| `planned` \| `built` \| `done` | open: nothing built; planned: a written plan exists (cite it in `ref`); built: code exists, unreleased or unverified (cite `ref`); done: landed and verified, hidden under "Already done" |
| `findings` | array of string | observation ids the option resolves; an option renders once, under the first of them in view |
| `kind` | `fix-shiploop` \| `fix-harness` \| `change-expectation` \| `gather-evidence` \| `accept` | an option with no kind is listed last and printed under "other" |
| `effort` | `S` \| `M` \| `L` | S one commit with a test; M a few increments; L needs a live run or days |
| `recommended` | boolean | at most one per finding; "Tick recommended" ticks it |
| `cost` | string | what it costs; its presence gates the option "ask me before starting" in the prompt |
| `change` | object `{target, to, reason}` | `target` is `page` or `spec`; required for `change-expectation`, absent otherwise |
| `ref` | string | a commit or plan path |

Options are ranked recommended first, then by kind in the order above, then by effort. `base` is no longer read.

**`reviews/<runKey>`** (Claude's reading of one run; the page never writes it)

| Field | Type | Notes |
| --- | --- | --- |
| `summary` | array of string | the arc, 3 to 6 lines: what was done, what the run showed, conclusions, learnings, next; heads step 1 |
| `basis` | map of string | criterion key to the one-line reason it holds or was examined; a criterion without one reads "not examined" |
| `reviewedAt` | ISO string | |

No verdict is stored: the chip is always derived.

**`config/page`**: `title`, `artifactUrl`. **`config/prompt`**: `constraints` (the rules printed in every prompt: about 600
characters, specific to repairing a reviewed run) and `closing` (the report-back instruction). The prompt itself is
built by one pure function in the page, `buildPrompt`, from what the viewer ticked; the page falls back to a short
default closing, and prints no rules, when the document is missing.

## The export file

`review-export.json` (the compact file to commit with the learnings entry) is `{"schema": "run-review-export/v2",
"docs": {<collection>: {<id>: <document>}}}`. v2 differs from v1 in three ways: `refusals`, `glue` and `failures` are
optional and omitted when unmeasured, `unmeasured` is new, and a stage's `min` may be null. Files written as v1 are
history; they are not read back. A run document also no longer has the `improve` array (Improve is read from each visit's
`improve` and the run's `improvePasses` and `improveMin`) and its `status` can be `paused`.

A **review file** (the findings, options and arc Claude writes for a run, committed beside the run's export as
`test/shiploop_e2e/evidence/<runKey>.review.json`) has the same shape. `export.py --check FILE` validates it with
these tables and the review rules in `SKILL.md`; `export.py --docs FILE` checks it, then writes its documents and
`writes.json` through the writer an export uses.

Limits of the run numbers, documented and not guarded. File-time spans (`improveMin`, `stages[].improve.min`) are right
on the original run directory; a copy needs `cp -p`, or every mtime becomes the copy time. A visit's `min` is accept to
accept, so it includes any host-kill or resume gap inside it. A `timeline.json` the engine recreated stamps every
action alike and cannot be told from a real one. Calls and context are the main thread: chain workers and Improve
agents report elsewhere.

## Writes

A new run adds `runs/<key>` and its `backchain/*` documents with `set` (no `if_version`). A write to an existing document
needs `if_version`: read it first, and never overwrite a document the owner edited on the page. The page itself writes only:
observations (add, status), actions (add) and backchain (verdicts). Nothing else is written from the page: expectations,
config and the runs are replicas written by publish.
