# Astra review of the parallel-plan-execution registration (2026-11-14, before any trial)

- Runner: ask.sh astra --json --effort max --profile consult (read-only, no fallback). Reported: model_used gpt-6-astra, persona codex-astra, effort max, profile consult, sandbox read-only, fallback False, exit 0.
- cwd: the skill-craft canonical checkout. Astra read the registration (552792ac1d412f67c3c5c4820a23d5c935d36e21) and, while it ran, the apparatus
  (2883cdbaed5148c2cf2b05e48c56363c0f3d194e) and the amendment (26d7e02496bc88f28992a3a735ab9936df94fa41); it made no edit and launched no trial.
- Question given to it: [astra-question.txt](astra-question.txt). Its answer follows verbatim, unedited. My weighing of each point is in the journal, entry R1.

---

1. **Intention: broadly understood, but narrowed too far toward executing implementation-step DAGs — P0.**

   The owner wants an **opt-in way to use native agent contexts and concurrency wherever they improve ShipLoop**, including planning and work inside the inner loop. The registration captures native agents, runtime dependencies, isolated experiments and readable timing evidence. It postpones three central questions: parallel planning, retaining only useful outcomes, and handling tasks that interact with changing parent state. Those should influence the first fixtures, not remain E6’s “question only.” [Registration — questions and experiment ordering](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/README.md:47)

   **P0 — “True dynamic workflow” should mean completion-driven execution under one authority.** Recompute eligible work when an outcome is accepted, a prerequisite fails, capacity changes or relevant state becomes stale. Do not wait for an arbitrary wave. This does **not** authorize workers to select successors or silently revise the graph. A2 is a useful diagnostic of model scheduling, but the owner’s script-navigation rule already excludes it as the production architecture.

   **P0 — Distinguish parallel subtasks from parallel ShipLoop steps.** Today, a ShipLoop step completes its implementation, tests, documentation, review and commit before the next step starts. The opt-in `ask-agent` route remains serial and has one candidate writer. An experiment with six concurrently executable synthetic units does not establish permission or feasibility for six concurrent ShipLoop steps. Initially interpret those units as bounded investigations or contributions **inside one authorized stage**, while keeping stage completion and callbacks under one owner. Cross-step execution requires a separate owner decision about that existing boundary. [navigator.md — delegation and ownership](/Users/dadleet/src/skill-craft/skills/shiploop/references/navigator.md:339), [inner-loop.md — per-step lifecycle](/Users/dadleet/src/skill-craft/skills/shiploop/references/inner-loop.md:25)

   **P1 — “Harness-independent” means a portable contract with qualified host bindings.** It should preserve fresh-context semantics, task ownership, evidence, acceptance and recovery across hosts. It need not use identical tool names, identical waiting APIs or identical concurrency limits.

   **P1 — Add three small, explicit intention tests.**

   | Owner concern | Minimal discriminating experiment |
   |---|---|
   | Parallelism during planning | Independent agents inspect separate supplied evidence, then one owner constructs or audits the dependency plan. Score omitted and invented edges against a hidden fixture oracle. |
   | Outcome-only retention | A worker processes substantial irrelevant material and returns a small result with evidence locators. A fresh parent continuation solves the next task from that retained result. |
   | Interaction with main-context state | A worker starts against state revision R1; the parent receives R2 before its return. Require an explicit stale-result disposition or clarification, rather than unconditional acceptance. |

   A smaller parent prompt is not sufficient if the summary loses a constraint needed by the next task. The repository already requires cold-start recovery from compact evidence and current packets. [execution-planning.md — cold-start evidence](/Users/dadleet/src/skill-craft/skills/shiploop/references/execution-planning.md:220)

