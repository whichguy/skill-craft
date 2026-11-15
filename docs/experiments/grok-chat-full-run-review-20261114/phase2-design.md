# Phase 2 design: the owner review hold, the API headroom record and the readiness record (2026-11-15)

**Status: not pursued (owner, 2026-11-15).** The owner, the same day: "I only care about modifying Shiploop as a generic
facility or the end-to-end test for Shiploop as a generic facility. If we're doing something outside of that, I don't know if
it's actually valuable because I'll end up deleting the Salesforce-specific run of Shiploop later." All three parts exist for
the Salesforce platform cases: the hold protects a platform's deployed app, the headroom record reads an org's daily API
allowance, and the readiness record serves the Grok chat journey. So none is built. The design and Astra's review (below)
stay as a record in case a generic need for a hold appears. Nothing below is a decision.

The text as written before that, kept unchanged: a design, nothing built, each part waiting on the owner's tick (decision 4
in [README.md](README.md)), with the decisions at the end the owner's. It answers the corrected requirements that Astra's
review of the first plan set for Phase 2: the hold must reach host-session termination, the resume start, the resumed
preflight, the final dispatch and the regrade; keep held, kept and cleaned apart in the records; preserve external artifacts
while producers stay stopped; read a check that does not support its phase as unexamined; and be tested with sentinel
commands through the real routes.

Words used here:

- **Platform**: the hosted service a case deploys into, here a Salesforce org. The case's `platform` hooks (`preflight`,
  `before`, `cleanup`) act on it.
- **Producer**: anything that can change the platform or the run's files: the host (the model's CLI session), a server the
  model started, a case check (the Apex oracle check deploys a test class).
- **Cleanup**: the case's `cleanup` command, which removes what the run made in the platform. `lifecycle.cleanup` and
  `listeners.reap` are different things: they stop processes and delete no file.
- **Kept**: `--keep-platform` left the platform in place because the delivery was judged worth keeping (`keep_decision`).
- **Held**: the owner deferred the decision. Nothing is judged, nothing in the platform is touched, and no producer starts.

## 2a. The owner review hold (P1)

### What the owner asked

The trial's operator recorded the owner's words in `operator/owner-review-hold.json`: "Owner requires code inspection and
working-product review before any further cleanup. Preserve deployed app, provider configuration, source and evidence." Its
resume policy: no automatic cleanup; finishing the inspection is not permission to clean; cleanup runs only after a new
explicit request from the owner.

### Why the harness cannot honour it today

- `--keep-platform` keeps a finished delivery, or an unfinished one only when the case's `keep_checks` all ran and passed
  (`keep_decision`). `keep_blocker` never keeps a person's stop, a signal, an invalid trial or a failed earlier cleanup
  (dcd91d4a9f75b50c90cf337f4d63734ee15f48cc). The trial ended blocked after the org's daily API allowance ran out, so no
  keep check could pass. Its cleanup ran at exit and failed at its first query: `run/platform/cleanup-record.json` reads
  `ran: true, ok: false`, "TotalRequests Limit exceeded".
- A hold placed after a run ended has no route in the code. The trial is protected only by a rule that sessions follow
  ("never regrade or resume the trial"). A regrade of it (`--resume-run` on a blocked run, or `--grade-only`) would:
  1. arm the cleanup again, because its record is not ok (the `platform_spec and regrade and not earlier_cleanup.ok`
     branch of `_main`);
  2. run the case's checks again against the org with `E2E_CHECK_PHASE=final`, because restating the earlier checks
     (`restated`) needs an ok cleanup record;
  3. run `product_at_stop`, which runs the same checks in the unreturned worktree;
  4. then run the cleanup.

### The hold record

`<run>/hold.json`, one JSON object:

```json
{"schema": "e2e-hold/1", "placed_at": "2026-11-14T23:26:16Z", "placed_by": "owner",
 "words": "<the owner's words, verbatim>", "released": null}
```

- **Who writes it:** the owner; a session quoting the owner's words from its conversation; or the harness itself, when the
  launch policy below holds a run (`"placed_by": "policy"`).
