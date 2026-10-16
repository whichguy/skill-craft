# Lessons A: mechanisms from 3 prompt-collection repos (read 2026-10-11)

Stars verified live via `gh api repos/<r>` (same as the github.com repo page, which WebFetch also showed).
Paths are relative to each repo root. Files were downloaded from raw.githubusercontent.com and read.

Caveat applied throughout: these are vendor prompts. Vendors usually pair a prompt rule with harness enforcement
(tool schemas, permission UI, tool filtering). The prompt alone is the weaker half of each mechanism.

---------------------------------------------------------------------
## 1. x1xhlol/system-prompts-and-models-of-ai-tools  (143,952 stars; 34.8k forks)
Large archive of vendor prompts + tool JSON: Cursor, Windsurf, Devin, Kiro, Warp, Amp, Claude Code, VSCode Agent, Lovable, v0 ...
Read in full or in substance: Cursor Prompts/Agent Prompt 2.0.txt, Windsurf/Prompt Wave 11.txt, Devin AI/Prompt.txt,
Kiro/Spec_Prompt.txt, Anthropic/Claude Code 2.0.txt, Warp.dev/Prompt.txt.

1. Persistence plus a narrow stop list.
   - What: autonomy is stated positively ("keep working until the query is resolved") and the stop conditions are enumerated.
   - Where: Cursor `Agent Prompt 2.0.txt` <tool_calling> item 5 ("If you make a plan, immediately follow it"; stop only for missing info or options to weigh);
     Windsurf `Prompt Wave 11.txt` <tool_calling> ("keep working ... until the user's query is completely resolved").
   - Why it works: models default to ending a turn early. Naming the only legal reasons to stop removes the ambiguity.
   - SDLC use: every action packet carries an explicit "you may stop only if: (a) completion call submitted, (b) blocked with X recorded". The script rejects any other exit.

2. Bounded retry loops with a forced hand-off.
   - What: a fix loop has a numeric cap, then the agent must stop and ask.
   - Where: Cursor 2.0 <making_code_changes> item 5 ("DO NOT loop more than 3 times on fixing linter errors on the same file ... stop and ask").
   - Why it works: gives the model a countable stop instead of a vague "if stuck".
   - SDLC use: do this in the script, not the prompt. The script counts attempts per (step, file) and emits a different packet (escalate/replan) at N. Note the owner's rule that ShipLoop quality/test loops are unbounded; use the cap only for no-progress detection.

3. Mandatory "think" checkpoints at named transitions.
   - What: a scratchpad tool the agent MUST call at fixed points: before git/branch decisions, when moving from exploration to editing ("have you found all locations to edit?"), and before reporting completion ("did you complete all verification steps?").
   - Where: Devin `Devin AI/Prompt.txt`, `<think>` command description (must-use list (1)-(3), should-use list (1)-(10), incl. "when tests/lint/CI failed: step back before editing").
   - Why it works: the checkpoint sits at the exact points where agents fail (premature edit, premature done). It fires on state transitions, not on a schedule.
   - SDLC use: the script knows the transition (explore->implement, implement->done) and the packet for that transition carries the checklist and requires the answers in the completion call. Stronger than a tool the model may skip.

4. Plan/standard mode split with an explicit plan-submission command.
   - What: two modes. In planning mode the agent only gathers information and must end by calling `suggest_plan` once it "knows all the locations you will have to edit". In standard mode it executes against plan steps shown by the host.
   - Where: Devin `Prompt.txt` "Planning" section.
   - Why it works: the mode is told to the model per turn by the host, so mode is external state rather than model memory.
   - SDLC use: same as ShipLoop's script-owned navigation; the lesson is the exit criterion of the planning mode ("all edit locations found, references updated") stated as the gate to submit.

