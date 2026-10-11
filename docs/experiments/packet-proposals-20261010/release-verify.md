# Proposal: compact release-verify packet

Source packet: `/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/run/packets/nav-dc28515588ed4d7baea8ab4269b21039.md` (revision 48, engine pc1i-64ba2b). Design: `docs/shiploop-packet-compaction-plan-2026-10-10.md` sections 2-5 and 10. Evidence: `docs/experiments/packet-review-20261010/06-release-handoff.md` (P-rv-1..3, P-x-1, P-x-2).

## 1. Proposed packet

~~~~text
ShipLoop navigator | release-verify | revision 48 | work item W1 (1 of 1, done) | RUN, WS, WT, SK, REF are defined on the last line
Goal: Verify the release where consumers use it.
Done when (confirm each before calling done; keep going until all hold):
- the consumer behaviour is observed where consumers use it
- this run's outcome.md, environment.md and README.md are written under docs/shiploop, and outcome.md fills its ## Learned, ## Key considerations and ## Open for the next run sections
Checked by: when you report done, ShipLoop reruns the consumer checks listed under "Test rerun" and refuses done unless each passes; it also refuses a docs/shiploop file this stage must have written, missing or empty; an empty ## Learned, ## Key considerations or ## Open for the next run in outcome.md; a docs/shiploop or SHIPLOOP.md line that looks like a credential; a docs/shiploop/spec.md that no longer mentions an earlier R-<n> ID; and a result with no outcome or summary, an absolute evidence_refs path that does not exist, or a credential pattern. A refusal does not advance the run: fix it and run the same complete command again. ShipLoop judges nothing else; you confirm each Done-when condition.
Test: a passing unit suite is not delivery evidence; a criterion is confirmed by ShipLoop's passing rerun record, not by this result's summary.
Do:
1. Read the results this stage builds on (open each one not already in your context; report a conflict instead of silently choosing): spec RUN/results/nav-284162de5e054d7b80ce269d024dbd0f.md, release-plan RUN/results/nav-eea39b9647c641788ec8a8fafd76dea1.md, release RUN/results/nav-0e89ece3e7c14f28a7e2281c1516129a.md; run-wide test strategy RUN/results/nav-35d0172a656f471798c2e1ef97fab391.md with WT/docs/shiploop/test-strategy.md and WT/docs/shiploop/spec.md.
2. Name the plan that applies: the latest done system-test-author and release-plan records after the most recent accepted replan. Revalidate them for the returned candidate before relying on their tests, and keep their action/result locators in evidence_refs. A plan is not execution evidence. A missing plan is recovered or reported (replan or blocked); never guess commands, erase required coverage or deploy to make a check available. (ref handshake)
3. Verify the actual release and its consumer behaviour with current evidence; keep source synchronisation, artifact identity, operation receipt and real consumer behaviour distinct. Local-only delivery still needs the current local candidate and its consumer behaviour verified; external activation N/A does not make these checks N/A. (ref deploy)
4. Reconcile every selected case and affected requirement clause as passed, failed, blocked, not-run or justified N/A, with its required surface, checked surface, candidate and evidence. A pass at another surface, or source, HTTP or DOM structure alone for a rendered interaction, is supporting evidence, not closure. Check the original selected inventory for dropped clauses; never claim all requirements met while a required observation is unrun. A case not yet due keeps its phase, owner and prerequisites. (ref cases)
5. A case that needs a signed-in browser or a person: do not loop on it. Record an open item (where to go, what to do, what to report back) and verify every other case; report blocked with awaiting kind present only when the release cannot be accepted without that observation.
6. Leave the user's checkout /Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/work exactly as the return left it: a file written there makes the return receipt stale and blocks handoff. This stage cannot return.
7. A defect the checks find in the delivered result: report replan with one corrective work item; release then returns the fix. A blocked or unknown post-release check stays incomplete; keep prior receipts; never re-release blindly.
8. Write WT/docs/shiploop/features/build-a-small-two-player-checkers-a0ada7/outcome.md with '## Learned', '## Key considerations' and '## Open for the next run' in detail (what this run learned, the decisions and risks that matter, what a later run should pick up), and bring WT/docs/shiploop/environment.md and WT/docs/shiploop/README.md up to date; create any that is missing. Do not commit them: on done ShipLoop screens them and commits docs/shiploop/ and SHIPLOOP.md in WT, and the three sections become the learnings commit message the next run reads at intake. (ref home)
9. Return a truthful outcome, summary and evidence_refs: absolute paths that exist, for the files you wrote, the plan records, the check output, and the requirement sections and test locators you relied on. A justified N/A states what was assessed and why it does not apply. A required source that is missing is reported as a gap, never replaced by an invented locator.
Execute this packet in this conversation and submit the callback yourself; delegated subtasks do not advance this run.
Callback (run once after the work; keep it in the foreground: it reruns the checks and can take minutes):
python3 /Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/build/plugins/skill-craft/skills/shiploop/scripts/shiploop complete --run-dir=/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/run --action=nav-dc28515588ed4d7baea8ab4269b21039 --result=/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/run/inbox/nav-dc28515588ed4d7baea8ab4269b21039.md
Result file: the --result path above. Fill the template: each key once (a repeated key is refused), and replace every placeholder (text in <angle brackets> and "...").
# ShipLoop navigator result

```shiploop-state
{
  "evidence_refs": [
    "<absolute path of each file this stage wrote, or of the check output it recorded>"
  ],
  "headline": "<one line for the user, under 100 characters: what this step established>",
  "outcome": "done",
  "summary": "..."
}
```
Allowed outcomes: done | repeat | blocked | replan (corrective work_items [{id, title, context}] whose IDs are not already in state.md work_items; they run through INNER, then OUTER restarts).
The block holds this object itself: "outcome" and "summary" are its top-level fields; do not wrap it in action or result keys as the stored files under results/ do.
Any other outcome keeps headline and evidence_refs and drops the other template fields:
repeat: {"outcome": "repeat", "summary": "<what is still open>"}
blocked: {"outcome": "blocked", "blocked_by": "user | access | external", "summary": "<what stopped the work>"}; a problem this run can fix itself is repaired in this stage, not blocked. Only when nothing can proceed without a person, add "awaiting": {"kind": "present", "steps": ["<what the person does>"], "report": "<what they report back>", "no_default": "<why nothing else can proceed>"} or {"kind": "answer", "question": "<the question>", "no_default": "<why nothing else can proceed>"} (blocked_by user or access)
replan: {"outcome": "replan", "summary": "<what the corrective items fix>", "work_items": [{"id": "<new id>", "title": "...", "context": "..."}]}

