# Round 4 web research: open source harnesses

Written by a Claude Opus 5.5 research agent on 2026-11-20 from the brief at the end of this file. Model output: every
claim is the agent's reading of the page it names, not checked again by the session that commissioned it.

## 1. Comparison table (every URL listed was opened)

| Project (URL) | Stage order | Tests vs code | Exit rule | Removal or simplification |
|---|---|---|---|---|
| **spec-kit** (github.com/github/spec-kit; templates/tasks-template.md, commands/implement.md, commands/converge.md) | constitution → specify → plan → tasks → implement ⇄ converge | Tests "OPTIONAL". When included they "MUST be written and FAIL before implementation". | All tasks marked [X] and tests pass. Converge is a model check of spec/plan/tasks against the code ("completion claims are not evidence"). No cap. | Added converge, which appends gap tasks. Made tests optional. |
| **OpenSpec** (github.com/Fission-AI/OpenSpec) | propose (proposal, specs, design, tasks) → apply → archive; verify is optional | Not specified | "All tasks complete!" | Calls spec-kit "heavyweight" and drops phase gates (OPINION) |
| **Kiro** (kiro.dev/docs/specs) | requirements → design (includes a testing strategy) → tasks run in dependency waves | Not specified | Task status | "Quick Spec": one pass "without approval gates" |
| **BMAD v7 bmad-build** (docs.bmad-method.org/build/build-a-change) | clarify → plan (a "light path" when clean) → implement → multi-lens independent review → present | Tests only "if your project has a test suite". The Test Architect is an add-on. | A human marks the ticket done. A flaw caused by the plan goes back to the plan layer. | About 500 changed LOC per session. v6 is frozen and v7 is an alpha. |
| **Agent OS** (raw CHANGELOG.md) | shape-spec on top of host plan mode | Not specified | Final verification kept | v2.1 cut per-task docs and specialist verifiers ("unnecessary and inefficient"). v3 retired the implementation/orchestration phases. |
| **superpowers** (github.com/obra/superpowers; SKILL.md files, fix-loop.md, RELEASE-NOTES.md) | brainstorm → plan → per task: implementer (TDD) → one reviewer giving spec and quality verdicts → fix loop → final whole-branch review | **Before** ("Iron Law"; code written first is deleted) | Review clean or finding parked. Max 5 rounds: rounds 1–3 resume the implementer, rounds 4–5 go to a stronger model, then the controller adjudicates. | Many removals, see §4 |
| **GSD core** (github.com/open-gsd/gsd-core; docs/explanation/the-phase-loop.md) | discuss → plan → plan-checker → execute (fresh 200k context, one atomic commit per task) → verify → ship | Not mentioned ("verification is not just testing") | Verifier checks requirement, decision and goal coverage and writes fix plans. No cap stated. | The original repo is archived |
| **Ralph** (ghuntley.com/ralph; github.com/snarktank/ralph; claude-plugins-official ralph-loop) | Same prompt every loop, one item per loop, plan regenerated often | Written in the same loop as the code, run for the touched unit | snarktank: typecheck and tests pass, then commit, `passes=true`, `COMPLETE` promise, max 10 iterations. Plugin: default "unlimited". | — |
| **Anthropic long-running harness** (anthropic.com/engineering/effective-harnesses-for-long-running-agents) | initializer writes a JSON list of 200+ features, each with test steps and all failing → one feature per session → browser end-to-end check | Acceptance steps come **before** the code | The agent may only flip `passes`. "Unacceptable to remove or edit tests." | Chose JSON over Markdown so the model is less likely to edit the list |
| **Claude Code best practices** (code.claude.com/docs/en/best-practices) | interview → SPEC.md → fresh build session → reviewer that did not write the code | Bug-fix example: "write a failing test that reproduces it, then fix it" | A check to run (tests, Stop hook, `/goal`). After two failed corrections, `/clear` and re-prompt. | "What you can stop doing" table: "loop until done" prompts cause over-work |
| **Aider** (aider.chat/2024/09/26/architect.html; aider.chat/docs/usage/lint-test.html) | architect → editor. Lint after every edit, optional auto-test. | The user supplies the test command | Fix while lint or tests exit non-zero. No documented cap. | — |
| **SWE-agent / mini-swe-agent** (arxiv.org/html/2405.15793; github.com/SWE-agent/mini-swe-agent) | Single agent loop | Not specified | Submit | SWE-agent "superseded" by the ~100-line, bash-only mini (>74% on Verified, MEASURED) |
| **Agentless** (github.com/OpenAutoCoder/Agentless; arxiv.org/html/2407.01489) | localize → 40 candidate patches → regression tests plus generated reproduction tests → rerank | Reproduction test generated, then used to select a patch | Script selection | Has no agent loop at all |
| **AlphaCodium** (github.com/Codium-ai/AlphaCodium; arxiv.org/html/2401.08500) | reflect → reason about public tests → candidate solutions → rank → 6–8 AI tests → code → iterate on public tests → iterate on AI tests | AI tests written **before** the code | "Until the tests pass, or until a try-limit" (limit not given) | Iterates on the code, not the AI tests |