2. **Premises: one material historical claim is false, and several capability claims need narrowing.**

   **P0 — The per-step pilot was run.** The registration says it was “proposed and never run,” citing `f824adeb`. That commit accurately described its status at that moment; later history superseded it.

   Commit **`eadad0c84f8a213287459bbf6252411ac0b90fce`**, later on October 29, records three `stand-in-parser` runs:

   | Measure | Inline | Per-step agents | Old item-level agents |
   |---|---:|---:|---:|
   | First acceptance to last acceptance | 5.3 min | 21.6 min | 17.3 min |
   | Fresh workers | 0 | 13 | 8 |
   | Input tokens | 8.06 M | 23.11 M | 19.94 M |
   | Output tokens | 23.5 k | 105.2 k | 85.1 k |
   | Slice verdicts | All five passed | All five passed | All five passed |

   These are single-case observations, not general effect estimates. They **do not supply the missing parallel-versus-serial counterfactual**, but they directly inform fresh-context overhead and A1. The killed-worker question remained unmeasured; the entire pilot did not. [LEARNINGS.md — actual pilot and limitations](/Users/dadleet/src/skill-craft/test/shiploop_e2e/LEARNINGS.md:4299), [design — “The pilot, run”](/Users/dadleet/src/skill-craft/docs/shiploop-review-after-tests-design-2026-10-27.md:1432)

   **P1 — The retirement account is otherwise supported.** I checked all six requested commit messages:

   - `8eca9d64`: four concrete conflicts between the chain and per-step iteration; no measured serial counterfactual.
   - `fb4b2843`: the owner adopts a2, accepting the changed lost-worker recovery boundary.
   - `ad30aa1c`: retires ShipLoop’s chain, while retaining standalone Plan Dispatcher and Ask-Agent.
   - `f824adeb`: proposes the pilot; subsequently superseded as described above.
   - `f810a78f`: Codex fan-out, 587 seconds, 29.3 seconds of overlap.
   - `e0fb4366`: Claude fan-out, 29.9 seconds of overlap, plus separate recovery evidence.

   The approximately 240-second join delay is supported by the journal, rather than the brief `f810a78f` message itself. However, the old `fanout.grade()` classifies a worker as native from the presence of a recorded handle. Treat that as historical orchestration evidence, not a sufficiently strong attribution oracle for this study. [LEARNINGS.md — fan-out](/Users/dadleet/src/skill-craft/test/shiploop_e2e/LEARNINGS.md:363), [fanout.py — grade](/Users/dadleet/src/skill-craft/test/shiploop_e2e/fanout.py:78)

   **P1 — Dependency validation is correctly described, but completeness is not established.** `_normalise_steps()` rejects duplicate, unknown, self and forward dependencies. It deliberately preserves omitted `deps`; omission does not mean independence. Narrow “dependencies at one level only” to **explicit step-to-step dependencies in the navigator’s accepted step-plan schema**: planning notes, expectations and Backchain contain other prerequisite information. Neither valid `deps` nor disjoint `paths` proves semantic independence. [shiploop_navigator.py — `_normalise_steps`](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:2708), [backchain-planning.md — owner binding](/Users/dadleet/src/skill-craft/skills/shiploop/references/backchain-planning.md:64)

   **P1 — “CodexTranslator … drops agent items” is inaccurate.** It drops some event forms, including unrecognized starts, and transforms others. Its generic `item.completed` branch preserves nonempty item types as synthesized tool calls and updates, including serialized item fields. Keep raw events, but justify that as preserving exact structure, timing and attribution—not as recovering universally discarded agent items. [hosts.py — `CodexTranslator.__call__`](/Users/dadleet/src/skill-craft/test/shiploop_e2e/hosts.py:538)

   **P1 — The declared defaults match `hosts.py`; complete isolation and uniform child models do not follow.** Codex’s argv sets default child model and effort, not an immutable prohibition on overrides. Claude’s Anthropic environment inherits `os.environ`; `--setting-sources project,local` does not itself establish absence of all ambient instructions, agents or environment overrides. Record effective capabilities and actual child model identities. The approximately 86,000-token Claude startup figure is a dated local observation, not a universal constant for these clean profiles. [hosts.py — Claude and Codex launch construction](/Users/dadleet/src/skill-craft/test/shiploop_e2e/hosts.py:384), [current-workspace.md — startup observation](/Users/dadleet/src/skill-craft/skills/ask-agent/references/current-workspace.md:113)

   **P1 — The amendment added during this review correctly identifies a profile distinction, but needs sharper interpretation.** `26d7e024` records `multi_agent_v2` off in the throwaway profile and on in the owner’s profile. Name the profile in every result. Demonstrating capability in one supported profile establishes that configuration’s capability; “Codex can do it” does not logically require success in both. Also freeze which profile scores each original prediction: “the profile as run” leaves selection ambiguous. [Registration — Amendment A1](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/README.md:220)