5. Hard approval gates with exact phrasing, one task at a time.
   - What: Kiro's spec workflow is requirements -> design -> tasks. Each document ends with a fixed question via a `userInput` tool, and "MUST NOT proceed ... until receiving clear approval". Execution is "ONLY ... one task at a time. Once it is complete, do not move to the next task."
   - Where: `Kiro/Spec_Prompt.txt`, <workflow-definition>, "Workflow Diagram" (Mermaid state machine), and the task-execution rules near the end. It also bans non-coding tasks from the task list.
   - Why it works: a state machine in prose plus a diagram, with approval as the only edge, and "read requirements.md, design.md, tasks.md before executing any task" so each task is grounded in the spec.
   - SDLC use: matches ShipLoop's spec -> architecture -> tasks. Steal two things: the "do not tell the user which workflow step you are on" rule (keeps the harness invisible) and the ban on non-coding tasks in the implement list.

6. "Read before you write" and "don't assume the library exists" as repeated grounding rules.
   - What: before using a library or pattern, check neighbouring files / package.json; mimic conventions; never modify tests to make them pass unless asked; if env is broken, report it and test via CI instead of fixing the machine.
   - Where: Devin `Prompt.txt` "Coding Best Practices" and "Approach to Work"; Cursor 2.0 <maximize_context_understanding> ("TRACE every symbol back to its definitions", "MANDATORY: run multiple searches with different wording").
   - Why it works: each rule targets one concrete failure seen in production (hallucinated dependency, test tampering, rabbit-holing on env issues).
   - SDLC use: put "tests are read-only unless the step is a test step" into the script as a check (diff touches test files outside a test-step -> refuse), not just a sentence.

7. Tool-substitution rules plus parallel batching.
   - What: dedicated tools over shell (Read not cat, Grep not grep), with "batch independent calls in one message"; Windsurf adds "explain why before each call" and "NEVER make redundant tool calls (expensive)"; Cursor adds an `explanation` field on every tool schema.
   - Where: Claude Code 2.0 `Anthropic/Claude Code 2.0.txt` "Tool usage policy" and Bash tool notes; Cursor `Agent Prompt 2.0.txt` tool schemas (`explanation?: string`); Windsurf <tool_calling> 5.
   - Why it works: constrains the action space and makes each call carry its own justification, which also makes transcripts auditable.
   - SDLC use: require a one-line `reason` on each script call that mutates state; a later audit step can check reason vs. diff.

8. Memory as a tool with explicit create/update/delete rules.
   - What: Windsurf tells the model its context will be deleted ("ALL CONVERSATION CONTEXT, INCLUDING checkpoint summaries") so it must write memories liberally, no permission needed. Cursor's `update_memory` is the opposite: create only on explicit user request; contradiction means delete, not update.
   - Where: Windsurf <memory_system>; Cursor 2.0 `update_memory` tool description.
   - Why it works: telling the model the loss is certain makes it persist early.
   - SDLC use: the same fact is true for ShipLoop (context cleared between stages). Make persisting a packet obligation with a script-checked file, instead of a model choice.

Surprise: Windsurf's shipped prompt (`Windsurf/Prompt Wave 11.txt`) has a planning section where a separate "plan mastermind" owns the plan and the agent MUST call `update_plan` whenever scope changes ("better to update when it didn't need to than miss"). A second model/owner for the plan is in production in a mainstream tool.

---------------------------------------------------------------------
## 2. asgeirtj/system_prompts_leaks  (69,387 stars; 11.3k forks)
Extracted prompts by vendor folder (Anthropic, OpenAI, Google, xAI, Cursor, ...). Unlike repo 1, the Claude Code content is mainly
per-model, per-release dumps plus separated sub-prompts, so mechanisms are easy to isolate.
Read: Anthropic/claude-code/prompts/plan-mode.md, Anthropic/claude-code/agents/Explore.md, Anthropic/claude-code/prompts/advisor-tool.md,
OpenAI/Codex/gpt-5.5.md (also listed: OpenAI/Codex/codex-full.md, codex-auto-review.md, Anthropic/claude-code/commands/compact.md - not fully read).

