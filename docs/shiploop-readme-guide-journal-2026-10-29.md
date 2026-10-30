# ShipLoop developer guide journal

Living record of writing the developer guide that now opens `skills/shiploop/README.md` (2026-10-29). Edit rather than delete:
mark a claim superseded with the date and reason.

## Question

The ShipLoop README was a 1,218-line design record for maintainers. It had no statement of what ShipLoop is, no quick start, no
use cases and no worked example, and its ten diagrams each covered one feature. Can developers who *use* ShipLoop learn what it
does, start a run, steer it and recover it from the README alone?

## Method and conditions

- Read `SKILL.md`, `references/navigator.md`, `glossary.md`, `state-files.md`, `status-display.md`, `keepalive.md`,
  `run-options.md`, `host-matrix.md`, `workspace-lifecycle.md`, the CLI `--help` of every verb the guide shows, and
  `scripts/shiploop_stage_spec.py` (the stage table).
- Ran `graph-dry-run` to read real packets, then one live end-to-end run for the worked example:
  `python3 test/shiploop_e2e/run.py --case hello --host codex --model gpt-6.1-terra --effort xhigh --source checkout`
  on `5faca0d3` (skill-craft 2.24.0, ShipLoop 1.23.0), default options, the owner's choice of Codex Terra
  as the E2E runner (2026-10-29), hooks on.
- Worked in a temporary worktree (`docs/readme-guide-e08226`), because another session landed ShipLoop 1.23.0 README edits on
  `main` while the work was in progress.

## The live run (status: firm for this one run; one case, not a baseline)

| Measure | Value |
|---|---|
| Verdicts | invoked, plugin, process, shiploop, committed and every case check passed |
| Elapsed | about 13 minutes (host 783.7 s) |
| Accepted results / packets / commands | 27 / 36 (0 reprints) / 60 |
| Improve reviews | 9 (`spec`, `test-strategy`, `plan`, `step-plan` twice, `document`, `carry-forward`, `system-test-author`, `release-plan`) |
| Refusals / send-backs / blocked | 0 / 1 (`implement` to `step-plan`) / 0 |
| Commits | 1 `feat(W1/S1)` and 9 `docs(shiploop)` knowledge-home commits |

Evidence: [trace export](evidence/shiploop-readme-guide-hello-trace-2026-10-29.json) (the 27 steps) and the
[harness baseline row](evidence/shiploop-readme-guide-hello-baseline-row-2026-10-29.jsonl). The harness appended that row to
`test/shiploop_e2e/baselines.jsonl`; it is kept here and not committed there, because this round was not an E2E baseline round and
`LEARNINGS.md` has no entry for it.

## Findings

| Finding | Status | Evidence |
|---|---|---|
| `skills/shiploop/README.md` is a normative guide root: `test/shiploop-reference-routing.test.py` walks its links and anchors and rejects a code span that names a package file which does not exist, or a link that leaves the package. | firm | `NORMATIVE_GUIDE_ROOTS`; a draft with `../improve/SKILL.md` would have failed it |
| `scripts/release.py` rewrites the README's first line when it ends with the old version, so line 1 must keep a trailing version. | firm | `scripts/release.py` module docstring |
| The maintainer part is kept byte for byte and moved down, because `navigator.md` links to `README.md#current-improve-and-until-loop-binding` and the reference-routing test pins the headings. | firm | the diff adds 682 lines and deletes none from the README |
| Prose that lists stages drifts from the stage table. Another session fixed one such drift (`31d627ae`: `test-spec` was listed as reviewed) while this guide was being written. The guide's stage list and its reviewed-stage list therefore come from `shiploop_stage_spec.py` (`STAGES`, `reviewed_stages`). | firm | `reviewed_stages('stage')` and `('none')` printed |
| Two of six Mermaid diagrams failed to render on the first draft: a `;` inside a sequence-diagram message ends the statement, and an edge from a subgraph to itself throws at render time though `mermaid.parse` accepts it. Both were found only by rendering with `mermaid@10.9.1`. | firm | rendered all six in the browser pane after the fixes |
| The recorded run's `shiploop check` after the run exited 2: "expectation E1 is works, but hello.py does not exist on the item's lint base. A new path needs an absent expectation." This is the harness's own post-run `--check-only` check, run against a finished run whose step plan recorded E1 as `absent`; not investigated. | exploratory | `failed` line of the run log |

## What the guide claims, and where each claim is checked

| Claim | Check |
|---|---|
| Every command and flag shown | `--help` of the verb, run during the work |
| The 23 stages, their phases and which are reviewed | `shiploop_stage_spec.py` |
| The worked example's stage table, packet text, results, send-back, test base run, commits and file tree | The run's `results/`, `packets/sent/`, `tests/`, `git log` and the trace export |
| Links, anchors and package file names | `test/shiploop-reference-routing.test.py` and an anchor scan of the README |
| Diagrams | Rendered with Mermaid 10.9.1 |

## Open items

- The guide's quick start shows the Claude and Codex invocations; Grok, Cursor and OpenCode are described, not exercised here.
- The worked example is one tiny case with no refusal, block or deployment. A second recorded run with a refusal from the lint or
  test gate, or a blocked question, would show those paths. Not run: it needs an owner decision on subject model and cost.