3. **Design: retain the controls, but repair what counts as success before spending on the matrix.**

   **P1 — A1 is essential, and should match the selected parallel arm more closely.**

   | Comparison | What it can estimate | Remaining confound |
   |---|---|---|
   | A0 versus A1 | Cost of delegation and fresh contexts | Additional dispatch, collection and reporting work |
   | A1 versus A2 | Effect of concurrent native workers | Different scheduling behavior and possibly different parent tool batching |
   | A2 versus A3 | Effect of script-provided readiness | A3 also hides the plan, adds claims and changes tool-call volume |
   | A0 versus A3 | Total effect of the proposed mechanism | Cannot explain which component produced the effect |

   For the smallest useful comparison, make the serial-agent control use the **same readiness, worker and return contract as A3, with capacity one**. Preserve the original A1 as a separately named condition if its wording is already frozen. A0 and A1 should also use a specified deterministic serial order. [Registration — arms](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/README.md:112)

   **P2 — The critical-path arithmetic is correct under its assumptions.**

   | Fixture | Serial work | Unlimited-capacity critical path |
   |---|---:|---:|
   | `one1` | 5 s | 5 s |
   | `fan4` | 120 s | 30 s |
   | `ragged6` | 120 s | 70 s |
   | `chain4` | 80 s | 80 s |

   For `ragged6`, ideal execution is S2 0–10, S3 10–20, S1 0–40, S5 0–30, S4 40–60, S6 60–70. A full-wave barrier delays S3 to 40–50, yielding 80 seconds.

   **P1 — Those bounds assume enough worker slots and negligible orchestration delay.** `fan4` needs four simultaneous workers for 30 seconds. Record available capacity and report a capacity-constrained bound. The ten-second makespan difference in `ragged6` is small relative to model/host latency. A completion-driven scheduler can miss M11’s threshold without employing a wave policy. Keep `chain4` as a negative control, and enlarge the refill observation window if E1 reveals substantial latency.

   **P0/P1 — Measures need the following corrections.** The source-level defects below were also checked against the apparatus that arrived during this review.

   | Measures | Rank | Required correction |
   |---|---|---|
   | **M1–M2: makespan and savings** | **P0** | Report launch-to-verified-result and launch-to-process-exit alongside the work interval. Excluding initial spawning and final collection hides much of the mechanism’s cost. Do not award savings to incomplete, invalid or misattributed runs. Mark theoretical parallel savings in `chain4` inapplicable; a faster chain can reflect overhead differences, not overlap. |
   | **M3: overlap** | **P1** | Use transitive incomparability, half-open intervals and explicit treatment of unfinished work. Overlapping commands establish concurrency, not native-agent execution. The current ancestor calculation and end-before-start tie ordering are sensible. |
   | **M4–M5: ordering and integrity** | **P0** | Separate premature, duplicate, unknown-step and failed-prerequisite refusals. Guard-enforced order is an apparatus property. Check exactly one start and terminal event, successful prerequisite outcomes and valid output consumption—not merely final derived states. |
   | **M6: exit** | **P0** | Measure from the last **work terminal event**, last child return, final report and actual process exit separately. `score_trial()` currently measures from the last host **or** ledger event, contradicting M6 and allowing late chatter to hide a long tail. |
   | **M7: fidelity** | **P0** | Accept only the parent’s terminal report; require every planned step to be accounted for. Current `final_claim()` accepts a child’s `FINAL`, and `fidelity()` accepts a report omitting a running step. |
   | **M8: tokens/context** | **P0** | Establish whether each host’s usage includes children, whether counters are cumulative, and whether cached tokens are included in input totals. Count each thread once. Current Codex parsing looks for `cache_read_input_tokens`, losing raw `cached_input_tokens`. Peak parent input is not sufficient evidence of outcome-only retention. |
   | **M9 and M11: dispatch/refill** | **P1** | Split dependency-end → notification → parent collection → dispatch → command-start. M11 establishes an observed overlap opportunity, not the cause of a missed opportunity. Include initial-root dispatch latency. |
   | **M10: mechanism** | **P0** | Require step-to-child-to-command attribution. Unrelated spawns plus overlapping parent commands must remain parent execution or unknown. Current `mechanism()` labels precisely that combination `native-agents`, even while reporting `attributed: false`. |

   These defects are in [score.py — ledger measures](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/score.py:51), [fidelity](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/score.py:105), [final-claim and token parsing](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/score.py:220), [mechanism classification](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/score.py:255), and [process-tail calculation](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/score.py:343).

   **P0 — The mechanism detector currently produces both false positives and false negatives.** In read-only, in-memory checks:

   - An unrelated spawn plus two parent `run` calls and peak concurrency two returned `native-agents`.
   - A child’s `FINAL` was accepted.
   - A report omitting a still-running step returned `fidelity_ok: true`.
   - `/tmp/parallel-probe/dagkit.py …` matched the shell-parallel regex because of the pathname.
   - Codex’s reported cached-input count became unknown.

   Command text is also truncated before classification, potentially removing the decisive argument or background operator. Tool names containing “agent” do not all mean spawn: collection and cancellation tools can contain that word too. E1 should provide exact event fixtures before this classifier grades subjects.

   **P1 — Several predictions are not mechanically determinate as written.**

   - **C1–C5:** freeze population, deduplication, treatment of amended plans and partial timing coverage, definitions of “level” and path overlap, and empty-denominator behavior. Missing dependencies remain unknown. Same-level pairs are only a subset of incomparable pairs.
   - **P3/P4:** no qualifying parallel runs or skipped A3 cells must not produce vacuous success.
   - **P8:** specify fixture, eligible arms, profile and treatment of failures before selecting the “best” arm. A best-of-several observation is exploratory, not an unbiased estimate.
   - **P9:** resolve whether “a parallel arm” means any arm, every arm or a designated arm; partial child accounting is not total usage.
   - **P10:** repair M6 first.
   - **P11/R1:** specify the exact arm and N/H variant used for each conjunct.
   - **P12:** requires a calibrated mechanism detector, not substring matching.

   Preserve original predictions and add dated scoring clarifications. Do not silently reinterpret their outcomes. [Registration — predictions](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/README.md:165)

   **P0 — R2 should not call the mechanism “safe.”** A guard prevents the very dependency violations being counted. Report “completed this guarded fixture correctly with verified native attribution,” separating model refusals, guard correctness and task completion. Failure fixtures also need an expected-outcome oracle: the newly implemented `PARTIAL` result is appropriate for injected failure, but is not ordinary all-success completion.

   **P1 — R0, R3 and R4 overreach their evidence.** A census average should not suppress a valuable opt-in tail, nor estimate planning-stage opportunity. Positive M2 plus a stated token penalty does not establish payoff under quality-then-tokens-then-time. Script ownership is already a constraint; A3 need not beat A2’s refusal count to retain it. [Registration — decision rules](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/README.md:188)