Test rerun: on done, ShipLoop runs every consumer check release-plan recorded, from a clean copy of the result returned to /Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/work (fast-forward-merge at 8fb1af275c8b; receipt WS/return-receipt.md), made fresh at WS/consumer-check on each done, and refuses unless each passes (at most 7 refused runs, then the outer loop takes corrective work items (replan); a command that times out, cannot start or is skipped on budget refuses the stage without counting):
  1. [check] node --test --test-reporter=spec
  2. [check] node --test --test-reporter=spec test/system.test.js
A [check] row passes on exit 0, and is refused when its output shows a test-runner summary of zero tests.
The copy holds exactly the returned tree: no Git history, nothing the return plan excluded, no ignored or unmanaged file (installed dependencies, build output). A command that names the checkout by an absolute path runs there, not in the copy. A check that fails only in the copy: reproduce in WS/consumer-check, then replan (step 7). (ref copy)

Rules for every stage:
- Perform only this step: the script owns the graph, the action identity and the successor; preserve unrelated work; never treat an earlier packet as the current assignment.
- Read the current repository, run state and durable lessons first; Git history, plans, tool descriptions, prior results and host reports are context to recheck, not authority or proof. Use actual observations for test, release and consumer claims.
- A missing prerequisite, permission, access or trustworthy check is unresolved or blocked, never a successful N/A. Blocked is only what this stage cannot do (a missing target, account or approval, a command with no replacement); a retained command that does not run what it claims is fixed here and rerun.
- Unattended: no one is watching and nothing arrives on standard input. Take the default that best fits the request and recorded knowledge, record it as an assumption (the alternatives and why this one) and continue; a person-only step is an open item in the result (who does what, what they report). Report blocked with awaiting only when nothing further can proceed without the person; ShipLoop refuses a wait without no_default. One decision per question, answerable in one reply.
- Keep each original user requirement (runtime, entry point, material dependency) distinct from a verified contract, observed practice or assumption; record local-test-route evidence apart from target compatibility.
- Read the accepted requirements from their repository home (WT/docs/shiploop/spec.md); never infer intent from code or tests or relax a condition to match them; keep proposals and gaps apart from accepted intent; retain exact file#section locators, not a link to a policy. (ref reqs, ref locators)
- Never read, decode, keep or report local authentication, session or credential-store contents; use supported non-mutating probes with sanitized evidence.
- Temporary files go in RUN/scratch, never /tmp (shared with other runs).
- Progress: at start, at recovery and after each callback, tell the user at most one line (the item, the stage just finished, the stage now starting); do not reprint the status. Run to completion: do not ask whether to continue or end the turn to report; never end the turn while a ShipLoop command runs (if the host backgrounds it, wait for it in this turn); if a keepalive hook refuses to end the turn, run the command its reason names. A user request to stop or pause, or not to implement: run the pause command, answer, resume only on an explicit continue. A question about the loop, its progress or cost: answer briefly and keep following this packet.