- **Scope, fixed:** while held, no command acts on the platform and no producer starts. Processes that are already running
  are stopped as they are today (see "Processes" below).
- **Release, by the owner only:** `released` becomes `{"at", "words", "to": "cleanup" | "continue"}`. The file is never
  deleted, so the hold's record survives its release.
  - `to: cleanup`: the next regrade runs the cleanup, through the existing branch for a cleanup that did not succeed.
  - `to: continue`: the next resume starts a host with the platform in place, treated like a run whose earlier segment
    kept an unfinished platform (`kept_unfinished`): the case's preflight is skipped and `resume_note_kept` is sent.
- **Read fresh** at every path below through one helper, `hold_state(out)`, never cached at start, so a hold placed while a
  run is live takes effect at the next path.

### Every path that reads it

| Path (symbol in `test/shiploop_e2e/run.py`) | Today | While held |
| --- | --- | --- |
| Final dispatch in `_main`: `keep_decision`, then `guard.keep` or `guard.finish` | keep or clean | neither: write the held record |
| `main`'s `finally`, which calls `guard.finish` after a crash, Ctrl-C or SystemExit | clean | write the held record |
| Regrade arming (`platform_spec and regrade and not earlier_cleanup.ok`) | arm the cleanup again | do not arm; print the hold |
| Regrade checks (`restated`), `product_at_stop`, the quality phase (`quality_gate`) | live checks when the cleanup was not ok | restate the run's own records; the quality phase is gated with "held for owner review" |
| Resume start: `lifecycle.cleanup`, `listeners.reap`, `take_leases` | stop the earlier invocation's processes, then start | refuse first: nothing stopped, nothing started; name any recorded process still alive |
| Automatic resume in the session loop (`while host.resumable and not regrade ...`) | start the next host session | start none; the run ends stopped by the hold |
| End of a host session (`listeners.end_group`), the final `listeners.reap` and `lifecycle.cleanup` | stop the run's processes | unchanged |
| Resumed preflight (`platform_preflight` with `skip_command`) | skipped only after `kept_unfinished` | after a release `to: continue`, skipped the same way |

**Processes.** The invocation that is running when a hold takes effect still stops its own host sessions and the processes
its ledger records. A host or server left running could deploy into the held platform, which is the opposite of preserving
it. `lifecycle.cleanup` deletes no file, and a product served locally can be restarted from its preserved source for the
review. An invocation that starts on a held run (a resume) stops nothing, as a regrade already stops nothing: a person may
be inspecting a process it would kill. It names any process the run's ledger records as alive, so the person can stop it.

### The launch policy: `--hold-platform`

The Astra plan separates the policy chosen at launch from the moment the hold takes effect.

- **Chosen at launch,** stored in `invocation.json`, and kept for the whole run: a resume or a regrade reads the first
  invocation's policy. This differs from `--keep-platform`, which each invocation must pass again.
- **Takes effect at the end** of any invocation whose delivery is not finished, judged before any cleanup by
  `keep_refusal` (ShipLoop done, its report written, every case check passed, no stop, no timeout, no invalid trial).
  The harness then writes `hold.json` with `"placed_by": "policy"` instead of cleaning. A finished delivery is cleaned, or
  kept with `--keep-platform`, as today.
- **A crash** reaches `main`'s `finally`, which holds. **A harness killed outright** leaves the pending record
  (`PENDING_CLEANUP`). The next invocation reads the policy and that record, and holds before it acts.

### The records

- **`cleanup-record.json` while held:** `{"ran": false, "ok": false, "held": true, "reason": "held for owner review
  (<placed_by>): <words>", "hold": "hold.json"}`.
- **`ok: false`** keeps the run from passing. A platform that was not cleaned is not a pass, as with `kept_unfinished`; a
  regrade after the release and the cleanup computes the verdict again. The alternative, judging the delivery and reporting
  the cleanup as pending, needs a verdict field the baselines do not have.
- **The report line** reads "platform HELD for owner review: not cleaned; NOT a pass". In `mismatch.md` the platform line
  says held, with the path to `hold.json`, and never "cleanup failed".
