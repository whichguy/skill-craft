<!-- Astra's review of the E17 registration (README Amendment A14) before any scored trial, 2026-11-15. Model gpt-6-astra via Codex (persona codex-astra),
     effort max, profile consult (read-only sandbox), fallback off, exit 0. The brief is review-brief.txt in this folder. Everything below the line is its answer,
     verbatim. Journal entry R9 records what was verified and what was changed. -->

---

**I would fix the oracle before running any scored E17 trial.** The experiment is useful as a small stress test of complete workflows, but its current implementation can declare incomplete features valid. Several measurements also support narrower conclusions than the registration assigns them.

**The one change I insist on:** make `ticketfix.evaluate` run the actual held-out acceptance suites, require all five interaction results, and calibrate that complete oracle on the composed reference and targeted defective deliveries. Assignment currently omits **18 acceptance checks**, and import omits **13**.

I reviewed the working-tree apparatus, packets, reference patches, relevant harness code, and earlier learning commits. I changed nothing. Verification was static plus small in-memory probes; I did not rerun calibrations that create repositories.

1. **The “acceptance oracle” does not run the full acceptance oracle. This is the principal blocker.**

   `case_checks()` returns only `cases[case]["checks"]`. For assignment and import, those are the suite check, pristine-base check, and one happy-path HTTP probe. Their substantial held-out acceptance modules live separately under `quality.acceptance` and are never invoked. [ticketfix.py — case_checks:88](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/ticketfix.py:88), [cases.json — assignment acceptance:929](/Users/dadleet/src/skill-craft/test/shiploop_e2e/cases.json:929), [cases.json — import acceptance:1391](/Users/dadleet/src/skill-craft/test/shiploop_e2e/cases.json:1391).

   Consequently, the independent oracle does not enforce assignment validation, assignment notifications, its audit behavior, or import atomicity, notifications, and the 5,000-ticket performance requirement. Worker-written tests might enforce them; that is precisely what an independent oracle must not assume.

   This omission affects the central conclusions: “valid,” P81, interference detection, and the interpretation of a green queue. A fast implementation that overlooks import atomicity can look better than a slower correct implementation.

   The existing calibration does not settle this: `calibrate_real.py` principally exercises queue mechanics using small fixed edits, and the interaction selfcheck also reads only the cases’ basic `checks` lists. [calibrate_real.py — synthetic additions:91](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/calibrate_real.py:91), [interactions.py — load_case_checks:462](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/real-repo/interactions.py:462).

2. **The interference measure cannot reliably attribute damage to integration, and R18 lacks a common denominator.**

   Every feature’s final verdict includes the same global suite and pristine-base checks. Suppose T1 works, while T2 contributes an independently broken test. The final global suite fails, so T1 can be labeled “interference” even if T1’s behavior survived unchanged. The comparison is between aggregate check results, not necessarily feature behavior. [ticketfix.py — final, alone, and interference:199](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/ticketfix.py:199).

   There are two further attribution gaps:

   - Only **first attempts** are checked alone. A feature that initially fails, is correctly repaired, and is subsequently broken by another merge is absent from this interference count.
   - R18 compares integration failures observed throughout the run with hidden-oracle failures observed only at the end. It misses green-but-broken intermediate merges that a later worker repairs. It therefore cannot estimate the re-test’s sensitivity or false-negative rate.

   Separate global health, feature-specific behavior, and cross-feature interactions. For R18, preserve the exact candidate tree at each attempted integration and evaluate it offline, outside the timed run. Record main-before, worker, and candidate commit IDs; currently a rejected clean merge is reset without recording its candidate commit ID. [dagkit.py — merge and rollback:323](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/dagkit.py:323).

   Also verify that all three first-attempt workspaces forked the original base. Workspaces use **main at `begin` time**, while the alone checks always use the original baseline. A late first start can inherit the landing or another feature and no longer be an isolated implementation. [dagkit.py — workspace base:455](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/dagkit.py:455), [ticketfix.py — alone baseline:203](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/ticketfix.py:203).