Also read: **MetaGPT** (arxiv.org/html/2308.00352). The Engineer writes and runs unit tests with at most 3 retries. **OpenHands critic** (openhands.dev/blog/20260305-learning-to-verify-ai-generated-code). **Cline Plan/Act** (docs.cline.bot/features/plan-and-act) and **Roo modes**, where Architect may edit only Markdown. **Task Master** (repo plus docs/task-structure.md): complexity scored 1–10 and expanded, with a `testStrategy` field per task.

## 2. Patterns that recur

- **One small unit per fresh context.** Ralph uses one item per loop; snarktank sizes a story "small enough to complete in one context window". GSD gives each executor a fresh 200k context; superpowers sends no session history to the implementer; Anthropic's harness does one feature per session. (OPINION, though Anthropic reports one-shot attempts ran out of context.)
- **A script-checkable signal ends the loop**, not the model's claim. Examples: snarktank's typecheck and tests, Aider's non-zero exit, the `passes` field, spec-kit converge. (OPINION)
- **Acceptance is executable or concrete before the code.** Superpowers writes failing test code into the plan; Anthropic gives test steps per feature; AlphaCodium writes AI tests before the initial code; Agentless writes a reproduction test. (Agentless and AlphaCodium MEASURED, the rest OPINION)
- **Retry caps with escalation or restart.** Superpowers: 5 rounds, stronger model at rounds 4–5. MetaGPT: 3 retries. Claude Code: 2 failed corrections, then clear. snarktank: 10 iterations.
- **Plan with a strong model, edit with a cheaper one.** Aider (MEASURED), Cline and Roo per-mode models (OPINION), superpowers cheapest tier for mechanical tasks (OPINION).
- **Reviews get consolidated over time.** Superpowers and Agent OS both cut per-task reviewers and kept one final review (partly MEASURED).
- **A light path for small work.** BMAD light path, Kiro Quick Spec, Cline "skip planning for small, obvious changes". (OPINION)

## 3. Where designs disagree

- **Test-first.** Superpowers requires it (Iron Law). Spec-kit makes it optional. BMAD v7, GSD and OpenSpec don't prescribe it. Ralph writes tests in the same loop as the code.
- **Per-step review.** Superpowers v6 still runs one reviewer per task. Agent OS v2.1 and superpowers' `executing-plans` review only at the end.
- **Plan detail.** Superpowers v6.4.2 cut full code out of plans. Spec-kit generates long design artifacts (2,067 Markdown lines in the Scott Logic trial).
- **Gates.** Spec-kit has gates and checklists. OpenSpec and Kiro Quick Spec drop approval gates.
- **Who judges "done".** Scripts (snarktank, Aider), a model (spec-kit converge, GSD verifier), or a human (BMAD).

## 4. Ideas to test in a harness like this