- **Three readers learn the held record:**
  - `keep_blocker` reads it as held, not as "an earlier cleanup of this run failed".
  - `resume_platform_note` sends `resume_note_kept` after a release `to: continue`.
  - The regrade arming and `restated` treat it as not cleaned and not failed.
- **Which file decides.** `hold.json` decides whether the run is held. `cleanup-record.json` stays the record of the last
  cleanup, keep or hold, and a resume reads it before `result.json`, as it does today (`earlier_cleanup_record` first).

### Checks that could not examine

A check that cannot examine in this phase, or cannot reach the platform, exits 77 and prints `UNEXAMINED: <why>` as its last
line. Two examples: a check that supports only some phases, and one that finds the org's daily allowance spent.

- **How it is read.** `run_checks` records `{"pass": false, "unexamined": true}` only when both are true. An exit of 77
  without that line stays a failure, so a product's tool that happens to exit 77 is not misread. The line goes last because
  `run_checks` keeps the last 2,000 characters of output.
- **No verdict loosens:** unexamined is never a pass.
- **What changes is the reading.** `product_at_stop` counts `unexamined` apart from `failed`, and `mismatch.md` lists those
  checks as unexamined.
- **The trial.** Its `product_at_stop` ran six checks. One passed (`grok_chat_full_salesforce.py project`). Two hit the quota
  (`grok_chat_salesforce.py deployed` and `tests`, "FAIL/UNKNOWN: ... TotalRequests Limit exceeded"). Three refused the
  phase:
  - `grok_chat_full_salesforce.py rules`: "UNKNOWN: the independent Apex oracle runs only in builder or final phase";
  - `grok_chat_full_ui.py --mode run`: "FAIL (phase not allowed)";
  - `grok_chat_full_quality.py`: "UNKNOWN (allowed only in builder/final)".

  All five were recorded as failures. Under this rule the record reads 1 passed and 5 unexamined.
- **The checks to change:** those four check scripts (the quota path of `grok_chat_salesforce.py`, the phase refusals of
  the other three) and `gym_membership_salesforce.py`, which refuses phases other than final and product_at_stop the same
  way.

### Tests

The tests go through the real dispatch, `run.main`, with the `PlatformCase` fixture in
`test/shiploop-e2e-platform.test.py`. Its platform commands log each verb they run, and the sentinel checks fail if
invoked. Each test asserts:

- which verbs ran, the records, and that the verdict and exit code stay as they were;
- that the hashes of the run's work tree, platform folder and evidence files are the same before and after.

| # | Situation | Expected |
| --- | --- | --- |
| 1 | Regrade of a blocked run whose cleanup failed, under an owner hold | no platform verb or check runs; the record reads held |
| 2 | A hold placed between host sessions | no further host session; no cleanup verb at the end |
| 3 | A resume under a hold | refused before `lifecycle.cleanup`, `listeners.reap` and the leases; nothing stopped or started |
| 4 | `--hold-platform` at a non-pass end, at a crash after arming, and after a killed harness's pending record | held each time; no cleanup verb |
| 5 | `--hold-platform` with a finished delivery | cleaned, as today |
| 6 | Release `to: cleanup` | the next regrade cleans once |
| 6b | Release `to: continue` | the next resume skips the case's preflight and sends `resume_note_kept` |
| 7 | No hold and no policy | every existing platform test passes unchanged (the regression control) |
| 8 | Exit 77 with the `UNEXAMINED:` line | reads unexamined in `product_at_stop` and `mismatch.md` |
| 8b | Exit 77 without the line | a failure |
| 8c | A final check that is unexamined | the verdict fails |
| 9 | `keep_blocker` given a held record | reads it as held, not as a failed cleanup |

**Files:**

- `test/shiploop_e2e/run.py`;
- the check scripts listed above and their shared helper;
- `test/shiploop_e2e/README.md` ("Platform hooks");
- `test/shiploop_e2e/SPEC.md` (the resource lifecycle clause);
- `test/shiploop-e2e-platform.test.py`, as a new `HoldTest`.

