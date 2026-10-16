"""Curated, file-linked claims per card. Every (repo, path) is verified against the live tree before use."""
import json, os, sys, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.dirname(os.path.abspath(__file__))
import importlib.util
spec = importlib.util.spec_from_file_location("br", os.path.join(BASE, "build_refs.py"))
src = open(os.path.join(BASE, "build_refs.py")).read().replace("\nmain()\n", "\n")
ns = {"__file__": os.path.join(BASE, "build_refs.py")}
exec(compile(src, "build_refs.py", "exec"), ns)
resolve, gh = ns["resolve"], ns["gh"]

G = "x1xhlol/system-prompts-and-models-of-ai-tools"; L = "asgeirtj/system_prompts_leaks"; RW = "repowise-dev/claude-code-prompts"
SP = "obra/superpowers"; ECC = "affaan-m/ECC"; GSD = "gsd-build/get-shit-done"; SK = "anthropics/skills"; CC = "anthropics/claude-code"
RA = "snarktank/ralph"; CX = "openai/codex"; AI = "Aider-AI/aider"; SA = "SWE-agent/SWE-agent"; MS = "SWE-agent/mini-swe-agent"
OS = "Fission-AI/OpenSpec"; BM = "bmad-code-org/BMAD-METHOD"; SKT = "github/spec-kit"

