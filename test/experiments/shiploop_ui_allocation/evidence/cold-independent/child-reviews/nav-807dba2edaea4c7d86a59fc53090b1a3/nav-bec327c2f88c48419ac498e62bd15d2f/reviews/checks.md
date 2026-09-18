# Improve check evidence — W1 step-plan

All commands ran from the stated current fixture after the plan-only correction.
They establish only the described local source/fixture facts; no command called
a real API, deployed a product, or exercised a browser/UI journey.

| Command / inspection | Result | Limit |
| --- | --- | --- |
| `git --no-optional-locks -C product log -n 7 --format=...` | Exit 128: `fatal: not a git repository (or any of the parent directories): .git`. | The archive has no commit history/HEAD/index; no history-informed Git lesson is available. |
| `DEVELOPER_DIR=/Library/Developer/CommandLineTools python3 -B scripts/probe_environment.py` | Exit 0; target `fieldnotes-embedded-v2`, storage `unavailable`, `draft_api: false`, no server runtime or WebSocket, observation hash `40a3900ae08cf109734f411f62c8a89dbd5fae84c5f04d127ff000ea3038c878`. | Controlled fixture observation, not a live deployment receipt. |
| `node --check app.js` | Exit 0 with no output. | JavaScript syntax only. |
| `node --test` | Exit 0 with `tests 0`, `suites 0`, `pass 0`, `fail 0`. | No test suite exists; this is not behavioral coverage. |
| Source review of `docs/api.md`, `docs/platform.md`, `docs/design.md`, `README.md`, `app.js`, and `index.html` | The API alone names `collectionId`; the current UI/code exposes account/note identity only and contains no export implementation or collection mapping. | Read-only plan review; no service response was observed. |
| Post-correction plan-content check | Exit 0; all `T-W1-00`–`T-W1-05` markers, `EXP-000`, fake-fixture prohibition, and zero-test limitation are present. | Confirms the plan record contains the correction; it does not prove future implementation. |
| SHA-256 preservation check | Exit 0; original producer output remains `5664255bd6d7b370ed7b7c6f62342c6d7d7d45944c510567cd10c70d23fe2461`; all nine product files recorded in the original plan retain their recorded hashes. | Proves this review did not change product content; it does not prove external behavior. |

## Second review cycle after the API-contract correction

| Command / inspection | Result | Limit |
| --- | --- | --- |
| `git --no-optional-locks -C product log -n 7 --format=...` | Exit 128: archive still has no Git history. | No commit-window evidence exists; no Git initialization occurred. |
| `DEVELOPER_DIR=/Library/Developer/CommandLineTools python3 -B scripts/probe_environment.py` | Exit 0; unchanged controlled v2 observation and hash `40a3900ae08cf109734f411f62c8a89dbd5fae84c5f04d127ff000ea3038c878`. | Fixture observation only. |
| `node --check app.js` | Exit 0 with no output. | Syntax only. |
| `node --test` | Exit 0 with zero tests/suites/passes/failures. | Empty suite is not behavior coverage. |
| Source/plan reconciliation | `docs/api.md:2` has only route-level prose; no current source defines collection mapping or list/operation/job response fields. The revised plan records both gaps and limits each affected API case to a contract-shaped future fake. | No API response or real service was observed. |
| Corrected-plan assertions and hash check | Exit 0; required response-contract markers present, the first correction's over-broad wording absent, original producer hash preserved, and all recorded product hashes unchanged. Corrected plan SHA-256: `71db4c50303041b0e10f9affbeaafbc87ab12d41337292cd54772954db60b7cc`. | Confirms plan text and unchanged fixture content, not implementation. |

## Third review cycle — qualifying no-change review 1

| Command / inspection | Result | Limit |
| --- | --- | --- |
| `git --no-optional-locks -C product log -n 7 --format=...` | Exit 128: the fixture remains a Git archive. | No Git history or commit evidence exists. |
| `DEVELOPER_DIR=/Library/Developer/CommandLineTools python3 -B scripts/probe_environment.py` | Exit 0; unchanged controlled v2/no-storage/no-server/no-WebSocket observation. | Not a live deployment result. |
| `node --check app.js` | Exit 0 with no output. | Syntax only. |
| `node --test` | Exit 0 with zero tests/suites/passes/failures. | No behavior suite exists. |
| Initial literal plan-marker script | Exit 1: it matched raw line breaks and a wording variant, while the two targeted clauses were visibly present in the plan. | Invalid review-check predicate; not a product, plan, or runtime failure. |
| Whitespace-normalized plan audit | Exit 0; confirms scope, preserved UI, platform constraints, API identity/response gate, recovery rules, and planned case markers. Plan SHA-256 remains `71db4c50303041b0e10f9affbeaafbc87ab12d41337292cd54772954db60b7cc`; producer SHA-256 remains `5664255bd6d7b370ed7b7c6f62342c6d7d7d45944c510567cd10c70d23fe2461`. | Text/audit evidence only. |
| Product hash inventory | README, index, design/platform/API docs, probe, host observation, app, styles, and `SHIPLOOP.md` retain the hashes recorded by the producer. | No external behavior established. |

## Fourth review cycle — qualifying no-change review 2

| Command / inspection | Result | Limit |
| --- | --- | --- |
| `git --no-optional-locks -C product log -n 7 --format=...` | Exit 128: no Git repository/history. | The fixture archive cannot supply a seven-commit review window. |
| `DEVELOPER_DIR=/Library/Developer/CommandLineTools python3 -B scripts/probe_environment.py` | Exit 0; unchanged controlled v2 storage/API/runtime observation. | Not a live target/deployment check. |
| `node --check app.js` | Exit 0 with no output. | Syntax only. |
| `node --test` | Exit 0 with zero tests/suites/passes/failures. | Empty-suite observation, not behavior coverage. |
| Initial final trace/case audit predicates | Exit 1 because they required `with that same in-memory ID` and `not a deployed service claim`; the plan instead states `using that same in-memory ID` and `deployed-service claim`. | Invalid exact-wording predicate, not a plan/product failure. |
| Final normalized trace/case audit | Exit 0; all `T-W1-00`–`T-W1-05`, `EXP-000`–`EXP-007`, API-contract, recovery, preservation, and honesty clauses are present. Plan SHA-256 remains `71db4c50303041b0e10f9affbeaafbc87ab12d41337292cd54772954db60b7cc`; producer SHA-256 remains `5664255bd6d7b370ed7b7c6f62342c6d7d7d45944c510567cd10c70d23fe2461`. | Plan-content evidence only. |
| Child artifact inventory / `stat` | Start and each completed callback packet are regular files; review records and checks are regular child-workspace files. | Does not itself prove semantic review quality. |