3. **The off-check substitution is defensible, but changes what T3’s verdict means. The interaction oracle also has concrete holes.**

   Using the assignment-enabled baseline for the final composition is reasonable: the original off probe compares normalized HTTP responses, and the unconditional `assignee` field necessarily changes those responses. However, the substituted T3 check now also tests assignment behavior. Missing assignment can fail “T3” even when due-time behavior is correct. Keep this as a composition compatibility check, distinct from attribution to T3. [ticketfix.py — substitution:152](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/ticketfix.py:152), [due_times_probe.py — response comparison:444](/Users/dadleet/src/skill-craft/test/shiploop_e2e/checks/due_times_probe.py:444).

   Three assertion gaps deserve repair:

   | Check | Hole |
   |---|---|
   | I3 | Missing `due` before and after assignment passes because `None == None`. An in-memory fake-server probe confirmed this. [Comparison:310](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/real-repo/interactions.py:310). |
   | I4 | Both seeded tickets are overdue. An implementation that ignores `overdue` whenever `assignee` is present can pass. Add non-overdue tickets with both assignee states. [Fixture and assertions:319](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/real-repo/interactions.py:319). |
   | I5 | A missing due time before restart is permitted; reconstruction after restart can masquerade as preservation. Require a valid value before restarting and unchanged afterward. [Comparison:378](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/real-repo/interactions.py:378). |

   These are demonstrated assertion gaps, not a claim that one defective candidate has passed every combined check.

   The oracle also **fails open** when `interactions.py` is absent, and an empty result object satisfies its `all(...)` expression. Require exactly I1–I5 with successful results and a successful checker process. [ticketfix.py — missing module:176](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/ticketfix.py:176), [ticketfix.py — interaction validity:208](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/ticketfix.py:208).

4. **S versus Q0 is a legitimate workflow comparison, but does not isolate concurrency or the merge queue.**

   S retains one context and sees previous implementations, tests, and design decisions. Q0 introduces fresh contexts, repeated repository discovery, isolation, a coordinator, commits, merges, automatic re-tests, and repair workers. These changes can affect both implementation quality and time. That is acceptable if R16 means “which complete workflow finished this workload better,” but insufficient for “parallelism itself paid” or “the queue cost X.” [real-A0.md — serial workflow:3](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/packets/real-A0.md:3), [real-A3.md — delegated workflow:1](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/packets/real-A3.md:1), [launch.py — isolated-only re-tests:220](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/launch.py:220).

   The highest-value additional control is **A3s: fresh workers, identical worktrees/coordinator/re-test, capacity one**. The launcher already supports it. It would help separate context reuse and orchestration from concurrency. It is unnecessary if you explicitly retain the broader workflow estimand. [launch.py — capacity-one arm:192](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/launch.py:192).

   There is also a small implementation mismatch: S is described as T1→T2→T3, but its packet permits taking **any** ready ID, and all three tasks have empty dependencies. Enforce the stated order or register order as agent-chosen. [real-A0.md — selection:6](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/packets/real-A0.md:6), [tickets3.json — task definitions:7](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/plans/tickets3.json:7).

5. **The rename is a fair mechanical-conflict test, with a strong bias toward cheap repair. It is not representative of semantic integration difficulty.**

   An internal API rename breaking newly written callers is realistic. The frozen patch is transparent and narrowly controlled. It is useful for demonstrating that a clean Git merge can require corrective work. [landing.patch — route and method rename:1](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/real-repo/landing.patch:1).

   But preserving minutes of completed implementation and changing a method name naturally favors `fix` over discarding that implementation and regenerating it. This tests a particularly repairable kind of incompatibility. It says little about conflicting persistence designs, incompatible business rules, or a repair that requires abandoning an approach.

   Nor does the rename guarantee that the first branch fails. That depends on which branch finishes first and whether its new code/tests call the old method or conflict with changed lines.

   Define whether adding a compatibility alias is acceptable recovery. Landed pristine tests protect the presence of `createTicket`, but restoring `create` and adding a forwarding `createTicket` alias can satisfy that requirement. The “no old calls” invariant is checked only during apparatus selfcheck. [ticketfix.py — selfcheck-only invariant:244](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/ticketfix.py:244).

   Finally, soften “all three touch” the entire listed file set. The supplied T2 reference touches neither notification templates nor the query filter; T3 also has a different footprint. Register overlapping implementations as expected, then measure actual paths. [T2.patch — reference changes:45](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/real-repo/refs/T2.patch:45), [T3.patch — reference changes:318](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/real-repo/refs/T3.patch:318).

