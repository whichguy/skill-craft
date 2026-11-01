# Astra's review of the start-route work (2026-11-01)

Asked after the work had shipped, in answer to the owner's question "Did we ask Astra for any feedback on the intention of what we're
trying to do and if it would modify anything, and then consider that plan and implement it?" (the answer was no; the standing rule is
in the owner's instruction of 2026-10-25 that design feedback goes to Astra at max effort). The journal section "Astra's review" in
`README.md` lists each finding, what was verified, and what was done.

- Consult: `ask.sh astra --json --effort max --profile consult --cwd <read-only checkout of origin/main at 1fa2e18b0cf9c62e83561d8db0852e2fd46e0a82>`
- Reported by the runner: model_used `gpt-6-astra`, persona `codex-astra`, effort `max`, fallback `False`,
  profile `consult`, sandbox `read-only`, exit `0`. About 2.4M input and 28.6K output tokens (14.3K reasoning).
- The file links in the answer point at the checkout the consult read; they resolve against the repository root at that commit.

## Brief sent

You are an independent senior reviewer at maximum effort. Analysis only: do not edit, create or delete any file; the working directory is a read-only checkout of the repository at commit 1fa2e18b0cf9c62e83561d8db0852e2fd46e0a82 (origin/main, 2026-11-01). Verify what you can against that checkout and say which claims you verified and which you only took from this brief.

WHAT THE WORK IS. Repository skill-craft; ShipLoop is a markdown-authoritative SDLC harness. Its CLI (skills/shiploop/scripts/shiploop) starts a run with `workspace start` (the isolated entry: a separate worktree, the finished work is returned to the starting folder, an empty folder is made a Git repository) or `init` (the direct entry: works in place, no return protection). A live Salesforce run on 2026-11-01 began with `init` in an empty folder that was not a Git repository, and its product was left uncommitted outside any repository.

THE INTENTION. Make that wrong first command rare, and recoverable when it happens, without harming an explicit in-place or non-Git request or other hosts, with every claim measured through the E2E harness (test/shiploop_e2e/run.py) rather than argued.

WHAT WAS DONE (one session, by one model, with the owner approving a ranked 8-item plan by saying "All of them"; no independent model reviewed the plan or the designs before they shipped, which is why you are asked now).
1. A card wording change (T2: the direct entry needs an explicit in-place or non-Git request; naming the current directory is not one). Codex gpt-6.1-terra xhigh, first start `init` on the Salesforce prompt: old wording 17/40 then 8/40 in a replication (pooled 25/80), T2 0/40 and 1/40 (pooled 1/80). Released as 2.27.3.
2. Explicit in-place and non-Git requests on T2 still begin with `init` (48/48). Claude and Grok hosts: 96 sessions each, 0/16 `init` on the Salesforce prompt under either wording (no headroom), explicit requests 24/24 `init`.
3. A script guard (released 2.31.0 / 1.30.0): `init` in an empty non-Git folder is refused with the `workspace start` command; `--in-place` overrides. First design (flag visible in `init --help`): of 60 old-wording Salesforce sessions, 16 began with `init` and 0 were refused, because all 16 had run --help first and passed the flag at once. Second design (flag hidden from --help via argparse.SUPPRESS, named only in the refusal, refusal also says a request naming the current directory is not an in-place request): 20/20 first-`init` sessions were refused and then ran `workspace start`; 24/24 explicit requests were refused once, then ran `init --in-place`; 0/20 sessions on the T2 card began with `init`. Only Codex Terra was probed after a refusal.
4. Harness work (--stop-after-start, start_route in result.json, orphan-observer cleanup), a probe driver (docs/experiments/start-route-20261101/start_probe.py), an analysis script with pre-registered rules (analyze.py), fixes to two load-sensitive tests, 17 suites' fixtures changed for the guard, a change to the release preflight so merge commits are not counted as ShipLoop changes, journal entries (docs/experiments/start-route-20261101/README.md, test/shiploop_e2e/LEARNINGS.md), and `No-E2E-Round:` trailers on the guard commits (the evidence behind them is the two probes, not a full case; one post-release `hello` case passed, n=1).

WHERE TO LOOK. Journal and registrations: docs/experiments/start-route-20261101/README.md. Guard: skills/shiploop/scripts/shiploop_protocol.py (`_in_place_refusal`, the `--in-place` argument), tests in test/shiploop-workspace.test.py (`DirectEntryGuardTests`). Card sentence: skills/shiploop/SKILL.md ("Use the direct entry only when ..."). Gate: scripts/release.py (`e2e_round_missing`) and test/release-preflight.test.py. Last three entries of test/shiploop_e2e/LEARNINGS.md.

