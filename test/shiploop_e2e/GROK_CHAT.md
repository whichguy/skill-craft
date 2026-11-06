# Salesforce Grok chat test case

`grok-chat-salesforce` gives a fresh ShipLoop subject an elaborated prompt to build an Apex/LWC assistant inspired by Grokbot. The application is the test challenge; improving ShipLoop is the learning goal. The authoritative prompt, deployment scope and check commands are in [cases.json](cases.json). This checkout supplies no chat application.

The case is ready for an **exploratory construction run**, not a qualified baseline comparison. Its `acceptance` check deliberately returns nonzero `UNKNOWN` until independent behavioral checks are calibrated. The runner records that as a failed check, so three green smoke checks cannot become a full E2E PASS, satisfy a passing baseline gate or retain an unqualified app. This known apparatus gap is separate from any defects discovered in the generated app.

| Journey | What the prompt requires | Evidence still needed beyond smoke checks |
|---|---|---|
| Setup | Detect missing/inaccessible configuration and guide setup before requiring a model connection | Rendered missing-setup path, valid setup transition and recovery |
| Salesforce tools | Runtime prompt knows the org/user; Apex executes structured read/create/update calls | Actual tool requests/results and independently queried records |
| Confirmed writes | Exact proposals, user confirmation, cancellation, stale-data/replay protection | No-write counterexamples and ordinary-user authorization checks |
| Conversation and UI | Durable user-separated history, progress, recoverable errors and accessible controls | Reload, keyboard and error-path observations in the deployed UI |
| Code knowledge | Review error checking, useful invariant/rationale comments and warranted tombstones | Findings with code locations, repairs and relevant rerun evidence |

## Run the case

Use Codex or Grok with an explicitly authorized target org `de`, a free `SLGrokChat` prefix and an available supported browser route. The existing org identity, snapshot, lease and cleanup checks apply. This case is opt-in and is absent from default suites. Constructing it does not deploy anything or provision a credential.

```sh
python3 -B test/shiploop_e2e/run.py \
  --case grok-chat-salesforce --host codex --source marketplace \
  --output /absolute/path/to/a/new-grok-chat-run \
  --baseline /absolute/path/to/grok-chat-exploratory.jsonl
```

Use a new output directory for every fresh attempt. Preserve the campaign's model/effort defaults and record the local case/check identity separately from the installed ShipLoop build. Do not use `--keep-platform`: this is a fresh-only case with default cleanup. A failed or unverified cleanup blocks prefix reuse.

No provider credential is required to start construction or test the missing-setup experience. For live Grok journeys, an administrator supplies the modern [Named Credential](https://developer.salesforce.com/docs/platform/named-credentials/guide/get-started.html) `Grok_Chat_Model`, its External Credential and principal access through an administrator-owned permission set outside the app prefix. The app references that credential and uses the documented [xAI function-calling protocol](https://docs.x.ai/developers/tools/function-calling); it never provisions or reveals secrets. Valid provider/model configuration is administrator-controlled. If setup is unavailable, complete independent work and report the exact blocked step. Do not wait indefinitely or silently use mock output as live evidence.

Attempt the UI first through discovered tools, preferring an available Chrome DevTools route. Verify the target org. Authenticate only as needed through an authorized available route; the subject must respect the CLI guard and cannot use `org display`, a raw session token or a guard bypass. If no supported route exists, preserve the blocker. The case currently supplies no independent authenticated UI driver.

## What the checks establish

`project` checks the declared layout, schema and metadata scope. `deployed` observes component/object/permission-set presence. `tests` runs the subject's Apex tests. These checks do not establish setup usability, real-provider tool round trips, correct confirmed writes, cross-user authorization, comment quality or rendered UI behavior. The explicit `acceptance` check preserves those gaps; a report or source keyword is not an independent behavioral oracle.

The unchanged gym lifecycle adapter handles owned custom objects and permission assignments. The declared child-object names sort before the sole permitted `Thread__c` parent. Cleanup removes tracked prefix-owned app state, including conversations and synthetic records. Page reload within a run preserves app state; a fresh run after cleanup does not. Cleanup does not observe arbitrary external DML, credential metadata, jobs, late deployments or all baseline contents. The prompt forbids those side effects; it does not make the guard a complete security boundary.

After the first run, review actual workflow and product evidence, code/comment findings, setup/auth snags and cleanup. Calibrate independent checks against observed positive and negative controls before registering a qualified comparison. Then evaluate a warranted generic ShipLoop change against a frozen case and rerun it. New scenario coverage alone is not a measured ShipLoop improvement.
