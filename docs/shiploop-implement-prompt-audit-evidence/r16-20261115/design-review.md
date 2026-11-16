1. **Goal**

Repair the four release-state instructions so they report actual observations and require independently qualified checks, while preserving existing authority, stage boundaries, and remaining delivery obligations.

2. **Material issues**

The plan is sound, with these narrow corrections.

- **Qualify each check for what it actually claims.** “Reject a check that accepts both correct and wrong identities” applies to an identity check. A behavior test can legitimately pass on both revisions; an existence query can establish presence without establishing revision. The existing `consumer_checks` list includes broader consumer tests ([shiploop_prompts.py — release-plan duty 6](/Users/dadleet/src/skill-craft-r16-20261115/skills/shiploop/scripts/shiploop_prompts.py:1780)). Preserve the Salesforce metadata query as presence evidence, and require separate identity evidence where needed ([salesforce.md — tab confirmation](/Users/dadleet/src/skill-craft-r16-20261115/skills/shiploop/references/platforms/salesforce.md:55)). Suggested wording: “Qualify each check against independent controls for its claimed observation; an identity check must reject a different revision.”

- **The three target states are valid observations, not exhaustive outcomes.** A failed command, unreadable target, or inconclusive response establishes neither absence nor a different revision. Add one short instruction to record an indeterminate observation honestly. Likewise, unavailable controls leave the check’s discrimination unverified; recording that limitation must not imply qualification or waive a required check. This belongs directly beside [release-check duty 4](/Users/dadleet/src/skill-craft-r16-20261115/skills/shiploop/scripts/shiploop_prompts.py:1806), without a new status schema.

- **Keep pre-release prose separate from structured delivery completion.** Your `summary`/`evidence_refs` approach is correct. The existing implementation permits positive effect/identity declarations at `release`, and rejects them at `release-check`; `already-current` is restricted to effect/identity obligations ([shiploop_consumer_delivery.py — observation validation](/Users/dadleet/src/skill-craft-r16-20261115/skills/shiploop/scripts/shiploop_consumer_delivery.py:424)). The acceptance fixture must not submit an early structured `already-current` observation or change this gate to accommodate it. Record the observed and requested identities in prose, then preserve the designated completion phase.

- **Resolve the adjacent “run once” wording for an initially current target.** [Release duty 3](/Users/dadleet/src/skill-craft-r16-20261115/skills/shiploop/scripts/shiploop_prompts.py:1827) explicitly avoids repeating an unchanged operation after a replan, but still initially says to run the planned operation once. The N/A branch helps, yet “candidate already present” must not turn the entire release into N/A while access, visibility, publication, or promotion remains incomplete. A warranted one-clause companion edit is: “Run each still-required authorized operation once; cite current evidence for effects already satisfied.” Preserve separate effect and identity checks. This is a small consistency edit adjacent to the four identified contradictions.

- **Name the acceptance boundary precisely.** The cited release-slice test invokes `check`, which establishes draft admission, not accepted progression ([release-slice test — submit](/Users/dadleet/src/skill-craft-r16-20261115/test/shiploop-e2e-release-slice.test.py:217)). The smallest stronger fixture uses actual release-plan producer completion, its existing Improve import, then actual release-check completion. The reusable helper already exercises those import callbacks ([actual-improve-cli test — completion helper](/Users/dadleet/src/skill-craft-r16-20261115/test/shiploop-actual-improve-cli.test.py:407)). Label its authored results and review content synthetic.

  An empty `consumer_checks` list with N/A proves only that admission branch. It cannot establish consumer-check execution: those commands run at `release-verify` ([shiploop_test_loop.py — OUTER_SOURCES](/Users/dadleet/src/skill-craft-r16-20261115/skills/shiploop/scripts/shiploop_test_loop.py:369)). No release-verify callback is needed for R16’s narrow admission claim; add one only if claiming execution through that gate.

3. **Minor nits**

- Say “four instruction sites across three files.” Preserve Salesforce navigation, source-file, and metadata-query details.
- Snapshot target paths as well as bytes, so accidental file creation or deletion is detected. Keep observer logs outside the target.
- Keep expected identity fixed independently of the observed target. A comparison whose expected value comes from that same target is circular.
- Add the required `changes/shiploop/` note. Leave generated versions and release output untouched.
- Refresh current recommendation links and status statements without rewriting frozen evidence or expanding into a general documentation cleanup.

4. **Open unknowns**

- **Model uptake remains unknown.** String contracts, actual observer execution, and synthetic CLI results cannot establish that a model follows the revised instructions.
- **The generic fixture’s authority coverage needs explicit selection.** The cited fixture initializes and synthetically advances its parent; do not assume this exercises the opted-in delivery-contract refusals. Reuse established authority tests or explicitly enable that contract in the selected fixture.
- **Local controls qualify the local observer only.** They establish neither Salesforce behavior nor coverage of every package type. Generic wording is appropriate; universal empirical coverage is not claimed.

I verified the clean checkout at `6207cffbf36c1632f9d9b18d6431c26cba0f447d`, the cited instruction sites, callback code, and four supplied commit messages. I ran no tests or callbacks and made no writes.

5. **If I were implementing tomorrow**

1. Add a fail-first emitted-packet/reference regression covering all four contradictions, including the distinction between actual-state observation and check qualification.
2. Patch those sites, plus the small release-duty qualifier above. Preserve authority and stage semantics.
3. Exercise one small generic observer against absent, correct, and wrong-revision fixtures; capture output and exit status, verify unchanged targets, and reject an always-success observer. Include an observation-error case that cannot become “absent.”
4. Reuse one generic CLI fixture through release-plan completion/import and release-check completion, attaching the actual observer artifacts. Assert preserved observations and normal refusals; identify all synthetic setup and submissions.
5. Run the affected established suites with the specified Sol 6.1/medium executor, obtain the independent Astra/high source review, and update the change note and current R16 record.

**Yes—skip an additional model benchmark for this deterministic contract repair.** The sufficient callback boundary is accepted release-plan import through release-check completion. Report instruction consistency, local observer qualification, and CLI admission separately; leave model behavior and deployed acceptance unclaimed.
