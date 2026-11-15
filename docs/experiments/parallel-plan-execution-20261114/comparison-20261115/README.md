# Comparison of worker systems across harnesses, and two model opinions (2026-11-15)

Journal: [E14](../../../shiploop-parallel-execution-journal.md). The owner asked for a comparison of how workers work in Claude Code, Codex, Grok Build and other harnesses
(read as the DeepSeek, Kimi, Qwen and other labs' harnesses too), and for when to use them to save time, and asked Opus and Astra for comparisons.

| File | What it is |
| --- | --- |
| `brief.txt` | The one question sent to both models: parts A (a harness comparison from their own knowledge), B (their model of when fan-out pays), C (a critique of the owner's measurements, read after the appendix of measured numbers). |
| `opus.md` | Opus 5.5 at xhigh, read-only tools, verbatim. It fetched vendor pages by URL; it could not run a web search. |
| `astra.md` | GPT-6 Astra at max effort, consult profile, read-only sandbox, verbatim. It had web access and cited versioned sources. |
| `research-claude-code.md` | A research sub-agent's report on Claude Code's sub-agents, agent teams, limits and Anthropic's multi-agent write-up (official docs). |
| `research-codex-copilot.md` | The same for Codex (V1 and V2 tools, limits, source-checked at tag rust-v0.169.0) and GitHub Copilot's parallel agents. |
| `research-grok-kimi-deepseek-qwen.md` | The same for Grok Build, Kimi (Agent Swarm, Kimi Code CLI), the DeepSeek Harness, Qwen Code, GLM's ZCode and MiniMax Code. |
| `research-cursor-opencode-gemini-others.md` | The same for Cursor, OpenCode, Gemini CLI, Amp, Cline, Roo Code, Aider, OpenHands and LangChain Deep Agents. |
| `research-evidence.md` | Published evidence for and against multi-agent speedups in coding, with each source tagged as a vendor claim, an independent measurement or an opinion. |

The five research files are model reports (web research by sub-agents): their claims are theirs and carry the tags they gave. The two answers are model opinions.

## What I checked, and what I did not

Checked against this repository's own records (all held): the F13 pilot's fresh-worker cost (1.25 min, 1.2 M input tokens each), the census counts (928 plans, 600 single-step, 92 with an
independent pair, width 3 in 23 plans and 4 or more in 5, median step 154 s, 11.6% and 20.8% ideal savings, the 21 plans that save anything), the family-weighted census figure Astra quoted
(1.6% to 1.7%, `census/README.md`), and Astra's parent-context peaks (45,035 tokens under A3 against 40,247 under A0 on Claude, `evidence/r1h-claude-a*/context.json`; the 0.73 figure is the
cumulative input over fewer calls, not a smaller resident context).

Spot-checked on the web (a search each, 2026-11-15): CooperBench (arXiv 2601.13295) exists, 652 tasks over 12 libraries, agents average 30% lower success working together than solo, two to four
agents decline monotonically, messaging reduces textual merge conflicts without raising success; Cursor's July 2026 swarm post exists (SQLite rebuilt in Rust from the manual, more than 70,000
merge conflicts in the old swarm against under 1,000, a neutral merge agent; pass-rate figures conflict between write-ups); Geng and Neubig (arXiv 2603.21489, CAID: a manager and worktree
engineers) exists with accuracy gains reported, but I found no wall-clock figure to confirm the agent's "692.6 to 1,583.2 s"; Mieczkowski et al. (arXiv 2603.12229, "Language Model Teams as
Distributed Systems") exists and its results follow Amdahl's law, but I could not confirm the agent's Sonnet 4.6 speedups (3.35, 1.30, 0.79 at 90, 50 and 20% parallel fraction); the concurrency
study Astra cites (Li et al., "dynamic concurrency", 354 tasks, 2,124 executions, runtime up in 14 of 15 agent and benchmark groups) was found only through two secondary write-ups
(a Chinese-language report of 2026-10-19 and agentpatterns.ai), not the arXiv page, and its arXiv number (2610.10263, from Astra) is unconfirmed.

Not checked: the version-by-version limits of products I did not run (Cursor, OpenCode, Gemini CLI, Amp, Cline, DeepSeek Harness, Qwen Code, ZCode, MiniMax Code, Copilot); the sub-agents
fetched the vendor pages themselves and report them as read. Where the models disagree (Cursor's nesting: Opus says one level, Astra and the research agent say two) I wrote "two layers per the docs"
and left it there.

## Measurements made for this comparison

- `../census/rescore.py` and `../census/evidence/rescore.txt`: the E0 census's ideal saving with a per-round fan-out overhead subtracted (Opus's first suggested measurement, which costs no model call).
- `../decompose.py`: E12's and E13's fan-out saving split into overlapped waits and overlapped model time.
- Six registered trials of a control arm, one context that overlaps its own waits (README A11 and A12, `../packets/task-A0p.md`, `../a0p_table.py`, `../evidence/e14-*`): journal E14.