C = {
"evidence-gate": [
 ("GateGuard denies the first edit of a file until the agent presents concrete facts; its header explains that a yes/no question always gets \"yes\".", ECC, "scripts/hooks/gateguard-fact-force.js"),
 ("The verifier must record each check as a command plus verbatim output and end with a literal VERDICT line; the caller may re-run any command and reject the report on a mismatch.", RW, "complete-prompts/agent-prompts/verification-specialist.md")],
"distrust-the-author": [
 ("Superpowers' task reviewer reads a diff file and is told not to trust the implementer's report.", SP, "skills/subagent-driven-development/task-reviewer-prompt.md"),
 ("GSD's verifier treats SUMMARY.md claims as non-evidence and starts from \"goal not achieved\".", GSD, "agents/gsd-verifier.md"),
 ("BMAD's claims check treats the plan as testimony and tries to falsify each claim against traced code.", BM, "skills/bmad-build/references/claims-check.md")],
"fresh-context-per-unit": [
 ("Ralph starts a new process for every iteration, feeding it the same prompt file.", RA, "ralph.sh"),
 ("Ralph's prompt picks the highest-priority story with passes:false and implements only that one.", RA, "prompt.md"),
 ("GSD's execute-phase workflow keeps the orchestrator lean and runs each plan in a fresh executor, wave by wave.", GSD, "get-shit-done/workflows/execute-phase.md"),
 ("Aider's architect creates a fresh editor coder with empty history and no repo map.", AI, "aider/coders/architect_coder.py")],
"size-by-context": [
 ("GSD's planner states the ~50% target and per-task percentages in prose; the numbers are a heuristic.", GSD, "agents/gsd-planner.md"),
 ("Ralph asks that a story fit one context window, with no estimator in code.", RA, "skills/ralph/SKILL.md"),
 ("BMAD sizes the plan document at 900-1600 tokens and says the limit is not a gate.", BM, "skills/bmad-build/workflow.md"),
 ("GSD's context monitor reads remaining context from the host and injects warnings at 35% and 25%.", GSD, "hooks/gsd-context-monitor.js")],
"format-over-prompt": [
 ("Aider reports GPT-4 Turbo at 20% with SEARCH/REPLACE and 61% with unified diffs on its laziness benchmark.", AI, "aider/website/docs/unified-diffs.md"),
 ("Codex defines apply_patch as a Lark grammar with no line numbers.", CX, "codex-rs/core/assets/tools/apply_patch.lark"),
 ("Codex matches patch context at decreasing strictness (exact, trailing-trimmed, fully trimmed).", CX, "codex-rs/apply-patch/src/seek_sequence.rs")],
"reject-and-explain": [
 ("SWE-agent's lint-gated edit refuses the edit and shows both the would-be and original code.", SA, "tools/windowed_edit_linting/bin/edit"),
 ("Aider answers a failed SEARCH block with \"did you mean\" lines and says which blocks already applied.", AI, "aider/coders/editblock_coder.py"),
 ("mini-swe-agent turns a format error into a message and stops after 3 consecutive ones.", MS, "src/minisweagent/agents/default.py")],
"code-owned-stage-graph": [
 ("OpenSpec declares artifacts, their requirements and instructions in a schema file.", OS, "schemas/spec-driven/schema.yaml"),
 ("OpenSpec marks an artifact done when its generated file exists.", OS, "src/core/artifact-graph/state.ts"),
 ("BMAD routes a build by the plan file's frontmatter status, mapped to step files in prose.", BM, "skills/bmad-build/step-01-clarify-and-route.md")],
"delta-spec-merge": [
 ("OpenSpec applies deltas to the persistent specs and throws on duplicates and cross-section conflicts.", OS, "src/core/specs-apply.ts"),
 ("The archive command validates rebuilt specs before writing and then moves the change into the archive folder.", OS, "src/core/archive.ts")],
"cap-ambiguity": [
 ("spec-kit's specify prompt caps [NEEDS CLARIFICATION] markers at 3 and turns the rest into recorded assumptions.", SKT, "templates/commands/specify.md"),
 ("spec-kit's clarify prompt asks at most 5 questions, each with a recommended option.", SKT, "templates/commands/clarify.md"),
 ("BMAD's spec skill has a headless mode that never asks and records assumptions and open questions.", BM, "skills/bmad-spec/SKILL.md")],
"lint-the-handoff": [
 ("spec-kit requires task lines of the form T012 [P] [US1] path.", SKT, "templates/commands/tasks.md"),
 ("BMAD runs a deterministic lint of the architecture spine before the parallel reviewers.", BM, "skills/bmad-architecture/references/reviewer-gate.md"),
 ("OpenSpec's schema instructions warn about formatting mistakes that fail silently.", OS, "schemas/spec-driven/schema.yaml")],
"exit-by-tool-call": [
 ("Plan mode ends only through AskUserQuestion or ExitPlanMode.", L, "Anthropic/claude-code/prompts/plan-mode.md"),
 ("Devin's prompt requires the think command before editing and before reporting done.", G, "Devin AI/Prompt.txt"),
 ("Kiro's spec workflow ends each document with an approval question and forbids moving on without it.", G, "Kiro/Spec_Prompt.txt")],
"trigger-only-descriptions": [
 ("Superpowers documents the failure where a workflow-summarising description led to one review instead of two.", SP, "skills/writing-skills/SKILL.md"),
 ("skill-creator tunes descriptions on a 60/40 train/held-out split and picks by held-out score.", SK, "skills/skill-creator/scripts/run_loop.py")],
"baseline-pressure-test": [
 ("Superpowers' RED/GREEN/REFACTOR method for skills is written up here.", SP, "skills/writing-skills/testing-skills-with-subagents.md"),
 ("skill-creator's grader writes a fixed grading.json with expectations, pass flags and evidence.", SK, "skills/skill-creator/agents/grader.md")],
"validator-per-finding": [
 ("Anthropic's code-review plugin validates each finding with a separate agent and drops unvalidated ones.", CC, "plugins/code-review/commands/code-review.md"),
 ("Codex's review rubric flags only discrete, actionable issues introduced by the change.", CX, "codex-rs/prompts/templates/review/rubric.md")],
"hooks-are-hard-enforcement": [
 ("hookify turns markdown rules into deterministic tool-call blocks.", CC, "plugins/hookify/hooks/pretooluse.py"),
 ("ECC blocks --no-verify with an exit-2 hook.", ECC, "scripts/hooks/block-no-verify.js"),
 ("The ralph-wiggum plugin enforces its loop with a Stop hook.", CC, "plugins/ralph-wiggum/hooks/stop-hook.sh")],
"readonly-by-tool-list": [
 ("The Explore agent removes Edit and Write and names the shell bypasses it forbids.", L, "Anthropic/claude-code/agents/Explore.md"),
 ("spec-kit's analyze pass is strictly read-only.", SKT, "templates/commands/analyze.md")],
"stop-is-script-owned": [
 ("ralph.sh loops to MAX_ITERATIONS and greps the output for the completion promise.", RA, "ralph.sh"),
 ("The ralph-wiggum Stop hook blocks exit and re-feeds the prompt until the promise matches or the cap is hit.", CC, "plugins/ralph-wiggum/hooks/stop-hook.sh"),
 ("mini-swe-agent checks step, cost and wall-time limits before each model call.", MS, "src/minisweagent/agents/default.py")],
"handoff-for-a-successor": [
 ("Codex's compaction prompt asks for a handoff summary written for another model.", CX, "codex-rs/prompts/templates/compact/prompt.md"),
 ("A fixed prefix frames the summary as work by another model.", CX, "codex-rs/prompts/templates/compact/summary_prefix.md"),
 ("Aider keeps the newest messages verbatim and summarises the head.", AI, "aider/history.py")],
"per-model-prompts": [
 ("Codex ships a short prompt for its codex model.", CX, "codex-rs/core/gpt_5_codex_prompt.md"),
 ("A much longer prompt serves gpt-5.2.", CX, "codex-rs/core/gpt_5_2_prompt.md")],
"counts-over-adjectives": [
 ("Cursor's prompt caps lint-fix loops at 3 per file.", G, "Cursor Prompts/Agent Prompt 2.0.txt"),
 ("The verifier requires at least one adversarial probe before PASS.", RW, "complete-prompts/agent-prompts/verification-specialist.md")],
"repo-map": [
 ("Aider builds the repo map with tree-sitter tags, personalised PageRank and a token-budget search.", AI, "aider/repomap.py")],
"bash-only-baseline": [
 ("The whole agent loop is one short file: query, execute, append.", MS, "src/minisweagent/agents/default.py"),
 ("Claude 4.5 Opus at high reasoning effort resolved 76.8% of SWE-bench Verified at $0.75 per instance (bash-only, one attempt).", "SWE-bench/experiments", "evaluation/verified/20260217_mini-v2.0.0_claude-4-5-opus-high/metadata.yaml"),
 ("Claude 4.6 Opus resolved 75.6% at $0.55 per instance under the same setup.", "SWE-bench/experiments", "evaluation/verified/20260217_mini-v2.0.0_claude-4-6-opus/metadata.yaml")],
}
WEB = {
 "trigger-only-descriptions": [("Anthropic's skill best-practices page covers writing effective descriptions.", "https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices")],
 "size-by-context": [("Anthropic's context-engineering post is qualitative and gives no estimation method.", "https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents"),
                     ("Token counts from the count_tokens endpoint are estimates.", "https://platform.claude.com/docs/en/build-with-claude/token-counting")],
 "handoff-for-a-successor": [("Anthropic describes progress files and feature lists for long-running agents.", "https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents")],
 "repo-map": [("Aider documents its repo map and token budget.", "https://aider.chat/docs/repomap.html")],
 "bash-only-baseline": [("The mini-swe-agent documentation site.", "https://mini-swe-agent.com/latest/")],
}
missing = []
for cid in os.listdir(os.path.join(BASE, "refpatch")):
    cid = cid[:-5]
    p = os.path.join(BASE, "refpatch", cid + ".json")
    d = json.load(open(p)); claims = []
    for text, repo, path in C.get(cid, []):
        rp, how = resolve(repo, path)
        if rp and how in ("exact", "dir") or (rp and how in ("basename", "suffix") and path.endswith(os.path.basename(rp))):
            claims.append({"text": text, "repo": repo, "path": rp, "url": gh(repo, rp)})
        else:
            missing.append((cid, repo, path))
    for text, url in WEB.get(cid, []):
        claims.append({"text": text, "repo": "", "path": url.split("//")[1], "url": url})
    d["claims"] = claims
    json.dump(d, open(p, "w"))
    print(cid, len(claims))
print("MISSING:", missing)