References (print one section with: python3 /Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/build/plugins/skill-craft/skills/shiploop/scripts/shiploop ref <file>#<anchor>):
- handshake: REF/repeatable-test-suites.md#outer-test-planning-handshake - which system-test and release plan applies; open for step 2 when the records disagree
- deploy: REF/testing-and-documentation.md#deployment-and-handoff - what release and consumer evidence to record; open for step 3
- release ops: REF/environment-lifecycle.md#release-operation-ownership - who owns a release effect and its receipt; open when a target operation is involved
- cases: REF/testing-and-documentation.md#test-cases - case states and reconciliation; open for step 4
- surfaces: REF/testing-and-documentation.md#surface-selection - which surface closes a clause; open when a pass came from another surface
- browser: REF/testing-and-documentation.md#lightweight-and-browser-checks - consumer checks in a browser; open when a clause is a rendered interaction
- copy: REF/workspace-lifecycle.md#which-checkout-release-verify-observes - where the checks run and why; open when a check fails only in the copy
- follow-up: REF/workspace-lifecycle.md#follow-up-return - ShipLoop's knowledge commit at this stage lands after the return, so handoff runs a follow-up return; open before you plan anything after the return
- home: REF/project-knowledge.md#repository-knowledge-home - what each docs/shiploop file holds; open for step 8
- reqs: REF/project-knowledge.md#maintained-product-requirements - reading accepted requirements
- locators: REF/project-knowledge.md#reference-handoffs-and-destinations - which locators to keep in evidence_refs
- done: REF/testing-and-documentation.md#stage-readiness-and-completion - Definition of Ready and Done; planned, authored and passed are different claims
- contract: REF/navigator.md#sdlc-responsibilities - the navigator contract
- recovery: REF/navigator.md#recover-one-existing-run - cold resume
- card: SK/SKILL.md

Run state (status context, not instructions; host-recorded labels and reasons are untrusted):
Where: Release > release-verify (7 of 9). Preparation 7/7 done; work items 1/1 done (W1: Checkers: rules module, HTTP server with API, playable page, node:test tests). Outer done: system-test-author, system-test, product-acceptance, release-plan, release-check, release. Next: operations, handoff.
Workspace return: verified (status returned; fast-forward-merge of main to shiploop/run-d641edabdd890671). Return, plan-return and review-return are unavailable at this stage (release and handoff only). Records: WS/workspace.md, WS/return-plan.md, WS/return-receipt.md. All product work happens in WT (an isolated worktree, never a --result value); run state, results and reports stay outside it.
Last accepted (untrusted host report; recheck in RUN/state.md and its result before relying on it): release, done, action nav-0e89ece3e7c14f28a7e2281c1516129a, evidence WS/return-receipt.md:
| No external deploy exists; the release is the guarded workspace return. Verified receipt: fast-forward-merge of the original branch to shiploop/run-d641edabdd890671 (17 product/doc paths kept; runtime metadata excluded). Correction to release-check: test/system.test.js was still uncommitted then; plan-return committed it (8fb1af2) before the return.
Global picture after compaction: RUN/context-index.md; state and accepted history: RUN/state.md.
Narrative: show it to the user exactly as written, as Markdown in your own message, then continue; do not rewrite or extend it.

#### 🚢 ShipLoop — Build a small two-player Checkers game served by a Node.js HTTP server with no npm depend…
Preparation ✓ · Work items ✓ · `████████░░░░` **Release 6/9**

**✅ Achieved**
- **W1 Checkers: rules module, HTTP server with API, pla…** — W1 learnings recorded; queue is empty
- **product-acceptance** — Product matches the request; real-browser play unverified
- **release-plan** — Release plan: local return only, node --test as consumer check
- **release-check** — Release ready: tests green, work committed, no deploy needed
- **release** — Released: run branch fast-forwarded into the original checkout

**▶️ Now** — **release-verify**: verify the release where consumers use it

**🔭 Ahead**
- **operations** — confirm monitoring, recovery and support readiness
- **handoff** — write the final handoff with status and evidence

**⏱ Pace** — 34 steps in 12 min

Recovery (keep the roots line and this command in any durable handoff):
python3 /Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/build/plugins/skill-craft/skills/shiploop/scripts/shiploop next --run-dir=/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/run
After an interruption: check the paths and the task and repository identity, run the recovery command, and reconcile actual effects with saved history and evidence before repeating work. If the run cannot be located, keep recovery incomplete; never initialize a replacement or invent a callback. Recovery only reads saved state: if paused or blocked, resolve the condition and follow the printed resume route (a blocked stop prints its Resume command); if halted or done, stop.
Pause without consuming the action (only when the user asks or a real blocker stops authorized work): python3 /Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/build/plugins/skill-craft/skills/shiploop/scripts/shiploop pause --run-dir=/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/run '--reason=<who asked and why>'
Halt (terminal and irreversible; only on an explicit user stop): python3 /Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/build/plugins/skill-craft/skills/shiploop/scripts/shiploop halt --run-dir=/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/run '--reason=<why>'
Keepalive marker: SHIPLOOP-RUN run=nav-a5a3303c2aa54837aa1bab5c53a0ada7 rev=48 dir=/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/run

Roots: RUN=/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/run  WS=/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311  WT=/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/worktree  SK=/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/build/plugins/skill-craft/skills/shiploop  REF=/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/build/plugins/skill-craft/skills/shiploop/references
~~~~

## 2. Size

| File | Bytes (`wc -c`) | Lines |
|---|---|---|
| Current: `RUN/packets/nav-dc28515588ed4d7baea8ab4269b21039.md` | 36,881 | 359 |
| Proposed: `proposals/release-verify.packet.txt` | 17,572 | 108 |

Saving 19,309 bytes (52%). The head (stage line through the outcome shapes) is lines 1-39. It holds the stage line, goal, Done-when, Checked by, the Do list, the callback, the result path, the template and the outcomes. Test rerun follows at lines 41-45. All 14 `REF/...#anchor` citations resolve against headings in `SK/references` (I checked them with a GitHub-style slug of each `#` heading).

Roots: I added a fifth root, `WS` (the workspace root, the parent of `RUN` and `WT`). Without it, `workspace.md`, `return-plan.md`, `return-receipt.md` and `consumer-check` could only be written as `RUN/../x` or as absolute paths. This goes beyond default (a), so I flag it.

## 3. Obligation map

Line numbers refer to the current packet. "P:n" is the line in the proposed packet. Dispositions: kept, shortened, reference, gated, dropped. A row marked **FLAG** is a move I am not sure is safe.

| # | Current text (short quote, line) | Disposition | Reason |
|---|---|---|---|
| 1 | "ShipLoop navigator \| release-verify \| revision 48" (1) | kept (P:1) | Adds the work item and a pointer to the roots line. |
| 2 | "Callback for this stage (run once after its work...)" + command (2) | kept once (P:19-20) | One copy of the command (section 10.3). It moves below Do, still on the first screen. |
| 3 | "Goal: Verify the release where consumers use it." (3) | kept (P:2) | |
| 4 | Done when: "the consumer behaviour is observed where consumers use it" (5) | kept (P:4) | Done-when |
| 5 | Done when: "outcome.md, environment.md and README.md ... ## Learned, ## Key considerations, ## Open for the next run" (6) | kept (P:5) | Done-when; review row 1 already fixed in this engine |
| 6 | "Checked by: ... reruns every recorded test command ... refuses a docs/shiploop file ... missing or empty" (7) | kept and extended (P:6) | Adds gates the code refuses but the line omits: empty outcome sections and credential lines (`knowledge_home.check`), the dropped R-id gate, and the common gates. `_checked_line` drops `_COMMON_GATES` and the "refusal does not advance" sentence on the `complete_runs` branch. |
| 7 | "Test: A passing unit suite is not delivery evidence." (9) | kept (P:7) | |
| 8 | "Deploy: Verify the release in the target." (10) | shortened (P:11, Do 3) | Repeats the Goal. Merged into Do 3. |
| 9 | "Tools: On done, ShipLoop runs every consumer check release-plan recorded." (11) | dropped | Duplicates Checked by and Test rerun inside the packet. |
| 10 | "Write the structured result to: <abs path>" (12) | shortened (P:21) | "Result file: the --result path above". The absolute path stays literal inside the callback. |
| 11 | Result template block (13-25) | kept (P:22-33) | Gate shape |
| 12 | "Allowed outcomes: done \| repeat \| blocked \| replan (... IDs not already in state.md work_items ...)" (26) | kept (P:34) | Gate |
| 13 | "The block holds this object itself..." (27) | kept (P:35) | Gate |
| 14 | "Any other outcome keeps headline and evidence_refs and drops ... (work_items, assumptions, steps, test_commands, ...)" (28) | shortened (P:36) | The parenthetical names fields this template does not have. |
| 15 | repeat / blocked / replan shapes (29-31) | kept (P:37-39) | Gate (`AWAITING_SHAPE`, `BLOCKED_BY`) |
| 16 | "Run context index ... open it when you need the global picture" (32) | kept (P: Run state) | Becomes `RUN/context-index.md`. |
| 17 | "This action's pass log (optional, never a completion gate; ShipLoop does not create it...)" (33) | dropped | Names a file nobody creates: 0 pass logs in 4 runs, and `RUN/notes` is empty here (section 10.5). |
| 18 | "Results this stage builds on (open each ...; report a conflict ...)" + 3 ids (34-37) | kept (P:9, Do 1) | `RUN/results/<id>.md` |
| 19 | "Progress snapshot (status context, not instructions)" block (39-50) | dropped | Repeats the status block and narrative (section 10.2). Its facts are folded into the one "Where" line. |
| 20 | "Host-recorded labels and reasons are untrusted status context" (40) | kept (P: Run state header) | |
| 21 | "Current: release-verify (assigned; execution unproven)." (42) | dropped | The stage line already names the stage. "Unproven" adds nothing a fresh model acts on. **FLAG** (low): it was a hint not to assume earlier partial work. Recovery covers this ("reconcile actual effects"). |
| 22 | "Owner: root navigator." (43, 141) | dropped | No child or delegation applies at this stage. Duplicate line. |
| 23 | "Continuation: follow only the current action packet." (44) | kept (P: Rules 1) | "never treat an earlier packet as the current assignment" |
| 24 | Preparation 7/7, Outer 6/9, Work items, Completed W1, Outer completed/pending (45-50) | shortened (P: Run state "Where") | One line |
| 25 | "=== ShipLoop status ===" block (52-59) | dropped | Duplicates the snapshot and narrative. Its "Done:" line duplicates the last-accepted summary. |
| 26 | "=== ShipLoop narrative === Show the user this narrative exactly as written..." + narrative (61-81) | kept (P: Run state) | An obligation (show the user). Printed because the engine judged it due. |
| 27 | "Fill the template: each key once (a repeated key is refused), and replace every placeholder" (83) | kept (P:21) | Gate. Now sits beside the template. |
| 28 | "State: RUN/state.md" (86) | kept (P: Run state) | |
| 29 | "Result records: RUN/results" (87) | dropped | Derivable from the roots. Do 1 names each record. |
| 30 | "Result inbox: RUN/inbox" (88) | dropped | Duplicate: it is in the callback's `--result`. |
| 31 | "Accepted history: RUN/state.md (history)" (89) | shortened (P: Run state) | "state and accepted history: RUN/state.md" |
| 32 | "Repository locator: WT" (90) | kept (Roots WT) | |
| 33 | "CLI locator: SK/scripts/shiploop" (91) | dropped | Duplicate. Every command carries the absolute CLI path. |
| 34 | "ShipLoop skill card: SK/SKILL.md" (92) | reference (card) | |
| 35 | "Run directory locator: RUN" (93) | kept (Roots RUN) | |
| 36 | "Scratch directory (your temporary files; /tmp is shared...)" (94) + "Write temporary files ... not /tmp" (190-192) | kept (P: Rules 8) | Two copies merged into one line. |
| 37 | "Keepalive marker: SHIPLOOP-RUN run=... rev=48 dir=..." (95) | kept literal (P: Recovery) | Machine-matched string |
| 38 | "Access-readiness policy: research-loop.md#early-access-readiness" (96) | dropped | Irrelevant here: a planning-stage policy. |
| 39 | "Delivery-authority policy: delivery-authority.md" (97) | dropped | Irrelevant here: release-plan and release record authority, and this stage performs no release effect. **FLAG** (low): a model that finds it must redeploy has no pointer. Do 7 forbids re-release, so I judge the drop safe. |
| 40 | "Environment lifecycle policy: environment-lifecycle.md" (98) | reference (release ops, by section) | Whole-file pointer replaced by its section. |
| 41 | "Environment lifecycle note (host-authored, if present): RUN/notes/environment-lifecycle.md" (99) | gated (file exists) | Absent in this run |
| 42 | "Cross-run knowledge policy: project-knowledge.md" (100) | reference (home) | Section, not file |
| 43 | "Maintained requirements policy: ...#maintained-product-requirements" (101) | reference (reqs) | |
| 44 | "Requirements definition guide: requirements-definition.md" (102) | dropped | Irrelevant here: spec reconciliation and NFR definition happen in planning. |
| 45 | "Stage readiness and completion guide: ...#stage-readiness-and-completion" (103) | reference (done) | |
| 46 | "Initial repository baseline guide: execution-planning.md#initial-repository-baseline" (104) | dropped | Irrelevant here: a planning baseline. |
| 47 | "Reference handoff policy: ...#reference-handoffs-and-destinations" (105) | reference (locators) | |
| 48 | "Repository knowledge index (host-authored, if present): WT/SHIPLOOP.md" (106) | gated (file exists) | Absent in this run. Checked by still names SHIPLOOP.md for the credential screen. |
| 49 | "Consumer testing guide: ...#lightweight-and-browser-checks" (107) | reference (browser) | |
| 50 | "Repeatable test-suite guide: repeatable-test-suites.md" (108) | dropped | Duplicate. The handshake section of the same file is cited. |
| 51 | "Selected-case reconciliation guide: ...#test-cases" (109) | reference (cases) | |
| 52 | "Real-boundary selection guide: ...#surface-selection" (110) | reference (surfaces) | |
| 53 | "Interaction design guide: behavioral-requirements.md#actors-..." (111) | gated (`surfaces` field) | Section 4. This stage plans no interaction. |
| 54 | "Worktree and artifact policy: workspace-lifecycle.md" (112) | reference (copy, follow-up; by section) | |
| 55 | "Recovery command:" + `shiploop next` (113-114) | kept literal (P: Recovery) | Command |
| 56 | "Retain these locators and recovery command in durable task handoff material" (115) | kept (P: Recovery header) | |
| 57 | "After interruption, check the paths ... do not initialize a replacement or invent a callback." (116) | kept (P: Recovery) | |
| 58 | "Recovery only reads the saved state. If paused or blocked ...; if halted or done, stop." (117) | kept (P: Recovery) | |
| 59 | "Execute this packet in this conversation, submit its current callback yourself..." (118) | kept (P:18) | One line under Do |
| 60 | "Original request ... BEGIN/END ORIGINAL REQUEST aa1bab5c53a0ada7" + request text + marker rule (119-123) | dropped (default c) | This is an outer delivery stage, not planning. The request's clauses reach it through the spec result and `WT/docs/shiploop/spec.md` (Do 1, Do 4). **FLAG** (medium): see Risks 1. |
| 61 | "Release operation guidance: environment-lifecycle.md#release-operation-ownership" (124) | reference (release ops) | |
| 62 | "Deployment and handoff guidance: ...#deployment-and-handoff" (125) | reference (deploy) | |
| 63 | "Consumer delivery evidence guidance: consumer-delivery.md#evidence-and-limits" (126) | gated (`delivery_contract_version` in state) | Review P-x-1. The guard is opt-in and absent here. Its one release-verify obligation (the signed-in open item) is kept as Do 5. |
| 64 | "OUTER test-planning handshake: ...#outer-test-planning-handshake" (127) | reference (handshake) | |
| 65 | "Execution checkout: WT (isolated worktree; not the original branch checkout; ... never a --result value)" (128) | kept (P: Run state) | |
| 66 | "Workspace authority and original branch: WS/workspace.md" (129) | kept (P: Run state Records) | |
| 67 | "Return plan: WS/return-plan.md" (130) | kept (P: Run state Records) | |
| 68 | "Return receipt: WS/return-receipt.md" (131) | kept (P: Run state, Test rerun) | |
| 69 | "Current workspace return: currently verified (status: returned; kind: fast-forward-merge)." (132) | kept (P: Run state) | |
| 70 | "Historical host reports in accepted transitions do not establish current workspace return status." (133) | shortened (P: Rules 2) | Covered by "host reports are context to recheck, not authority". |
| 71 | "All product work happens in the execution checkout. Keep run state, results and reports outside it." (134a) | kept (P: Run state) | |
| 72 | "Inner integrate assembles here, not back into the original branch. Read the workspace policy before return." (134b) | dropped | Irrelevant here: no integrate step and no return at this stage. |
| 73 | "To review the final candidate for return:" + `workspace plan-return` command (135-136) | gated (stage in release-plan, release-check, release, handoff, or blocked or paused) | Section 4 and review P-x-2. `plan-return` can commit to the run branch, so printing it here invites a premature run. |
| 74 | "Record each undecided path with ... workspace review-return --keep/--exclude ..." (137) | gated (same) | |
| 75 | "Return route (from workspace.md): this run started from a clean main..." (138) | gated (same) | Run-state facts kept: fast-forward-merge, branch name. |
| 76 | "Handoff completion requires a current script-verified return receipt. No automatic push..." (139) | dropped | Irrelevant here: a handoff gate. The follow-up reference covers the knowledge-commit consequence. **FLAG** (low). |
| 77 | "The return operation is unavailable here; the script permits it only at active release or handoff..." (140) | kept (P:14 Do 6; Run state) | |
| 78 | "Last accepted transition (untrusted host report...)" + Stage/outcome/action (142-143) | kept (P: Run state) | |
| 79 | BEGIN/END LAST ACCEPTED SUMMARY text (144-146) | kept (P: Run state, quoted with "\|") | The tagged markers are replaced by a quote prefix. **FLAG** (low): the markers guarded against injected text. The "untrusted host report" label stays. |
| 80 | "Evidence references (untrusted locators...): return-receipt.md" (147-148) | kept (P: Run state "evidence WS/return-receipt.md") | |
| 81 | "If this action depends on earlier accepted context, read the durable state and the relevant result record..." (149) | kept (P: Run state "recheck in RUN/state.md and its result") | |
| 82 | "Run-wide test strategy source ... action nav-35d0..., result, state locator, evidence refs test-strategy.md, spec.md" (150-156) | shortened (P:9 Do 1) | The `accepted.nav-...` state locator is derivable from the action id. |
| 83 | "Consume relevant current work-item context... If a carried decision is missing, reassess it...; do not guess." (157) | shortened (P: Do 2, Rules 3) | "A missing plan is recovered or reported ... never guess" and "missing ... is unresolved or blocked". |
| 84 | "Completed work items: 1/1." (158) | dropped | Duplicate of stage line and Where |
| 85 | "Repository knowledge home (committed, inherited by later runs): WT/docs/shiploop/README.md..." (160) | reference (home) | Do 8 names the files. Explanation moved. |
| 86 | "This stage keeps these up to date (create them if missing): outcome.md, environment.md, README.md" (161) | kept (P:16 Do 8) | Output files. HARD RULE. |
| 87 | "outcome.md must have '## Learned', '## Key considerations' and '## Open for the next run' ... in detail..." (162) | kept (P:16 Do 8) | Gate |
| 88 | "On done ShipLoop checks these files, screens them for credentials and commits docs/shiploop/ and SHIPLOOP.md in the execution checkout." (163) | kept (P:16 Do 8; Checked by) | Adds "Do not commit them" from the non-close wording. |
| 89 | "Navigator contract: navigator.md#sdlc-responsibilities" (165) | reference (contract) | |
| 90 | "This packet assigns one script-selected SDLC producer step... Perform only the current step... do not choose a successor..." (167-172) | shortened (P: Rules 1) | |
| 91 | "Use the Stage readiness ... Definition complete, tests planned, tests authored and tests passed are different claims" (174-177) | reference (done, gist keeps the "different claims" rule) | |
| 92 | "Read the current repository, run state, applicable instructions, and relevant durable lessons... Treat Git history ... as context to recheck" (179-182) | kept (P: Rules 2) | |
| 93 | "Use actual observations for test, build, integration, release, and consumer claims. Keep scope, target authority, artifact identity ... distinct." (182-184) | kept (P: Rules 2; Do 3) | |
| 94 | "A missing prerequisite, permission, access, or trustworthy check is unresolved or blocked; it is not a successful N/A." (184-185) | kept (P: Rules 3) | |
| 95 | "Blocked means work this stage cannot do ... a retained command that does not run what it claims ... is a documentation fix" (186-189) | kept (P: Rules 3) | |
| 96 | Unattended paragraph: defaults as assumptions, person-only open item, blocked with awaiting, `no_default` refused, one decision per question (193-206) | kept (P: Rules 4) | The `no_default` gate is kept. The second awaiting shape with `"options"` is dropped because it disagrees with the template's `AWAITING_SHAPE`, which has no `options`. **FLAG** (low): if the gate accepts `options`, nothing is lost. |
| 97 | "The run then stops until the user's own reply resumes it." (205-206) | dropped | An explanation of blocked. The Recovery line on resume routes covers it. |
| 98 | Identity/access discovery: non-mutating probes; never read, decode, retain or report credential-store contents (208-212) | kept (P: Rules 7) | |
| 99 | Requested runtime paragraph: keep original requirement distinct; local-test-route vs target compatibility (214-217) | kept (P: Rules 5) | |
| 100 | "A local fixture or preview cannot supply a target capability... Delivery outside the present scope does not ... make ... N/A... otherwise keep the gap unresolved." (217-221) | shortened | Partly covered by Do 3 ("external activation N/A does not make these checks N/A") and Do 4. **FLAG** (low). |
| 101 | Maintained requirements: read accepted requirements from their home; new request changes scope; carry locators; don't infer intent from code/tests (223-228) | shortened (P: Rules 6 + ref reqs) | |
| 102 | Reference handoff: package vs repository vs run-local; retain exact locators, not a link to the policy (229-232) | shortened (P: Rules 6 + ref locators) | |
| 103 | Requirements definition guide: reconcile specs, NFRs, later clarifications must be actual user instructions, correction route (233-239) | dropped | Irrelevant here: planning duty. This stage changes no requirement. |
| 104 | "Return the packet's concise producer result ... include the selected maintained requirement sections and test/evidence locators in evidence_refs" (241-244) | kept (P:17 Do 9) | The reason clause ("so the next Improve packet...") is dropped per default (d). |
| 105 | "If a required source is missing, report the gap rather than inventing a locator" (245) | kept (P:17 Do 9) | |
| 106 | "A justified N/A is still an output that states what was assessed and why" (246-247) | kept (P:17 Do 9) | |
| 107 | "Do not embed an Improve review campaign ... Only planning results ... get an actual Improve-skill handoff; every other result ... advances directly." (247-251) | dropped | Default (d), section 10.4: this stage has no Improve child. |
| 108 | "Run only the checks this step's change needs. When this step changes no product file, its check is the named command..." (251-254) | shortened (P:7 Test line) | At this stage ShipLoop runs the check, so the rule reduces to "confirmed by ShipLoop's passing rerun record". |
| 109 | "On done, ShipLoop runs the consumer checks ... the record it writes is the evidence, so a criterion is confirmed by its passing command" (257-259) | kept (P:6-7) | It was also a third copy of the Tools line. Merged. |
| 110 | "Verify the actual release ... Distinguish source synchronization, artifact identity, operation receipt, and real consumer behavior." (260-262) | kept (P:11 Do 3) | |
| 111 | "A blocked or unknown post-release check remains incomplete; preserve prior receipts and do not re-release blindly." (262-263) | kept (P:15 Do 7) | |
| 112 | "For local-only work, verify the current local candidate ...; external activation N/A does not make these checks N/A." (264-265) | kept (P:11 Do 3) | |
| 113 | "In an isolated run this stage cannot return, so a defect ... is fixed through replan (one corrective work item)..." (266-268) | kept (P:15 Do 7) | |
| 114 | "Anything you run yourself inside the user's checkout must leave it exactly as the return left it..." (268-270) | kept (P:14 Do 6) | The checkout path is now literal. Before, it appeared only in the Test rerun block. |
| 115 | Browser surface: consumer entry after authentication, account/target, visible feature, action/outcome per clause (271-272) | reference (browser) + shortened (Do 4) | **FLAG** (low): the per-clause checklist moved to the reference. It applies only to a browser clause. |
| 116 | "Retain non-secret routing state; require app chrome/branding only when specified. An embedded feature can satisfy its accepted boundary." (273-274) | reference (browser) | An explanation |
| 117 | "Source or local test passes cannot discharge an unobserved required deployed interaction." (274-275) | kept (P:12 Do 4) | |
| 118 | Person-only case: do not loop; open item with steps and report; verify every other case; blocked awaiting present only when the release cannot be accepted (276-281) | kept (P:13 Do 5) | |
| 119 | "the person's report resumes the run, and only the blocked cases are checked again against the same release" (281-282) | dropped | An explanation of resume behaviour, not an obligation of this pass. |
| 120 | OUTER handshake: recover the latest done system-test-author and release-plan records after the most recent accepted replan; earlier records historical; pending/repeat/blocked are not authority (285-290) | kept (P:10 Do 2) | Pending/repeat/blocked detail moved to the reference. |
| 121 | "Review a pending producer proposal separately during its Improve handoff." (290) | dropped | Irrelevant here (Improve wording, default d) |
| 122 | "Read the selected results and relevant evidence_refs; retain their action/result and durable plan locators in this result." (291-292) | kept (P:10 Do 2) | |
| 123 | "At system-test-author or release-plan, create/reconcile the plan owned by that stage..." (293-294) | dropped | Irrelevant here: producer stages only |
| 124 | "At consumers, acknowledge which plan applies and revalidate it ... never guess commands, erase required coverage, or deploy to make a check available. A plan is not execution evidence." (295-298) | kept (P:10 Do 2) | |
| 125 | "Material changes to code, tests, fixtures, configuration or target invalidate affected observations; ... rerun affected checks ... Reuse unaffected evidence only with identity" (298-301) | reference (handshake) | **FLAG** (low): ShipLoop reruns the consumer checks on every done here, so a stale observation cannot pass the gate. |
| 126 | Selected-case reconciliation: classify every case passed/failed/blocked/not-run/justified N/A; source, HTTP or DOM structure alone cannot close a rendered interaction (304-308) | kept (P:12 Do 4) | |
| 127 | "Reconcile each affected requirement clause with its case ... A pass at a different surface is supporting evidence" (309-311) | kept (P:12 Do 4) | |
| 128 | "Preserve cases not yet due with their phase, owner and prerequisites..." (312-313) | kept (P:12 Do 4) | |
| 129 | "Check the original selected inventory for dropped clauses/cases; do not claim all requirements met..." (314-315) | kept (P:12 Do 4) | |
| 130 | "Progress: do not reprint this packet's ShipLoop status block ... at most one line ... narrative first line" (318-324) | kept (P: Rules 9) | |
| 131 | "Only the current owner reports overall progress. State labels say which action is assigned..." (324-325) | dropped | Irrelevant here: there is no child or delegate. |
| 132 | "Describe Improve activity only from its own observed records..." (325-326) | dropped | Default (d) |
| 133 | "Run to completion ... do not wait for acknowledgement ... including a bound Improve child" (327-332) | kept (P: Rules 9) | Improve clause dropped (d) |
| 134 | Stop/pause/not-implement → pause command; question about loop → answer and continue; do not pause on your own (332-339) | kept (P: Rules 9) | |
| 135 | "Never end the turn while a ShipLoop command is still running ... headless host ends the whole session" (339-344) | kept (P: Rules 9; P:19 callback line) | |
| 136 | "If a host keepalive hook refuses to end the turn, its reason names this run's next command: run it" (344-345) | kept (P: Rules 9) | |
| 137 | "Resolve recoverable conditions through the printed route and ask only for an actually missing decision" (345-346) | shortened (P: Rules 4) | Duplicate of the unattended rule |
| 138 | "Call this when done:" + second copy of the callback (349-350) | dropped | Duplicate inside the packet (section 10.3) |
| 139 | "Improve: This result advances directly; no Improve child runs ... If work cannot continue, submit outcome 'blocked'...; the next packet prints its Resume command." (351) | dropped / shortened | The Improve part is dropped (d). The blocked part is covered by outcome shapes and Recovery ("a blocked stop prints its Resume command"). |
| 140 | "Pause without consuming the action: <cmd> (only when the user asks or a real blocker...)" (352) | kept literal (P: Recovery) | Command |
| 141 | "Halt (terminal and irreversible; only on an explicit user stop): <cmd>" (353) | kept literal (P: Recovery) | Command |
| 142 | "Test rerun: ... clean copy of the result returned to .../work (fast-forward-merge at 8fb1af275c8b; receipt ...), made fresh at .../consumer-check ... at most 7 refused runs ... times out ... without counting" (355) | kept (P:41) | Gate. `WS` root. |
| 143 | "1. [check] node --test --test-reporter=spec / 2. [check] ... test/system.test.js" (356-357) | kept (P:42-43) | Commands the gate runs |
| 144 | COUNT_RULE: "passes only when it exits 0 and actually ran tests ... listed ID ... TC-4a ... --verbose ..." (358) | gated (any row is not `check`) | Replaced by the true one-line rule for check rows from `test_loop.judge`: exit 0, refused when the summary shows zero tests. Review P-rv-2. |
| 145 | "Where they run: the copy holds exactly the returned tree ... absolute path runs there" (359) | kept (P:45) | Adds "reproduce in WS/consumer-check, then replan", from `_copy_refusal`. |
| 146 | (absent) ShipLoop's own knowledge commit at release-verify makes handoff need a follow-up return | added (P: ref follow-up gist) | Review P-rv-3 |

Disposition counts (rows 1-145; row 146 is an addition):

| Disposition | Rows |
|---|---|
| kept (incl. kept once, kept and extended, kept literal) | 76 |
| shortened (incl. "dropped / shortened", "reference + shortened") | 16 |
| reference | 18 |
| gated | 8 |
| dropped | 27 |

Rows marked **FLAG**: 21, 39, 60 (medium), 76, 79, 96, 100, 115, 125.

## 4. Risks after a context clear

1. **The original request is gone (row 60, the riskiest move).** Done-when asks for consumer behaviour "observed where consumers use it", and Do 4 asks for every requirement clause to be reconciled. A cleared model now finds the clauses only by opening `WT/docs/shiploop/spec.md` and the spec result. If spec.md paraphrased or dropped a clause (for example "Red moves first toward higher row numbers"), release-verify cannot catch it, though today it could check the verbatim text. Why I think it holds: spec is in this stage's `reads`, the living spec keeps R-ids under a gate, and product-acceptance already compared product and request. Probe: the S-6 clear inside release-verify with a spec.md that omits one request clause. Does the model notice? If not, keep the request at release-verify and handoff (both close the delivery). That costs about 1.4 KB.
2. **Unexpanded roots in a write.** Do 8 asks the model to write `WT/docs/shiploop/features/.../outcome.md`, and the roots legend is the last line. A model that slices the head (the observed pattern: Goal to template) may pass `WT/...` to a Write tool and create a literal `WT/` directory in its cwd. The knowledge gate would then refuse with absolute paths, so the run recovers, but at the cost of one refusal. Mitigation already in the packet: the stage line says where the roots are. Probe this case specifically. If it fails, print the roots line second (after the stage line) rather than last, or print the three knowledge paths absolute because they are files the model must write.
3. **Gated plan-return and review-return.** A model that finds a defect might want to "fix and re-return". With the commands gone it cannot, and Do 7 and the copy line route it to replan, which is the only exit `_copy_refusal` accepts. I judge this safer than today, where the commands were printed beside "unavailable here".
4. **The consumer-delivery pointer is gated off.** If a run opts into `delivery_contract_version`, the gate prints it again. Do 5 carries the one rule from that section that applies without the guard.
5. **The "Checked by" line is longer.** It now names six refusals. That is the purpose of the change, because refusals came from gates the line omitted (review row 1). A model reading only the head now knows every refusal it can hit here.
6. **The `ref` verb is assumed.** If the verb is not built, the reference lines still give `REF/<file>.md#<anchor>`, which the model can grep. Nothing obligatory depends on opening a reference.

## 5. Engine changes needed

- `shiploop_navigator.render`: new print order (head, test rerun, rules, references, run state, recovery, roots). It drops the second callback and the "Write the structured result to" line. It drops `_progress_lines` snapshot and status block when the narrative is due.
- `shiploop_navigator._checked_line`: the `complete_runs` branch also appends `_COMMON_GATES` and the "refusal does not advance" sentence.
- `shiploop_navigator._stage_gates`: knowledge-close gate text adds the empty-sections fault (`knowledge_home.LEARNING_SECTIONS`) when stage is release-verify, plus the credential and dropped-R-id faults that `knowledge_home.check` refuses at every close.
- `shiploop_navigator._goal_lines`: drops the Tools consideration when it repeats `complete_runs`, and the Deploy consideration when it repeats the goal. It prints the Do list from `shiploop_prompts.DUTIES["release-verify"]`, which is rewritten as numbered obligations with `ref` tags.
- `shiploop_navigator._result_contract_lines` and `_outcome_shape_lines`: "Result file: the --result path above"; the parenthetical lists only fields the template has.
- `shiploop_prompts` frame constants (the producer preamble and the progress/continuation text): rewritten as the "Rules for every stage" bullets. Improve clauses are removed for stages without an Improve child. The requirements-definition paragraph is gated to planning stages.
- `shiploop_stage_spec.Stage`: new `refs` (anchor plus gist) replaces the per-stage guidance-locator tuple in `shiploop_prompts`. `blocks` is honoured for workspace, consumer-delivery and interaction.
- Workspace block builder in `shiploop_navigator.render` (plan-return/review-return/return route): gated by stage in `{release-plan, release-check, release, handoff}` or status blocked/paused.
- `shiploop_knowledge_home.stage_lines`: folded into Do 8 (files with roots, "do not commit them"); the home pointer line moves to a reference.
- `shiploop_test_loop.rerun_lines`: prints `COUNT_RULE` only when some row is not `check`, otherwise a new `CHECK_ROW_RULE`; adds the "reproduce in the copy, then replan" clause for `returned-result`.
- Locator block (the run, policy and guide locator lines): replaced by a roots line (`RUN`, `WS`, `WT`, `SK`, `REF`) and existence-gated lines for `RUN/notes/environment-lifecycle.md` and `WT/SHIPLOOP.md`. The pass-log line is deleted.
- Original-request block: printed only for planning stages (default c).
- New CLI verb `shiploop ref <file>#<anchor>` in `scripts/shiploop`.

## Independent check

Checked against engine `pc1i-64ba2b/skills/shiploop/scripts/` and the build references. No blockers found.

**(1) Gate obligations lost or only referenced.** None lost.
- fine: Checked by matches `knowledge_home.check`, in this order: missing or empty close files; a credential line in `docs/shiploop/**/*.md` or `SHIPLOOP.md`; an empty `LEARNING_SECTIONS` at release-verify; a dropped `R-<n>`. It also matches `_COMMON_GATES` and `_CHECK_TEXT["test-rerun"]`. `MAX_REFUSED_RUNS = 7` is correct. The `judge` check-row rule is correct: exit 0, and `no-tests` when `tally["ran"] == 0`.
- fine: `AWAITING_SHAPE` without `options` is safe. `options` is optional, and the parser requires at least two only when it is present (`shiploop_navigator.py` ~l.415).
- should-fix (low): "ShipLoop judges nothing else" overstates the case. The headline placeholder and length check, repeated keys, `_DONE_ONLY_FIELDS` and the no_default refusals also apply. Each one is stated elsewhere in the packet, so say "nothing else about the work" instead.
- should-fix (low): the copy line ("then replan") and Risk 3 ("the only exit `_copy_refusal` accepts") leave out the exception in `_copy_refusal`: "If the cause is not about what was delivered (a busy port, a missing tool), fix it and submit done again."

**(2) REF anchors.** All 14 `REF/...#anchor` citations resolve against headings in both the worktree source and the build references. `SK/SKILL.md` exists. fine.

**(3) False claims.**
- should-fix: the Run state line "Return, plan-return and review-return are unavailable at this stage (release and handoff only)" is false. Only `return` is stage-gated (`shiploop_protocol.py`: `navigator.current_stage(saved) in ("release", "handoff")`). `plan-return` and `review-return` run at any stage, and `plan-return` calls `workspace.commit_leftovers`, which commits to the run branch. Reword it as an instruction: "return is unavailable here (release and handoff only); do not run plan-return or review-return at this stage."
- should-fix: the References header tells the model to run `shiploop ref <file>#<anchor>`. No such verb exists in `scripts/shiploop` today, so argparse rejects the command. Ship the verb in the same change as the packet, or fall back to "open REF/<file>, section <anchor>".

**(4) Can a model act after a context clear?** Mostly yes.
- should-fix: Do 8's required writes are `WT/...`, and `WT` is defined only on the last line (Risk 2). Print these three output paths as absolute paths. They are the files this stage must write, and the current packet prints them absolute.
- should-fix: the continuation obligation is weaker. The current packet says "submit its current callback yourself and consume the returned packet" and "immediately follow the newly returned packet". The proposal keeps only "submit the callback yourself". Add "then follow the packet the callback prints".
- fine/probe: dropping the original request (Risk 1) is acceptable only if the S-6 probe passes. Spec R-ids are gate-kept, but paraphrased wording is not.
- fine: "Do not commit them" is true and useful. If the model commits the files itself, `_home_changed` is false, `knowledge_home.commit` does nothing, and the learnings commit body is lost.

Verdict: safe with the listed fixes.