1. **Make test-spec emit executable failing tests, and run the red check before implement.** The implementer then has a target instead of prose. This could shrink the slow test→fix iteration after the code. Motivated by superpowers and Claude Code (OPINION), AlphaCodium (19%→44% pass@5 with GPT-4 for the whole flow, MEASURED but not isolated) and Agentless (reproduction tests 27.0%→32.0% resolved, MEASURED). The test must be checked against the spec: in Agentless only 94 of 213 reproducing tests behaved correctly on the true patch (MEASURED).
2. **Test anchors.** Fix one failing test at a time, easy to hard. Every passing test becomes an anchor that later fixes must keep green. From AlphaCodium (no isolated number).
3. **Cap the test-fix loop, then restart or escalate.** After N failed rounds, start a fresh context with a summary of what was learned, or hand off to a stronger model. Superpowers: 5 rounds, rounds 4–5 on a higher tier (OPINION). MetaGPT: 3 retries, with executable feedback worth +4.2 points on HumanEval and +5.4 on MBPP (MEASURED). Claude Code: "after two failed corrections" (OPINION).
4. **Drop or merge the per-step second-model review in favour of one end-of-work review.** Superpowers removed its plan-review loops (~25 min overhead, no measurable quality gain, MEASURED). Its v6.0.0 rewrite, including the move to one reviewer, ran "roughly twice as fast" with nearly 50% fewer tokens (MEASURED, but for the whole rewrite). Agent OS removed its specialist verifiers (OPINION).
5. **Keep step-plan to decisions, files and check commands, never full code.** Superpowers v6.4.2: plans took "a quarter of the time and about a third of the tokens" (MEASURED, self-reported).
6. **Run lint or typecheck on every edit inside implement**, as cheap feedback before tests. SWE-agent: edits guarded by a linter 18.0% vs 15.0% without, on SWE-bench Lite (MEASURED). Aider runs auto-lint by default.
7. **Split architect from editor for mid-tier models**, including the same model in both roles. Aider: Sonnet+Sonnet 80.5% vs Sonnet alone 77.4%; GPT-4o pair 75.2% vs 71.4% (MEASURED).
8. **Script-sized steps and a light path.** Size a step to one context window, about 500 LOC (snarktank, BMAD, OPINION). Skip test-spec and document for trivial steps (Kiro Quick Spec, Cline, OPINION). Also borrow spec-kit's converge check of intent against code, so a claim of completion is not taken as evidence (OPINION).

## 5. Cautions

- **Spec-kit can be slow.** In one hands-on trial (blog.scottlogic.com/2025/11/26/…) it took 33.5 min of agent time and 3.5 h of review, producing 2,577 Markdown lines for 689 LOC. The plain approach took 8 min, about "ten times faster", with no quality gain, and the author dropped TDD. MEASURED, one case.
- **Superpowers' old review structure.** Its subagent review loops "doubled execution time" (v5.0.6). The two-reviewer flow was "expensive and easy to game" (v6.0.0). Pasted diffs were "the single biggest reviewer cost".
- **Agent OS subagents.** The maintainer says they bring "higher token usage, less transparency, slower to finish tasks" (OPINION).
- **ralph-loop plugin.** Default iterations are "unlimited", and the exact-match completion promise cannot express BLOCKED. Its README says to set `--max-iterations`.
- **Anthropic harness failure modes.** Agents declared victory too early and marked features done without end-to-end testing. Fixed with browser checks and a JSON list the agent may only flip.
- **Model-written tests are unreliable.** Agentless: 213 of 300 issues got a reproducing test, but only 94 were correct on the true patch. AlphaCodium: fixing an AI test "just copies the code's output", so iterate on the code.
- **Over-fixing review findings.** Claude Code docs: a reviewer "will always find something", and fixing everything adds abstractions. Its sample reviewer prompts say to skip style.
- **Abandoned or churning projects.** The original get-shit-done repo is archived. SWE-agent is superseded by mini-swe-agent. BMAD v6 is frozen and v7 is an alpha whose skills and docs "change often".