1. Structural read-only enforcement stated twice (prompt plus tool list).
   - What: Explore agent's front-matter has `disallowedTools: ... Edit, Write ...` and the body opens "=== CRITICAL: READ-ONLY MODE ===" with an itemised prohibition list (no temp files in /tmp, no redirects, no heredocs).
   - Where: `Anthropic/claude-code/agents/Explore.md`.
   - Why it works: tool removal is the real guard; the loud text keeps the model from trying shell workarounds (redirects) that bypass the tool list.
   - SDLC use: per-step tool allow-lists in the script, plus the packet names the specific bypass routes (shell redirect, heredoc) that stay forbidden.

2. Plan mode as a phased procedure with a single legal exit.
   - What: Phase 1 explore (up to 3 parallel Explore agents, default 1), Phase 2 design (Plan agent), Phase 3 review (read critical files, align with request), Phase 4 write the plan file (context section first, one recommended approach, reuse existing functions, a verification section), Phase 5 end the turn only via `AskUserQuestion` or `ExitPlanMode`. Approval phrases ("Is this plan okay?") must go through ExitPlanMode, not free text.
   - Where: `Anthropic/claude-code/prompts/plan-mode.md`.
   - Why it works: the terminal condition is a tool call, so the harness can detect "done" and "wants approval" without parsing prose. "Only file you can edit is the plan file" makes the artifact the single write target.
   - SDLC use: matches ShipLoop's "exact completion call" idea. Copy the requirement that a plan include a verification section and a reuse list; enforce both with a script lint.

3. A stronger reviewer as a tool, called at fixed moments.
   - What: `advisor()` takes no parameters and forwards the full transcript. Call it before substantive work, when the task is believed done, when stuck, and when changing approach. Before the "done" call, "make your deliverable durable" (write file, commit). If the advisor conflicts with gathered evidence, do not silently switch: ask a reconcile question.
   - Where: `Anthropic/claude-code/prompts/advisor-tool.md`.
   - Why it works: zero-parameter forwarding removes the cost of writing a handoff (and the chance of leaving out the damning detail). Durable-before-review protects the work if the session dies. The reconcile rule stops sycophantic reversals.
   - SDLC use: the closest match to an adversarial-review step. In the harness the script does the forwarding (builds the review input from the ledger/diff), and the "persist first, then ask" order becomes a precondition check.

4. Persistence and end-to-end ownership, with a channel model for progress.
   - What: Codex GPT-5.5 "Autonomy and persistence": stay until handled end to end in the turn; do not stop at analysis or half-finished fixes; default to implementing unless asked for a plan or a question; sanity-check after resume/compaction that the answer targets the NEWEST request, "not an older ghost lingering in the thread"; progress updates go to a `commentary` channel, completion to `final`.
   - Where: `OpenAI/Codex/gpt-5.5.md`, "Autonomy and persistence" and the channel notes.
   - Why it works: separating channels lets the host render progress without the model mistaking an update for an end. The resume sanity check is a direct counter to context-loss errors.
   - SDLC use: every packet starts with "newest instruction = this packet; ignore earlier narrative". It also fits the owner's tenet that context is cleared between stages.

5. Working-tree etiquette rules.
   - What: never revert changes you did not make; treat unknown changes as the user's and work with them; no `git reset --hard` / `git checkout --` without explicit request; prefer non-interactive git; edit via `apply_patch`, not shell write tricks.
   - Where: `OpenAI/Codex/gpt-5.5.md` (git/editing section).
   - Why it works: names the high-damage actions concretely (a deny list), which the model can match against.
   - SDLC use: matches the owner's global CLAUDE.md git rules; encode them as a script-side command filter for step shells.

6. Output-shape budgets and bans on filler.
   - What: final answer short ("Never overwhelm ... over 50-70 lines"), no "If you want" closers, no "save/copy this file", flat bullets, no coined metaphors; Claude Code 2.0 equivalents: "concise ... less than 4 lines", no preamble/postamble, plus 9 worked one-line examples.
   - Where: `OpenAI/Codex/gpt-5.5.md` "Final answer instructions"; `x1xhlol` mirror `Anthropic/Claude Code 2.0.txt` "Tone and style".
   - Why it works: examples set a length prior far more strongly than adjectives.
   - SDLC use: step reports to the script should have a fixed schema and size; use few-shot of the exact JSON/markdown completion body.

