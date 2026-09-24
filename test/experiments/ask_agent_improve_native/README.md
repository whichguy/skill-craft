# Native Ask Agent / Improve pilot

Opt-in Codex experiment for Ask Agent's explicit consumer-owned route. The fixture
uses real Git, ShipLoop CLI and bundled Improve runtime interfaces; it never
launches a model or manufactures review callbacks. It is outside hermetic CI.

`pilot.py setup --package /absolute/skill-craft --case /new/absolute/case`
creates a disposable dirty caller and bound final-handoff candidate. Predecessor
navigation is synthetic setup, explicitly not an executed full ShipLoop run.
The product has a bounded totals defect and four established tests. The caller
has staged and unstaged content in an excluded file and in the scoped calculator
file, plus an untracked input. The scoped caller comments must survive exactly.

The case directory must be outside both the selected package and the pilot's
source checkout. The CLI rejects either location before setup or imports so raw
receipts, local paths, and native lifecycle evidence stay outside source control.

From the ongoing native parent:

1. Read the selected Ask Agent, ShipLoop context and Improve cards. Freeze the
   exact contract from `pilot.json` and `packet.md`; record package hashes,
   candidate scope, checks, scoped-commit policy and the unchanged continuation.
   An inline-learning claim needs the actual first native request and first
   review or plan evidence that carries the learning; a later patch or test
   does not show when that learning entered the worker context.
2. Append launch intent to the bound receipt's sibling `host-owner.md` before
   native fresh dispatch, then append the actual native handle. Use the host's
   operation-directory binding on every command. The worker owns the whole
   Improve invocation, not a single review. Keep the parent alive to collect it.
3. Have the real worker review, fix when warranted, check, and reach two distinct
   qualifying reviews using the selected bundled runtime. Commit checked scoped
   changes with the required learning sections; never commit runtime receipts or
   unrelated caller inputs. Preserve exact JSON
   packets and actual review/check evidence. The worker never executes parent
   callbacks or edits the parent owner record.
4. Collect the actual native return and all delegates. Independently verify the
   candidate and evidence. Record the observed stop evidence in `host-owner.md`
   and write `parent-collected.json` with boolean `worker_stopped`, boolean
   `delegates_stopped`, and `owner_record_sha256` for the exact retained owner
   record. These are parent attestations, not fixture-produced facts.
5. Run `pilot.py finalize --package /absolute/skill-craft --case /absolute/case`.
   It refuses a `pilot.json` whose `commit_policy` is not `scoped-required`;
   run `setup` for a new case instead. It first verifies actual commits since the
   frozen candidate baseline, their exact SHAs in the terminal handoff, scoped path
   sets and learning sections, and that all scoped changes are committed; it saves
   `worker-commits.json`. This dirty-caller fixture returns a patch-like
   working-tree delta: the worker commit stays private, and caller HEAD/index
   remain unchanged. It validates the successful terminal receipt, resolves only scoped return
   paths, runs guarded workspace return, and compares every named product and
   test path in the caller with the candidate before parent import. It first
   writes `scoped-delivery.json` with each path's caller digest, candidate digest
   and match result. This pre-import record says `git_delivery: INCOMPLETE`; a
   failed scope check records `scoped_delivery: FAIL` and blocked parent
   advancement before raising. The workspace return may already have occurred,
   but the parent import is blocked. A passing scope check still records parent
   advancement as incomplete until the import and existing safeguards finish;
   only then does `delivery.json` report `git_delivery: PASS` and link the scoped
   record. Those digests establish scoped delivery only; they do not establish
   semantic correctness, review quality or caller-test results. Native lifecycle
   remains labeled parent-attested and requires separate evaluation.
6. After a completed case, rerun the same read-only delivery comparison without
   repeating return or parent import:

   ```sh
   python3 -B test/experiments/ask_agent_improve_native/pilot.py verify-delivery \
     --package /absolute/skill-craft --case /absolute/case
   ```

   Expect `scoped_delivery: PASS` with `match` for each scoped path. This prints
   its manifest only; it does not rewrite either delivery record.
   To check the failure path without touching a completed case, make a disposable
   copy, alter only its caller test file, and expect the read-only check to fail:

   ```sh
   PILOT_PACKAGE=/absolute/skill-craft
   PILOT_CASE=/absolute/completed-case
   PILOT_NEGATIVE_CASE="$(mktemp -d /tmp/ask-agent-improve-native-negative.XXXXXX)"
   mkdir -p "$PILOT_NEGATIVE_CASE/workspace"
   cp -R "$PILOT_CASE/caller" "$PILOT_NEGATIVE_CASE/caller"
   cp -R "$PILOT_CASE/workspace/worktree" "$PILOT_NEGATIVE_CASE/workspace/worktree"
   cp "$PILOT_CASE/pilot.json" "$PILOT_NEGATIVE_CASE/pilot.json"
   perl -0pi -e 's/\z/\n# intentional scoped-delivery mismatch\n/' \
     "$PILOT_NEGATIVE_CASE/caller/test_calculator.py"
   python3 -B test/experiments/ask_agent_improve_native/pilot.py verify-delivery \
     --package "$PILOT_PACKAGE" --case "$PILOT_NEGATIVE_CASE"
   ```

   Expect a nonzero exit with `Scoped delivery mismatch: test_calculator.py`.
   This is a transport-only negative check, not a semantic test. Then delegate
   the current caller test command from `pilot.json` through the established
   test-runner and retain its result. Report complete scoped delivery and current
   caller-test evidence separately.

Use a separate case for interruption: before stopping an actual native owner,
retain its identity or handle, active child packet and the frozen-contract SHA-256.
Confirm native stop, append that evidence, and launch a fresh executor resuming
the **same child invocation and saved packet**, using its exact runtime
`next_argv`. Append the replacement's **new native agent handle**; the old native
handle remains evidence for the stopped owner. Keep every earlier owner event.
Exercise unknown-launch and running-owner refusal with separate native parent
probes. A missing handle after launch intent never authorizes a replacement.
Use existing workspace suites for foreign/stale receipts, conflicting return,
duplicate return and dirty-state preservation; they do not establish native
behavior. Include a native stale-evidence acceptance probe too.

Retain incomplete/blocked cases and all raw evidence. No cleanup until actual
workers/delegates stop and required artifacts are archived. This qualification
does not establish automatic return after parent exit or behavior on other hosts.