This is E2E apparatus with no ShipLoop skill file, so the commits carry `No-Change-Note`. Effort: M.

### Left out of 2a

- **The offline inspection summary** the Astra plan proposes, which reads the retained source and evidence and calls no
  platform. It is a separate tool, built after the hold.
- **Naming listeners to keep at teardown.** The trial's viewer was reaped because its command line named the run folder
  (README, finding 4). The hold does not change `listeners.reap`.
- **The trial itself.** Once the hold ships, writing `run/hold.json` into the trial folder from the owner's recorded words
  would make the code enforce what sessions enforce by rule today. It writes into the held folder, so it needs the owner's
  go.

## 2b. The API headroom record

- **What happened.** The org's daily API requests ran out at 14:48:09 PST, and the cleanup's first query failed on that.
  The guard log holds the model's 203 `sf` calls from 08:14 to 14:46 PST: 59 deploys and 56 Apex test runs. The operator,
  the UI helper and any other client are not counted, so the cause is not measured.
- **The hook.** An optional platform hook, `limits`: a command that prints one JSON object
  `{"name": ..., "max": int, "remaining": int}`. It is the case's own adapter, such as `sf org list limits` filtered to
  `DailyApiRequests`, so the harness stays free of platform words.
- **When it runs:**
  - `start`: after `before` and before the model starts;
  - `session`: after each host session;
  - `end`: before the cleanup or the hold.
- **The record.** Each reading appends `{phase, at, ok, name, max, remaining}` to `<run>/platform/limits.jsonl`, or
  `ok: false` with the scrubbed tail of its output. The platform block of `result.json` carries the first and last readings,
  and `used` = start `remaining` minus end `remaining`. `used` is present only when both readings were measured; otherwise
  `unmeasured.limits` says why, never 0.
- **Record only.** A reserve that refuses a start, or stops a run before the allowance is spent, is a limit on the run, and
  limits are the owner's call. The record first measures what such a reserve would need to know: how much a run uses, and
  how much of that is the model's (the guard log) against everyone else's (the difference).
- **Cost.** One request per reading. When the allowance is spent the reading fails, and that failure is itself recorded.
- **Tests:** a fake `limits` command that prints valid JSON, prints malformed JSON, or fails; no hook means no record;
  `used` appears only with both readings.
