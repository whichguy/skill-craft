# Backchain harness inventory (adapters only)

Planning logic lives in **prompts**, not here. Use these when a checkout is available.

## Whole-skill completion boundary

The native skill invokes the actual Until Loop skill through `references/convergence.md`.
Direct harness commands generate or package candidates only; they do not perform two
consecutive semantic reviews. Within a Backchain invocation, feed their output back
into that subcall. A CLI success or `completionStatus=complete` cannot stand in for an
actual Until Loop terminal receipt and planning evidence. The harness does not bundle or
invoke a second review controller; Backchain reuses the selected Until Loop runtime.

## Product labels

| Label | How | Claim |
|-------|-----|--------|
| **native-unvalidated** | Session model drafts, elaborates, and completes internal convergence | Useful plan JSON; **not** scheduler-ready |
| **script-packaged** | `bash harness/run-prompt.sh --package-only <enriched.json>` | Schema/DAG/waves validated |
| **full-harness** | `bash harness/run-prompt.sh --prompt …` or `--from-draft …` | Router generator; router or configured alternate elaborator |
| **nbq-experiment** | same + `--nbq` | External EVSI → `dependency-context.*`; requires Ollama chat URL |

## Key commands

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

# A/B measurements
bash harness/casebook-ab-backchain.sh   # raw draft vs elaborator
bash harness/casebook-ab-nbq.sh         # elaborator vs elaborator+EVSI
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