WHAT I NEED FROM YOU.
1. The intention: is it the right goal? What is the real failure to prevent, and is a first-command guard the right lever, or would you move the protection elsewhere (for example return protection or an end-of-run check for direct runs, making `init` in an empty folder bootstrap Git, or removing the direct entry from the card)? Would you reorder, merge, drop or add anything in the 8-item plan (it was: opposite-direction probe; record the start route in the harness; the CI test flake; same guards on Claude and Grok; harness fixes for orphan observers and a stop-at-first-start mode; the script guard; a probe checklist; align three references with the card sentence)?
2. The guard: what could go wrong that the two probes could not show (self-certification after the refusal on other models, friction on explicit runs, hidden-from-help flag as a product practice, scripts outside the repo, the refusal text as a prompt)? What would you change, and what is the smallest experiment that would settle each?
3. The measurement: threats to validity in the registered rules, single prompt/model/effort, instrument errors found mid-run (a --help read counted as a start; python -c starts with escaped quotes missed; stray observers), the replication result (control 17/40 vs 8/40), and the "insufficient, add sessions" remedy I declined to run after the first probe.
4. The process: the release-preflight change, the `No-E2E-Round` trailers and journal entries used to pass the gate, the side effect (probe sessions ran the real Salesforce CLI and raised macOS keychain dialogs on the owner's screen). Any integrity or hygiene problem?
5. What did I get wrong or not consider? Return a ranked list of modifications (P0/P1/P2), each with the evidence that would settle it and the smallest experiment; then list what you would NOT change. Keep it concrete, cite file and symbol, and separate verified facts from opinion.

## Answer (verbatim)

**I would keep T2 and retain the current refusal provisionally. I would not yet call the original delivery failure fixed.** The strongest evidence concerns entry selection and recovery to a workspace. It does not establish that a mistaken start reliably ends with the intended product safely delivered, or that the new refusal preserves legitimate direct runs across hosts.

The real failure to prevent is **an unintended delivery state being accepted as completion**: here, product files outside Git when the normal workflow should have produced a versioned delivery. “The first command was `init`” is a useful diagnostic, but it is not that failure itself.

I verified HEAD as `1fa2e18b0cf9c62e83561d8db0852e2fd46e0a82`, inspected the implementation, relevant tests and full commit messages, recounted the committed compact results, and exercised analysis functions in memory. I made no file changes and ran no live model, Salesforce command, or write-producing test suite.

| Claim | What I verified |
|---|---|
| Card experiment | Committed rows reproduce C **17/40 then 8/40**, T2 **0/40 then 1/40**, and T1 **4/40 then 1/40**. |
| Explicit requests, card only | T2 **48/48** direct starts; the control also **48/48**. |
| Other hosts, card only | Each host has 96 recorded sessions, with the reported Salesforce and explicit-request counts. |
| First guard | All **16** first-`init` Salesforce sessions already carried `--in-place`; **15** produced direct runs and **one produced no run**. |
| Second guard | Recorded sequences show **20/20** mistaken starts switching to workspace and **24/24** explicit requests retrying with `--in-place`. |

The [experiment artifacts and journal](/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/astra-view/docs/experiments/start-route-20261101/README.md:195) support those counts. This verifies the retained records and their arithmetic, **not an independent reconstruction from every raw event stream**. The live Salesforce incident, keychain dialogs, CI passes and post-release `hello` result are documented evidence that I did not independently reproduce. The absence of an earlier independent design review comes from your brief; the owner approvals are also quoted in repository commit messages.

My ranked modifications follow. **P0 here means before further probes on the owner’s machine**, not that the shipped card needs an emergency rollback.

1. **P0 — Make probe containment real, and replace the driver’s broad process killing.**

   “Stop after startup” does not prevent actions before startup. The supplied Salesforce prompt explicitly requests deployment and says the CLI is authenticated. Nevertheless, `run.py` rejects a declared platform under `--stop-after-start` and recommends `--prompt`, which removes that platform configuration. It also skips port leases on the assumption that nothing will be served. Neither assumption constrains the model.

   This is especially significant across hosts: `ClaudeHost.env` inherits the base environment, whose `Host.env` preserves the real HOME; Codex receives a throwaway HOME but runs with `danger-full-access`. A disposable profile is not filesystem, credential or network isolation. These are source-verified behaviors in [hosts.py — environment and invocation](/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/astra-view/test/shiploop_e2e/hosts.py:253) and [run.py — probe platform handling](/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/astra-view/test/shiploop_e2e/run.py:4064).

   The cleanup workaround introduces another risk. `start_probe.reap` sends `SIGKILL` to any process whose command contains the trial path or whose working directory starts with that string. It verifies neither ownership nor process identity. For example, `/tmp/probe-a10/work` matches the prefix `/tmp/probe-a1`; an unrelated reader mentioning the directory can also match. The repository already has stronger identity checks in `lifecycle.stop`. [start_probe.py — reap](/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/astra-view/docs/experiments/start-route-20261101/start_probe.py:191)

   **Change:** run route probes without real application credentials or unrestricted application access; provide deterministic Salesforce responses where needed. Keep leases unless the execution boundary actually prevents listeners. Use the existing lifecycle ownership machinery for cleanup, with path-component checks only as supporting evidence.

   **Smallest settling experiment:** one adversarial fake-host case through `run.py` that attempts an application command, binds a port before ShipLoop starts, and leaves an escaped child. Add an unrelated process with a matching-looking path. Verify that application access is contained, the owned child disappears, and the unrelated process survives. Then run one Salesforce-prompt smoke per host.

   Keep `SF_USE_GENERIC_UNIX_KEYCHAIN`: it addresses the observed dialog mechanism and is an officially documented headless-use setting. It does **not** establish general probe containment. [Salesforce CLI setup guide](https://resources.docs.salesforce.com/latest/latest/en-us/sfdc/pdf/sfdx_setup.pdf)

2. **P1 — Separate attempted entry, successful initialization and final delivery in the measurements.**

   There is a concrete early-success problem in `start_route.route`: a `workspace.md` beneath `.shiploop-runs` returns `"workspace"` **without requiring `run/state.md`**. `workspace._prepare` writes that manifest before the internal `init`; it can also write a manifest with status `blocked`. Consequently, a probe can stop and credit workspace recovery before initialization succeeds. I reproduced the classification with an in-memory stub. [start_route.py — route](/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/astra-view/test/shiploop_e2e/start_route.py:39), [shiploop_workspace.py — manifest creation](/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/astra-view/skills/shiploop/scripts/shiploop_workspace.py:1080)

   The field also searches for *any* workspace and is recomputed when `result.json` is written. It does not establish which route happened first, or necessarily describe the run selected by `run_choice.choose`. A direct run followed by an abandoned workspace can therefore be described misleadingly.

   The command detector remains fallible too. I reproduced these results from `detect_start`:

   | Input | Current classification | Correct interpretation |
   |---|---|---|
   | `…/scripts/shiploop init --repo /tmp/work --help` | direct | Help request |
   | `printf … '…/scripts/shiploop init --repo …'` | direct | Printed text |
   | `$CLI init --repo … --prompt=x`, without “shiploop” elsewhere | none | Potential invocation |
   | Python command with an earlier unrelated `['init']` list, then a workspace invocation | direct | Workspace invocation |

   [start_probe.py — detect_start](/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/astra-view/docs/experiments/start-route-20261101/start_probe.py:85)

   **Change:** retain separate records for attempted commands, actual refusal results, successfully initialized run identity/mode, and delivery outcome. Require a validated state associated with the workspace and successful initialization before counting recovery. Preserve the first successful initialization rather than inferring chronology from final directory contents. Keep refusal instrumentation outside the product/run directory so refusal remains non-mutating.

   **Smallest settling experiment:** deterministic harness fixtures for help, printed commands, partial/blocked workspace preparation, successful direct initialization, and direct-then-workspace histories. Then independently audit the 20 recorded recoveries for successful initialization. Re-run only cases whose retained evidence cannot settle that question.

3. **P1 — Make the analyzer refuse incomplete or unreadable evidence.**

   I reproduced two false assurances:

   - Eight recovered GOLD sessions plus four successful `inplace-hello` sessions produce `RELEASE`, with **zero G Salesforce sessions and zero non-Git sessions**.
   - Other-host cells containing only no-start sessions produce `NO REGRESSION FOUND`.

   `load` does not check the planned slot inventory. `evaluate_guard` allows H3 to pass vacuously on zero observations. `evaluate_hosts` lacks the registered “unreadable” outcome. These did not change the reported complete-batch counts, but they undermine the analyzer as an enforcement mechanism. [analyze.py — load and evaluators](/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/astra-view/docs/experiments/start-route-20261101/analyze.py:44)

   Additional weaknesses:

   - A model session that never touches the skill is marked invalid and retried. That can be a behavioral failure, not infrastructure failure; the Claude journal reports one such exclusion.
   - Validity checks the installed **card** hash, while the guard lives in a script. `plugin_verdict` is recorded but not enforced.
   - `card_sizes` reconstructs historical arms from the **current** card. On this checkout, original `arms.json` produces C=30,115 and T1=30,137 bytes, rather than the historical 30,011 and 30,033. Historical analysis should not silently depend on today’s source.

   **Change:** require the registered plan and immutable artifact manifest as analysis inputs. Distinguish pre-model infrastructure failure, behavioral no-start and unobserved outcome. Verify whole-package and harness identities, enforce cell completeness, and return `INSUFFICIENT` for missing or unreadable cells. Preserve requested versus observed model identity separately where available.

   **Smallest settling experiment:** feed those two counterexamples, a missing slot, a mismatched script build and a no-skill session through the analyzer. Then replay every committed batch and verify that complete historical results retain their conclusions.

4. **P1 — Make the guard’s advertised recovery work for the states it refuses.**

   The `.shiploop` corner case is a source-verified mismatch:

   - `_in_place_refusal` ignores the selected run directory when deciding whether the product folder is empty.
   - `bootstrap_empty` accepts only a directory with **no entries at all**.
   - Thus, a non-Git folder containing only an empty `.shiploop` is refused and directed to `workspace start`, whose bootstrap does nothing.

   The existing test checks that this folder is refused, but never executes the recommended recovery. [shiploop_protocol.py — _in_place_refusal](/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/astra-view/skills/shiploop/scripts/shiploop_protocol.py:541), [shiploop_workspace.py — bootstrap_empty](/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/astra-view/skills/shiploop/scripts/shiploop_workspace.py:966), [DirectEntryGuardTests](/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/astra-view/test/shiploop-workspace.test.py:2909)

   The suggested command also drops requested options such as `--delivery-contract`, `--lint`, `--delegation` and the selected Improve skill. The model may reconstruct them, but the probes did not verify that. Finally, detection depends on the English Git error string; a localized error can bypass it.

   **Change:** share eligibility logic between refusal and recovery, preserve applicable options, and handle options without a workspace equivalent explicitly. Normalize the Git probe’s diagnostic locale. Do not automatically delete a pre-existing run directory to make recovery succeed.

   **Smallest settling experiment:** execute refusal followed by the printed recovery for a truly empty folder, an empty `.shiploop`, and `.shiploop/.lock`; inspect the resulting state with nondefault options. Add a localized-error fixture.

   Also retain boundary tests for a missing target directory, `.gitignore`/other content, nested repositories and existing runs. Those currently bypass the guard deliberately. They show why it cannot be the sole delivery safeguard.

5. **P1 — Add an outcome-level check for direct runs, governed by the requested delivery policy.**

   The missing protection is visible in the code. `workspace_completion_guard` applies only to `navigator-worktree`. `_commit_stage` explicitly skips committing when there is no iteration/base record and lets the workflow continue. The new `--in-place` flag is used for entry admission but is not passed into `new_state` as a durable explanation of the exception. [shiploop_protocol.py — workspace_completion_guard](/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/astra-view/skills/shiploop/scripts/shiploop_protocol.py:390), [shiploop_navigator.py — _commit_stage](/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/astra-view/skills/shiploop/scripts/shiploop_navigator.py:3230)

   **My architectural recommendation:** keep the early guard, but distinguish workspace isolation from versioning and delivery expectations. An in-place request does not necessarily request unversioned work. Conversely, explicitly non-Git or intentionally uncommitted work must remain valid.

   Record the selected policy and its basis, check prerequisites before product edits where possible, and verify the actual disposition at completion. A default protected run must not silently finish unversioned. A legitimate non-Git run should finish with its files verified in the requested location and an accurate report. Existing mistaken direct runs need a preservation-first recovery path, not an instruction to abandon them and start over.

   Do **not** require every final checkout to be clean and committed indiscriminately: workspace returns can intentionally apply a working-tree delta without a commit. That is documented behavior. [workspace-lifecycle.md — working-tree returns](/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/astra-view/skills/shiploop/references/workspace-lifecycle.md:249)

   **Smallest settling experiment:** four complete harness cases: mistaken direct entry and recovery; explicit in-place Git work with unrelated existing edits; explicit non-Git work; ordinary workspace delivery. Assert product correctness, requested location, preservation state and preservation of unrelated files. The non-Git case needs an explicitly different expected disposition: the current `committed_facts` verdict necessarily fails without Git. Declare that expectation in advance rather than waiving a failed result afterward.

   The post-release `hello` run is useful, but it exercised none of the refusal/recovery path.

6. **P1 — Test the refusal across hosts and prior knowledge before treating hidden help as a durable design.**

   Hiding the flag is a behavioral intervention, not verification of user authorization. A model can learn it from the README, source, earlier sessions or the refusal itself. The code trusts the flag regardless of who decided to pass it.

   The second design changed **two things**: help visibility and refusal wording. Its success establishes evidence for that bundle. The journal’s stronger statement that visibility was *the* cause is unsupported. Moreover, all other-host probes preceded this refusal test; they establish card compatibility, not guard compatibility.

   I would keep the current behavior while testing alternatives, rather than immediately restoring the failed help presentation. A visible override with an equally sharp condition in its help text remains an untested alternative. A stable documented override is particularly important for external scripts, which cannot reason about stderr and retry: this is an intentional CLI compatibility break.

   **Smallest useful screen:** 36 short recovery sessions: Claude/Grok × ordinary Salesforce/explicit in-place Salesforce/explicit non-Git × help-only/README-exposed × three repetitions. Supply the real refusal as a prior tool outcome without changing the original user’s intent; label these as conditional recovery probes, not natural first-command rates. Use varied natural wording, not only “I explicitly want an in-place run.”

   If changing help visibility, compare the two help presentations contemporaneously while holding the sharpened refusal fixed. Do not infer the ablation from the two historical batches.

   Those small screens can expose systematic failures. They cannot certify a low failure rate: 20/20 success still has a Wilson lower bound of approximately **84%**; 24/24 has approximately **86%**.

7. **P1 — Replace blanket merge exemption and journal chronology with scoped evidence.**

   The merge complaint was legitimate. The solution is too broad.

   `e2e_round_missing` now excludes every merge commit, and `test_what_a_conflict_resolution_itself_changed_is_not_read` deliberately demonstrates acceptance of newly written conflict-resolution code. This is a verified blind spot, not a hypothetical accusation. The owner approved the rule change, and the commit discloses it; I would revisit that decision rather than describe it as unauthorized. [release.py — e2e_round_missing](/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/astra-view/scripts/release.py:197), [release-preflight.test.py — conflict-resolution exemption](/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/astra-view/test/release-preflight.test.py:226)

   There is also an older weakness: any qualifying later journal commit covers its ancestors, regardless of whether it records an experiment on them. A journal merge can itself become the anchor. Transparent explanations make this auditable, but do not make chronology evidence of validation.

   Finally, default path-limited Git history can prune branches. I compared this checkout: **797** non-merge path commits with the current style of query versus **806** with `--full-history`; the 2.31.0 release interval showed no difference. Thus “every non-merge commit is read” is not generally guaranteed. Git documents this simplification. [Git history documentation](https://git-scm.com/docs/git-log)

   **Change:** exempt mechanical merges without exempting novel resolution behavior. Bind evidence or explicit waivers to identified changes and tested artifacts; distinguish a startup probe from a full workflow round. Journal housekeeping should not confer experimental coverage. Use complete history traversal where the policy promises it.

   **Smallest settling experiment:** synthetic histories covering a clean merge, uncovered side commit, novel conflict resolution, and journal-only merge. The clean covered merge should pass; the others should require appropriately scoped evidence or a waiver. No model runs are needed to verify this gate logic.

   The `No-E2E-Round` trailers themselves are allowed by repository policy, and their limitations were disclosed. I see **an inadequate gate and overbroad coverage claims**, not evidence of fabricated results. “E2E cases start with workspace” is nevertheless a weak exemption rationale: the incident under review exists because the model sometimes chooses otherwise.

8. **P2 — Tighten the statistical claims, registrations and retained coverage.**

   The card experiment is persuasive within its scope. I recomputed T2’s one-sided Fisher results: approximately **8.74×10⁻⁷** initially and **0.01444** in R2. The split threshold for two candidates and the independent replication are meaningful strengths. T2’s superiority to T1 was not established; retaining the preregistered selection is still reasonable.

   Several interpretations need tightening:

   - **17/40 versus 8/40 does not prove hourly service drift.** It is compatible with substantial sampling variation as well as environmental variation. Interleaving supports the within-batch comparisons. Pooling remains descriptive.
   - **Repeated sessions on one prompt estimate behavior on that prompt.** They do not provide prompt diversity or isolate “current directory” as the causal phrase. T1’s unexpected benefit is contrary evidence to a narrow causal story.
   - **No detected regression is not equivalence.** The explicit-path harm rules tolerated large losses. H2 could accept 20/24 successful explicit runs—four requests dishonored—despite the stated intention of preserving them.
   - **The first guard’s H1 conditioned on being refused**, excluding precisely the bypasses that defeated it. Switching to E for the next experiment was warranted. E is a useful diagnostic, but an all-assigned-session outcome should also count unauthorized direct starts, non-starts and other failures.
   - **50 versus 44 seconds is an observational comparison**, not an isolated six-second refusal cost. The groups chose different routes and may have done different preparation.
   - **“No measurement changed” after the keychain incident is not established by medians.** The repository’s incident report records blocked Salesforce processes in earlier trials. A median cannot exclude affected tails or interference between trials. [keychain evidence report](/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/astra-view/docs/e2e-salesforce-chess-evidence/2026-11-01-keychain-dialog.md:19)

   **You were right to decline more sessions on the first guard.** “Insufficient H1 evidence” did not erase the observed bypass mechanism. Stopping an unreleased candidate for futility, recording the deviation, then preregistering a new design is sound engineering. The 19% upper bound was not an estimated refusal rate, and the extrapolated “160 more sessions” was not a guaranteed sample requirement; the rejection did not need that argument.

   The mid-run instrument repairs were also defensible because they were documented and followed by R2. Retrospective classification can recover the first command from a missed event; it cannot undo premature stopping or side effects from sessions allowed to continue. Treat R2 as the stronger confirmation and retain R1 as corrected evidence.

   **Smallest next work:** audit the retained streams around every first start/refusal, freeze the corrected instrument, and register a small diverse prompt set with explicit no-start and harm outcomes. Broaden prompts and recovery conditions before buying more repetitions of the same Salesforce request. Replace the checklist’s automatic “two control arms” prescription with blocked replication when the question is variation over time.

   Preserve some formerly non-Git test fixtures using `--in-place`. Converting them to Git changes exercised behavior even when assertions remain unchanged; it can remove coverage of the commit-skipping paths now central to this issue.

I would reorder the eight-item plan as follows:

| Order | Work |
|---|---|
| First | Merge **2 + 5**: route instrumentation, stopping and lifecycle cleanup. Add containment and analyzer calibration. Move **7**, the checklist/registration, here. |
| Second | Combine **1 + 4** into bidirectional, cross-host checks. Include **8**, reference alignment, in the candidate being tested. |
| Third | Evaluate **6**, the guard, including explicit recovery, prior flag knowledge and affected full-run delivery. Add the missing completion-policy work. |
| Separately | Keep **3**, CI flake maintenance, independently reviewable. Treat release-preflight policy as its own direction-setting decision. |

An independent review before the guard’s public CLI change and before changing the release gate would have been particularly valuable. The likely benefit is catching the wrong success criterion and exemptions—not adding another vote on wording.

I would **not** change these things:

- **Keep T2.** Its benefit replicated; no evidence justifies reverting it or claiming T1 is better.
- **Keep direct entry available.** Removing it from the card would damage legitimate workflows and move discovery elsewhere.
- **Do not silently bootstrap Git in every `init`.** That violates explicit non-Git requests and still does not supply isolation or return protection.
- **Keep refusal before the run lock**, with no run artifacts created by refusal.
- **Keep the failed first guard and deviations in the journal.** Declining to release it was the correct decision.
- **Keep the stop-race test fix.** It accepts two legitimate process endings while preserving the meaningful stop/no-resume assertions.
- **Keep the bounded teardown retry as a disclosed mitigation**, not a proven root-cause fix. Its failure-rate benefit remains unmeasured.
- **Keep first-start probes as a cheap tool.** Require full runs for delivery claims, and deterministic checks for instrument and release-gate claims.
