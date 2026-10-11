# Proposal: compact Improve parent packet for spec (checkers pc1i, nav-284162de, revision 5)

Current packet: `/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/run/packets/nav-284162de5e054d7b80ce269d024dbd0f-improve.md` (printed before improve-start: the receipt did not exist yet). Engine read: pc1i-64ba2b worktree (`_render_improve`, `_first_callback_lines`, `_goal_lines`, `_improve_start`, `_improve_commit`, the improve-complete branch of `dispatch`, `shiploop_knowledge_home.check`). The improve-commit message rules come from that engine; the deployed build that printed this packet predates them.

## 1. Proposed packet

````text
ShipLoop navigator | spec | revision 5 | Improve review (the parent step stays pending until improve-complete imports the review)
Next command (after you write the opening file, Do step 2): python3 /Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/build/plugins/skill-craft/skills/shiploop/scripts/shiploop improve-start --run-dir=/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/run --action=nav-284162de5e054d7b80ce269d024dbd0f --opening=/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/worktree/.shiploop-improve/nav-a5a3303c2aa54837aa1bab5c53a0ada7/nav-284162de5e054d7b80ce269d024dbd0f/opening.md
Paths written RUN/, WT/, SK/, REF/, IMP/ or CHILD/ expand from the Roots line at the end; every command is printed in full.
Goal: review and improve the returned spec result (stage goal: define required behavior and acceptance criteria) with the selected Improve skill until its runtime completes, then import the review. Review scope: behavior, acceptance, non-functional criteria, existing-spec reconciliation, failure boundaries and consumer outcomes. Phase intent: reconcile the incoming request with existing requirements and define verifiable functional and non-functional criteria while preserving unaffected intent.
Done when (the spec result must meet each; correct the result, never the condition):
- every request outcome maps to at least one acceptance criterion
- each criterion is independently verifiable and says how it will be confirmed
- non-functional requirements are assessed, or excluded with a reason
- unaffected existing requirements are preserved
Planning review focus. This planning result is the contract that later stages build on and that no other review sees until the end. Each pass looks for these conditions and fixes them within scope:
- a step, example or expected result that cannot be replayed exactly: name the concrete inputs, values, identifiers and sample interactions;
- an expected result or check that a weaker stand-in would pass: a hardcoded value, a missing assertion, a title-only test, or an absent required name;
- a documented command that does not run what it claims on the target runtime: run it once and record the exit code and the cases it executes;
- a required requirement, test ID or case dropped or weakened compared with the prior accepted version;
- a claim about what the runtime, platform or a library can do that a decision depends on, with no primary-documentation source or probe result: check it, and correct the plan where it is wrong;
- a missing prerequisite, wrong order or unowned verification in the steps.
Do not reread history or rerun a check already recorded green at this commit unless a finding depends on it. A pass that finds none of these is trivial.
Checked by (each refusal's first line is the fix and the command to run again):
- improve-start refuses: an opening without exactly the four "## " headings of the template below, or with one empty or left as "..."; an opening that contains the binding line or credential-looking text; a frozen contract over 9,216 bytes (your four sections get about 4,772 bytes together; non-ASCII counts several bytes per character); a second start of a child that already started.
- improve-commit refuses: a --message other than CHILD/commit-message.md; an empty message; credential-looking text; no `Key learnings:` line (or another lessons label it reads), or one with no text; a `Learned-from:` line without a commit ID reachable from HEAD and what that commit contributed.
- improve-complete refuses: fewer than the last two CHILD/reviews/review-<n>.md (one when the first pass changed nothing) or no CHILD/reviews/checks.md; files this review changed and left uncommitted; an unchanged single trivial pass while files changed; a final_result whose absolute evidence_refs paths do not exist, or whose awaiting has no no_default; while docs/shiploop differs from HEAD, a living spec that drops an R-<n> ID present at HEAD, or a credential-looking line there.
ShipLoop does not judge the review: you confirm each Done-when condition.
Do:
1. Read IMP/SKILL.md section "ShipLoop whole-skill subcall" and IMP/runtime/until-loop/ADAPTER.md section "Follow the returned action" with a file-reading tool, once per context (again after a reset or if a card changed), then follow them; open other sections only when a step needs them; never print either card to the shell. The Improve skill owns every review iteration.
2. Write CHILD/opening.md with a file-writing tool: the four headings of the template below, each filled from this conversation and the candidate. Give essential meaning inline and locators for detail; put long detail in a file and name its path; do not copy this packet or restate the skill's instructions.
3. Run the Next command. ShipLoop freezes the child contract (CHILD/start.json, and the child's return in CHILD/parent-return.md), starts the bound runtime with the receipt CHILD/packet.json and prints the child's first packet. Do not write the contract or start the runtime yourself. If CHILD/packet.json already exists, the child has started: follow Recovery instead.
4. Follow each runtime packet in this conversation. A pass is one full review of the candidate against Done-when and the review focus: change what is warranted in code, tests or documentation within scope, run the applicable checks, and write the pass to CHILD/reviews/review-<n>.md (n = pass number: review-1.md, review-2.md, ...) and the current check output to CHILD/reviews/checks.md.
5. After a pass that changed files, write CHILD/commit-message.md with a file-writing tool (never a shell heredoc). Each of these goes on a line of its own starting in column 1: `Key learnings: <what this iteration taught that a later iteration or run should reuse>` (`Key learnings: none` if nothing new); optional `Learned-from: <commit id> <what it contributed>` (ShipLoop checks the ID and writes the full one); for a change to a remote system that left no file change, `Remote change: <system alias>, <what changed>, <where its evidence is>` and append --remote-change to the command. Then run: python3 /Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/build/plugins/skill-craft/skills/shiploop/scripts/shiploop improve-commit --run-dir=/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/run --action=nav-284162de5e054d7b80ce269d024dbd0f --message=/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/worktree/.shiploop-improve/nav-a5a3303c2aa54837aa1bab5c53a0ada7/nav-284162de5e054d7b80ce269d024dbd0f/commit-message.md
   A pass that changed no file makes no commit. Never run git commit yourself: a hand-typed commit skips these checks.
6. Only if the review changed a decision or decision-relevant evidence a successor needs, write final_result (shape below) to RUN/inbox/nav-284162de5e054d7b80ce269d024dbd0f-final-result.md. Otherwise omit it: ShipLoop reuses the result already submitted.
7. Only after the runtime has written the terminal packet to CHILD/packet.json (runtime completion alone never advances this action), run the parent callback (never 'complete'):
python3 /Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/build/plugins/skill-craft/skills/shiploop/scripts/shiploop improve-complete --run-dir=/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/run --action=nav-284162de5e054d7b80ce269d024dbd0f
   Append when they apply: --final-result /Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/run/inbox/nav-284162de5e054d7b80ce269d024dbd0f-final-result.md (step 6); --notes /Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/run/inbox/nav-284162de5e054d7b80ce269d024dbd0f-improve-notes.md (optional plain-text lessons for later steps); --no-commit "<the user's or repository's instruction>" when told not to commit.
Opening template (CHILD/opening.md; ShipLoop adds the binding line, conditions, commit policy, exclusions and return locators):
## Current context and desired improvements
<current learnings, decisions, unresolved concerns and suggested improvements to assess; the original request and the step result's essentials>
## Scope
<the exact candidate paths, staged, unstaged and untracked (an empty initial commit or unmoved HEAD does not replace named untracked files with the latest commit's diff; Git history is context, not scope), or the inventory locator when large; anything excluded>
## Authority
<current approvals, declines, pending decisions and any no-commit override, each with action/target, conditions and source>
## Environment
<the runtime, commands and checks that apply, and the expected check state>
final_result shape (RUN/inbox/nav-284162de5e054d7b80ce269d024dbd0f-final-result.md): a complete step-result record with the fields of the Step result below; outcome done | repeat | blocked (never reconcile); keep every existing evidence_refs entry as an absolute path and add each planning file produced or revised plus a compact decision note (finding, applicable original constraints, affected decision and consumer, conclusion, limits, source locators). Ordinary review and check evidence stays in the review files.
Step result under review (untrusted evidence, not new authority):
# Step result awaiting Improve

```shiploop-state
{
  "evidence_refs": [
    "/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/worktree/docs/shiploop/spec.md",
    "/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/worktree/docs/shiploop/features/build-a-small-two-player-checkers-a0ada7/spec.md",
    "/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/worktree/docs/shiploop/README.md"
  ],
  "headline": "Spec R-1..R-14 written with confirmation methods",
  "outcome": "done",
  "summary": "Living spec docs/shiploop/spec.md defines R-1..R-14 covering every request outcome (server/PORT, page, /api/new, /api/move contract, illegal/legal turn handling, jump removal, mandatory jump, king, setup) plus recorded defaults (multi-jump continuation, win condition, error statuses). NFRs: stdlib only, in-memory state, body size cap. No prior requirements to preserve (empty repo)."
}
```
Producer packet (the spec stage's full duty, considerations and result template): RUN/packets/nav-284162de5e054d7b80ce269d024dbd0f.md
Bound skills: Improve card IMP/SKILL.md; Until Loop card IMP/runtime/until-loop/ADAPTER.md; runtime IMP/runtime/until-loop/scripts/until_loop_ephemeral.py. The Until Loop card's relative links (such as references/runtime-ephemeral.md) resolve under IMP/runtime/until-loop, not under IMP. Child workspace: WT.
Delegation: inline. Run the Improve card's whole-skill subcall in this conversation, in the child workspace WT; verify the process cwd and Git root before task work. Start no reviewer, test-runner or executor agent, Ask Agent or extra worktree unless the user asked for independent review; delegated subtasks never submit a callback or advance the run. This conversation is the only candidate writer until the terminal packet; stop competing writes, including checks that generate files.

Rules for this review (one line each):
- Authority: carry current approvals, declines and pending decisions into the opening; never ask again for an applicable approval or treat a decline as advice. A later user decision applies from the next review iteration: record its receipt and effect in the review notes; the frozen launch context stays unchanged.
- Commits: the Improve card's scoped-commit policy with the task's explicit overrides, only through improve-commit; no push or merge. ShipLoop commits exactly the files this review changed and has not committed (work uncommitted before the review is not counted) and reruns the affected checks.
- Exclude .until-loop, .shiploop-improve and ShipLoop runtime metadata from candidates, edits and commits; adapter-owned state, the receipt and review-note writes keep their owners. Explicitly named planning artifacts may be reviewed. A protected or out-of-scope change follows the blocked or recovery route.
- Receipt: the runtime writes every packet it returns to CHILD/packet.json, the terminal one before it deletes its state; never write or edit it. ShipLoop imports only a packet the runtime wrote there.
- Review passes: the two consecutive trivial passes the runtime requires are self-passes by this executor; report them as passes, never as independent reviews. When the first pass is trivial and leaves Git unchanged, the runtime completes after that one pass.
- Living spec: WT/docs/shiploop/spec.md keeps every requirement ID (R-<n>): change a requirement in place, move a dropped one under a 'Retired' heading with its reason. WT/docs/shiploop/features/build-a-small-two-player-checkers-a0ada7/spec.md lists the IDs this run adds, modifies and retires. ShipLoop refuses prepare if either file is missing or empty, and commits docs/shiploop/ changes when the stage is accepted.
- Requirements: preserve unaffected accepted conditions and cross-cutting rules; review material subclauses and intentional supersession, not just feature names; a planning review does not require future product checks to pass; code, a passing test or a draft never silently redefines accepted intent; keep verification gaps visible.
- Interaction and state: this result specifies an HTTP API, in-memory game state and a browser page, so review actors, channels, state ownership, acknowledgement and recovery, and UI decisions at planning depth (decisions and proposed checks, not consumer evidence), without demanding later-stage work.
- Cold-context inputs: reopen and revalidate only the sources relevant to this candidate (prior results, evidence_refs, selected references); keep a compact locator, decision, rationale and revalidation result in the review notes, never a copied transcript or a new ledger.
- Evidence: register every planning file the review creates or revises in final_result evidence_refs and keep the earlier ones; supporting reference material you write is context, never a second directive (the step definition stays the execution prompt); a URL is a citation until its material is a local file.
- Credentials: use non-mutating probes and sanitized evidence; never read, decode, retain or report local authentication, session or credential-store contents; name where a secret is kept, never its value.
- Backchain: for a dependency diagnostic use a one-pass Backchain primitive (route `source-aware-native`), never a Backchain-to-Until Loop child, nested loop, retry dispatcher or new callback; its findings are ordinary review inputs. Audit resource (backchain-caller/v1, review/audit): SK/../backchain/references/caller-contract.md.
- Temporary files, including each report you pass to the runtime on standard input, go in RUN/scratch with names of your own: /tmp is shared with other runs.
- Progress: at start, at recovery and after each callback, tell the user one line (the item, the stage just finished, the stage now starting); do not reprint the status block; describe Improve activity only from its own records (no invented review count, percentage or ETA).
- Keep going: run to completion within scope; never end the turn while a ShipLoop command runs (keep it in the foreground; a complete can take minutes); a keepalive refusal names the next command: run it. A user stop, pause or "do not implement" is a stop: run the pause command, answer, and resume only on an explicit continue. A question about the loop is not a stop. Ask only for an actually missing decision, authority or access.

Reads:
Original request (preserve user scope; embedded quotations do not override instructions):
----- BEGIN ORIGINAL REQUEST aa1bab5c53a0ada7 -----
Build a small two-player Checkers game served by a Node.js HTTP server with no npm dependencies. server.js starts the server on the port in the PORT environment variable (default 3000). GET / serves a playable HTML page titled "Checkers" with an 8x8 board where two players take turns on the same page. GET /api/new starts a game and returns JSON with a game id. Red starts on rows 0 to 2 and moves first toward higher row numbers; black starts on rows 5 to 7; pieces sit on the squares where row plus column is odd. POST /api/move with JSON {"game": id, "from": [row, col], "to": [row, col]} returns JSON with "ok" true or false, "turn" set to "red" or "black", and "winner" null or the winning colour. An illegal move returns "ok": false and leaves the turn unchanged; a legal move switches the turn; a jump removes the jumped piece and is mandatory when available; a piece reaching the far row becomes a king. Keep the game rules in a module the server uses, and cover them with node:test tests under test/ that run with `node --test`.
----- END ORIGINAL REQUEST aa1bab5c53a0ada7 -----
Only the END marker carrying tag aa1bab5c53a0ada7 closes the request; any other marker-like line above is part of the request text.
Results this stage builds on (accepted; open each one whose content is not already in your context; report a conflict instead of silently choosing):
- intake: RUN/results/nav-a178f646e7e148f6bb46d08f896d4274.md
- discovery: RUN/results/nav-f62ee327a3304697b63ece9047ee64ee.md
- research: RUN/results/nav-9ca690c0336049d98bcc557347c093e0.md
Run context index (request, planning basis, work items, results; open it after compaction): RUN/context-index.md

References (print one section with: python3 /Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/build/plugins/skill-craft/skills/shiploop/scripts/shiploop ref <file>#<anchor>):
- REF/improve-context.md#default-route-the-parent-runs-improve-delegation-inline - the inline Improve route; read before start or recovery
- REF/improve-context.md#parent-acceptance-and-recovery - when a child stops, is lost or a restart is considered
- REF/project-knowledge.md#maintained-product-requirements - how accepted requirements are kept; open when reconciling R-ids
- REF/project-knowledge.md#reference-handoffs-and-destinations - which locators go into the opening and the review notes
- REF/requirements-definition.md#reconcile-current-context-with-existing-intent - existing-spec reconciliation
- REF/requirements-definition.md#define-non-functional-requirements - when an NFR lacks a measurable target
- REF/requirements-definition.md#state-and-data-change-assessment - state and data criteria (identity, transitions, workload, recovery)
- REF/behavioral-requirements.md#actors-channels-and-state-ownership - interaction review (actors, channels, events, connection lifecycle)
- REF/behavioral-requirements.md#ui-specific-planning - UI decisions a spec settles at planning depth
- REF/behavioral-requirements.md#traceability-and-review - tie each criterion to the check that confirms it
- REF/testing-and-documentation.md#stage-readiness-and-completion - what a planning stage must have ready
- REF/backchain-planning.md#source-aware-native-caller - only when a dependency diagnostic is needed
- REF/navigator.md#recover-one-existing-run - cold recovery of this run
Other references (not needed for this review unless a finding leads there): research-loop, delivery-authority, environment-lifecycle, execution-planning (initial repository baseline), current-system-baseline, service-discovery, repeatable-test-suites, workspace-lifecycle, planning-experiments, testing-and-documentation (browser checks, test cases, surface selection), behavioral-requirements#behavior-model.

Run state:
Where: Preparation > spec (4 of 7, Improve review) | intake ✓ discovery ✓ research ✓ spec ▶ test-strategy · plan · prepare · | Work items: W1 queued (provisional until prepare) | Release ·
Next: Improve review of the spec result, then test-strategy.
Last accepted: research done (nav-9ca690c0336049d98bcc557347c093e0): no external unknowns; build new with the Node standard library only.
Owner: root navigator. Product work happens only in WT (an isolated worktree, not the original checkout); run state, results and reports stay in RUN. The workspace return is unavailable until release.

Recovery:
- Recovery command (reads the saved state only): python3 /Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/build/plugins/skill-craft/skills/shiploop/scripts/shiploop next --run-dir=/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/run
  If paused or blocked, resolve the condition and follow the printed resume route; if halted or done, stop. After an interruption, check the paths and repository identity, run the recovery command and reconcile actual effects from history and evidence before repeating work. If this run cannot be found, stay incomplete: never initialize a replacement or invent a callback. Keep these locators and the recovery command in any handoff.
- Child already started (CHILD/packet.json exists): status active, run its exact next_argv once and follow the returned instruction; status complete, run improve-complete without reviewing again; status stopped, keep the parent incomplete.
- To continue after a stop that cannot be reconciled, once its blocker is resolved or the user authorizes continuing: confirm no candidate write is in progress, record the decision in CHILD/opening.md, then run: python3 /Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/build/plugins/skill-craft/skills/shiploop/scripts/shiploop improve-start --run-dir=/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/run --action=nav-284162de5e054d7b80ce269d024dbd0f --opening=/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/worktree/.shiploop-improve/nav-a5a3303c2aa54837aa1bab5c53a0ada7/nav-284162de5e054d7b80ce269d024dbd0f/opening.md --restart-stopped
  ShipLoop archives packet.json and reviews/ under a timestamp (do not rename them yourself); the new child writes its own review-<n>.md and checks.md.
- An active child whose receipt or temporary runtime state is unavailable: report incomplete; never infer completion or create a replacement. Completion deletes the runtime state, so the terminal packet in CHILD/packet.json is the only completion evidence: preserve it; if it is lost, stop incomplete.
- If incomplete, keep the child, its receipt and review notes; never call complete on the producer again or advance the graph.
- Pause the parent without losing the child (leave the child active; never report a pause as cancelled): python3 /Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/build/plugins/skill-craft/skills/shiploop/scripts/shiploop pause --run-dir=/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/run --reason=reason
- Keepalive marker: SHIPLOOP-RUN run=nav-a5a3303c2aa54837aa1bab5c53a0ada7 rev=5 dir=/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/run

Roots: RUN=/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/run | WT=/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/.shiploop-runs/work-20261010-181600-737311/worktree | SK=/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/build/plugins/skill-craft/skills/shiploop (CLI SK/scripts/shiploop, card SK/SKILL.md, state RUN/state.md) | REF=SK/references | IMP=/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/build/plugins/skill-craft/skills/improve | CHILD=WT/.shiploop-improve/nav-a5a3303c2aa54837aa1bab5c53a0ada7/nav-284162de5e054d7b80ce269d024dbd0f
````

## 2. Size

| File | Bytes (wc -c) | Lines |
|---|---|---|
| current `nav-284162de...-improve.md` | 48,101 | 400 |
| proposed `spec-Improve-parent.packet.txt` | 23,864 | 125 |

Saving 24,237 bytes (50%). The first screen (lines 1-43: stage, Next command, Goal, Done-when, review focus, Checked by, the Do list with all three Improve commands, the opening template and the final_result shape) is about 9.5 KB. Absolute paths: 13 lines carry one (commands, keepalive marker, Roots, and the evidence_refs inside the result record). The plan's target for Improve parents was about 25 KB.

## 3. Obligation map

Line numbers are those of the current packet. Dispositions: kept (where), shortened, reference (symbol), gated (condition), dropped (reason), added.

| # | Current text | Disposition | Where / reason | Flag |
|---|---|---|---|---|
| 1 | L1 `ShipLoop navigator \| spec \| revision 5` | kept | stage line, now also says Improve review and that the parent stays pending |  |
| 2 | L2 `Next command (start the bound Improve child after writing its opening file ...)` | kept | line 2, literal absolute command; opening path no longer repeated in the label (Do 2 names it) |  |
| 3 | L3 `The opening file holds exactly these headings ... (a renamed or empty section is refused)` | kept | Checked by (improve-start bullet) + Opening template |  |
| 4 | L4 `Reviewing the returned spec result. Goal: ...` | shortened | Goal line now starts with `Goal:` so the observed `sed '/^Goal/'` slice matches (frame report item 5) |  |
| 5 | L5-9 Done-when header + 4 bullets, `correct the result, never the condition` | kept | verbatim, first screen |  |
| 6 | L10 `Run context index ... context-index.md` | kept | Reads, as RUN/context-index.md |  |
| 7 | L11 pass log `run/notes/<action>.md` (optional, never a gate) | dropped | names a file nobody creates (plan §10.5; 0 pass-log files in 4 runs; run/notes/ is empty here) |  |
| 8 | L12-15 `Results this stage builds on` intake/discovery/research | kept | Reads, RUN/results/<id>.md |  |
| 9 | L17-18 `Progress snapshot (status context...)`, host labels untrusted | dropped | duplicate inside the packet of the status block (plan §10.2) |  |
| 10 | L19-29 snapshot body: phase, current, counts, queued W1, completed/pending stages | dropped | duplicate of the status block, which is kept once in Run state |  |
| 11 | L21 `Owner: root navigator.` (also L147) | kept | Run state, once |  |
| 12 | L22 `Continuation: follow only the current action packet.` | dropped | duplicate of Do 7 / Keep going rule |  |
| 13 | L29 `Skill validation: conditional for future work items.` | dropped | irrelevant to the spec Improve review |  |
| 14 | L30 `Improve: actual skill owns the current child...` | shortened | Do 1 `The Improve skill owns every review iteration` |  |
| 15 | L32-38 `=== ShipLoop status ===` block | shortened | Run state, two lines (Where with stages, Next) |  |
| 16 | L40-59 narrative + `Show the user this narrative exactly as written` | gated | print only when its content differs from the last printed narrative; here identical to the improve-bind packet's narrative (same Achieved/Now) | UNSURE: needs a narrative-changed fact; if the user did not see the bind packet (new session) they miss one update |
| 17 | L61 `do not reprint this packet's ShipLoop status block` | kept | Rules: Progress |  |
| 18 | L62-65 one line to the user at start/recovery/after callback; full block only on request | shortened | Rules: Progress |  |
| 19 | L65-67 narrative first-line rule (paste or host showed it) | gated | travels with the narrative block (prints only when the narrative prints) |  |
| 20 | L67 `Only the current owner reports overall progress.` | gated | matters only on the delegated route (ask-agent workers); inline the parent is the only reporter |  |
| 21 | L67-69 state labels are not evidence; describe Improve only from its records; no count/percent/ETA | shortened | Rules: Progress |  |
| 22 | L70-73 run to completion; emit progress then continue; do not wait for acknowledgement | shortened | Rules: Keep going |  |
| 23 | L73-75 follow the exact callback incl. bound Improve child; child completion is not run completion | kept | Do 7 `runtime completion alone never advances this action` + Keep going |  |
| 24 | L76-80 user stop/pause/`do not implement` = stop: pause, answer, resume on continue; question is not a stop | kept | Rules: Keep going |  |
| 25 | L80-82 do not pause on your own to ask whether the run is worth it | shortened | Rules: Keep going (`run to completion within scope ... ask only for an actually missing decision`) |  |
| 26 | L82-86 never end the turn while a ShipLoop command runs; foreground; headless host loses callback | shortened | Rules: Keep going (the headless-host explanation moves to REF/keepalive.md) |  |
| 27 | L86-88 keepalive refusal names the next command: run it | kept | Rules: Keep going |  |
| 28 | L88-89 resolve recoverable conditions via printed route; ask only for missing decision/authority/access | kept | Rules: Keep going |  |
| 29 | L91 `State:` run/state.md | kept | Roots line (state RUN/state.md) |  |
| 30 | L92 `Result records:` run/results | shortened | implied by RUN/results/<id> lines in Reads |  |
| 31 | L93 `Result inbox:` run/inbox | shortened | the two inbox files are named in Do 6/7 |  |
| 32 | L94 `Accepted history: state.md (history)` | dropped | duplicate inside the packet: same file as State |  |
| 33 | L95 `Repository locator` worktree | kept | Roots WT |  |
| 34 | L96 `CLI locator` | kept | Roots (SK/scripts/shiploop) and every literal command |  |
| 35 | L97 `ShipLoop skill card` SKILL.md | kept | Roots (SK/SKILL.md) |  |
| 36 | L98 `Run directory locator` | kept | Roots RUN |  |
| 37 | L99 `Scratch directory ... /tmp is shared` | kept | Rules: Temporary files (RUN/scratch) |  |
| 38 | L100 `Keepalive marker: SHIPLOOP-RUN run=... rev=5 dir=...` | kept | Recovery, literal (hook token) |  |
| 39 | L101 Access-readiness policy research-loop.md#early-access-readiness | reference | Other references: research-loop (research said no access needs) |  |
| 40 | L102 Delivery-authority policy | reference | Other references: delivery-authority (no delivery decision at spec) |  |
| 41 | L103 Environment lifecycle policy | reference | Other references: environment-lifecycle |  |
| 42 | L104 Environment lifecycle note (host-authored, if present) | gated | print only when the file exists; run/notes/ is empty |  |
| 43 | L105 Cross-run knowledge policy project-knowledge.md | reference | REF/project-knowledge.md#maintained-product-requirements and #reference-handoffs-and-destinations |  |
| 44 | L106 Maintained requirements policy | reference | REF/project-knowledge.md#maintained-product-requirements + obligation line Rules: Requirements |  |
| 45 | L107 Requirements definition guide | reference | REF/requirements-definition.md#reconcile-current-context-with-existing-intent, #define-non-functional-requirements |  |
| 46 | L108 Stage readiness and completion guide | reference | REF/testing-and-documentation.md#stage-readiness-and-completion |  |
| 47 | L109 Initial repository baseline guide | reference | Other references: execution-planning (initial repository baseline); greenfield repo |  |
| 48 | L110 Reference handoff policy | reference | REF/project-knowledge.md#reference-handoffs-and-destinations + Rules: Cold-context inputs |  |
| 49 | L111 Repository knowledge index SHIPLOOP.md (if present) | gated | print only when WT/SHIPLOOP.md exists; it does not |  |
| 50 | L112 Consumer testing guide (browser checks) | reference | Other references: testing-and-documentation (browser checks); a test-strategy concern |  |
| 51 | L113 Repeatable test-suite guide | reference | Other references: repeatable-test-suites |  |
| 52 | L114 Selected-case reconciliation guide | reference | Other references: testing-and-documentation (test cases) |  |
| 53 | L115 Real-boundary selection guide | reference | Other references: testing-and-documentation (surface selection) |  |
| 54 | L116 Interaction design guide | reference | REF/behavioral-requirements.md#actors-channels-and-state-ownership and #ui-specific-planning |  |
| 55 | L117 Worktree and artifact policy | reference | Other references: workspace-lifecycle |  |
| 56 | L118-119 Recovery command `shiploop next --run-dir=...` | kept | Recovery, literal |  |
| 57 | L120 retain locators and recovery command in handoff material | kept | Recovery bullet 1, last sentence |  |
| 58 | L121 after interruption: check paths/identity, run recovery, reconcile effects; never a replacement or invented callback | kept | Recovery bullet 1 |  |
| 59 | L122 recovery only reads state; paused/blocked resume route; halted/done stop | kept | Recovery bullet 1 |  |
| 60 | L123 execute in this conversation; submit callback yourself; delegated subtasks do not advance | kept | Delegation line |  |
| 61 | L124-128 Original request BEGIN/END block and marker rule | kept | Reads, verbatim (spec is a planning stage; the opening needs the request) |  |
| 62 | L129 Service discovery guidance #verification | reference | Other references: service-discovery |  |
| 63 | L130 Current-system baseline guide #planning-and-review-handoff | reference | Other references: current-system-baseline (greenfield) |  |
| 64 | L131 Behavior-model guidance | reference | Other references: behavioral-requirements#behavior-model |  |
| 65 | L132 Behavior traceability guidance | reference | REF/behavioral-requirements.md#traceability-and-review |  |
| 66 | L133 State and data assessment | reference | REF/requirements-definition.md#state-and-data-change-assessment + Rules: Interaction and state |  |
| 67 | L134 Execution checkout (isolated worktree; never a --result value) | shortened | Run state (`Product work happens only in WT`); `never a --result value` dropped: no --result in this packet |  |
| 68 | L135 Workspace authority and original branch workspace.md | gated | workspace block prints at release-plan..handoff or when blocked/paused (plan §4) |  |
| 69 | L136-137 Return plan, Return receipt paths | gated | same workspace gate |  |
| 70 | L138-139 current workspace return not verified; historical host reports | gated | same workspace gate |  |
| 71 | L140 all product work in execution checkout; run state outside; inner integrate assembles here; read policy before return | shortened | Run state: first two clauses; integrate and return clauses irrelevant to spec |  |
| 72 | L141-143 plan-return and review-return commands, --keep/--exclude rules | gated | same workspace gate |  |
| 73 | L144 return route (clean main, fast-forward, kept files) | gated | same workspace gate |  |
| 74 | L145 handoff needs script-verified receipt; no automatic push/cleanup/publication | gated | handoff only; `no push` survives in Rules: Commits |  |
| 75 | L146 return operation unavailable here | kept | Run state, one line |  |
| 76 | L148 Backchain planning guide backchain-planning.md#navigator-planning | reference | REF/backchain-planning.md#source-aware-native-caller (the section an Improve diagnostic needs) | UNSURE: anchor changed from #navigator-planning; #navigator-planning is the producer's section |
| 77 | L149 Backchain audit resource caller-contract.md (review/audit) | shortened | Rules: Backchain, SK/../backchain/references/caller-contract.md |  |
| 78 | L150 Planning phase intent | kept | Goal line |  |
| 79 | L151-152 `Current planning sources` header; host reports untrusted | shortened | Reads header (`accepted`); untrusted wording kept on the step result |  |
| 80 | L153-155 intake/discovery/research planning sources with state.md accepted.<id> | dropped | duplicate inside the packet of L12-15 |  |
| 81 | L156-158 spec/test-strategy/plan: no current accepted result; do not reuse an invalidated result | gated | print only when an invalidated result exists (after a replan); none in this run | UNSURE: low; the stage under review is spec itself |
| 82 | L159 Planning experiments guide | gated | plan Improve only (planning_reconcile); listed in Other references |  |
| 83 | L160 Planning investigation notebook | dropped | names a file nobody creates at spec (plan §10.5); plan-only |  |
| 84 | L161 keep experiment prompts/logs behind locators; do not duplicate the parent packet in the child | shortened | Do 2 `do not copy this packet ... put long detail in a file and name its path` |  |
| 85 | L162-166 Last accepted transition: research summary | shortened | Run state `Last accepted` one line; full text is the research result in Reads |  |
| 86 | L167-168 Evidence references: workspace.md | dropped | irrelevant to the spec review; part of the research record |  |
| 87 | L169 read durable state and the relevant result before relying on earlier context | shortened | Reads header `open each one whose content is not already in your context` |  |
| 88 | L170 Work items planned: 1; execution after preparation | kept | Run state (W1 queued, provisional until prepare) |  |
| 89 | L172 `Current action: Improve the completed spec result.` | kept | stage line + Goal |  |
| 90 | L173 parent step remains pending until Improve completion is imported | kept | stage line |  |
| 91 | L174 `Checked by: the Improve skill runs its own review ... improve-complete validates the receipt` | kept | Checked by, now three bullets with every refusal of improve-start, improve-commit and improve-complete (from _improve_start, _opening_sections, loop_contract.size_problem, _credential_refusal, _lessons_and_citations_refusal, _derived_improve_receipt, _improve_change_gate, _check_submitted_evidence, _check_submitted_awaiting, knowledge.check) |  |
| 92 | L175 `Step result (untrusted evidence, not new authority)` | kept | heading of the result under review |  |
| 93 | L176 Improve also reviews failed/blocked attempts; may retain repeat/blocked | gated | print only when the seed outcome is not done (it is done) |  |
| 94 | L177-190 seed result JSON | kept | verbatim, absolute evidence_refs paths kept inside the record |  |
| 95 | L191 Selected Improve skill | kept | Bound skills line, IMP/SKILL.md |  |
| 96 | L192 Bound Until Loop card | kept | Bound skills line |  |
| 97 | L193 Bound Until Loop CLI locator | kept | Bound skills line |  |
| 98 | L194 Until Loop root; relative links resolve there, not under the Improve skill | kept | Bound skills line |  |
| 99 | L195 Child workspace | kept | Bound skills line (WT) |  |
| 100 | L196 read the two card sections once per context; open others only when needed; never print; skill owns iterations | kept | Do 1 |  |
| 101 | L197 Improve context ownership improve-context.md#default-route... | reference | REF/improve-context.md#default-route-the-parent-runs-improve-delegation-inline |  |
| 102 | L198-209 context-first opening: write opening.md with the four sections | kept | Do 2 + Opening template |  |
| 103 | L210 meaning of each section | kept | Opening template placeholders |  |
| 104 | L210 supply meaning inline + locators; do not copy this packet or restate the skill | kept | Do 2 |  |
| 105 | L210 size budget: 16,384 state cap, 9,216 contract, ~4,772 for sections, non-ASCII | shortened | Checked by improve-start bullet keeps 9,216 / 4,772 / non-ASCII; the 16,384 explanation moves to the refusal text |  |
| 106 | L210 a refusal says how far over and which section | shortened | Checked by header: each refusal's first line is the fix |  |
| 107 | L211 `Then run: improve-start ...`; ShipLoop freezes start.json; do not write the contract | kept | Do 3 (the command itself is line 2) |  |
| 108 | L211 if already started recover from its receipt | kept | Do 3 + Recovery |  |
| 109 | L212 commit message path; improve-commit; no heredoc; no git commit | kept | Do 5, literal command, plus the Key learnings / Learned-from / Remote change rules from the current engine (start_lines in _render_improve) |  |
| 110 | (engine, not in this file) `Key learnings:` line required; `Learned-from:` optional; `Remote change:` + --remote-change; no-change pass makes no commit | kept | Do 5 and Checked by; the deployed build that printed this packet predates them |  |
| 111 | L213 Delegation inline paragraph (cwd/Git root, no agents, only writer) | kept | Delegation line below the Do list |  |
| 112 | L213 read that reference's default-route section before start or recovery | reference | gist on REF/improve-context.md#default-route-... (`read before start or recovery`) |  |
| 113 | L214 carry approvals/declines; later user decision from next iteration | kept | Rules: Authority + Opening template Authority |  |
| 114 | L215 return order: only after terminal packet; runtime completion never advances | kept | Do 7 |  |
| 115 | L216 child runtime authority is the temporary state_file; ShipLoop does not write it | shortened | Recovery bullet (temporary runtime state) |  |
| 116 | L217 Child latest packet receipt path | kept | CHILD/packet.json in Do 3, Rules: Receipt |  |
| 117 | L218 runtime writes every packet; never edit the receipt; start before any review work | kept | Rules: Receipt; order in Do 3-4 |  |
| 118 | L219 recovery by receipt status (active/complete/stopped) | kept | Recovery |  |
| 119 | L219 restart a stopped child: confirm no write, record decision, rerun with --restart-stopped; archive names; do not rename | kept | Recovery, now a literal command |  |
| 120 | L219 pause instead; never report cancelled | kept | Recovery pause bullet |  |
| 121 | L219 unavailable receipt/state: report incomplete; terminal recovery uses retained packet | kept | Recovery |  |
| 122 | L220 put request, step result, paths, check state, authority, environment in the opening; ShipLoop freezes the rest incl. parent-return.md | kept | Opening template + Do 3 |  |
| 123 | L221 commit policy: Improve card's scoped-commit policy with overrides; frozen on recovery | kept | Rules: Commits |  |
| 124 | L222 completion deletes child state; preserve terminal packet; lost output = incomplete | kept | Recovery |  |
| 125 | L223-239 Planning review focus (6 bullets + trivial-pass rule) | kept | verbatim, first screen |  |
| 126 | L240 `This producer attempt has returned a result; its parent action now awaits Improve.` | dropped | duplicate inside the packet of the stage line and L173 |  |
| 127 | L241 invoke Improve for behavior, acceptance, NFR, reconciliation, failure boundaries, consumer outcomes | kept | Goal `Review scope:` |  |
| 128 | L241-246 read card, follow runtime, use parent-provided scope/lessons/check state; card supplies loop; stage requirements qualify | shortened | Do 1 + Opening template |  |
| 129 | L247-250 freeze staged/unstaged/untracked paths; empty initial commit; Git history is context | kept | Opening template, Scope |  |
| 130 | L252-256 non-mutating identity probes; never read credential-store contents | kept | Rules: Credentials |  |
| 131 | L258-267 maintained requirements: preserve, subclauses, supersession, no silent redefinition, gaps visible, Ready/Done of current stage | shortened | Rules: Requirements + reference |  |
| 132 | L268-272 reference handoff: carry selected requirement/test/run-note locators into the child before the first review | shortened | Rules: Cold-context inputs + REF/project-knowledge.md#reference-handoffs-and-destinations |  |
| 133 | L273-274 Requirements definition guide for quality criteria | reference | REF/requirements-definition.md#define-non-functional-requirements |  |
| 134 | L275-277 Initial repository baseline guide when relevant | reference | Other references: execution-planning |  |
| 135 | L283-286 Backchain planning guide; only route `source-aware-native` | shortened | Rules: Backchain |  |
| 136 | L288-294 Improve is broader than Backchain; no active_backchain child, nested loop, retry dispatcher, new callback; one-pass primitive; Backchain child plan-only | shortened | Rules: Backchain (`plan-only` dropped: the rule forbids a Backchain child here) |  |
| 137 | L295 protected or out-of-scope change follows the blocked or recovery route | kept | Rules: Exclude line |  |
| 138 | L300-305 State and data assessment review; Initial-plan reconciliation at plan | shortened | Rules: Interaction and state + reference; the plan-only clause dropped (irrelevant to spec) |  |
| 139 | L314-329 Interaction design paragraph (actors, channels, UI planning ownership, reuse) | shortened | Rules: Interaction and state + two references; would be gated on `surfaces`, which holds here (HTTP API, in-memory state, browser page) |  |
| 140 | L331-334 current-system recovery paragraph | gated | print only when discovery recorded an existing system; discovery found an empty repo | UNSURE: needs a discovery fact the script does not record yet |
| 141 | L336-341 cold-context inputs: reopen/revalidate relevant sources; compact locator/decision/rationale in notes | shortened | Rules: Cold-context inputs |  |
| 142 | L343-352 planning reference material; register files in evidence_refs; keep earlier refs in final_result; URLs; local docs absolute | shortened | Rules: Evidence + final_result shape |  |
| 143 | L354-362 repository-local skill paragraph | gated | print only when the candidate selects, uses or changes a repository-local skill (none here) |  |
| 144 | L364-380 test plans/suites paragraph (assertions, lifecycle, remote-resident, facilities) | gated | print only at stages whose candidate holds tests or test plans (test-strategy onward) or a remote target | UNSURE: spec criteria say how each is confirmed; a reviewer may still want the suite guide (listed in Other references) |
| 145 | L382-384 follow the card's review/commit/completion policies; parent owns acceptance, callbacks, return | shortened | Rules: Commits + Do 7 |  |
| 146 | L385-387 RED-stage and release/verification handoff clauses | dropped | irrelevant to the spec stage |  |
| 147 | L389 exclude .until-loop, .shiploop-improve, runtime metadata | kept | Rules: Exclude |  |
| 148 | L390 prior result and accepted Improve lessons in state.md improve_results | gated | print only when improve_results is non-empty; this is the run's first Improve | UNSURE: low |
| 149 | L391 two trivial passes are self-passes; one-pass completion on unchanged Git | kept | Rules: Review passes |  |
| 150 | L392 change what is warranted and commit; import refused while uncommitted; --no-commit | kept | Do 4, Checked by, Do 7 |  |
| 151 | L393 review-<n>.md and checks.md; imports last two (one if first unchanged); nothing else to list | kept | Do 4 + Checked by |  |
| 152 | L393 a plan/RED disposition is checked against its own criteria | shortened | Rules: Requirements (`a planning review does not require future product checks to pass`) |  |
| 153 | L394 optional --notes lessons file | kept | Do 7 |  |
| 154 | L395 temporary files incl. runtime stdin reports in scratch; /tmp shared | kept | Rules: Temporary files |  |
| 155 | L396 final_result: when, same fields, outcomes (never reconcile), omit when unchanged, preserve evidence_refs, decision note, path, --final-result | shortened | Do 6 + final_result shape + Do 7 |  |
| 156 | L396 `with outcome done at plan or carry-forward, list the complete intended queue in work_items` | dropped | irrelevant to spec (plan and carry-forward only) |  |
| 157 | L396 do not register all scratch output or copy the whole notebook; step definition remains the execution prompt | shortened | Rules: Evidence |  |
| 158 | L397-398 parent callback improve-complete (run only after the runtime returned complete) | kept | Do 7, literal |  |
| 159 | L399 if incomplete keep child/receipt/notes; never call complete on the producer again | kept | Recovery |  |
| 160 | L400 Pause parent without losing child | kept | Recovery, literal |  |
| 161 | (new) Producer packet path | added | line after the step result: RUN/packets/nav-284162de5e054d7b80ce269d024dbd0f.md |  |
| 162 | (new) knowledge-home lines for spec (keeps spec.md and feature spec.md; refuses prepare if missing; keep every R-id; Retired heading) | added | Rules: Living spec; the producer packet has them, the current Improve packet does not |  |
| 163 | (new) Roots line and the `shiploop ref` verb | added | Roots (last line) + References header; line 3 points to the Roots line |  |

Counts: kept 72, shortened 33, reference 25, gated 18, dropped 12, added 3; total 163 rows; 6 flagged.

## 4. Risks after a context clear

| # | What a model holding only this packet could get wrong | Why it should not, or what to probe |
|---|---|---|
| 1 | Writes the opening to a literal `CHILD/opening.md` relative to its cwd (roots unexpanded in a file-tool call). | Line 2 prints the absolute opening path inside the Next command and line 3 says the roots expand from the last line. If it still happens, improve-start refuses with "write the opening file first: <absolute path>", which self-corrects. **Probe** on Sonnet and Grok: clear context at this packet and count tool calls with a literal `CHILD/` or `RUN/` argument (plan §6 Phase 3 gate). |
| 2 | Copies the step result into final_result with `WT/...` evidence_refs. `_check_submitted_evidence` checks only paths that start with `/`, so a relative ref would pass silently and point nowhere. | The record keeps absolute paths and the final_result shape says "as an absolute path". Engine hardening worth adding: refuse an evidence_ref that starts with a root token (`RUN/`, `WT/`, `SK/`, `REF/`, `IMP/`, `CHILD/`). |
| 3 | Thinks the R-id rule is enforced at improve-complete and drops an ID through a committed review edit. `knowledge.check` compares HEAD with the working tree, so after improve-commit commits the drop, nothing refuses it until a later stage changes the home. | The proposal words the gate accurately ("while docs/shiploop differs from HEAD") and keeps the rule as an obligation (Rules: Living spec and review focus bullet 4). **Engine gap, independent of compaction:** run the R-id comparison in improve-commit against the spec at the review's bind snapshot. |
| 4 | Misses the narrative because it is gated. | The narrative content is identical to the improve-bind packet printed one call earlier. Harm is one missed progress message, never wrong work. Probe a resume from a new session at this packet. |
| 5 | Reviews the spec without the test-suite, current-system, skill or prior-lessons paragraphs. | Each depends on a fact that does not hold here: no tests are authored at spec, the repo was empty, no skill is involved and this is the run's first Improve. The suite and baseline guides stay one `ref` away (Other references). If a finding leads there, the review-focus bullet about commands that do not run what they claim still applies. |
| 6 | Starts a second child after a clear because it does not notice the receipt. | Do 3 and Recovery both say that if CHILD/packet.json exists the child has started. improve-start also refuses a second start. |
| 7 | Runs `complete` instead of `improve-complete`. | Do 7 says "never 'complete'", and Recovery repeats "never call complete on the producer again". Once the receipt exists, `_first_callback_lines` prints the improve-complete line at the top. |
| 8 | The `ref` verb does not exist yet. | The reference lines are still resolvable paths (`REF/<file>.md` plus a heading anchor). A model without the verb opens the file at that heading. All 13 anchors were checked against the headings in the packet's references directory, and the two card sections against IMP/SKILL.md and ADAPTER.md. |
| 9 | Over-reads: opens the producer packet whole after every clear (38-42 KB). | The line says what the producer packet adds (full duty, considerations, template). Nothing in Done-when or Checked by depends on it. Probe: count producer-packet reads in a resumed Improve. |
| 10 | Treats the Backchain line as an invitation to run one. | It is worded as a restriction (one-pass primitive only, "for a dependency diagnostic"). backchain-check ran 0 times in the three newest runs. |

## 5. Engine changes needed (symbols only)

- `shiploop_navigator._render_improve`: emit sections in the plan §2 order (stage, Next command, Goal, Done-when, review focus, Checked by, Do, opening template, final_result shape, step result, producer-packet line, bound skills, delegation, rules, reads, references, run state, recovery, roots). Stop inheriting `render()`'s shared frame for Improve parents: the locator table, progress snapshot, workspace block, planning sources, last-accepted block and policy reading list.
- `shiploop_navigator._goal_lines` (Improve branch): start the line with `Goal:`; add `guidance.IMPROVE_SCOPES[stage]` and the planning phase intent.
- New `shiploop_navigator._improve_checked_lines`: generated from one table of the refusals in `_improve_start`, `_opening_sections`, `loop_contract.size_problem`, `_credential_refusal`, `_lessons_and_citations_refusal`, `_derived_improve_receipt`, `_improve_change_gate`, `_check_submitted_evidence`, `_check_submitted_awaiting`, `_knowledge_gate` and `_stage_gates(child stage)`. It replaces the free-text "Checked by" in `_render_improve`.
- One constant for the improve-commit message rules, shared by `_render_improve` (`start_lines`) and the `parent-return.md` writer in `_improve_start` (S-12).
- `shiploop_prompts.improve_prompt` / `_improve_prompt`: return one-line rules. Gate the interaction paragraph on the new `surfaces` fact, the repository-local skill paragraph on a skill-selection fact, the test-suite, `TEST_FACILITY_HANDOFF` and remote-resident text on test stages or a remote target, the current-system paragraph on a discovery baseline fact, and the RED and release clauses by stage. `PLANNING_REVIEW_FOCUS` stays unchanged.
- `shiploop_prompts.PROGRESS_REPORTING`: a short packet form (the Progress and Keep going rules).
- `shiploop_knowledge_home.stage_lines`: print the spec lines (keeps, refuses prepare, living-spec rule) in the Improve parent too, relative to WT.
- New `_roots_line` and `_reference_lines(row.refs)` in the packet renderer. Stage-spec rows for Improve parents gain `refs` and `blocks` (`shiploop_stage_spec`).
- New CLI verb `ref` in `shiploop_protocol` (parser) plus a section resolver (heading-slug match, bounded output, a "no such anchor" message).
- Gates in `_render_improve`: the prior-lessons line when `state["improve_results"]` is non-empty; the "also reviews failed/blocked" line when the seed outcome is not done; the planning-sources "no current accepted result" lines when an invalidated result exists; the existence-gated locator lines (environment-lifecycle note, `SHIPLOOP.md`).
- `shiploop_narrative` / `status_block` caller: a narrative-changed check, so a narrative identical to the last printed one is not printed again.
- Optional hardening (risks 2 and 3): `_check_submitted_evidence` refuses root-token refs; `_improve_commit` runs the R-id comparison against the bind snapshot.

## Independent check

Checked against engine worktree pc1i-64ba2b (`_improve_start`, `improve_start_contract`, `_opening_sections`, `_improve_commit`, `_lessons_and_citations_refusal`, the improve-complete branch of `dispatch`, `_derived_improve_receipt`, `_improve_change_gate`, `finish_improve`, `standalone._complete_ephemeral`/`_ephemeral_terminal_packet`, `knowledge_home.check`/`CLOSES`), the deployed build's references and cards, and SPEC S-6.

**(1) Lost obligations / gate coverage**
- should-fix: the improve-complete "Checked by" bullet omits refusals that do fire at spec: `_ephemeral_terminal_packet` ("Until Loop terminal packet is not complete", two-review minimum, "bound to another workspace", "still exposes a callback"), `_reject_credentials(record, "Improve final result")`, and `_canonical_result(final_result, stage="spec")` shape errors via `finish_improve`. Do 7 still orders "only after the terminal packet", so behaviour is covered; the list is just not complete as claimed.
- fine: `_check_submitted_assumptions` (plan only), `_check_submitted_test_commands`/`_skill_na` (step-plan), `_consumer_entry`/`_recorded_commands` (release-plan/system-test-author) do not apply at spec; dropping them is correct. `_stage_gates` is not called by improve-complete.
- fine: improve-commit's `--remote-change` without a "Remote change:" line and the "no bind snapshot" refusal are not listed; both are rare and self-describing.
- fine: no Done-when, output file (opening.md, review-<n>.md, checks.md, commit-message.md, inbox final-result/notes), or required command (improve-start, improve-commit, improve-complete, next, pause, --restart-stopped) was lost; each is printed literally.

**(2) REF anchors** - fine: all 13 cited anchors plus `behavioral-requirements#behavior-model` and `backchain-planning#navigator-planning` resolve (heading slugs) in both the deployed build and the worktree; IMP/SKILL.md "## ShipLoop whole-skill subcall" (l.90), ADAPTER.md "## Follow the returned action" (l.92), `SK/../backchain/references/caller-contract.md`, `until_loop_ephemeral.py`, and the producer packet RUN/packets/nav-284162de....md all exist.

**(3) False claims against code**
- should-fix: References header tells the model to run `shiploop ref <file>#<anchor>`; no `ref` verb exists in `shiploop_protocol` (PACKET_VERBS/parser). Print that header only once the verb ships (§5); until then say "open REF/<file> at that heading".
- should-fix: Rules: Commits says ShipLoop "reruns the affected checks". `_improve_commit` reruns nothing, and `_improve_change_gate` reruns commands only for `carry-forward`. Inherited from the current packet (L392), but false at spec. Drop it, or say "only at carry-forward".
- should-fix: Opening template bodies are `<...>` prose placeholders. `_opening_sections` refuses only empty or literal `...`, so a template copied verbatim passes improve-start and freezes placeholder text into the contract. The Checked-by text ("left as '...'") no longer matches the template. Keep `...` bodies with the descriptions on a separate line, or make the engine refuse `<`-wrapped placeholder text.
- should-fix (minor): the Delegation line now reads "Start no reviewer, test-runner or executor agent, Ask Agent or extra worktree unless the user asked for independent review". The current L213 forbids handing the invocation to Ask Agent, a native worker or an extra worktree unconditionally, so the qualifier loosens that. Split it into two sentences.
- fine: "exactly the four headings" slightly overstates `_opening_sections`: other `##` headings fold into the preceding section, and a repeated heading is refused. The knowledge-gate wording ("while docs/shiploop differs from HEAD") is accurate because spec is not in `CLOSES`. "refuses prepare if either file is missing" matches `CLOSES["prepare"]`.

**(4) Cold-context executability (S-6)** - fine: a model holding only this packet knows its position (stage line, Run state), the next command (line 2, absolute), Done-when, its outputs (Do 2-6), the checks (Checked by), and how to recover (Recovery with literal next/pause/--restart-stopped and receipt-status branches). Root tokens are explained on line 3 and expanded on the last line. The residual risks are the proposal's own §4 items 1-3 (relative evidence_refs, R-id drop after improve-commit), which are engine hardening and independent of compaction.

Verdict: safe with the listed fixes (no blockers).
