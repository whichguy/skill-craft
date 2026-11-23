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
| **Qualification status** | **Qualified** for neutral spawn/fan-out (`2.1.325`, `E1`/`E9`–`E13`); **unqualified** for direct ShipLoop review brief | **Qualified** for neutral spawn/fan-out (`0.169.0`, `E1`/`E9`–`E13`); **pilot** for old consumer-owned route | **Qualified** for neutral spawn/fan-out (`1.0.77`, `E1`/`E9`–`E13`); **unqualified** for direct ShipLoop review brief | **Schema-inspected (IDE, 2026-11-23); UNQUALIFIED** for runtime (CLI `2026.09.18` passed old managed-worktree pilot only) | **Pilot only** (`1.18.31` persistent TUI with experimental flag); **UNQUALIFIED** |
| **Native spawn tool** | `Agent` (listed as `Task` in init stream) | `spawn_agent` (`collaboration.spawn_agent`) | `spawn_subagent` | `Task` (`cursor` namespace) | `task` |
| **General-purpose worker type** | `general-purpose` | *(default general-purpose)* | `general-purpose` (never `explore`/`plan` for coding) | `generalPurpose` *(camelCase!)* | *(default general-purpose)* |
| **Fresh context rule** | Omit `resume`; non-fork `Agent` | `fork_turns: "none"` *(required)* | Omit `resume_from` | Omit `resume` (**never** `resume: "self"`) | Omit `task_id` |
| **Forked context rule (inherit history)** | **Check in Phase 0** (verify live `Agent` / fork schema) | **Check in Phase 0** (`fork_turns` non-`"none"` values) | **Check in Phase 0** (`spawn_subagent` schema — likely fresh-only) | `resume: "self"` *(verified in live `Task` schema 2026-11-23; test behavior in Phase 0)* | **Check in Phase 0** (likely fresh-only) |
| **Forbidden isolation args** | **Omit `isolation: "worktree"`** (creates 2nd checkout) | *(none on spawn)* | *(none on spawn)* | **Omit `environment: "cloud"`** (runs on remote VM/worktree) | *(none on spawn)* |
| **Native `cwd` on spawn?** | **No** — prefix every Bash call with `cd "<WORKTREE>" &&` + abs file paths | **No** — set `workdir` on every shell call + abs file paths | **Yes** (`cwd: "<WORKTREE>"`), still verify `pwd` + Git root | **No** *(verified in live `Task` schema 2026-11-23)* — set `working_directory` on Shell + abs file paths | **No** — set `workdir` on every bash call + abs file paths |
| **Serial review mode (Surface 1)** | **Foreground** (`run_in_background: false` / omitted) — blocks cleanly until return | **Async** `spawn_agent` + `wait_agent(timeout_ms=120000)` | **Foreground** (`background: false`) — blocks cleanly until return | **Foreground** (`run_in_background: false`) — blocks cleanly until return | Foreground (or `background: true` in persistent TUI only; one-shot CLI exits early) |
| **Parallel read-only fan-out (Surface 2)** | Multiple `Agent(run_in_background=true)` in one turn; notifications re-enter parent (do **not** poll) | Up to **3 workers** (`4` slots incl. parent); `wait_agent(timeout_ms=120000)` | Multiple `spawn_subagent(background=true)` in one turn; `get_command_or_subagent_output(timeout_ms=120000)` | Multiple `Task(run_in_background=true)` in one turn; auto-notifies after turn ends (do **not** poll); confirm concurrency cap in Phase 0 | Experimental flag `OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS=true` in TUI only; otherwise run serial |
| **Steer / cancel running worker** | `SendMessage` + `TaskStop` | Native interrupt | `kill_command_or_subagent` | `Task(resume=id, interrupt=true)` (no dedicated stop-only tool) | Unqualified |
| **Subagent nesting / depth** | Configurable (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`); headless nested unstable on `2.1.296` — **Surface 1 & 2 are depth 1 only** | Depth 1 sufficient | Depth 1 in local `1.0.50` guide — **Surface 1 & 2 are depth 1 only** | Depth 1 sufficient; confirm in Phase 0 | Depth 1 sufficient |
| **Keepalive & Skill-call hooks** | `PostToolUse` (Bash, Skill), `Stop`, `SessionEnd` work in interactive + `-p`; see §4.2 for subagent Skill-call fix | `PostToolUse`, `Stop`, `SessionEnd` work in interactive + `exec`; no Skill hook | `PostToolUse`, `Stop` (8/turn cap), `SessionEnd` work in interactive + `-p`; no Skill hook | `afterShellExecution`, `stop`, `sessionEnd` work in IDE; **`cursor-agent -p` never fires `stop`** (`shiploop-drive` required for unattended CLI); no Skill hook | Plugin `session.idle` in TUI; `opencode run` needs `shiploop-drive`; no Skill hook |

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
      "tested": ["2.1.325"],
      "tools": {"spawn": ["Agent", "Task"], "stop": ["TaskStop"]},
      "worker_type": "general-purpose",
      "serial_mode": "foreground",
      "cwd_on_spawn": false,
      "fresh_args": {},
      "fork_args": null,
      "background_args": {"run_in_background": true},
      "forbidden_fresh_args": ["isolation", "resume"],
      "collect_parallel": "completion notifications re-enter the parent as new turns; do not poll",
      "observation_timeout_ms": null,
      "capacity": null,
      "hint": "Use a fresh general-purpose Agent (omit isolation and resume); foreground for a serial review, run_in_background=true for parallel readers (do not poll); prefix every Bash command with cd \"<WORKTREE>\" &&."
    },
    "codex": {
      "name": "Codex",
      "status": "qualified",
      "tested": ["0.169.0"],
      "tools": {"spawn": ["spawn_agent"], "wait": ["wait_agent"]},
      "worker_type": null,
      "serial_mode": "async-wait",
      "cwd_on_spawn": false,
      "fresh_args": {"fork_turns": "none"},
      "fork_args": null,
      "background_args": {"fork_turns": "none"},
      "forbidden_fresh_args": [],
      "collect_parallel": "wait_agent with timeout_ms: 120000, not short polls",
      "observation_timeout_ms": 120000,
      "capacity": {"workers": 3, "slots": 4, "parent_holds": 1},
      "hint": "Use spawn_agent with fork_turns=\"none\" (at most 3 concurrent workers; 4 slots include the parent), wait with wait_agent timeout_ms=120000 (no short polls), and pass explicit workdir on every shell command."
    },
    "grok": {
      "name": "Grok Build",
      "status": "qualified",
      "tested": ["1.0.77"],
      "tools": {"spawn": ["spawn_subagent"], "wait": ["get_command_or_subagent_output"], "stop": ["kill_command_or_subagent"]},
      "worker_type": "general-purpose",
      "serial_mode": "foreground",
      "cwd_on_spawn": true,
      "fresh_args": {},
      "fork_args": null,
      "background_args": {"background": true},
      "forbidden_fresh_args": ["resume_from"],
      "collect_parallel": "get_command_or_subagent_output with all task ids and timeout_ms: 120000",
      "observation_timeout_ms": 120000,
      "capacity": null,
      "hint": "Use general-purpose spawn_subagent with cwd=\"<WORKTREE>\" and omit resume_from (never explore/plan for coding); foreground for a serial review, background=true + get_command_or_subagent_output(timeout_ms=120000) for parallel readers."
    },
    "cursor": {
      "name": "Cursor",
      "status": "unqualified",
      "tested": [],
      "tools": {"spawn": ["Task"]},
      "worker_type": "generalPurpose",
      "serial_mode": "foreground",
      "cwd_on_spawn": false,
      "fresh_args": {"subagent_type": "generalPurpose"},
      "fork_args": {"subagent_type": "generalPurpose", "resume": "self"},
      "background_args": {"subagent_type": "generalPurpose", "run_in_background": true},
      "forbidden_fresh_args": ["resume", "environment"],
      "collect_parallel": "background subagents notify on completion after the parent turn ends; do not poll",
      "observation_timeout_ms": null,
      "capacity": null,
      "hint": "Use Task with subagent_type=\"generalPurpose\" (omit resume and environment=\"cloud\"); run_in_background=false for a serial review, run_in_background=true for parallel readers (do not poll); set working_directory on every shell call and use absolute file paths."
    },
    "opencode": {
      "name": "OpenCode",
      "status": "unqualified",
      "tested": [],
      "tools": {"spawn": ["task"]},
      "worker_type": null,
      "serial_mode": "foreground",
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

1. **Claude Code subagent Skill-call capture (`skills/shiploop/scripts/shiploop_keepalive.py` + `shiploop_skill_calls.py`):**
   - Keep `observe`, `stop`, and `session-end` strictly ignoring subagents (`_is_subagent(payload)`), so a worker can never steal keepalive ownership.
   - In the `skill` hook (`PostToolUse` on `Skill`), when `session` has no binding (or `_is_subagent(payload)` is true), inspect `tool_input.args` for the literal prefix `ShipLoop Improve: <handoff_path>`. If `<handoff_path>` resolves to a file inside `<RUN>/.shiploop-improve/...` where `<RUN>/state.md` exists, append the call directly to `<RUN>/skill-calls.jsonl` (including `agent_id`, which `shiploop_skill_calls.record_call()` already supports on line 75!).
   - Then remove the `if delegation(state) != guidance.INLINE: enforce = False` bypass in `_skill_call_record()`! On Claude Code with hooks active, a fresh Improve worker that skips invoking the `improve` skill is caught by the exact same gate as an inline run.
   - *(Note: verify in Phase 0 whether Claude Code fires `PostToolUse` for `Skill` inside a subagent; if Claude Code suppresses `PostToolUse` inside subagents, document that measured limit honestly rather than assuming it fires!)*
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

- Implement `DELEGATIONS = ("inline", "agents")` (keeping `inline` as default until Phase 3), `CHILD/worker-brief.md`, updated `improve_packet()`, Surface 2 read-only fan-out guidance + F17 rules on `discovery`/`research`/`product-acceptance`, emit-time 2-line host hints, `passes.md` `review_mode` provenance, and Claude subagent Skill-call recording (if Phase 0 confirms `PostToolUse` fires in subagents).
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
| **D1** | Review worker context mode and stage scope under `--delegation agents` | **Open (informed by Phase 0 P0-B):** **(a) Forked context where supported, fresh fallback elsewhere** (keeps full conversation context + prompt cache hit while isolating Improve tool calls from parent), **(b) Hybrid** (forked for planning reviews, fresh for code & end-of-work reviews to avoid confirmation bias), or **(c) Fresh context for code & end-of-work only** | Run **Phase 0 P0-B** first to establish which of Cursor, Claude Code, Codex, and Grok actually expose a native fork parameter; then decide between (a) and (b) — and compare forked vs fresh code review in Phase 3 if needed. |
| **D2** | Behavior when `--delegation agents` runs on a host with no usable native subagent tool (or `unknown` host without native spawn)? | **(a) Graceful inline fallback** (run Improve / exploration inline, disclose it, record `review_mode: inline-fallback`) vs **(b) Fail closed** (block until the user switches `--delegation inline`) | **(a) Graceful inline fallback with explicit provenance** — keeps ShipLoop truly portable on any host while staying 100% honest in traces and Run Review. |
| **D3** | Legacy `--delegation ask-agent` route | **Decided (owner, 2026-11-23):** keep `ask-agent` as a third mode alongside `inline` and `agents` (`DELEGATIONS = ("inline", "agents", "ask-agent")`). | Keep `ask-agent` intact; add `agents` beside it; keep `inline` default until Phase 3 qualifies `agents`. |
| **D4** | How does the parent learn host-specific quirks? | **(a) Emit-time detection by `shiploop`** (reads `os.environ` at render time, prints a 2-line host hint directly in the packet; zero extra tool call; never persisted in `state.md`) vs **(b) Explicit command** (tell the model to run `shiploop host-binding` once per session) | **(a) Emit-time detection** — eliminates the "model forgot to run the host command" failure mode (`fbfebee74`) and keeps prompts minimal, with a `--host` override for deterministic dry runs and tests. |
| **D5** | Scope of Phase 0 live probes | **Decided (owner, 2026-11-23):** run Phase 0 on **Cursor + Claude Code + Codex + Grok Build** now (leave OpenCode `unqualified` in `host-bindings.json` until tested). | Execute Phase 0 across Cursor, Claude Code, Codex, and Grok Build. |