6. **Qp−Q0 and Qr−Qp are unpaired workflow differences, not isolated recovery costs.**

   These cells generate different initial implementations, potentially different tests, different finish orders, and different conflict histories. A faster Qr could result from a simpler initial implementation; a slower Qp could result from a difficult initial bug. The four complete runs are independent launches. [run_cells.sh — cell sequence:25](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/real-repo/run_cells.sh:25).

   If recovery-rule efficiency matters, add a **paired replay of the same failed branch against the same main commit**, once with `fix` and once with `redo`. Keep the end-to-end cells, but call their differences observed workflow differences.

   Fixed S→Q0→Qp→Qr order further confounds condition with changing machine/provider load and warm caches. One observation per cell supplies no within-cell variance estimate. Three different hosts are three different systems, not three interchangeable replicates. Counterbalance the order and retain an explicit inconclusive outcome.

   R16 also needs **both S and Q0 valid** before crediting a speedup. Its supplied wording requires Q0 validity but omits S validity. The new table currently prints all ratios whenever times exist, bypassing the older scorer’s validity and identity matching safeguards. [real_table.py — unconditional ratios:91](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/real_table.py:91), [score.py — existing comparison safeguards:733](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/score.py:733).

7. **Host and machine differences need explicit treatment-compliance evidence.**

   The launch environments are materially different. Codex uses unrestricted filesystem access with approvals disabled; Claude and Grok use their respective automatic permission systems and allow rules. Grok and Codex receive isolated profiles; Claude’s ordinary environment inherits the caller’s environment. These are valid native-host comparisons, but permission failures must be distinguished from coding failures. [hosts.py — Claude launch:412](/Users/dadleet/src/skill-craft/test/shiploop_e2e/hosts.py:412), [hosts.py — Grok launch:343](/Users/dadleet/src/skill-craft/test/shiploop_e2e/hosts.py:343), [hosts.py — Codex launch:465](/Users/dadleet/src/skill-craft/test/shiploop_e2e/hosts.py:465), [hosts.py — inherited environment:267](/Users/dadleet/src/skill-craft/test/shiploop_e2e/hosts.py:267).

   Capacity three fits the stated Codex limit, but verify actual overlap, fresh contexts, effective models, and recovery settings. Current validity does not require treatment compliance. Requested model/effort is recorded; that is not equivalent to verifying each served child’s identity. [score.py — mechanism versus validity:682](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/score.py:682), [launch.py — requested identity:242](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/launch.py:242).

   The historical record already shows host-dependent spawn staggering. Preserve startup and dispatch measurements alongside whole-run time; do not attribute those seconds to Git integration. [Journal — F32:557](/Users/dadleet/src/skill-craft/docs/shiploop-parallel-execution-journal.md:557).

   Side-by-side hosts also interfere through **untimed scoring**: after one host exits, its oracle runs while another host may still be timed. The launcher captures only initial load average. Record load throughout, including scoring activity, or run timed cells in a controlled quiet window. [launch.py — load snapshot and post-run scoring:251](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/launch.py:251).