4. **Apparatus: there are concrete pre-trial blockers, beyond the design risks.**

   The kit and runner appeared during this review in `2883cdba`, followed by profile amendment `26d7e024`. These findings concern the files as inspected; I made no edits and launched no study trial.

   **P0 — Normal Codex and Grok launches construct argv before creating the trial directory.** `launch.main()` calls `host.argv()` at line 121; those two adapters immediately write `prompt_file`. `trial.mkdir()` does not occur until line 131. A new normal trial therefore attempts to write into a nonexistent parent directory. The dry-run uses a different prompt location, so its success does not qualify this path. Create the owned directories before calling an adapter with filesystem side effects, and exercise the normal setup path using a non-model fake executable. [launch.py — setup order](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/launch.py:110), [hosts.py — Grok argv](/Users/dadleet/src/skill-craft/test/shiploop_e2e/hosts.py:323), [Codex argv](/Users/dadleet/src/skill-craft/test/shiploop_e2e/hosts.py:445)

   **P0 — The comparison code violates the new profile-separation rule.** `compare()` keys A0 baselines only by `(host, plan)`. A second Codex profile overwrites the first baseline, and both can then be compared against it. Include frozen host version, model, effort, feature profile, fixture, packet condition and matched replicate in comparison identity; reject unmatched baselines. [score.py — compare](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/score.py:377)

   **P0 — Claims can strand A3 indefinitely.** `ready --claim` claims every ready step. There is no owner/attempt identity, launch acknowledgement or release/reconciliation path. If the fourth launch exceeds host capacity, or a launch fails, that step remains claimed. A3 subsequently interprets empty-ready plus incomplete as “a step is still running,” although no worker may exist. Cold recovery has the same problem. Claim only available capacity and retain `claimed → launch-confirmed → running → returned → accepted` distinctions, with explicit handling of unlaunched claims. [dagkit.py — claim and classification](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/dagkit.py:115), [A3 packet — waiting assumption](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/packets/A3.md:5)

   **P1 — The lock placement is good; the ledger’s verification contract is incomplete.** `cmd_run()` atomically checks prerequisites and appends `start`, then releases the lock during the sleep. That avoids both duplicate-start races and accidental serialization. But:

   - `derive()` overwrites terminal state; `verdict()` does not require exactly one start and terminal event.
   - Verification checks prerequisite end order, but does not independently require successful prerequisite terminal states.
   - The stored plan hash is not rechecked against the current plan.
   - Execution uses dependency hashes from the ledger, rather than reading and validating predecessor output files.
   - `PPE_TIME_SCALE` is recorded but not rejected for live scoring.
   - Verification reads its snapshot outside the ledger lock.

   Freeze input identities, validate an event-state machine and use one consistent snapshot. Keep the lock out of the work interval. A hash chain demonstrates internal consistency only to the extent that its inputs and writer are trustworthy. [dagkit.py — execution and verdict](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/dagkit.py:174)

   **P1 — Separate work completion, native return, parent acceptance and process exit.** The existing Dispatcher explicitly distinguishes these and requires workers to stop before resources are released. Its protocol also handles unconfirmed launch identities and unknown recovery outcomes. Reuse those lessons without importing the whole retired chain. [plan-dispatcher/SKILL.md — collection and acceptance](/Users/dadleet/src/skill-craft/skills/plan-dispatcher/SKILL.md:318), [recovery](/Users/dadleet/src/skill-craft/skills/plan-dispatcher/SKILL.md:412)

   **P1 — Host-specific qualifications must be established in E1.**

   | Host | Established information | What this study must qualify |
   |---|---|---|
   | **Claude Code** | Local recipes use fresh general-purpose `Agent`/`Task`, commonly background mode. `TaskOutput` was absent in a tested schema. Current official documentation distinguishes foreground, background and headless nested waiting; documents three default nesting layers and a default concurrent-agent limit of 20. | Actual tools in 2.1.325, non-fork context, terminal delivery and process exit. Older 2.1.296 evidence includes early coordinator returns and a successful result followed by a process that failed to exit. Neither old failures nor current documentation qualifies this launch. |
   | **Codex** | Local recipes use asynchronous native spawn with `fork_turns="none"` and native collection. The registered profiles now differ between v1 and v2. | Exact exposed spawn/wait schema, effective slots/depth, which events represent terminal completion, child command attribution and child usage. A mailbox wakeup or observation timeout is not necessarily a result. |
   | **Grok Build** | Local recipes use `spawn_subagent(background=true)`, collect through `get_command_or_subagent_output`, and stop through `kill_command_or_subagent` where exposed. Public documentation confirms separate child contexts returning summaries. | The 1.0.77 schema, positive-wait behavior, child shell access and process exit. Depth one is an older local-guide observation, not a universal public guarantee. `explore` and `plan` workers lack shell access and cannot execute this fixture. |

   Sources: [local host recipes](/Users/dadleet/src/skill-craft/skills/ask-agent/references/host-capabilities.md:61), [retained headless qualifications](/Users/dadleet/src/skill-craft/skills/in-parallel/references/hosts.md:10), [Claude subagent documentation](https://code.claude.com/docs/en/sub-agents), [Codex subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents), [Grok subagent documentation](https://docs.x.ai/build/features/subagents).

   **P1 — Record three distinct timeout classes:** shell-command timeout/yield, native-agent observation timeout and outer trial deadline. A yielded command may still be running; a timed-out collection call may leave the worker active. Require the worker to collect the command’s terminal exit before reporting success. Do not turn observation timeouts into retries or substitute shell polling for native collection.

   **P0 — Process-group termination is insufficient cleanup evidence.** The repository already records that Claude Bash children can have separate process groups and outlive the host. Sleeping kit processes are not TCP listeners, so the existing listener cleanup would not automatically find them either. Record owned descendant/kit identities, terminal status and ledger quiescence; retain uncertainty instead of starting a conflicting retry. [listeners.py — known process-group limitation](/Users/dadleet/src/skill-craft/test/shiploop_e2e/listeners.py:1)

   **P1 — Harden the observer, not its influence on the subject.** Save invocation identities before launch; preserve evidence on exceptions and external interruption; distinguish actual process exit from the subsequent reader join; record reader failures and incomplete streams. Use monotonic time for durations and UTC for display. Keep complete attributable tool events behind the compact timeline. The runner should launch one host and observe it, never dispatch steps itself. [launch.py — `run_host` and invocation recording](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/launch.py:59)

5. **Least-spend recommendation: pilot after repairing the P0 evidence gates; defer the full matrix.**

   **P0 — First, finish no-model apparatus qualification.** Add negative controls for unrelated spawns, parent execution, child-only final reports, omitted running work, duplicate terminal events, altered plans, scaled sleeps, command-text truncation and mixed-profile comparisons. Exercise the real launcher setup using fake host executables. Existing constructed-ledger calibration does not cover these failure modes. [calibrate.py — current cases](/Users/dadleet/src/skill-craft/docs/experiments/parallel-plan-execution-20261114/calibrate.py:71)

   **P1 — First paid call: Claude E1, aimed specifically at return and exit.** This directly revisits the strongest known host-lifecycle uncertainty. Then qualify the intended Codex profile and Grok. Record actual schemas, fresh-context selection, command execution, terminal return and process exit. Give an N failure the registered H diagnostic only when the failure could plausibly be elicitation. Unsupported tools, permissions or attribution need diagnosis, not another prompt.

   **P1 — On one qualifying host, run matched `fan4` A0, A1 and A3.** This answers whether concurrency exists and distinguishes its benefit from delegation overhead. Run A2 later if model navigation remains an interesting research question. Do not multiply every arm across both Codex profiles merely because the feature distinction exists.

   **P1 — Next run `ragged6` A3, then a failure and context fixture.** Establish completion-driven refill, independent-branch progress after failure, truthful reporting and a cold parent continuation from retained outcomes. Expand the matched timing comparison only if the mechanism remains promising. Bring the small planning/context experiment forward before shared-checkout commits.

   **P1 — Run timing comparisons without overlapping other study trials.** Sleeping reduces CPU work; it does not eliminate scheduling delay, service congestion, cache effects or rate-limit interference. Counterbalance arm order and repeat only comparisons whose result could change the next decision.

   **P0 — Stop the affected condition when attribution cannot be established, the scorer credits a known-invalid trace, the host cannot reliably return/exit, or owned work remains unresolved.** Record it as unqualified or censored, not a successful mechanism or a global host failure. Do not stop the entire investigation merely because 30-second tasks lose on cost: that establishes a granularity problem, not the absence of value for longer work.

   **P1 — Stop pursuing cross-step integration if the only demonstrated benefit requires violating the per-step lifecycle.** Redirect to planning and bounded work inside a stage unless the owner explicitly changes that product constraint.

6. **Harness independence: use a portable core plus explicit, small host bindings — P1.**

   A text packet can specify duties, scope, outcomes and evidence. It cannot create unavailable tools, force asynchronous execution, select an unsupported fresh-context mode, change depth limits, guarantee callbacks after process exit, make hook events attributable, or clear a conversation by printing a command. The repository already has measured failures of text-driven context clearing. [navigator.md — context boundaries](/Users/dadleet/src/skill-craft/skills/shiploop/references/navigator.md:422)

   **P1 — A3 buys authoritative dependency calculation, not a complete execution protocol.** It reduces the model’s need to reconstruct graph readiness and can rehydrate decisions from durable state. It does not prove the dependencies are correct, reserve native capacity, establish successful launches, validate task quality, integrate writes or recover lost workers. Its current claimed-step deadlock is an example of that distinction.

   **P1 — Yes, the operational packet should name each host’s actual tools when known.** Keep N as a separate experiment about spontaneous elicitation. For the usable portable route, provide a small binding identifying:

   - Fresh, non-fork launch operation and required parameters.
   - Collection/notification mechanism and terminal-success evidence.
   - Workspace binding and command-wait behavior.
   - Capacity/depth limits and unsupported conditions.

   This is host adaptation, not a second scheduler. The script remains the sole source of eligible task IDs; the model translates those authorized actions into visible native tool calls. A failure of anonymous wording is not evidence that the harness lacks the capability.

7. **The single biggest risk: proving a fast scheduler for the wrong unit of work — P0.**

   The study can succeed completely—real overlap, correct dependency order, accurate reports—and still leave no viable opt-in ShipLoop route.

   Real ShipLoop progress means **accepted, tested, reviewed and committed changes against a specific base**, with one current stage owner, meaningful dependency evidence and safe recovery. A sleep ending is a much weaker event. Disjoint output paths do not establish independence of interfaces, test baselines, shared configuration, documentation, Git index operations or later review findings. Those are precisely the boundaries implicated in `8eca9d64` and the retirement.

   The next bridge should therefore demonstrate a material benefit from parallel work **within one legal ShipLoop stage**, followed by one owner’s acceptance and one valid continuation, including a context reset or stale-state case. If the desired gain instead requires multiple implementation steps to be active simultaneously, make that lifecycle trade-off explicit before building integration. Synthetic DAG success alone cannot settle it.