- **Files:** `run.py` (the hook and the record), `cases.json` (the Salesforce cases' `limits`), a small check-side adapter,
  `README.md`, and the platform tests. E2E apparatus.

## 2c. The readiness record (P2a)

- **What happened.** The builder polled for the operator's evidence: 46 calls in about 56 minutes. The operator's trace
  window became ready 1.3 s after a journey ended, so that journey's six calls could not qualify.
- **The Astra plan's design, adopted unchanged.** A readiness record made before the journey and bound to the intended
  candidate (its source hash), the deployment, the actor and the owned trace window (its id and expiry). The producer, the
  UI journey, starts only after that record exists. The existing acceptance request after the journey, and its exact
  six-call binding, stay as they are: moving that request before the journey would be circular, because it needs the
  finished, passing receipt.
- **Where it could go:**
  - **A.** The registered case `grok-chat-salesforce-full`, through its checks `grok_chat_full_ui.py` and
    `grok_chat_full_quality.py`. Commit 71fa298e44db73f6afa46217377ba0ea850de916 found that this case's 4,030-word prompt
    and its checks prescribe internals.
  - **B.** The unregistered scenario `test/shiploop_e2e/scenarios/grok-chat-outcome`, added in 71fa298e and revised today
    in b69bad19. Its `READINESS.json` lists "independent read-only observation capability" among its launch blockers, and
    its runnable integration is future work.
- **Recommended: B,** built as part of that scenario's runnable integration by the session that owns it. A only if the
  registered case is to run again before B can.
- **Out of scope here:** the record's fields beyond the plan. They belong to the session that owns the chosen target.

## Decisions for the owner

1. **Build the hold (2a), and how far `--hold-platform` reaches.** Should it hold every ending that is not a finished
   delivery, including the ones dcd91d4a never keeps (a person's stop, a signal, an invalid trial, a failed earlier
   cleanup)? Recommended: yes. A hold defers the decision; it does not choose to keep a delivery, so dcd91d4a's rule still
   governs `--keep-platform`. A hold the owner places by hand covers every ending, because the owner said so.
2. **The default.** Recommended: keep "cleanup always", with `--hold-platform` as an opt-in. A held org makes the case's
   preflight refuse the next run of that case until the org is cleaned, and the default keeps runs comparable with earlier
   evidence. The alternative is to hold by default for platform cases.
3. **Headroom (2b).** Recommended: build the record, with no reserve. A reserve is a limit, so it stays the owner's call.
4. **Readiness (2c).** Target A or B; B is recommended. Whichever is chosen goes to the session that owns it.
5. **The trial.** Once 2a ships, write the trial's hold record from the owner's recorded words. This needs the owner's go;
   nothing else in that folder changes.

## Evidence

- **The trial,** under `/Users/Shared/Codex/shiploop-e2e/salesforce-grokbot-independent-20261114T161019Z/`:
  - `operator/owner-review-hold.json`;
  - `run/platform/cleanup-record.json`;
  - `run/platform/sf-calls.jsonl` (406 lines, 203 calls);
  - `run/result.json` (`product_at_stop`, six checks);
  - `operator/observer/RESULT.md`;
  - `operator/improvement-plan/improvement-plan.md`: P1, P2, and evidence cards E20 and E21.
- **The code:**
  - symbols in `test/shiploop_e2e/run.py`: `PlatformGuard` (`arm`, `keep`, `finish`), `PENDING_CLEANUP`, `keep_blocker`,
    `keep_refusal`, `keep_decision`, `earlier_cleanup_record`, `resume_platform_note`, `platform_preflight`,
    `product_at_stop`, `run_checks`, `quality_gate`, `end_live_hosts`, `main` and `_main`;
  - `lifecycle.cleanup`, `listeners.reap` and `listeners.end_group`.
- **The commits:**
  - dcd91d4a9f75b50c90cf337f4d63734ee15f48cc, the never-kept rule and the unfinished keep;
  - 2d47ab820027535f5532284370b78071739abe2c, the pending record at arming (`PENDING_CLEANUP`);
  - 71fa298e44db73f6afa46217377ba0ea850de916 and b69bad199a677f5ff7ee6e09fea84aa8b64068c7, the outcome scenario.

## Review

Astra (gpt-6-astra, max effort, read-only) reviewed the design as committed in
7ea06fbcb64052f6a1fead788b8cbc6e3e2a57fd. **Verdict: not ready**, with 15 material findings and 3 minor ones. Its summary:
"The direction is sound, but the hold's enforcement boundary, release transitions, and evidence-preservation rules need
revision before implementation." The material findings include:

- the path table does not define an enforceable hold;
- "stops nothing and names live processes" does not keep producers quiescent;
- a release must authorize an action, not just remove a prohibition;
- pending-record and concurrent-hold semantics are not durable enough;
- a held record must not erase the earlier failed cleanup;
- the activation rule differs from both "non-pass" and the unfinished keep;
- restatement lacks missing-evidence rules;
- `ok: false` alone does not classify truthfully across the exporter;
- the exit-77 capture contract is unreliable under truncation;
- the quota paths are not covered;
- a headroom delta cannot measure a run's own use;
- several tests cannot run on the unchanged fixture;
- the decision list omits choices the design already made.

The findings were **not verified** against the code, because the owner closed Phase 2 before that step. The full text is in
[evidence/phase2-astra-review.md](evidence/phase2-astra-review.md). None of them names a defect in the harness as it is
today; all concern the proposed hold.

The same day the owner also chose concurrency over isolation for runs on one org. That meant scoping the org-wide platform
lease (`lifecycle.lease_keys`, f0c244253e3ff050ef55409ea2e632d89de1a46f) and the epoch dispatch barrier
(`epoch.target_launch_state`) back to the case's prefix. It serves only the Salesforce cases, so under the same scope
rule it was not built either. Nothing was edited for it.
