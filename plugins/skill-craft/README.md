# Skill Craft

Skill Craft: portable multi-host agent skills (ShipLoop, Improve, Ask-Agent, Backchain and more) packaged as one plugin for Claude, Codex, Grok and Cursor.

## Install

Add the `whichguy` marketplace, install `skill-craft@whichguy`, then start a fresh host session so it loads the packaged skills.

## Use

Every skill is namespaced by this plugin: in Claude, invoke `/skill-craft:<skill>` (for example `/skill-craft:shiploop`); in Codex, ask for `$skill-craft:<skill>`; in other hosts, select the installed plugin skill. Read each skill's SKILL.md before execution; it defines the workflow and any task-specific limits. When a skill invokes a bundled helper, resolve it from the loaded skill directory (for example, `skills/<skill>/scripts/...`), never from the consumer project's current directory.

## Skills

| Skill | Claude command | Version | Purpose |
|-------|----------------|---------|---------|
| [architect](skills/architect/SKILL.md) | `/skill-craft:architect` | 0.1.2 | Design system architecture and make technology decisions. Uses a structured inline design or an available independent… |
| [ask-agent](skills/ask-agent/SKILL.md) | `/skill-craft:ask-agent` | 0.7.10 | A delegation skill, not an agent type. Ask native agents to work in the background, continue useful work in the main… |
| [backchain](skills/backchain/SKILL.md) | `/skill-craft:backchain` | 0.6.0 | Use when an implementation task needs a dependency-aware plan before coding: backward planner / backchain /… |
| [c-plan](skills/c-plan/SKILL.md) | `/skill-craft:c-plan` | 0.1.2 | Resolve ambiguous user prompts by choosing whether to answer now, answer with assumptions, ask 1–2 high-value… |
| [compare-prompts](skills/compare-prompts/SKILL.md) | `/skill-craft:compare-prompts` | 0.1.3 | Compare two prompt versions (A vs B) by running both against a directory of test input files, then evaluating results… |
| [devloop](skills/devloop/SKILL.md) | `/skill-craft:devloop` | 0.7.0 | Run the DevLoop engine (shim only) |
| [evidence-gates](skills/evidence-gates/SKILL.md) | `/skill-craft:evidence-gates` | 0.2.4 | Optional offline evidence gates (freeze/prove/stop with guard digests) for machine-checkable red→green contracts… |
| [improve](skills/improve/SKILL.md) | `/skill-craft:improve` | 0.3.0-rc.6 | Review and improve until two clean passes |
| [improve-agent](skills/improve-agent/SKILL.md) | `/skill-craft:improve-agent` | 0.1.1 | Run Improve in a fresh native agent |
| [improve-system-prompt](skills/improve-system-prompt/SKILL.md) | `/skill-craft:improve-system-prompt` | 0.1.2 | Benchmark and compare system prompt variants (V2/V2a/V2b/V2c) for Sheets Chat by running test scenarios through the… |
| [plan-dispatcher](skills/plan-dispatcher/SKILL.md) | `/skill-craft:plan-dispatcher` | 0.3.0 | Use when executing or resuming an agreed dependency graph with one main dispatcher and parallel native workers: claim… |
| [plan-test](skills/plan-test/SKILL.md) | `/skill-craft:plan-test` | 0.1.3 | Generate comprehensive tests for code. Uses an inline strategy or an available independent test specialist for complex… |
| [prompt-align](skills/prompt-align/SKILL.md) | `/skill-craft:prompt-align` | 0.1.2 | Compare an agent or skill prompt against its test harness skill for phase-model, skip-condition, and wiring… |
| [prompt-audit](skills/prompt-audit/SKILL.md) | `/skill-craft:prompt-audit` | 0.1.2 | Audit an agent or skill prompt file for internal inconsistencies (phase numbering, behavioral contracts, terminology… |
| [prompt-migrate](skills/prompt-migrate/SKILL.md) | `/skill-craft:prompt-migrate` | 0.1.2 | TDD-based prompt migration — given a target agent/skill prompt and a remediation list, writes failing tests first… |
| [prompt-refine](skills/prompt-refine/SKILL.md) | `/skill-craft:prompt-refine` | 0.1.2 | Full prompt-improvement workflow — runs prompt-audit to find inconsistencies, presents a remediation plan, then runs… |
| [review-coverage](skills/review-coverage/SKILL.md) | `/skill-craft:review-coverage` | 0.3.2 | Add a post-ship improve-to-exhaustion directive to a plan, or run that directive after implementation. Invoke like any… |
| [review-fix-bench](skills/review-fix-bench/SKILL.md) | `/skill-craft:review-fix-bench` | 0.1.2 | Compare two code-review prompt versions against supplied fixture ground truth using an explicitly configured external… |
| [shiploop](skills/shiploop/SKILL.md) | `/skill-craft:shiploop` | 0.33.1 | Markdown-authoritative delivery harness. Start or resume once, follow the script's current action packet, and submit… |
| [shiploop-e2e-audit](skills/shiploop-e2e-audit/SKILL.md) | `/skill-craft:shiploop-e2e-audit` | 0.4.6 | Run the ShipLoop test harness and audit its retained graph, review, test, product and incremental-change evidence. Use… |
| [skill-interop](skills/skill-interop/SKILL.md) | `/skill-craft:skill-interop` | 0.2.6 | Use when authoring or reviewing a portable multi-host agent skill (Grok, Claude Code, Codex, Hermes): scaffold a… |

## Support

[Skill Craft source and issue tracker](https://github.com/whichguy/skill-craft)