Not verified: Codex CLI, Goose, ChatDev and OpenHands' own agent loop (I read only its critic blog). Kiro's test placement and spec-kit's changelog history were not covered by the pages I read.

---

## The brief the agent was given

You are doing web research for an engineering study. Read-only: do not edit any files, do not clone or run anyone's code; read repositories through their web pages (READMEs, docs, prompt files, issues, discussions). Use web search and page fetches. PRIVACY: put only generic topic words and the public names of the projects you are looking up in search queries and URLs; never include any person's name, email, local file path or private project name from this brief.

## Context (what the study is about)
A script-driven software delivery harness hands a coding model one stage "packet" at a time. Per work item the order is:
1. step-plan: list steps, files, completion criteria, and the shell commands that will confirm each criterion.
2. test-spec: write prose test cases (one per criterion) BEFORE any code.
3. implement: write the product code for one step, inside a loop that repeats until that stage's exit conditions hold.
4. test: write the executable tests AFTER the code, run them, and fix the product code until all pass; the harness then checks that each new test fails on the pre-change tree (red check), samples mutants, and reruns everything itself.
5. document, then a second-model review of the step, then commit.
Planning before this is: spec -> test strategy -> plan. After all steps: system tests, acceptance, release.

Observed problem: the first implementation is "moderately correct"; only when real tests are executed do logic gaps show, and the model then iterates test-run -> fix -> rerun to tune it. That iteration is slow. The harness will be driven by mid-tier models (GPT at medium reasoning, Claude Sonnet-class at high effort, Grok at high effort), not the strongest ones. We want to know whether the ordering and the per-step exit criteria are right, or whether some stages are unnecessary or mis-ordered.

## Your job: how OPEN-SOURCE agent harnesses and workflow kits on GitHub order this work
Survey the designs of well-used open projects and what their maintainers changed over time and why. Candidates (verify each exists and read its actual docs/prompts; add others you find, drop any you cannot verify): spec-driven kits (GitHub spec-kit, OpenSpec, BMAD-METHOD, Agent OS, Kiro-style spec workflows), task planners (Task Master), skill/workflow packs for coding agents (e.g. "superpowers" style TDD and verification skills, "get-shit-done" style kits), autonomous loops (the "Ralph" loop technique and its variants, stop-hook driven loops), agent frameworks (Aider including its architect/editor split and its lint/test auto-fix loop, OpenHands, SWE-agent and mini-swe-agent, Cline/Roo Code modes, Goose, Codex CLI and Claude Code documented best practices), and research pipelines with public code (AlphaCodium, Agentless, MetaGPT, ChatDev).

For each project you cover, extract concretely:
- The stage order: where planning, test writing, implementation, test execution and review sit; whether tests are written before or after the code; whether the implementer is handed executable tests or prose criteria.
- The loop exit rule: what must be true to stop (tests pass, a checklist, a judge model, a hook), who checks it (script or model), and any cap on iterations or a rule for giving up/restarting.
- Step size / granularity guidance (how big a task, how many acceptance criteria).
- Anything the maintainers REMOVED or simplified for speed or because it did not help, and any stated guidance for weaker/cheaper models (e.g. strong model plans, weak model edits).
- Any measured result they publish (benchmark deltas, ablations), with the number.

## What to return (your final message is the whole deliverable; keep it under 1,400 words)
1. A compact comparison table of 10-14 projects: name, URL you opened, stage order in one line, tests before/after code, exit rule, notable removal/simplification.
2. "Patterns that recur" (5-8 bullets) and "Where designs disagree" (3-5 bullets), each tied to named projects.
3. "Ideas to test in a harness like this": up to 8 concrete changes to ordering, step criteria or loop exit rules, each with the project that motivates it and whether that project shows a measurement or only an opinion.
4. "Cautions": designs that maintainers or issue threads report as slow, flaky or abandoned, with links.
Mark every claim MEASURED (the source shows a number) or OPINION. Do not cite pages you did not open.