7. Scope-minimisation clauses.
   - What: "Do what has been asked; nothing more, nothing less. NEVER create files unless absolutely necessary. ALWAYS prefer editing." injected as a system-reminder on every user turn, not just in the system prompt.
   - Where: `Anthropic/Claude Code 2.0.txt` top `<system-reminder>` block (mirrored in repo 1; the per-model dumps in this repo, `Anthropic/claude-code/claude-code-*.md`, are the same family).
   - Why it works: repetition at the end of the context (recency) keeps the rule alive over long sessions.
   - SDLC use: the packet re-injects the 3-4 rules that matter for that step at its tail; consistent with "cross-packet repetition is grounding".

Surprise: this repo versions the same product across many models (`claude-code-opus-4.6.md` ... `claude-code-sonnet-5.5.md`, ~400KB each), so prompt diffs per model are visible; and the Claude Code "Plan" and "Explore" roles are separate files with their own tool deny-lists, i.e. role = (prompt, tool list, model) triple.
(I did not diff the per-model files; only noted their existence.)

---------------------------------------------------------------------
## 3. repowise-dev/claude-code-prompts  (1,210 stars; 399 forks)
Self-described independently written prompts "studied from Claude Code behavior", not leaks (README + DISCLAIMER.md; not affiliated with Anthropic; promotes the RepoWise tool).
Structure: `complete-prompts/` (system, agent, tool, memory, utility prompts), `patterns/01..09-*.md`, `skills/`.
Read: complete-prompts/agent-prompts/verification-specialist.md, complete-prompts/coordinator-prompt.md, complete-prompts/system-prompt.md,
complete-prompts/memory-prompts/memory-consolidation.md, patterns/ listing.
Treat as reconstruction, so use it for ideas, not as evidence of what any vendor ships.