8. **The network retry policy identifies error strings, not machine-caused failures.**

   `ECONNRESET`, `ECONNREFUSED`, and `EPIPE` can also result from defective application code. The current regex does not establish their cause. Moreover, retries overwrite earlier output; a successful final attempt records its count but loses the previous failure evidence. [dagkit.py — retry and logging:260](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/dagkit.py:260), [ticketfix.py — oracle retry:158](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/ticketfix.py:158).

   Keep every attempt’s output, return code, duration, and candidate identity. Report first-attempt and eventual outcomes separately. Describe these as **network-error retries** unless machine causation is independently established. The interaction server’s narrower retry on its own startup `EADDRINUSE` is a better-grounded classification. [interactions.py — startup retry:118](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/real-repo/interactions.py:118).

The queue’s normal paths are sensibly structured: completed branches remain available, merges follow recorded completion order, failed clean merges are rolled back, and repair gets the failed branch plus current main. These failure boundaries remain uncovered:

| Failure mode | Consequence and evidence |
|---|---|
| **Landing re-test fails, but merging continues.** | `_apply_landing` records `ok=False` and returns normally; `_merge_pending` proceeds. I confirmed the normal return with an in-memory probe. Landing commit failure is also unchecked. An invalid intervention can therefore contaminate the trial instead of being classified as an apparatus fault. [dagkit.py:285](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/dagkit.py:285). |
| **A repair legitimately needs no new edit.** | Merging current main into the failed branch may itself fix the failure, or a transient failure may disappear. That merge is already committed, but `complete` insists on another successful commit and refuses the clean tree as “empty.” This can strand a correct repair or induce an irrelevant edit. [Workspace merge:460](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/dagkit.py:460), [completion refusal:492](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/dagkit.py:492). |
| **Workspace creation fails after `start`.** | `start` is logged first. A failed `worktree add` leaves the task running; another `begin` is refused, while `release` cannot release a started task. A worker disappearing after `begin` has the same lack of recovery. [begin:535](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/dagkit.py:535), [release:375](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/dagkit.py:375). |
| **Git operational errors become “conflicts.”** | Any failed merge is classified as a conflict, even without unmerged paths. Abort/reset results are unchecked. Lock or filesystem errors can consume attempts and inflate conflict counts. [Merge failure handling:333](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/dagkit.py:333). |
| **Re-tests hold the global ledger lock.** | Other workers’ `begin`/`complete` calls wait behind integration tests. This is bounded during ordinary successful tests, but can distort attempt durations and delay unrelated workers substantially on timeouts. Measure lock waiting separately. [ready lock:348](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/dagkit.py:348), [re-test timeout:262](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/dagkit.py:262). |

These deserve targeted calibration cases. The existing seven mutation checks establish those seven guards; they do not establish crash recovery or every retry state.

Several promised measurements also need correction before scoring:

- **P74’s “kit seconds” excludes re-tests, landing, and the merge duration of red-test failures.** Rollback/abort time is unrecorded. Adding all re-tests plus landing duration would double-count the landing’s test. Define one nonoverlapping accounting scheme. [score.py — script sum:624](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/score.py:624), [dagkit.py — landing duration:280](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/dagkit.py:280).
- **R17’s denominator is ambiguous.** `first_round_s` is latest first completion minus earliest start, including dispatch stagger—not the longest individual first attempt. Specify the metric and which cell supplies it. [real_table.py:43](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/real_table.py:43).
- **Codex token totals silently omit children without usage records.** Missing usage must make the aggregate incomplete, rather than contribute zero to P80. [score.py:461](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/score.py:461).
- **“Faithful report” currently means faithful status lists.** Ticket trials’ numeric answers are not checked. Compare FINAL’s answer with the recorded T3 outcome; separately verify workers’ reported counts against their own test outputs. [score.py — fidelity:137](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/score.py:137), [score.py — unused ticket counts:605](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/score.py:605).
- **Freeze scoring provenance.** Preserve the source revision and hashes of fixture, checks, cases, interaction oracle, and landing. The launcher currently hashes kit and packet, while later scoring reads live repository files. [launch.py:251](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/launch.py:251), [ticketfix.py:88](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/ticketfix.py:88).

For P70–P81, these are my calibration judgments, not replacement empirical probabilities:

| Prediction | Assessment |
|---|---|
| **P70 — 85%** | Plausible, but strong as an all-three-host conjunction. Overlapping files make failure likely; actual footprints and scheduling determine whether it occurs. Verify common starting bases and actual concurrent execution. |
| **P71 — 75%** | **Too optimistic as a reliability statement, and too weak as written.** A task can hang without ever reaching `mergefail`. Require every task to integrate within four attempts. The disclosed smoke’s three-attempt task leaves limited margin. |
| **P72 — 65%** | I would lower confidence modestly. Minute-scale work helps, but S benefits from accumulated understanding and Q bears repeated repair. Score speed claims only on valid, compliant pairs. |
| **P73 — 40%** | More optimistic than P72: a 25% saving on every host requires substantial room beyond coordination and repair. The Claude smoke supplies no measured S denominator. |
| **P74 — 80%** | Not ready to score until inclusive kit time, the median population, and zero-retest cases are defined. It is primarily an engineering-budget prediction informed by apparatus measurements. |
| **P75 — 75%** | Plausible, not guaranteed. Define “first attempted integration,” not “first branch merged.” The rename only trips branches that encounter its changed interface or lines. |
| **P76 — 70%** | I would lower confidence. It combines a direction requirement with an upper bound across independent implementations. A different completion order alone can change total time materially. |
| **P77 — 85%** | **The most overconfident timing prediction.** Cheap repair favors fix, but redo can avoid a poor implementation, and Qp/Qr are unpaired. One host reversing the ordering falsifies it. |
| **P78 — 60%** | Also high. A longer individual redo need not produce a 30% longer whole run: repairs can overlap other work, and the critical path can change. |
| **P79 — 50%** | Reconsider after repairing attribution. Current aggregates can inflate “interference,” while checking only first attempts and the final tree misses repaired intermediate failures. |
| **P80 — 70%** | Reasonable directionally, but fresh contexts may avoid S’s growing history. Complete child accounting is a prerequisite; input tokens alone do not establish dollar cost. |
| **P81 — 30%** | I would lower it after adding the omitted acceptance suites. For intuition only, 30% for twelve independent successes corresponds to roughly 90% success per trial. The smoke does not establish that rate. |

None of these is inherently unfalsifiable. P71 can pass despite operational failure, and P74 needs an executable definition. P79 and P81 are mutually exclusive under the proposed validity definition; their probabilities are coherent, but their outcomes are not independent evidence.

The disclosed smoke is legitimate pilot information. It informs feasibility, repair times, and the choice of thresholds. It does **not** answer the all-host predictions, Q0/S, or Qr/Qp. Describe the registration as prospective **after a disclosed pilot**, and preserve that pilot’s evidence.

Before committing, explicitly classify invalid pairs, timeouts, absent token records, missing first attempts, budget exhaustion, permission failures, and apparatus reruns. R16 needs an inconclusive outcome for 0.90–1.00 and invalid comparisons. Preserve original failed runs alongside reruns.

The owner could use a corrected E17 to decide whether this particular workflow is promising enough for a further ShipLoop experiment, identify expensive failure paths, and assess whether ordinary project tests miss consequential composition defects. The results would not justify:

- A general speedup or reliability rate for feature-level fan-out.
- A causal estimate of the merge queue’s cost or fix-versus-redo superiority.
- The claim that parallel coding works only for completely independent features; E17 lacks a matched disjoint-feature control.
- A host or model ranking independent of permissions, startup behavior, effort, and machine conditions.
- A decision to place concurrency inside stages, across build steps, or across work items. Those alternatives’ lifecycle and commit obligations are absent here; the journal already identifies that gap. [Journal — F15:540](/Users/dadleet/src/skill-craft/docs/shiploop-parallel-execution-journal.md:540), [Journal — F69:594](/Users/dadleet/src/skill-craft/docs/shiploop-parallel-execution-journal.md:594).

All three E17 tasks also have empty dependency lists. This is feature composition through a queue, not a feature-scale test of dependency scheduling. That narrower experiment is worth conducting once its validity gate measures the promised work.
