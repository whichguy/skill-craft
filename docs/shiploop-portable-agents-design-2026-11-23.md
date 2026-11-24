# ShipLoop portable native agents: design and portability contract (2026-11-23)

Status: **design only; nothing built in `skills/` or `agents/`.** Written in task worktree `/Users/dadleet/src/skill-craft-shiploop-always-agents-df4c` (branch `cursor/shiploop-always-agents-df4c`) based on `origin/main` at `d0185ef5dd4cab7438834be1c3cf42b4006928b8` (skill-craft 4.6.0, ShipLoop 2.8.0, Improve 0.7.3, Ask Agent 0.11.0).

Consumer: first the owner, deciding D1–D5 (§7), then the session that runs the Phase 0 cross-host probe and implements the approved phases (§6).

## 0. Direction and preserved decisions

Owner direction (2026-11-23):

1. **Granularity — inline core loop + selective native agents:** keep the core SDLC build loop (`intake` through `handoff`, including `step-plan`, `test-spec`, `validate-existing`, `implement`, `test`, `document`, `carry-forward`) inline in the invoking conversation; use **native agents** for **reviews** (evaluating **forked context** vs **fresh context** — see §2.1 and D1) and **in-stage parallel read-only exploration/research**.
2. **Layer architecture — direct ShipLoop worker briefs + thin shared host-bindings data:** drop the heavy `ask-agent` workspace-helper / `improve-agent` / `plan-dispatcher` / `in-parallel` orchestration chain inside the new `agents` route; extend the thin host-detection and measured-bindings data (`ask_agent_host.py` / `host-bindings.json`) to **Cursor** (and **OpenCode**) and let ShipLoop emit compact, self-contained, tool-name-agnostic worker briefs directly.
3. **Delegation modes (D3, decided 2026-11-23):** **keep `ask-agent` as a third mode** alongside `inline` and the new `agents` route (`DELEGATIONS = ("inline", "agents", "ask-agent")`), so existing `ask-agent` workflows remain intact while `agents` is qualified.
4. **Portability target:** one portable prompt contract across **Cursor** (IDE and CLI), **Claude Code**, **Codex**, **Grok Build**, and **OpenCode**, without hardcoding host-specific tool names into stage prose.

Standing repository decisions preserved (not reopened here):

- **Per-step iteration and commit stage** (`8eca9d64826e0073540b6029b6071fc91b553e8e`, design T §8–§9): each step is built, tested, documented, reviewed, and committed by ShipLoop before the next step starts; no parallel build steps or implementation chain.
- **No silent state migrations** (`a8302f258027c901896ddbac96d3effde9f2cbff`, `b960891b8`): saved runs from an older state schema are refused with a clear hint rather than silently migrated. (Keeping `ask-agent` as an explicit third value of `delegation` adds a new option value without migrating legacy formats.)
- **Honesty: discovery ≠ execution** (`docs/ARCHITECTURE.md`): installing a skill or reading a live tool schema does not qualify a host for runtime claims; every host binding carries an explicit qualification status and tested version.
- **No silent downgrades or tool restrictions** (`skills/ask-agent/SKILL.md`, `skills/improve/SKILL.md`): fresh workers inherit the host's model, effort, tools, skills, and task authority unless the user explicitly asks otherwise.
- **No model subprocess launchers, no `/clear` pauses** (`docs/shiploop-clear-ledger-experiments-2026-09-21.md`): ShipLoop scripts never spawn models or pause for context resets (packet-driven `/clear` failed 0/2 on Claude and 0/4 on Grok).
- **Priority order:** quality > tokens > time.

---

## 1. Evidence behind this shape

Every structural choice below rests on measurements already recorded in this repository:

| Question | Recorded evidence | Consequence for this design |
|---|---|---|
| Why keep the core build loop inline instead of spawning a fresh worker per stage/step? | Per-step pilot (`eadad0c84f8a213287459bbf6252411ac0b90fce`, Codex `gpt-6.1-terra` xhigh, 2 steps): 13 serial fresh workers took **21.6 min / 23.1M input / 105k output** vs **5.3 min / 8.1M / 23k** inline (**4.1× slower, 2.9× input tokens**). In `E17` (`9dd67bdfa`), serial fresh workers (`qs`) were **1.64× slower on Claude** and **1.47× on Grok** than inline (`s`). | Do not pay cold-start (~27k–86k startup tokens, 15–45 s) on tightly coupled build stages (`step-plan` → `test-spec` → `implement` → `test` → `document`). |
| Why use a fresh worker for reviews instead of inline self-review? | Builder self-look (`85d61ec79`, `docs/ratchet-vs-shiploop-journal.md` §18) recorded "works" **4 of 4 times**. Fresh reviewers (`b630b965c`, `docs/ratchet-pilot-journal.md` Part R) caught a planted defect **6 of 6 times** with **62 of 62 real findings** (0 false positives), though their accept/reject verdict was too strict as a hard gate (rejected a valid build 4 of 6 times on open choices). | Reviews are where context freshness and independence actually pay off in product quality. |
| Why one **coding-capable** fresh Improve worker instead of read-only reviewer(s) handing findings back to the inline builder? | (1) `547ab12e5` (`docs/ratchet-vs-shiploop-journal.md` §20): a fresh read-only finder caught real defects, but handing them to the medium-effort inline builder produced minimal patches (e.g., a 1-line README disclaimer) and **no net gain** over unchanged ShipLoop at 1.4×–2.0× minutes. (2) Round 3 (`e68a5fc4`, `docs/shiploop-sdlc-structure-journal.md` `F13`–`F16`): 3 plain or 3 lens read-only reviewers caught only 17%–22% of end-of-work defects while generating ~30 unverified findings/step of triage noise. | Make the fresh review worker the coding-capable Improve executor itself (inheriting full model/effort/tools) so the fresh eyes both find and properly fix + test defects, rather than spawning a panel of read-only reviewers. |
| Why allow in-stage parallel read-only exploration/research, but not parallel build steps? | `E0` & `E16` (`3070bde12`): 65% of 922 step plans are single-step, 24% pure chains, 96.4% of 750 runs had 1 work item; concurrent writes also conflict with ShipLoop's step commit stage (`8eca9d648`). Meanwhile `E12` (`2adb7b5d6`) showed read-only fan-out cuts wall-clock **25%–56%** once independent tasks exceed ~20–30 s of work, with zero merge cost. | Confine parallel fan-out inside ShipLoop to **read-only** exploration/research (`discovery`, `research`, optionally `product-acceptance`) where there is no write conflict or merge step. |
| Why drop `ask-agent` workspace helpers, `improve-agent`, `plan-dispatcher`, and `in-parallel` from ShipLoop's hot path? | Today's `--delegation ask-agent` Improve launch traverses **7 files (~1,500+ lines)** across 4 skills (`shiploop` → `improve-context.md` → `shiploop-route-ask-agent.md` → `improve-agent` → `ask-agent` → `consumer-owned-workspace.md` → `host-capabilities.md`) — while `consumer-owned` explicitly disables every `ask-agent` workspace script (`prepare`, `inspect`, `check-context`, `close`) because ShipLoop already owns the worktree. `plan-dispatcher` adds Node.js 18+ and heavy latency (`F3`: 587 s for a 60 s ideal fan-out). `in-parallel` requires nested subagents (broken on depth-1 Grok and fragile on headless Claude `2.1.296`). | ShipLoop already owns the worktree, packet files, checks, and commits. Emit a ~20-line worker brief directly from `shiploop`, backed only by the thin host-bindings data layer. |
| Why do tool-name-agnostic prompts + thin host-bindings data work across hosts? | `E10`/`E11` (`d717bef0e`, `fbfebee74`): a neutral prompt spawned native subagents reliably on Claude Code, Codex, and Grok Build without host-specific spawn wording. The **only** host-specific details that measurably changed outcomes were **Codex's 4-slot cap (3 workers)** and **Codex's long wait (`timeout_ms: 120000`, cutting polls 12→3 and total tokens -11.5%)**, plus exact-name innermost-first host detection (never prefix matching, because `CODEX_COMPANION_*` leaks into Claude and Grok). | Keep stage and worker prompts host-neutral; inject only a 2-line detected-host quirk hint from machine-readable binding data. |

---

## 2. Target architecture: two native-agent surfaces in ShipLoop

In the new design, the invoking conversation owns the ShipLoop control plane (`state.md`, all `shiploop complete` callbacks, workspace start/return, and user communication) and executes every producer stage inline. Native subagents are used in exactly **two** bounded surfaces:

```text
Parent session (single ShipLoop control plane; runs all producer stages inline)
  │
  ├── Surface 1: Fresh Review Worker (Improve stages)
  │     • 1 fresh general-purpose coding-capable native worker (serial, exclusive writer in WORKTREE)
  │     • Driven by ShipLoop-generated CHILD/worker-brief.md -> CHILD/handoff.md + CHILD/packet.json
  │     • Runs selected improve/SKILL.md inline inside the worker (fixes + tests + improve-pass/commit)
  │     • Returns compact summary; parent verifies receipt/diff and runs `shiploop complete`
  │
  └── Surface 2: In-Stage Parallel Read-Only Workers (discovery, research, product-acceptance)
        • Optional fan-out of 2..capacity fresh general-purpose native workers
        • Strictly read-only on WORKTREE and RUN; F17 process/port/TMPDIR isolation rules
        • Parent collects all workers, synthesizes/verifies findings, writes stage result, runs `complete`
```

### 2.1 Surface 1 — Fresh Review Worker (Improve stages)

#### Lifecycle (single hop, zero middleman skills)

