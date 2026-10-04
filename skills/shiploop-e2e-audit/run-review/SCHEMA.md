# Run Review data contract

The Run Review page is a **static template**. It holds no run data and no content defaults: everything it shows
lives in the artifact's database (capability `db`) as the collections below, and is exported to the repository as JSON.
To show a new run, write documents. Do not edit or republish the template for data.

| Piece | Where | Changes when |
| --- | --- | --- |
| Template | `template/index.html`, one file, published once with `capabilities: {db: {}}` | the page's behaviour changes (republish, note it in the journal) |
| Defaults | `defaults/*.json`: starting phases, groups, criteria, prompt settings | the starting expectations change; written create-only |
| Contract | this file | a field is added, renamed or removed (change the template, exporter and tests together) |
| Data | the `db` collections below | every iteration |
| Exporter | `export.py`: a run output directory in, documents out | the run layout changes |

Anything not in this contract is ignored by the page. A missing optional field hides its panel.

## Collections

**`expectations/<key>`** (what we expect; the page edits `text`, `status`, `revs`)

| Field | Type | Notes |
| --- | --- | --- |
| `kind` | `phase` \| `group` \| `criterion` \| `iter` | required |
| `order` | number | sort key: phases `0..N-1`, groups, criteria within their group |
| `title` | string | phases, groups, criteria |
| `short` | string | phases only: the chevron subtitle |
| `text` | string | the expectation wording; for a group, a one-line blurb |
| `group` | string | criteria only: key of a `group` doc; none means "Other" |
| `status` | `holds` \| `bent` \| `broken` \| `unjudged` | criteria only; default `unjudged` |
| `revs` | array of `{at, from, to, reason, obs?, iter?}` | appended when an expectation is revised; never rewritten |
| `updatedAt` | ISO string | |

Keys: `phase-<order>`, `group-<name>`, a short id for a criterion (`P1`, `B1`), `iter-<iterationId>` (the override and
history for an iteration's expectation; the base text is that iteration's `expect`). The number of `phase` docs sets
the number of columns in the flow; `Observed` states in a run's `phases` array align with their `order`.

**`runs/<key>`** (one document per run output directory)

| Field | Type | Notes |
| --- | --- | --- |
| `key`, `name` | string | required |
| `order` | number | required; sort key |
| `release` | string | required: the plugin and ShipLoop version under test |
| `phases` | array of `done` \| `running` \| `blocked` \| `none` | required; aligned with the phase docs |
| `time`, `imp` | string | required: short text shown in the run header |
| `refusals`, `glue` | number | required |
| `wallMin` | number | wall minutes so far or in total |
| `host`, `model`, `effort`, `case` | string | |
| `status` | `done` \| `active` \| `blocked` \| `failed` | the ShipLoop run status |
| `startedAt`, `endedAt` | ISO string | |
| `verdicts` | object of booleans | invoked, plugin, process, shiploop, committed, checks |
| `stages` | array of `{stage, outcome, min, turns?, packetBytes?, resultBytes?}` | `min` is the accept-to-accept delta from `timeline.json`, never the harness's stage metric |
| `knowledge` | object `{fileName: bytes}` | sizes of the planning documents the run committed (spec, test strategy, plan, ...) |
| `improve` | array of `{stage, passes, seconds, bytes}` | Improve children |
| `failures` | array of `{verb, line}` | ShipLoop commands that exited non-zero |
| `evidence` | string | path of the output directory (local, not durable) |

**`backchain/<id>`** (a loop ledger; id `<runKey>-<loop>`; none is written when a run has no loop; none is written for a run without a loop)

`run`, `loop` (the owning stage name such as `plan`, `step-plan` or `carry-forward`, or `none`), `phase` (order), `order`, `title`, `stageMin` (number or null),
`segments` (array of `{label, min, kind, note, pass?, change?, streak?}`), `facts` (array of `{k, v}`).
`kind` is `added`, `wasted`, `insurance`, `unclear` or `neutral`. A pass segment has `pass` (1-based), `change` (what the
pass changed, from candidate digests) and `streak` (the clean streak after it). When `stageMin` is set the segments' minutes
sum to it. A hand-set verdict is interim; the default for an unjudged pass is `unclear`.

**`observations/<id>`**: `phase` (a phase `order`), `criterion` (an expectation key), `kind` (`defect`, `recovered`,
`decision`, `noise`, `added`, `wasted`), `run` (a run key or `any`), `status` (`open`, `fixed`, `accepted`, `reexpected`),
`title`, `expected`, `observed`, `evidence`, `createdAt` (ISO; orders the list).

**`actions/<id>`**: `title`, `why`, `goal`, `criterion`, `base` (number), `status`.

**`iterations/<id>`**: `n`, `title`, `kind` (`retrospective`, `build`, `pilot`, `screen`, `e2e`, `decision`), `status`
(`planned`, `running`, `done`), `run`, `cost`, `setBeforeData` (boolean: false means the expectation was written after
looking), `expect`, `observed`, `verdict` (`pending`, `confirmed`, `partly`, `refuted`), `touches` (criterion keys),
`ifConfirmed`, `ifRefuted`, `next`, `engineChange`, `observedAt`.

**`config/page`**: `title`, `artifactUrl`. **`config/prompt`**: `concatPreamble`, `constraints`, `closing`.
The page builds the planning sentence itself and falls back to a one-line default for each prompt string when the document is missing.

## Writes

A new run adds `runs/<key>` and its `backchain/*` documents with `set` (no `if_version`). A write to an existing document
needs `if_version`: read it first, and never overwrite a document the owner edited on the page. The page itself writes only:
observations (add, status), actions (add), expectations (status, revisions), backchain (verdicts), iterations (status,
verdict, observed, engine change).