1. Verification agent built around naming its own failure modes.
   - What: opens with "Your job is not to confirm that the implementation works - it is to try to break it", then names two traps ("Check-skipping", "Getting lulled by the obvious 80%") and a list of rationalisations to catch ("The code looks correct based on my reading", "The implementer's tests already pass").
   - Where: `complete-prompts/agent-prompts/verification-specialist.md`.
   - Why it works: describing the exact internal excuse the model will generate lets it recognise it mid-generation.
   - SDLC use: strong fit for a ShipLoop test/verify step. Copy the rationalisation list into the verify packet. (Related to the owner's "LLM closes ~80% of the remaining gap" memory.)

2. Evidence format that is machine-checkable and re-executable.
   - What: every check is `### Check / Command run / Output observed (verbatim) / Result`; "the caller may re-execute any command ... if output doesn't match, the entire report is rejected"; report ends with exactly `VERDICT: PASS|FAIL|PARTIAL` literal (no bold, no variation); PARTIAL only for environmental limits, "uncertainty is not a reason for PARTIAL".
   - Where: same file, "Output" section and bad/good examples.
   - Why it works: a bad example (PASS with no command) is shown and labelled rejected; the strict verdict line is parsable.
   - SDLC use: the script parses the VERDICT line and re-runs a sampled command, rejecting on mismatch. This is the test-pass-is-the-evidence principle in prompt form.

3. Verifier is read-only and must try an adversarial probe before PASS.
   - What: no project writes, no installs, no git writes (tmp scripts allowed, cleaned up); strategy per change type (UI, API, CLI, migration, refactor, bugfix = reproduce first); universal steps (build, full tests, lint); at least one adversarial probe (concurrency, boundary, idempotency, orphan) recorded before PASS.
   - Where: same file, "Approach", "Required universal steps", "Adversarial probes".
   - Why it works: a minimum evidence quota (one probe) breaks the 'looks fine' default.
   - SDLC use: the script keeps a per-change-type verify matrix; the completion call must include a probe entry or is refused.

4. Coordinator that owns synthesis; workers get self-contained prompts.
   - What: phases Research (parallel, read-only) -> Synthesis (coordinator only, "never hand raw findings to another worker and say figure it out") -> Implementation -> Verification. Banned phrases: "based on what you discovered". Prompts must embed paths, lines, errors, "done" criteria and a purpose statement. Do not spawn a worker just to review another's output; continue a worker via SendMessage when context overlaps; second failed correction -> change strategy or escalate; hard delegation depth limit; write tasks serialised per file set.
   - Where: `complete-prompts/coordinator-prompt.md`.
   - Why it works: the banned-phrase rule targets the precise way delegation loses information.
   - SDLC use: since the script is the coordinator, it can lint worker prompts mechanically (must contain a file path, a done-criterion, a purpose line; must not contain the banned phrases).

5. Risk-tiered action rule (reversibility first).
   - What: local reversible actions proceed; shared-state or destructive ones need confirmation; approval is scoped, does not generalise; tool output is treated as potentially adversarial (surface injection, do not comply); obstacles: investigate, do not use destructive shortcuts.
   - Where: `complete-prompts/system-prompt.md` (summary at top; rules in the "risk" section); `patterns/03-safety-and-risk-assessment.md`.
   - Why it works: gives a one-question test (reversible? shared?) instead of a list.
   - SDLC use: classify each script action as reversible/shared at definition time; the packet states the class.

6. Code-style minimalism bans.
   - What: no speculative error handling, no helpers for one-use logic ("three nearly identical lines beat premature generalisation"), no backward-compat shims, comments only for non-obvious why, no docstrings on untouched code, no time estimates.
   - Where: `complete-prompts/system-prompt.md` code-style section.
   - Why it works: each rule bans a specific padding habit that inflates diffs.
   - SDLC use: a review-step checklist; matches the owner's "one supported version, no shims" memory.

7. Failure-recovery protocol: diagnose, isolate, fix.
   - What: on failure, check assumptions, change something before retry, do not abandon a sound strategy after one setback; denied tool call must not be retried unchanged.
   - Where: `complete-prompts/system-prompt.md` (task execution discipline).
   - Why it works: separates the two opposite errors (blind retry vs. giving up).
   - SDLC use: failure packet = fixed three questions; script compares the new attempt's diff to the last and refuses an identical retry.

8. Memory consolidation as a phased "dream" pass.
   - What: Orient -> Gather signal -> Consolidate (merge, absolute dates, delete contradicted) -> Prune/index to a size limit; "fewer, stronger memories".
   - Where: `complete-prompts/memory-prompts/memory-consolidation.md`.
   - Why it works: fixed phases with a size limit prevent unbounded growth.
   - SDLC use: a periodic knowledge-home compaction step with a script-checked size budget.

Surprise: the most useful single file is a verifier prompt whose report is designed to be rejected by the caller on re-execution mismatch; the repo's value is in that adversarial contract, not in the "Claude Code reconstruction" framing.

---------------------------------------------------------------------
## Cross-repo take-aways for a script-driven SDLC harness
- Prompt text states intent and the excuses to resist; the exit is a tool/command call the script can validate. (Plan mode's ExitPlanMode; Devin's suggest_plan; Kiro's approval question.)
- Counts and quotas beat adjectives: "max 3 lint loops", "at least one adversarial probe", "up to 3 explorers", "one task at a time".
- Read-only is enforced by the tool list, then repeated in text with the bypass routes named.
- Verification evidence must be verbatim command output with a literal verdict line; callers sample-reexecute.
- Re-inject the few critical rules at the tail of each turn/packet (Claude Code system-reminder pattern).
- Gaps in these sources: none of the three shows how a script, rather than the model, owns the loop; the prompts assume the model drives. Everything above would need to be turned into script-checked preconditions.