1. **Transition (script-owned, unchanged):** When a reviewed producer submits `done`, ShipLoop already resolves the Improve card, writes `CHILD/opening.md`, freezes `CHILD/start.json`, starts the ephemeral Until Loop runtime (`CHILD/packet.json`), and writes `CHILD/handoff.md`.
2. **Worker brief generation (new, script-owned):** At that same transition (and on `next` recovery), ShipLoop also writes **`CHILD/worker-brief.md`** (~20–25 lines, <2 KB) containing every path, invariant, and return requirement the fresh worker needs.
3. **Parent Improve packet (`improve_packet()`):** Instead of pointing through `improve-context.md` → `improve-agent` → `ask-agent` → `consumer-owned-workspace.md`, `improve_packet()` prints a compact 3-step parent instruction (~12–15 lines total):
   - **Step 1 — Launch one fresh review worker:** Launch one fresh general-purpose native subagent (inheriting current model, effort, tools, and permissions; no history fork; no extra worktree) using the worker prompt in `CHILD/worker-brief.md` (or passing the concise 12-line prompt printed inline that points to `CHILD/worker-brief.md` and `CHILD/handoff.md`), **plus** a brief `Conversation context` note only if this chat holds user approvals, declines, or live corrections not yet recorded in `state.md` or `RUN/owner-notes/`. Include the 2-line detected-host quirk note (§3.2). Prefer foreground/blocking execution when the host supports it.
   - **Step 2 — Verify return:** After collecting the worker's actual native return (never from files alone), confirm `CHILD/packet.json` reports terminal `complete`, review the returned findings/changes/checks, and confirm the worker has finished writing.
   - **Step 3 — Parent-only callback:** Run `shiploop complete --action=<improve id>` (with `--notes` / `--final-result` / `--no-commit` if warranted). The worker never runs `complete` or workspace return.
4. **Inside the worker (`CHILD/worker-brief.md`):**
   ```markdown
   # ShipLoop fresh review worker

   Role: You are the sole leaf Improve worker for this review stage (<stage>, <improve_id>).
   Work directly in your own context. Do NOT spawn subagents, do NOT start another ShipLoop
   run, and do NOT run `shiploop complete` or workspace return.

   Workspace: <WORKTREE>
   Before any read or edit, verify your shell cwd and Git root match <WORKTREE>
   (`pwd` and `git rev-parse --show-toplevel`). Use <WORKTREE> as the working directory
   for every shell command and absolute paths for file tools. Stop and return BLOCKED on mismatch.

   Assignment:
   1. Invoke the Improve skill at <ABS_IMPROVE_SKILL_MD> with argument:
      ShipLoop Improve: <CHILD/handoff.md>
      (Use the host's skill tool if available for skill "improve"; otherwise read that SKILL.md
      directly and follow its "ShipLoop whole-skill subcall" section.)
   2. Read <CHILD/handoff.md> and <ROUTE> with a file-reading tool (not cat), then continue the
      already-started loop from <CHILD/packet.json>'s `next_argv` until the runtime returns
      terminal `complete` (or `stopped`/`blocked`).
   3. You are a coding-capable reviewer and the exclusive writer in <WORKTREE> until you return:
      inspect, run checks, make warranted in-scope fixes and regression tests, write
      `CHILD/reviews/review-<n>.md` and `CHILD/reviews/checks.md`, and end each pass with the
      handoff's `improve-pass` and `done` commands. Follow the handoff's commit rule exactly.

   Return inline to the parent:
   - Terminal runtime status (`complete`, `stopped`, or `blocked` with blocker)
   - Observed workspace, Git root, initial/final HEAD, and changed paths (or commit SHAs)
   - Key findings, fixes made, and checks run (with pass/fail counts)
   - Paths to `CHILD/packet.json` and `CHILD/reviews/`
   - Confirmation that all writes finished and no parent callback (`complete` / workspace return) ran.
   ```
5. **What stays in `improve` (`skills/improve/`):**
   - `skills/improve/references/shiploop-route.md` already says: *"No agents. Do every review, check and commit here, never clearing or handing off; start no reviewer, test-runner or executor agent."* That rule works **identically** inside the fresh review worker!
   - Replace the stale 33-line `skills/improve/references/shiploop-route-ask-agent.md` (which still references Ask Agent's old "default extra-worktree route" and `improve-agent`/`host-owner.md`) with a short ~10-line worker note in `shiploop-route.md` (or `shiploop-route-worker.md`): *"When running as a ShipLoop fresh review worker, follow `CHILD/worker-brief.md`: run passes inline in your own context, use `improve-pass`/`improve-commit` as printed, and return without executing the parent's `complete` callback."*

#### Context mode for review workers: **Forked** vs **Fresh** (Owner insight, 2026-11-23; Decision D1)

The owner raised a key design consideration: running Improve in a **forked context** (a child subagent that inherits the parent's conversation history so it already knows all context and decisions, while isolating Improve's review passes and tool calls so they do not bloat the parent's context window) vs a **fresh context** (no parent history; orients from `CHILD/worker-brief.md`, `CHILD/handoff.md`, `KNOWLEDGE/`, and `git diff`).

| Property | **Forked context** (inherits parent history) | **Fresh context** (no parent history) |
|---|---|---|
| **Context orientation** | Instant — already knows every user nuance, rejected approach, and file read so far. No risk of "not knowing what to do". | Relies on ShipLoop's durable files (`CHILD/handoff.md`, `KNOWLEDGE/`, `RUN/owner-notes/`) plus parent's short `Conversation context` note. |
| **Startup cost & cache hit** | Reuses the parent's cached prompt prefix — near-zero cold-start re-reading! | Pays cold-start (~27k–86k startup tokens) and re-reads target files from disk. |
| **Parent context isolation** | **Yes** — all Improve review passes, diffs, and test runs stay inside the forked child and never bloat the parent's history (`eeb31fdca`: 56% of Sonnet bill is parent history re-read). | **Yes** — same parent isolation. |
| **Confirmation bias / independence** | **Risk (unmeasured for forked Improve):** inherits the builder's own reasoning chain and rationalizations; inline builder self-look recorded "works" 4/4 (`85d61ec79`). Needs paired measurement against fresh! | **Proven independent:** fresh reviewers caught 6/6 planted defects with 62/62 real findings (`b630b965c`). |
| **Cross-host availability** | **Host-dependent — must verify in Phase 0!** Cursor `Task` supports `resume: "self"`; Codex `spawn_agent` has `fork_turns` (check allowed values); Claude Code & Grok Build fork support must be verified live in Phase 0. | Supported across all four target hosts (Claude, Codex, Grok, Cursor). |

**Portable hybrid design:**

- `host-bindings/v2` records **both** `fresh_args` and `fork_args` (nullable when a host has no native fork).
- Even when a review worker runs in a **forked** context, ShipLoop still writes `CHILD/worker-brief.md` and `CHILD/handoff.md` so:
  1. On a host that supports native fork (when fork mode is chosen), the forked worker gets full conversation memory **plus** the exact anti-recursion, directory, and parent-only-callback boundaries.
  2. On a host without native fork (or on cold crash recovery after the parent session ended), the exact same `CHILD/worker-brief.md` + `CHILD/handoff.md` runs cleanly in a **fresh** worker without losing orientation or breaking portability.
- This also opens a clean **hybrid by review kind** to compare in Phase 3:
  - **Planning reviews** (`spec`, `test-strategy`, `plan`, `step-plan`, `system-test-author`, `release-plan`): highest dependence on nuanced conversation context → **forked** (or inline).
  - **Code & end-of-work reviews** (`document` step review + `carry-forward` end-of-work review): highest risk of builder confirmation bias, and full artifacts (`git diff`, `spec.md`, `handoff.md`, tests) are on disk → compare **forked** vs **fresh** in Phase 3!

#### Which Improve stages get a delegated worker? (Decision D1)

ShipLoop has 8 possible Improve checkpoints (`skills/shiploop/scripts/shiploop_stage_spec.py`):

| Group | Stages | Count in a typical 1-item, 1-step run | Trade-off |
|---|---|---|---|
| **Code & end-of-work reviews** (`item`, `last-item`) | Each step's `document` review; final `carry-forward` end-of-work review | 2 (or `steps + 1`) | Highest value for fresh/forked isolation: attacks builder bias and keeps code-review tool spam out of parent context. |
| **Planning & outer reviews** (`always`, `first-item`) | `spec`, `test-strategy`, `plan`, `step-plan` (item 1 / send-back), `system-test-author`, `release-plan` | 4–6 (2 when `--planning-review none`) | Forked context solves both the orientation gap ("knowing what to do") and parent context bloat without cold-start re-reads; fresh context adds cold-start tax on low-edit Sol reviews (3/82 edits, `eeb31fdca`). |

Phase 0 probes native fork support across all four hosts first so D1 (forked vs fresh vs hybrid) can be chosen on real host capability data rather than guesses.

### 2.2 Surface 2 — In-Stage Parallel Read-Only Exploration & Research

#### Applicable stages

- **`discovery`:** codebase architecture/conventions, existing test harnesses/linters/CI, and delivery/consumer boundaries are naturally independent read-only investigations.
- **`research`:** resolving 2+ independent technical unknowns, library/API checks, or reuse-vs-build surveys.
- **`product-acceptance`:** optionally checking 2+ independent acceptance surfaces or requirement groups against the assembled candidate (read-only inspection or isolated temporary-copy execution).

*(Not `intake`, `spec`, `plan`, `step-plan`, `test-spec`, `validate-existing`, `implement`, `test`, `document`, `carry-forward`, or `release*`: single-writer stages stay strictly serial and inline.)*

#### Fan-out predicate (when to spawn vs stay inline)

Grounded in `E12`, `E14`, and `E15`:

1. **Width ≥ 2:** At least two genuinely independent read-only questions that do not depend on each other's answers.
2. **Task size ≥ ~20–30 s of model work each:** Broad codebase exploration, multi-file tracing, or external/doc research — **never** spawn a subagent to read 1–2 known files or run one quick command (fixed spawn cost is ~15–43 s and 27k–86k tokens).
3. **Capacity cap:** Launch at most `min(questions, capacity)` concurrent workers, where `capacity` comes from the host binding (**3 on Codex**, default max 4 when the host binding specifies `null`). Launch the batch in a single assistant turn where supported; wait with `timeout_ms: 120000` on Codex.
4. **Automatic serial fallback:** If the host has no usable native subagent tool (or only 1 question applies), run the investigation directly inline — no error, no blocker.

#### Mandatory Read-Only Isolation Contract (incorporating Round 3 `F17`)

Round 3 (`docs/shiploop-sdlc-structure-journal.md` R21, `F17`) proved that concurrent read-only workers leave the shared checkout byte-identical (18/18 clean) **yet still collide outside it** via `pkill -f` (7/108 readers), shared ports (3 cases), shared `/tmp/<name>` files (3/6 rehearsal readers), and read-only copied trees (49/108 readers). Every read-only worker prompt emitted or composed under ShipLoop MUST carry these five rules:

1. **Read-only on `WORKTREE` and `RUN`:** Create, edit, stage, commit, or delete nothing inside `WORKTREE` or `RUN`. Avoid incidental bytecode writes (`PYTHONDONTWRITEBYTECODE=1` / `python3 -B`).
2. **Private scratch directory:** If running probes or testing a copy of the code, create a unique temporary directory (`mktemp -d`), ensure copied files are writable (`chmod -R u+w`), keep all temporary files inside it (`TMPDIR=<scratch>`), and remove it before returning. Never write to fixed `/tmp/...` paths.
3. **Ephemeral loopback ports only:** Any local server started for a probe must bind `127.0.0.1` on port `0` (OS-assigned). Never use hardcoded ports or wildcard binds (`0.0.0.0` / `::`).
4. **PID-scoped cleanup only:** Track and stop only exact PIDs this worker started. Never run `pkill -f`, `killall`, or name-pattern kills.
5. **Leaf worker & compact return:** Do not spawn subagents or run ShipLoop commands (`complete`, `next`, etc.). Return concise factual answers with exact `path:line` or command-output locators, distinguishing observed facts from hypotheses.

---

## 3. Cross-host portability contract & thin host-bindings layer

### 3.1 Architecture: self-contained packages, single schema, CI-enforced parity

Because every `skills/<leaf>/` package must remain self-contained and individually installable (`docs/ARCHITECTURE.md` — no escaping symlinks or cross-skill runtime imports), host bindings use a **shared JSON schema (`host-bindings/v2`)** mirrored in two places and pinned equal by a hermetic test:

- `skills/shiploop/references/host-bindings.json` + `skills/shiploop/scripts/shiploop_host_bindings.py` (used by `shiploop_navigator.py` at packet render time AND by `shiploop_grants.py` `detect_host()`)
- `skills/ask-agent/references/host-bindings.json` + `skills/ask-agent/scripts/ask_agent_host.py` (standalone Ask Agent host command)
- **Parity test** (extending `test/ask-agent-host.test.py`): asserts that `skills/shiploop/references/host-bindings.json` and `skills/ask-agent/references/host-bindings.json` have identical `detect` and `hosts` payloads, and that `shiploop_grants.detect_host()` agrees with `ask_agent_host.detect()` over every marker combination.

### 3.2 Emit-time host hints (zero extra tool call, zero state coupling)

When `shiploop` prints a packet that uses native agents (Surface 1 Improve packet, or Surface 2 `discovery`/`research`/`product-acceptance`), `shiploop` inspects `os.environ` **at render time**:

- **Never stored in `state.md`:** resuming a run on a different host automatically adapts on the next `shiploop next`.
- **Compact (2 lines):** prints *only* the detected host's actionable quirks (never all five hosts' prose), plus the standing authority sentence: *"The live native tool schema wins over this host hint; where they differ, follow the live schema and disclose it."*
- **Deterministic testing & dry runs:** `render()` accepts an explicit `environ` / `--host auto|claude|codex|grok|cursor|opencode|unknown` parameter so hermetic tests and `graph-dry-run` stay deterministic regardless of the caller's environment.
- **No tool names in stage duties:** stage duties and `CHILD/worker-brief.md` remain 100% tool-name-agnostic; only the 2-line runtime hint names host-specific gotchas (e.g., Codex's `fork_turns="none"`, `timeout_ms: 120000`, and 3-worker cap; Cursor's `subagent_type="generalPurpose"` and avoiding `resume="self"` / `environment="cloud"`).

### 3.3 Exact host detection rules (innermost host first)

Exact environment variable names only — **never** match a prefix (`E10`, `d717bef0e`: `CODEX_COMPANION_SESSION_ID` and `CODEX_COMPANION_TRANSCRIPT_PATH` are set inside Claude Code and Grok sessions).

| Priority (innermost first) | Host ID | Exact non-empty env markers | Evidence / Phase 0 check |
|---|---|---|---|
| 1 | `codex` | `CODEX_SANDBOX`, `CODEX_THREAD_ID` | Measured in parent + subagent (`E10`, Codex 0.169.0). |
| 2 | `grok` | `GROK_AGENT`, `GROK_SESSION_ID`, `GROK_SANDBOX` | Measured in parent + subagent (`E10`, Grok Build 1.0.77). |
| 3 | `opencode` | `OPENCODE` *(confirm exact markers in Phase 0)* | Referenced in `shiploop_keepalive.py` line 464; **needs Phase 0 live verification**. |
| 4 | `claude` | `CLAUDECODE` | Measured in parent + subagent (`E10`, Claude Code 2.1.325). |
| 5 | `cursor` | `CURSOR_AGENT`, `CURSOR_CONVERSATION_ID` *(not `TERM_PROGRAM` or `CURSOR_TRACE_ID`)* | Observed live in Cursor IDE agent session 2026-11-23. **Phase 0 must verify:** (a) markers inside `cursor-agent` CLI, (b) markers inside a Cursor `Task` subagent, and (c) precedence when Claude Code is launched inside Cursor's terminal vs a Cursor agent launched from Claude Code (`CURSOR_AGENT` is agent-only, not plain terminal, which keeps `claude` ahead when `claude` runs in a Cursor terminal, while `codex`/`grok` launched inside a Cursor agent still win over `CURSOR_AGENT`!). |
| fallback | `unknown` | *(none matched)* | Not an error; emits the neutral portable instructions without host-specific quirks. |

*(Note: `CURSOR_PLUGIN_ROOT` is only set for plugin hooks, not ordinary shell commands; keep it in `shiploop_keepalive.py`, not as a generic agent marker unless Phase 0 shows it is set inside shell tool calls.)*

### 3.4 Five-host native agent compatibility matrix

Honesty boundary (`ARCHITECTURE.md`): cells distinguish **measured** behavior from **schema-inspected** and **unqualified** behavior.

| Dimension | Claude Code | Codex | Grok Build | Cursor (IDE & CLI) | OpenCode |
|---|---|---|---|---|---|
| **Qualification status** | **Qualified** for neutral spawn, fork, foreground parallel, micro review brief, F17 read-only, and subagent `PostToolUse(Skill)` (`2.1.330`, Phase 0 2026-11-23) | **Qualified** for neutral spawn, fork (`fork_turns: "all"`), fresh (`"none"`), micro review brief, and F17 read-only (`0.171.0`, Phase 0 2026-11-23) | **Qualified** for neutral fresh spawn, foreground parallel, micro review brief, and F17 read-only (`1.0.92`, Phase 0 2026-11-23); **no native fork** | **Cursor IDE: Qualified** for fresh, fork (`resume: "self"`), foreground parallel (93% overlap), micro review brief, and F17 read-only (Phase 0 2026-11-23). **Cursor CLI (`2026.09.23`): UNQUALIFIED** (`agent login` needed) | **Pilot only** (`1.18.31` persistent TUI); **UNQUALIFIED** |
| **Native spawn tool** | `Agent` (listed as `Task` in init stream) | `spawn_agent` (`collaboration.spawn_agent`) | `spawn_subagent` | `Task` (`cursor` namespace) | `task` |
| **General-purpose worker type** | `general-purpose` (or omit) | *(default general-purpose)* | *(default general-purpose; `subagentType` absent in `1.0.92` schema)* | `generalPurpose` *(camelCase!)* | *(default general-purpose)* |
| **Fresh context rule** | Omit `resume`; `subagent_type: "general-purpose"` (never `"fork"`) | **`fork_turns: "none"`** *(required — `"all"` is the `0.171.0` default!)* | Omit `resume_from` | Omit `resume` (**never** `resume: "self"`) | Omit `task_id` |
| **Forked context rule (inherit history)** | **`subagent_type: "fork"`** *(verified live `2.1.330`; inherits parent model/effort, ignores overrides)* | **`fork_turns: "all"`** *(verified live `0.171.0`; also default)* | **Not supported** (`has_fork: false`; falls back cleanly to fresh worker + `CHILD/worker-brief.md`) | **`resume: "self"`** *(verified live IDE 2026-11-23)* | **Unqualified** (likely fresh-only) |
| **Forbidden isolation args** | **Omit `isolation`** (`"worktree"` / `"remote"`) | *(none on spawn)* | **Omit `isolation: "worktree"`** *(added in `1.0.92`; mutually exclusive with `cwd`)* | **Omit `environment: "cloud"`** (runs on remote VM/worktree) | *(none on spawn)* |
| **Native `cwd` on spawn?** | **No** — prefix every Bash call with `cd "<WORKTREE>" &&` + abs file paths | **No** — set `workdir` on every shell call + abs file paths | **Yes** (`cwd: "<WORKTREE>"`), still verify `pwd` + Git root | **No** *(verified live IDE)* — set `working_directory` on Shell + abs file paths | **No** — set `workdir` on every bash call + abs file paths |
| **Serial review mode (Surface 1)** | **Foreground** (`run_in_background: false`) — blocks cleanly until return | **Async** `spawn_agent` + `wait_agent(timeout_ms=120000)` | **Foreground** (`background: false`, waits up to 10 min) — blocks cleanly until return | **Foreground** (`run_in_background: false`) — blocks cleanly until return | Foreground (or `background: true` in persistent TUI only) |
| **Parallel read-only fan-out (Surface 2)** | **Foreground parallel:** multiple `Agent(run_in_background=false)` in one turn *(verified live `2.1.330`: 3 workers concurrent in one turn, zero `Stop`-hook yield!)* | Up to **3 workers** (`4` slots incl. parent); `spawn_agent(fork_turns="none")` + `wait_agent(timeout_ms=120000)` | **Foreground parallel:** multiple `spawn_subagent(background=false)` in one turn *(verified live `1.0.92` concurrent streaming)*; or `background=true` + `get_command_or_subagent_output(timeout_ms=120000)` | **Foreground parallel:** multiple `Task(run_in_background=false)` in one turn *(verified live IDE: 5.60 s / 6.00 s = 93% overlap, zero `Stop`-hook yield!)* | Experimental flag `OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS=true` in TUI only; otherwise run serial |
| **Steer / cancel running worker** | `SendMessage` + `TaskStop` | `interrupt_agent` (`collaboration.interrupt_agent`) | `kill_command_or_subagent` | `Task(resume=id, interrupt=true)` (no dedicated stop-only tool) | Unqualified |
| **Subagent nesting / depth** | Depth 1 only for Surface 1 & 2 | Depth 1 only | Depth 1 only | Depth 1 only | Depth 1 only |
| **Keepalive & Skill-call hooks** | `PostToolUse(Skill)` **VERIFIED FIRING** inside BOTH fresh and forked depth-1 subagents (`2.1.330`) with parent's exact `session_id` + `agent_id` + `agent_type`! | `PostToolUse`, `Stop`, `SessionEnd` work in interactive + `exec`; no Skill hook | `PostToolUse`, `Stop` (8/turn cap), `SessionEnd` work; no Skill hook | IDE hooks active; `cursor-agent -p` never fires `stop` (`shiploop-drive` needed); IDE shell sandbox allows `../.shiploop-runs` and `.git`; no Skill hook | Plugin `session.idle` in TUI; `opencode run` needs `shiploop-drive`; no Skill hook |

Notice a major simplification achieved by this design: **both Surface 1 and Surface 2 are strictly depth 1** (parent → leaf worker; leaf workers never spawn subagents). That eliminates every nested-subagent failure mode seen on Grok (`1.0.50`) and headless Claude (`2.1.296`).

### 3.5 Concrete `host-bindings/v2` schema sketch

```json
{
  "schema": "skill-craft/host-bindings/v2",
  "authority": "The live native tool schema wins over this file: where they differ, follow the live schema and disclose the difference.",
  "detect": {
    "order": ["codex", "grok", "opencode", "claude", "cursor"],
    "markers": {
      "codex": ["CODEX_SANDBOX", "CODEX_THREAD_ID"],
      "grok": ["GROK_AGENT", "GROK_SESSION_ID", "GROK_SANDBOX"],
      "opencode": ["OPENCODE"],
      "claude": ["CLAUDECODE"],
      "cursor": ["CURSOR_AGENT", "CURSOR_CONVERSATION_ID"]
    }
  },
  "hosts": {
    "claude": {
      "name": "Claude Code",
      "status": "qualified",
      "tested": ["2.1.325", "2.1.330"],
      "tools": {"spawn": ["Agent", "Task"], "stop": ["TaskStop"]},
      "worker_type": "general-purpose",
      "serial_mode": "foreground",
      "parallel_mode": "foreground",
      "cwd_on_spawn": false,
      "fresh_args": {"subagent_type": "general-purpose", "run_in_background": false},
      "fork_args": {"subagent_type": "fork", "run_in_background": false},
      "background_args": {"subagent_type": "general-purpose", "run_in_background": true},
      "forbidden_fresh_args": ["isolation", "resume"],
      "collect_parallel": "issue multiple foreground Agent(run_in_background=false) calls in one turn (zero Stop-hook yield); if backgrounded, notifications re-enter as new turns — do not poll",
      "observation_timeout_ms": null,
      "capacity": null,
      "hint": "Use Agent (omit isolation and resume): subagent_type=\"general-purpose\" for fresh workers, subagent_type=\"fork\" for a forked review; use run_in_background=false (multiple foreground calls in one turn run concurrently); prefix every Bash command with cd \"<WORKTREE>\" &&."
    },
    "codex": {
      "name": "Codex",
      "status": "qualified",
      "tested": ["0.169.0", "0.171.0"],
      "tools": {"spawn": ["spawn_agent"], "wait": ["wait_agent"], "stop": ["interrupt_agent"]},
      "worker_type": null,
      "serial_mode": "async-wait",
      "parallel_mode": "async-wait",
      "cwd_on_spawn": false,
      "fresh_args": {"fork_turns": "none"},
      "fork_args": {"fork_turns": "all"},
      "background_args": {"fork_turns": "none"},
      "forbidden_fresh_args": [],
      "collect_parallel": "wait_agent with timeout_ms: 120000, not short polls",
      "observation_timeout_ms": 120000,
      "capacity": {"workers": 3, "slots": 4, "parent_holds": 1},
      "hint": "Use spawn_agent: fork_turns=\"none\" for fresh workers (default is \"all\"), fork_turns=\"all\" for a forked review; at most 3 concurrent workers (4 slots include the parent); wait with wait_agent timeout_ms=120000 (no short polls); pass explicit workdir on every shell command."
    },
    "grok": {
      "name": "Grok Build",
      "status": "qualified",
      "tested": ["1.0.77", "1.0.92"],
      "tools": {"spawn": ["spawn_subagent"], "wait": ["get_command_or_subagent_output"], "stop": ["kill_command_or_subagent"]},
      "worker_type": null,
      "serial_mode": "foreground",
      "parallel_mode": "foreground",
      "cwd_on_spawn": true,
      "fresh_args": {"background": false, "isolation": "none"},
      "fork_args": null,
      "background_args": {"background": true, "isolation": "none"},
      "forbidden_fresh_args": ["resume_from", "isolation"],
      "collect_parallel": "issue multiple spawn_subagent(background=false) calls in one turn (blocks up to 10 min), or background=true with get_command_or_subagent_output(timeout_ms=120000)",
      "observation_timeout_ms": 120000,
      "capacity": null,
      "hint": "Use spawn_subagent with cwd=\"<WORKTREE>\", background=false, and omit resume_from and isolation=\"worktree\" (no native fork on Grok: use the fresh brief); multiple foreground calls in one turn run concurrently."
    },
    "cursor": {
      "name": "Cursor",
      "status": "pilot-ide",
      "tested": ["ide-2026-11-23"],
      "tools": {"spawn": ["Task"]},
      "worker_type": "generalPurpose",
      "serial_mode": "foreground",
      "parallel_mode": "foreground",
      "cwd_on_spawn": false,
      "fresh_args": {"subagent_type": "generalPurpose", "run_in_background": false},
      "fork_args": {"subagent_type": "generalPurpose", "resume": "self", "run_in_background": false},
      "background_args": {"subagent_type": "generalPurpose", "run_in_background": true},
      "forbidden_fresh_args": ["resume", "environment"],
      "collect_parallel": "issue multiple foreground Task(run_in_background=false) calls in one turn (93% overlap verified, zero Stop-hook yield); if backgrounded, notifications arrive after turn end — do not poll",
      "observation_timeout_ms": null,
      "capacity": null,
      "hint": "Use Task with subagent_type=\"generalPurpose\" (omit environment=\"cloud\"): omit resume for fresh workers, resume=\"self\" for a forked review; use run_in_background=false (multiple foreground calls in one turn run concurrently); set working_directory on every shell call and use absolute file paths."
    },
    "opencode": {
      "name": "OpenCode",
      "status": "unqualified",
      "tested": [],
      "tools": {"spawn": ["task"]},
      "worker_type": null,
      "serial_mode": "foreground",
      "parallel_mode": "foreground",
      "cwd_on_spawn": false,
      "fresh_args": {},
      "fork_args": null,
      "background_args": {"background": true},
      "forbidden_fresh_args": ["task_id"],
      "collect_parallel": "requires OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS=true in a persistent TUI; otherwise run serially",
      "observation_timeout_ms": null,
      "capacity": null,
      "hint": "Use task without task_id and pass workdir on every bash call; background fan-out requires a persistent TUI with OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS=true (otherwise run serially)."
    }
  }
}
```

*(Note: `ask-agent` tests currently assert `ask-agent/host-bindings/v1` and `tested` semvers on every host in `hosts`. When extending `ask-agent`, either bump its schema to `v2` with explicit `status` gating — allowing empty `tested` only when `status == "unqualified"` — or update `test/ask-agent-host.test.py` together with the Phase 0 live measurements so Cursor enters with real observed versions!)*

---

## 4. Reconciling ShipLoop subsystems

### 4.1 Run option `delegation` and state schema

- Today: `state.md` records `delegation: inline | ask-agent` (`DEFAULT_DELEGATION = "inline"`).
- **Decided (D3, owner 2026-11-23):** Keep `ask-agent` as a third mode alongside `inline` and `agents`: `DELEGATIONS = ("inline", "agents", "ask-agent")`.
  - `inline`: strictly single-context, zero subagents (useful for benchmarking, non-agent hosts, or user override).
  - `agents`: inline core loop + Surface 1 (coding-capable Improve worker via direct ShipLoop brief — forked or fresh per D1) + Surface 2 (in-stage read-only fan-out in `discovery`, `research`, `product-acceptance`).
  - `ask-agent`: existing opt-in route preserved unchanged (`improve-agent` + `ask-agent` consumer-owned route + INNER workers).
- `shiploop delegation --run-dir RUN --set inline|agents|ask-agent` switches from the next issued action (preserving `delegation_hold`).
- Keep `DEFAULT_DELEGATION = "inline"` during Phases 1–2; flip to `"agents"` **only** after Phase 3's paired E2E comparison meets the acceptance bar.
- Keeping `"ask-agent"` avoids breaking existing `inline` and `ask-agent` runs (no forced state-version bump solely for removing a delegation value).

### 4.2 Fixing the Claude Code Skill-call gate & adding host-neutral review provenance

Today (`skills/shiploop/scripts/shiploop_navigator.py` lines 442–443), the Claude Code Skill-call gate **turns itself off** whenever `delegation != "inline"`, because `shiploop_keepalive.py` filters out subagent hooks (`_is_subagent`) and only looks up runs via the parent session's binding.

Fix both layers cleanly:

1. **Claude Code subagent Skill-call capture (SIMPLIFIED BY PHASE 0!):**
   - Phase 0 (`2.1.330`) verified live that Claude Code's `PostToolUse(Skill)` hook **ALREADY fires inside BOTH fresh (`general-purpose`) and forked (`fork`) depth-1 subagents**, carrying the parent's **exact `session_id`** plus `agent_id` and `agent_type`!
   - And `skills/shiploop/scripts/shiploop_keepalive.py::skill_call()` (lines 444–459) **already does not filter out `_is_subagent()`** and already passes `agent_id=payload.get("agent_id")` to `shiploop_skill_calls.record_call()`!
   - Therefore, keeping the Skill-call gate **enforced** on `--delegation agents` requires **zero hook rewrite** on Claude Code: simply allow `delegation(state) in (guidance.INLINE, guidance.AGENTS)` in `shiploop_navigator.py::_skill_call_record()` (line 442), and add `"CURSOR_AGENT"` alongside `"CURSOR_PLUGIN_ROOT"` in `shiploop_keepalive.py::NESTED_NON_CLAUDE` (line 464)!
   - Keep `observe`, `stop`, and `session-end` ignoring `_is_subagent(payload)`, so workers never steal keepalive ownership.
2. **Host-neutral review provenance (all hosts — Cursor, Codex, Grok, Claude, OpenCode):**
   - All existing script-enforced review gates remain active for fresh workers: `improve-pass` form validation, `checks.md` freshness check, `review-<n>.md` anti-repetition check, lint gate, step Proof/test rerun, and Until Loop receipt match.
   - Add a `review_mode` field (`fresh-worker` | `inline-fallback` | `inline`) passed on `shiploop complete --action=<improve id>` (optional, defaulting from `delegation`) and recorded in `RUN/improve/<reviewed action>/passes.md` and `trace.jsonl`, so E2E audits and Run Review can measure how often reviews ran fresh vs fell back.

### 4.3 Keepalive hooks, background tasks, and sandbox grants

- **Foreground serial reviews (Claude, Cursor, Grok):** Because the parent's subagent call is synchronous/blocking, the parent turn stays inside the tool call until the worker returns — no premature `Stop` hook firing, no `host-owner.md` background state tracking, no notification drop.
- **Async workers (Codex serial review; parallel read-only fan-out on Claude/Cursor/Grok):**
  - Keepalive's existing `_background_tasks(payload)` check refuses `Stop` when the host payload reports active background tasks. **Phase 0 must verify** whether Cursor's `stop` hook payload includes background task status (and whether Claude's `Stop` hook interacts cleanly with `run_in_background: true` turn-end notifications — note that on Claude and Cursor, background completion notifications re-enter the parent *after* the parent ends its turn, so a `Stop` hook that blocks the parent from ending its turn while waiting for a background notification would deadlock!).
  - **CRITICAL TRAP IDENTIFIED RIGHT HERE:** Look at Cursor's live `Task` tool description: *"When an agent runs in the background, you will be automatically notified when it completes after you end your own turn."* And Claude Code's `host-bindings.json`: *"completion notifications re-enter the parent as new turns; do not poll."* If `shiploop-keepalive-stop` blocks the parent from ending its turn whenever `backgroundTasks` is non-empty on Claude or Cursor, the parent can NEVER yield its turn to receive the completion notification!
  - **Design rule to resolve that trap:**
    - For **Surface 1 (serial review)** on Claude, Cursor, and Grok: use **foreground** (`run_in_background: false`) so the turn never needs to yield!
    - For **Surface 2 (parallel read-only fan-out)** on Claude and Cursor: test BOTH options in Phase 0 — (a) **multiple foreground parallel `Task`/`Agent` tool calls in one assistant message** (which run concurrently *within* the single turn and return all results before the turn ends — zero yield, zero keepalive conflict!!), vs (b) `run_in_background: true` with keepalive yielding cleanly. Option (a) (parallel foreground tool calls in one message) is vastly cleaner if Claude/Cursor execute them concurrently!
- **Cursor write grants (`shiploop_grants.py`):** Check in Phase 0 whether Cursor's shell sandbox blocks `<repo-parent>/.shiploop-runs` or `.git`, and add a `"cursor"` entry to `shiploop_grants._fixes()` if needed.

### 4.4 Approvals, owner notes, and crash recovery

- **Approvals & declines:** Keep `ask-agent`'s crisp rule in the parent's dispatch instruction: if the conversation has any user approval, decline, or constraint not yet captured in `state.md` / `RUN/owner-notes/`, append a short `## Conversation context` block to the worker's launch prompt (action, target, condition, source).
- **Owner notes:** Already persisted on disk and injected by `owner_notes.review_lines()` into `CHILD/handoff.md` — fresh review workers automatically see them.
- **Crash recovery (no `host-owner.md` ceremony):**
  - Native subagents die with their parent session on all hosts (`test/shiploop_e2e/LEARNINGS.md` line 669).
  - On cold recovery (`shiploop next`):
    - If `CHILD/packet.json` is `complete`, the parent verifies the receipt/diff and submits `complete --action=<improve id>` without spawning a new worker.
    - If `CHILD/packet.json` is `active` (previous worker died mid-loop), `CHILD/reviews/` already preserves completed passes; the parent launches one fresh worker on the same `CHILD/worker-brief.md` + `CHILD/handoff.md`, which continues from `CHILD/packet.json`'s `next_argv`.
    - Within one *live* parent session on an async host (Codex), if `wait_agent` times out without worker completion, the parent calls `wait_agent` again (never launches a second concurrent writer while the first handle is still alive).

### 4.5 Packet size & prompt hygiene

- `CHILD/worker-brief.md` lives on disk beside `CHILD/handoff.md` and `CHILD/opening.md`.
- `improve_packet()` grows by only ~4–6 lines (~350 bytes) on the `agents` route, keeping the printed packet well within ShipLoop's `--group prompt` packet-size bounds.
- Surface 2 guidance adds one compact ~6-line block (`read-only-fanout`, registered in `shiploop_stage_spec.BLOCKS` or in `discovery`/`research`/`product-acceptance` duties) + the 2-line host hint only on those stages, keeping all other 20 stages byte-identical.

---

## 5. Impact on the `ask-agent*` skill family

| Skill | Role after this change | Changes needed |
|---|---|---|
| `skills/ask-agent/` | Standalone user delegation (`current`, `worktree`, `helper-managed`, `consumer-owned`) and canonical host-binding reference | Extend `references/host-bindings.json`, `scripts/ask_agent_host.py`, and `references/host-capabilities.md` with Cursor & OpenCode (and `v2` fields). Keep all standalone routes unchanged. |
| `skills/improve/` | Core review-and-improvement engine (runs inline whether invoked directly or inside a fresh ShipLoop review worker) | Add concise worker-route note (~10 lines); retire stale `shiploop-route-ask-agent.md` references to `improve-agent` / "default extra-worktree route". |
| `skills/improve-agent/` | Standalone `/improve-agent` user entrypoint outside ShipLoop | Unchanged; no longer invoked by ShipLoop. |
| `skills/in-parallel/` | Standalone parallel-batch coordinator outside ShipLoop | Unchanged for now (separate future follow-up: read `capacity` from `host-bindings.json` instead of hardcoding 5 on Codex). |
| `skills/plan-dispatcher/` | Standalone DAG executor outside ShipLoop | Unchanged; never invoked by ShipLoop. |

---

## 6. Phased verification and rollout plan

Following `docs/ARCHITECTURE.md` (honesty: discovery ≠ execution) and `AGENTS.md` (evidence before shipping/changing defaults):

### Phase 0 — Cross-host live conformance probe (before changing ShipLoop code)

Run a small, cheap, scripted probe on **Cursor (IDE + CLI)**, **Claude Code**, **Codex**, and **Grok Build** (and OpenCode if available):

1. **Environment, nesting & sandbox probe (P0-A):**
   - Record exact env markers in parent and in a depth-1 subagent, plus nested combinations (e.g., Claude inside Cursor terminal; Codex/Grok inside Cursor agent).
   - Confirm Cursor's `cursor-agent` CLI markers, `Task` tool arguments, and whether Cursor's sandbox blocks `.shiploop-runs` or `.git`.
2. **Forked vs Fresh context probe (P0-B):**
   - Inspect each host's live native spawn tool schema for **forked context** support (Cursor `Task(resume="self")`, Codex `spawn_agent(fork_turns=...)`, Claude Code `Agent`, Grok Build `spawn_subagent`).
   - On every host that exposes fork, run a 1-step live fork probe: plant a secret fact in the parent conversation (not on disk), spawn a forked worker vs a fresh worker, verify (a) the forked worker sees the parent fact while the fresh worker does not, (b) the forked worker's intermediate tool calls stay out of the parent context, and (c) the forked worker honors the anti-recursion and cwd rules.
3. **Parallel foreground vs background & keepalive/hooks probe (P0-C):**
   - Test issuing **2 foreground `Agent`/`Task`/`spawn_subagent` calls in a single assistant turn** on Claude Code, Cursor, and Grok Build: do they execute concurrently and return within the same turn without yielding to the `Stop` hook?
   - Verify whether Claude Code's `PostToolUse` hook on `Skill` fires inside a depth-1 subagent (decides whether §4.2's subagent Skill-call capture enforces on Claude or must remain documented as host-limited).
4. **Micro end-to-end brief probe (P0-D):**
   - **Review brief:** in a scratch git worktree, parent spawns 1 coding-capable worker using the ~20-line file-pointer brief pointing to a synthetic `handoff.md` and `improve/SKILL.md`. Verify: `pwd`/Git-root verified, worker edits in place without creating a second worktree, worker does not spawn recursively, worker does not run parent callback, parent sees the edit.
   - **Read-only fan-out:** parent spawns 2 concurrent read-only workers with F17 rules on the same scratch repo. Verify: worktree byte-identical (`git status` + digest), no shared `/tmp` or port collision, clean collection.

Record measured versions and outcomes in `host-bindings.json` (only hosts passing P0-A..D get `status: "qualified"`).

### Phase 1 — Shared host-bindings layer + hermetic parity tests

- Update `skills/ask-agent/references/host-bindings.json`, `scripts/ask_agent_host.py`, `references/host-capabilities.md`.
- Add `skills/shiploop/references/host-bindings.json` + `skills/shiploop/scripts/shiploop_host_bindings.py` and wire `shiploop_grants.detect_host()` to it.
- Extend `test/ask-agent-host.test.py` with full parity and marker-combination checks across all 5 hosts.

### Phase 2 — ShipLoop direct worker briefs, Surface 2 guidance, and gate/provenance updates

- Implement `DELEGATIONS = ("inline", "agents", "ask-agent")` (keeping `inline` as default until Phase 3), `CHILD/worker-brief.md`, updated `improve_packet()`, Surface 2 read-only fan-out guidance + F17 rules on `discovery`/`research`/`product-acceptance`, emit-time 2-line host hints, `passes.md` `review_mode` provenance, and enabling the existing Claude Code Skill-call gate on `"agents"` (Phase 0 confirmed `PostToolUse(Skill)` already fires inside both fresh and forked subagents with the parent's `session_id`).
- Update `skills/improve/references/shiploop-route*.md` and `skills/shiploop/references/{run-options,improve-context,navigator,host-matrix}.md`.
- Verify offline: `bash test/run-all.sh --group prompt`, `--group shiploop`, `--group ask-agent`, and `python3 scripts/check-release-boundary.py`.

### Phase 3 — Paired E2E qualification before flipping the default

- Register and run a small paired comparison (`--delegation inline` vs `--delegation agents`) on 2 cases (one greenfield e.g. `node-chess-engine` or `shared-expenses`, one brownfield `ticket-assignment`) across at least **Claude Code (Sonnet medium)** and **Codex (Sol medium)**, plus a live verification run in **Cursor**.
- Measure: held-out acceptance checks, seeded-fault mutation catch, blind defect count, total wall-clock minutes, review minutes, total input/output tokens, dollar bill, and `review_mode` / refusal / hook fidelity.
- Flip `DEFAULT_DELEGATION` from `"inline"` to `"agents"` only if the paired evidence meets the owner's quality > tokens > time bar.

---

## 7. Open and settled decisions

| # | Decision | Status / Options | Recommendation / Outcome |
|---|---|---|---|
| **D1** | Review worker context mode and stage scope under `--delegation agents` | **Decided (owner, 2026-11-23): Hybrid** — **forked** for planning & outer reviews (`spec`, `test-strategy`, `plan`, `step-plan`, `system-test-author`, `release-plan`; fresh + 2-line conversation context fallback on Grok) and **fresh** for code & end-of-work reviews (`document`, `carry-forward`) to guard against builder confirmation bias. | Confirmed end-to-end across all 4 hosts in §9 (8/8 real ShipLoop Improve reviews passed). |
| **D2** | Behavior when `--delegation agents` runs on a host with no usable native subagent tool (or `unknown` host without native spawn)? | **(a) Graceful inline fallback** (run Improve / exploration inline, disclose it, record `review_mode: inline-fallback`) vs **(b) Fail closed** (block until the user switches `--delegation inline`) | **(a) Graceful inline fallback with explicit provenance** — keeps ShipLoop truly portable on any host while staying 100% honest in traces and Run Review. |
| **D3** | Legacy `--delegation ask-agent` route | **Decided (owner, 2026-11-23):** keep `ask-agent` as a third mode alongside `inline` and `agents` (`DELEGATIONS = ("inline", "agents", "ask-agent")`). | Keep `ask-agent` intact; add `agents` beside it; keep `inline` default until Phase 3 qualifies `agents`. |
| **D4** | How does the parent learn host-specific quirks? | **(a) Emit-time detection by `shiploop`** (reads `os.environ` at render time, prints a 2-line host hint directly in the packet; zero extra tool call; never persisted in `state.md`) vs **(b) Explicit command** (tell the model to run `shiploop host-binding` once per session) | **(a) Emit-time detection** — eliminates the "model forgot to run the host command" failure mode (`fbfebee74`) and keeps prompts minimal, with a `--host` override for deterministic dry runs and tests. |
| **D5** | Scope of Phase 0 live probes | **Completed (2026-11-23):** ran Phase 0 across Cursor IDE, Claude Code `2.1.330`, Codex `0.171.0`, and Grok Build `1.0.92` (`cursor-agent` CLI `2026.09.23` unauthenticated; OpenCode `1.19.4` left `unqualified`). | See §8 below. |

---

## 8. Phase 0 live probe results (measured 2026-11-23)

All probes ran against throwaway scratch Git repositories under `/tmp/shiploop-phase0-20261123/` (deleted after recording; zero edits to user profiles or repository checkouts; cross-host env prefixes scrubbed before launching each CLI).

### Summary table

| Host & build | Parent + subagent markers (`F31` depth marker?) | Native fork (`P0-B`: canary inherited vs fresh `null`) | Parallel foreground overlap (`P0-C`) | Surface 1 edit brief (`P0-D`) | Surface 2 F17 read-only (`P0-D`) | Extra checks |
|---|---|---|---|---|---|---|
| **Cursor IDE** (live session, 2026-11-23) | `CURSOR_AGENT`, `CURSOR_CONVERSATION_ID`, `CURSOR_REQUEST_ID`, `CURSOR_WORKSPACE_LABEL` (same in parent, fresh, fork; **no depth marker**) | **YES — `resume: "self"`** (`cobalt-7319-ide` vs fresh `null`) | **YES — 5.60 s / 6.00 s (93% overlap)** (`139.062..145.063` vs `139.464..145.464`, `run_in_background: false`) | **PASS** (`M calc.py`, 1 commit, `unittest` rc 0, `pwd == git_root` via `realpath`) | **PASS** (`git status ""`, port `62637`, scratch cleaned) | `shiploop_grants` outside `/tmp`: `runs_probe=null`, `git_probe=null`; `detect_host()` currently returns `"unknown"` |
| **Claude Code `2.1.330`** (`claude-sonnet-5-5`, medium; `31.9 s`) | `CLAUDECODE`, `CLAUDE_CODE_SESSION_ID`, `CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_PID` (same in parent, fresh, fork; **no depth marker**) | **YES — `subagent_type: "fork"`** (`amber-9042-claude` vs fresh `null`; runs on parent model/effort) | **YES — 3 foreground `Agent` calls concurrent in 1 turn** (`321.703..326.706` vs `323.942..328.945`, 2.76 s / 5.00 s overlap) | **PASS** (`M calc.py`, 1 commit, `unittest` rc 0, zero subagents) | **PASS** (`git status ""`, port `64134`, scratch cleaned) | **`PostToolUse(Skill)` FIRED inside BOTH fresh (`general-purpose`, 6.5 s) AND forked (`fork`, 7.1 s) depth-1 subagents** with parent's exact `session_id` + `agent_id` + `agent_type`! |
| **Codex `0.171.0`** (`gpt-6.2-sol`, medium; `63.8 s`) | `CODEX_THREAD_ID`, `CODEX_SESSION_ID`, `CODEX_HOME`, `CODEX_VERSION` (same in parent, fresh, fork; **no depth marker**) | **YES — `fork_turns: "all"`** *(and `"all"` is now default! `"none"` starts fresh)* (`amber-9042-codex` vs fresh `null`; 4 rollout threads at depth 1) | Async `spawn_agent` + `wait_agent` (no blocking spawn; `wait_agent` blocks inside turn with `timeout_ms=120000`) | **PASS** (`M calc.py`, 1 commit, `unittest` rc 0, zero subagents) | **PASS** (`git status ""`, port `64275`, scratch cleaned) | Live tools: `collaboration.spawn_agent`, `wait_agent`, `interrupt_agent` |
| **Grok Build `1.0.92`** (`grok-4.6`, medium; `133.9 s`) | `GROK_AGENT`, `GROK_SESSION_ID`, `GROK_CONFIG_DIR` (same in parent and subagents; **no depth marker**) | **NO (`has_fork: false`)** — `resume_from` resumes a child transcript only; clean fallback to fresh brief | **YES — 2 foreground `spawn_subagent(background=false)` calls streamed concurrently in 1 turn** (Worker B hit one `--permission-mode auto` prompt on `mktemp`/socket and succeeded on parent retry) | **PASS** (`M calc.py`, 1 commit, `unittest` rc 0, zero subagents) | **PASS** (`git status ""`, port `64608`, scratch cleaned) | Live params: `prompt`, `description`, `background`, `isolation` (`none\|worktree`, mutually exclusive with `cwd`), `resume_from`, `cwd` (`subagentType` absent in `1.0.92`) |
| **Cursor CLI `cursor-agent` `2026.09.23-86fc751`** | **Not run** (`cursor-agent -p` exited 1: `Error: Authentication required`) | Unqualified | Unqualified | Unqualified | Unqualified | Needs `cursor-agent login` (or `CURSOR_API_KEY`) before CLI & `--sandbox enabled` qualification |

### Key design implications settled by Phase 0

1. **Forked reviews are natively portable across 3 of 4 daily hosts (Cursor IDE `resume="self"`, Claude Code `subagent_type="fork"`, Codex `fork_turns="all"`), with seamless fresh fallback on Grok Build (`has_fork=false`)** because ShipLoop always writes `CHILD/worker-brief.md` + `CHILD/handoff.md` on disk.
2. **Foreground parallel tool calls in a single turn work on Cursor IDE, Claude Code, and Grok Build**, and `wait_agent` blocks within the turn on Codex — so **neither Surface 1 nor Surface 2 needs `run_in_background: true` + turn-end notification yielding**, eliminating the keepalive `Stop`-hook deadlock!
3. **Claude Code's `PostToolUse(Skill)` gate needs zero hook rewrites for `--delegation agents`**: both fresh and forked subagents already fire `PostToolUse(Skill)` under the parent's `session_id` with `agent_id`.
4. **Two real schema changes caught live before coding:**
   - Codex `0.171.0` defaults `fork_turns` to `"all"` (not `"none"`), so fresh workers MUST explicitly pass `fork_turns: "none"`.
   - Grok `1.0.92` added `isolation: "worktree"` to `spawn_subagent` (mutually exclusive with `cwd`), so Grok's binding must forbid `isolation: "worktree"` just like Claude's.
5. **macOS `/tmp` realpath normalization:** every host resolved `/tmp/...` to `/private/tmp/...` in `pwd` and `git rev-parse --show-toplevel`, so worker briefs should state canonical realpaths (or instruct `realpath` comparison).
6. **Ready for owner decision on D1 (forked vs hybrid vs fresh for reviews) and Phase 1–2 implementation.**

---

## 9. Phase 0.5 confirmation results: strict zero-hint byte-identical prompts + real ShipLoop Improve reviews (measured 2026-11-23)

Owner chose **Hybrid** (`D1`: forked for planning reviews, fresh for code & end-of-work reviews) and asked for end-to-end confirmation that **one byte-identical, zero-hint prompt** works across hosts and completes real ShipLoop Improve children before implementing Phase 1–2.

### Method

All prompts were generated from a single template module asserting **zero** host brand names, **zero** native tool names (`Agent`, `Task`, `spawn_agent`, `spawn_subagent`, `wait_agent`), and **zero** host parameter names (`resume`, `fork_turns`, `subagent_type`, `isolation`, `cwd`, `background`, `environment`, `timeout_ms`). All runs used throwaway scratch repositories under `/private/tmp/shiploop-phase05-20261123/` (deleted after recording; zero edits to `skills/` or user profiles):

- **Test A (strict zero-hint fork vs. fresh):** parent holds in-conversation-only canary `CANARY_PARENT_ONLY=quartz-5510-<host>` (never on disk, never in subagent prompts); launches Task 1 (forked, or fresh fallback if host cannot fork) and Task 2 (strictly fresh, no parent history). Cursor IDE ran as a **100% blind fresh depth-1 parent `Task`** spawning depth-2 children.
- **Test B1 (real ShipLoop `spec` Improve stage — Hybrid forked planning review):** real `shiploop init` → `complete` through `spec` starting a real `until_loop_ephemeral.py` child, real `CHILD/handoff.md`, real `CHILD/packet.json`, and proposed ~22-line `CHILD/worker-brief.md`. Parent holds a **chat-only user decision** never written to disk (`divide(a, 0)` MUST raise `ValueError("division by zero")`, confirmed by `T-DIV-ZERO`). Parent runs `shiploop next`, dispatches one forked coding-capable review worker (fresh + 2-line conversation note on Grok), verifies `CHILD/packet.json` is `complete`, and alone runs `shiploop complete --action <improve_id>`.
- **Test B2 (real ShipLoop `document` step Improve stage — Hybrid fresh coding review):** real `shiploop` run advanced through `step-plan` → `test-spec` → `validate-existing` → `implement` → `test` → `document` into a real active `document` step Improve child, with a real planted spec violation (`calc.py` does bare `a / b` raising `ZeroDivisionError` instead of `ValueError("division by zero")`, while `test_calc.py` only tested `divide(6, 2)` and passed). Parent holds in-conversation-only canary `CANARY_CODE_FRESH=crimson-8812-<host>` to prove the worker ran strictly fresh. Parent dispatches one fresh coding-capable review worker, verifies `CHILD/packet.json` is `complete`, and alone runs `shiploop complete --action <improve_id>`.
- **Claude Code B1 & B2** ran with `--plugin-dir plugins/skill-craft` and an isolated `SHIPLOOP_KEEPALIVE_HOME` to test the **real shipped `PostToolUse(Skill)` hook and keepalive** live.

### Results table

| Host & build | Test A: Zero-hint fork vs. fresh | Test B1: Real `spec` Improve (forked planning) | Test B2: Real `document` Improve (fresh coding) | Measured context isolation & hooks |
|---|---|---|---|---|
| **Cursor IDE** (blind depth-1 parent `Task` → depth-2 children) | **PASS** — `fork` saw `quartz-5510-cursor-ide`; `fresh` saw `null`; `wt_count=1` *(also proved depth-2 nesting works on Cursor IDE)* | **PASS** — `mode_used: "fork"`, `packet.json: complete`, `review-1.md` + `review-2.md`, `passes.md`, `spec.md` gained `ValueError("division by zero")` + `T-DIV-ZERO`, parent `complete` rc 0 → `test-strategy` | **PASS** — `worker_canary_seen: null`, `packet.json: complete`, `review-1.md` + `review-2.md`, `passes.md`, `calc.py` fixed (`VALUE_ERROR: division by zero`), `unittest` 4 tests OK, 0 worker commits, parent `complete` rc 0 → `carry-forward` | No token telemetry exposed to Cursor IDE agent; all disk/git/gate assertions verified independently |
| **Claude Code `2.1.330`** (`claude-sonnet-5-5` medium; real plugin hooks on B1/B2) | **PASS (`9.9 s`, `$0.092`)** — stream confirmed `Agent(subagent_type="fork", run_in_background=false)` saw `quartz-5510-claude` + `Agent(subagent_type="general-purpose", run_in_background=false)` saw `null`; `isolation=null`; `wt_count=1` | **PASS (`198.2 s`, `$0.965`, keepalive drove on to `step-plan`)** — stream confirmed `Agent(subagent_type="fork")`, `subagent complete=0`; `spec.md` gained `ValueError("division by zero")` + `T-DIV-ZERO`; real `skill-calls.jsonl` recorded `improve` with `agent_id: ae724a6004813e8e5` and passed the real Skill-call gate! | **PASS (`290.2 s`, `$1.485`, keepalive drove rest of run to `done`)** — stream confirmed `Agent(subagent_type="general-purpose")`, `worker_canary_seen: null`, `subagent complete=0`; `calc.py` fixed (`VALUE_ERROR: division by zero`), `unittest` 3 tests OK; real `skill-calls.jsonl` recorded `improve` with `agent_id: a2a9f294c1945eff8` and passed the real Skill-call gate! | **B1:** parent `cache_read = 945k` vs total `modelUsage` `cache_read = 2.82M` (**~1.87M tokens of Improve work stayed outside parent**); `subagent shiploop complete = 0` across all 3 runs |
| **Codex `0.171.0`** (`gpt-6.2-sol` medium) | **PASS on retry (`25.2 s`)** — rollout JSONL confirmed `spawn_agent(fork_turns="all")` saw `quartz-5510-codex-retry` + `spawn_agent(fork_turns="none")` saw `null`; `wt_count=1`. *(First attempt timed out at 240 s: parent issued the exact same `fork_turns="all"` + `fork_turns="none"` + `wait_agent(120000)` and `forked` returned `quartz-5510-codex`, while `fresh` child's first OpenAI API call stalled with `tokens: null`.)* | **PASS (`174.2 s`)** — rollout confirmed `spawn_agent(task_name="spec_review", fork_turns="all")`, `subagent complete=0`; `packet.json: complete`, `review-1/2.md`, `passes.md`, `spec.md` gained `ValueError("division by zero")` + `T-DIV-ZERO`, parent `complete` rc 0 → `test-strategy` | **PASS (`210.4 s`)** — rollout confirmed `spawn_agent(task_name="improve_review", fork_turns="none")`, `worker_canary_seen: null`, `subagent complete=0`; `packet.json: complete`, `review-1/2.md`, `passes.md`, `calc.py` fixed (`VALUE_ERROR: division by zero`), `unittest` 3 tests OK, parent `complete` rc 0 → `carry-forward` | **B1:** parent `114.7k` input (`679` out) vs forked child `1,108k` input (`1,047k` cached = **94.5% cache hit**, `6,067` out). **B2:** parent `172.8k` input (`1,119` out) vs fresh child `1,364.7k` input (`1,293.8k` cached = **94.8% cache hit**, `6,877` out). **>1.1M tokens of Improve work kept out of parent on both!** |
| **Grok Build `1.0.92`** (`grok-4.6` medium) | **PASS (`38.6 s`, `74.4k` tokens)** — stream confirmed 2 blocking `spawn_subagent(background=false, cwd=...)`; `fork_supported_by_host=false`, `fork_fallback_to_fresh=true`, both `canary_seen=null`, `wt_count=1` | **PASS (`300.9 s`, `1.63M` tokens)** — `spawn_subagent(background=false, cwd=...)`, `mode_used: "fresh-fallback"` (carried 2-line conversation note); `packet.json: complete`, `review-1/2.md`, `passes.md`, `spec.md` gained `ValueError("division by zero")` + `T-DIV-ZERO`, parent `complete` rc 0 → `test-strategy` | **PASS (`218.1 s`, `967.9k` tokens)** — `spawn_subagent(background=false, isolation="none")`, `worker_canary_seen: null`; `packet.json: complete`, `review-1/2.md`, `passes.md`, `calc.py` fixed (`VALUE_ERROR: division by zero`), `unittest` 3 tests OK, parent `complete` rc 0 → `carry-forward` | Notice on B2 Grok omitted `cwd` on `spawn_subagent` (relied on explicit shell cwd) — harmless, and the 2-line host hint keeps `cwd` consistent |

### Verified conclusions & caveats

1. **Confirmed: one 100% zero-hint, byte-identical prompt works across all four hosts** (Cursor IDE, Claude Code `2.1.330`, Codex `0.171.0`, Grok Build `1.0.92`), including Codex choosing `fork_turns="none"` for fresh code reviews despite `"all"` being its default, and Grok cleanly falling back to `fresh-fallback` with the 2-line conversation context note.
2. **Confirmed: real ShipLoop Improve children (`improve/SKILL.md` + `until_loop_ephemeral.py` + `improve-pass` + parent `shiploop complete`) succeeded 8 of 8 (4/4 forked planning B1 + 4/4 fresh coding B2) with 0 subagent `complete` calls and 0 extra worktrees.**
3. **Confirmed: parent context isolation is real and substantial** (~1.1M–1.87M tokens of Improve work stayed inside the child threads on Codex and Claude instead of accumulating in the parent), and forked children hit **94.5% cache read** on Codex.
4. **Confirmed: Claude Code's shipped `PostToolUse(Skill)` hook already records subagent `Skill(improve)` calls (with `agent_id`) and satisfies `shiploop complete`'s Skill-call gate on BOTH forked and fresh reviews.**
5. **Why the 2-line runtime host hint from `host-bindings/v2` still adds concrete value:** even though the zero-hint prompt passed everywhere, the 2-line hint still prevents non-inferable quirks (Codex's 4-slot / 3-worker cap for Surface 2 fan-out and `120000 ms` wait; Grok passing `cwd` and omitting `isolation="worktree"`; guarding against host default drift).
6. **Honest caveats recorded:**
   - One transient provider stall occurred on Codex Test A attempt 1 (fresh child never received its first model completion in 240 s; exact same prompt passed in 25.2 s on retry).
   - In Test B2's synthetic fixture, `setup_fixtures.py` fast-forwarded `prepare → step-plan` via `navigator.apply()`, skipping `lint-base`, so ShipLoop's `_commit_stage` left `calc.py`/`test_calc.py` uncommitted with its documented "no base captured" path (fixture artifact, not a worker or ShipLoop fault).
   - `cursor-agent` CLI (`2026.09.23`) remains unqualified until `cursor-agent login`; forked vs. fresh *code-review quality* (confirmation bias) remains a Phase 3 paired E2E measurement.

---

## 10. Phase 3 registration: paired E2E comparison (`--delegation inline` vs. `--delegation agents`) + live Cursor IDE delivery (registered 2026-11-23, before any run)

### Tree & apparatus

- Branch `cursor/shiploop-always-agents-df4c` (Phase 1 `f5fc1bf01` + Phase 2 `4f1a50bb0` + harness `--delegation` option in `test/shiploop_e2e/run.py`), run with `--source checkout` and external output/baseline under `~/e2e-runs/phase3-agents-20261123/`.

### Arms & cases

1. **Paired brownfield delivery (`ticket-assignment`, 3 case checks + 18 held-out `ticket_assignment_accept` checks):**
   - **Codex `gpt-6.2-sol` medium** (`inline` vs. `agents`, launched together)
   - **Claude Code `claude-sonnet-5-5` medium** (`inline` vs. `agents`, launched together)
2. **Live Cursor IDE whole delivery (`csv-report`, 5 `csv_report.py` checks):**
   - One blind fresh Cursor IDE `Task` parent executing the checkout's `skills/shiploop/scripts/shiploop` from `workspace start --delegation agents` through `handoff` + workspace return (`status == "done"`, `report.html`), graded by the exact 5 `csv_report.py` checks from `cases.json`.

### Pre-registered measures & pass bar

- **Verdicts & correctness:** all 6 E2E verdicts (`invoked`, `plugin`, `process`, `shiploop`, `committed`, `checks`), held-out acceptance (`18/18` on `ticket-assignment`), and `5/5` `csv_report.py` checks on Cursor IDE.
- **Hybrid delegation fidelity (read from state, `passes.md`, `skill-calls.jsonl`, and raw host traces):**
  - `state.md` `delegation` matches arm (`inline` vs. `agents`);
  - every `agents` Improve stage writes `CHILD/worker-brief.md` and records `Review mode: fork (delegation: agents)` for planning/outer reviews and `Review mode: fresh (delegation: agents)` for `document` and `carry-forward` (or `inline-fallback` if fallback occurred);
  - `0` subagent `shiploop complete` calls;
  - on Claude Code, `skill-calls.jsonl` records `agent_id` for delegated `improve` Skill calls and satisfies the real Skill-call gate.
- **Efficiency & isolation:** wall-clock seconds, review seconds, parent vs. child token counts (Claude `usage` vs. `modelUsage`; Codex parent vs. child rollout JSONL), Claude dollar cost, and Surface 2 read-only fan-out count.
- **Decision rule:** Passing all verdicts, case checks, held-out checks, and Hybrid fidelity checks qualifies `--delegation agents` as an opt-in route and satisfies ShipLoop's release preflight (recorded in `test/shiploop_e2e/LEARNINGS.md`). Whether to flip `DEFAULT_DELEGATION` from `"inline"` to `"agents"` stays an explicit owner decision after reading the paired quality, token, cost, and time table.

---

## 11. Phase 3 results (measured 2026-11-23, serial re-run after parallel/port-lease failure)

### Tree & apparatus (decision arms)

- Branch `cursor/shiploop-always-agents-df4c` at `c74495bfe` (Phase 1–2 + E2E `--delegation`); plugin build reused from `~/e2e-runs/phase3-agents-20261123/plugin-build/` (checkout skill-craft 4.6.0 / ShipLoop 2.8.0).
- Decision outputs under `~/e2e-runs/phase3-agents-serial-20261123/` (serial launcher `launch_serial.py`). Combined summary: `phase3_summary.json`.
- First parallel attempt (`~/e2e-runs/phase3-agents-20261123/`) is **forensic only** — see salvage footnote below; not used as a decision cell.

### Paired brownfield (`ticket-assignment`, Codex Sol 6.2 medium + Claude Sonnet 5.5 medium)

| Arm | Pass | Case checks | Held-out | Committed | Process s | Turns | Cost USD | Hybrid fidelity |
|---|---|---|---|---|---|---|---|---|
| Codex `inline` | PASS | 3/3 | 18/18 | yes | 681.6 | 195 | n/a | n/a (`review_mode` inline×8) |
| Codex `agents` | PASS | 3/3 | 18/18 | yes | 2127.5 | 277 | n/a | yes — 9 `worker-brief.md`; fork×6 / fresh×3 |
| Claude `inline` | PASS | 3/3 | 18/18 | yes | 928.4 | 273 | 5.62 | n/a (`review_mode` inline×9) |
| Claude `agents` | PASS | 3/3 | 18/18 | yes | 1075.8 | 278 | 6.45 | yes — 9 briefs; fork×6 / fresh×3; Skill `agent_id` 9/9; Agent×9 |

Launcher wall-clock (includes harness wrap): inline Codex 720.1 s, agents Codex 2162.6 s, inline Claude 954.0 s, agents Claude 1099.8 s. Serial total ~82 min. Zero port-lease refusals.

### Live Cursor IDE (`csv-report`, `--delegation agents`, model `grok-4.7-high-fast`)

- Parent Task [Cursor IDE csv-report agents](e12d75d9-89ad-402b-a4d0-9ee33170c0e9) completed successfully (Gemini weekly quota blocked the earlier default model; Grok was used explicitly).
- ShipLoop `status=done`, `report.html` present, workspace return on `main` at `f365645…`.
- Independent checks: **5/5** `csv_report.py` (`unit`, `totals`, `invalid`, `missing`, `empty`).
- Hybrid: 8 Improve `worker-brief.md`; `review_mode` fork×6 / fresh×2; `any_fallback=false`; stages delegated: spec, test-strategy, plan, step-plan, document, carry-forward, system-test-author, release-plan.

### Efficiency read (quality first)

- Correctness bar met on every decision arm (verdicts + case checks + held-out 18/18 + Cursor 5/5).
- Claude cost: agents **+$0.83** vs inline (~15%); turns nearly flat (278 vs 273).
- Codex wall time: agents **~3.1×** inline process seconds (2127 vs 682) at equal correctness — review fan-out cost, not a quality miss.
- Claude wall time: agents ~1.16× inline — much smaller penalty than Codex on this sample.

### Qualification & default

- **`--delegation agents` qualifies as an opt-in route** under the §10 decision rule (paired evidence + Hybrid fidelity + Cursor live delivery).
- **`DEFAULT_DELEGATION` stays `inline` until an explicit owner flip** after reading this table (quality > tokens/cost > time). No flip in this pickup.

### Salvage footnote (parallel batch `phase3-agents-20261123`, not a decision cell)

- Parallel `launch_cli.py` held `port-4180` on the first `ticket-assignment` harness; three siblings refused in ~16 s.
- Sole completer `claude-tickets-agents`: engine `done`, case checks 3/3, Hybrid already live (10 briefs, fork×7/fresh×3, Skill `agent_id` 10/10, $9.22) but **`committed` failed** (product on `shiploop/run-*`, `master` stuck at base). Re-run above cleared that miss.
- Cursor IDE attempt in that batch never started: Task defaulted to Gemini 4 Neon → weekly usage refusal.

### Apparatus lessons

1. Cases with `refuse_ports` must launch **serially** (or with distinct ports); parallel same-case batches are structurally refused.
2. Cursor IDE Task must pass an **explicit allowed model** when Gemini weekly quota is exhausted; omitting `model` pulled Neon and aborted before ShipLoop.
3. `passes.md` provenance was absent on both agents arms; Hybrid mode is evidenced by state `review_mode` + `worker-brief.md` + Claude `skill-calls.jsonl` `agent_id` (LEARNINGS notes the gap; not a release blocker for this round).

Journal: `test/shiploop_e2e/LEARNINGS.md` entry 2026-11-23 Phase 3 portable native agents.



