Execute: ask

# ShipLoop efficiency and concision: final plan (revision 4, red-teamed). Land tranche 1 on the release branch, fix three audit defects, complete the head, cut what the model reads, add one small start-here card

> **Update 2026-10-17 (written after the plan; the plan text below is unchanged).** The plan's own state section is out of date in one respect: the
> credential-pattern removal and the Skill-call hook (with the deadlock fix, the SPEC S-9 edit and the review fixes) were reviewed, merged and **released as
> skill-craft 2.5.0 / ShipLoop 1.5.0** (origin/main `da9e2e75`, full CI green, all three hosts refreshed). The integration branch the plan names was merged
> into main and removed; later steps start from main. The three branches still unmerged (`feat/shiploop-eff-packets-6afcbc`, `-loop-`, `-stop-`) have been
> adversarially reviewed; their findings and why none is releasable yet are in `docs/shiploop-efficiency-journal-2026-10-16.md`.


Plan only; nothing here is implemented, pushed, merged or released by this document. Paths are repo-relative to `/Users/dadleet/src/skill-craft`. Each workstream step is an Until Loop unit: **Work** / **Exit when ALL of these hold** (every item is a command or file check with an expected result) / **Repeat while any fails; no iteration limit** / **Stop blocked when**. A unit runs through `/until-loop` with its exit conditions as the argument and the journal row as its receipt.

**State at red-team time (verified by git, a scratch merge and a recount of the live stream; read-only).**
- `main` and `origin/main` are 1a7c12d7 (skill-craft 2.4.1, shiploop 1.4.1). The **integration branch already exists**: `feat/shiploop-eff-release-ca2c6e` (320a526e, worktree `.claude/worktrees/shiploop-eff-release-ca2c6e`, 7 commits ahead of main, unpushed). It holds the credential-pattern removal (f1f38850, d4d08351, merged b6b290a7), the Skill-call hook (996a378c, merged c61e80e6), the hook deadlock fix 5d028aee (a Codex/Cursor process started from a Claude shell was refused by the gate) and 320a526e (SPEC S-9 no longer lists a credential screen; the change note states what is not redacted). **Do not create another integration branch off main and do not re-merge the old `-hook-` tip.**
- Still unmerged, all committed: `feat/shiploop-eff-packets-6afcbc` (f3f6a6bc owner rule and index pointer under the header, 0eeb68e2 new-file diff pointer, aeed522f prose paths as symbols), `feat/shiploop-eff-loop-6afcbc` (0d462ca4 explicit Until Loop block), `feat/shiploop-eff-stop-6afcbc` (60018152 stop on one unchanged pass with the SPEC S-10 carve-out, 3b9ca9c9 gate experiment).
- **Scratch merge probe** (clone under `scratchpad/plan-final/redteam3/`): stop merges green. Packets then loop merge textually clean but are red: `shiploop-packet-recut` 2 failures (step-plan printed head 20,504 against HOST_CUT 20,000; ask-agent 22,186 against 22,000) and `shiploop-packet-completeness` 68 failures (the symbols guard flags the loop block's literal `Work:` lines). Loops, improve-runtime, improve-schedule and skill-calls pass. Step 1.0 owns the reconciliation.
- Every live number is from one Grok 4.7 medium run (live2, Salesforce chess, installed 2.4.0 renderer, 163-char run dir, a normal install about 83): a projection for any other program until re-measured on the integration branch.

## 1. The answer in ten lines

1. **Order.** Reconcile and land tranche 1 on the existing release branch (packets + loop are red together today), fix the three audit wording defects, then a complete, budgeted printed head and a measurement of the whole reading path.
2. **Re-aim at ingest.** Of the 5.09 MB that entered the model's context 75% was file reads and printed packet heads 9.6%; the context breaks cost 41%. The repeats: entry card (80 KB, read first after each of the last 9 compactions), packet files, Improve handoffs, improve/SKILL.md plus ADAPTER.md. Packet bytes (65.5% repeat) are second.
3. **Centralised reference: yes, small, as a recovery landing page.** A derived `RUN/start-here.md` of at most 4,600 chars, delivered by the script call (`next`/`init`/`resume` print it when the head leaves room, else name it), named in the first lines of every packet, at the top of SKILL.md and in each Improve handoff. The print fits inline in only about 2 of 8 stages of a small bug fix (card plus head must stay under the 20,000 host cut), so the head builder reserves its room and the card may be split; on Claude a SessionStart(compact) hook is a measured arm.
4. **A file cannot fix typed paths** (22% of output at the live prefix, about 12% at a normal install): default `--result` and RUN-relative `evidence_refs` give about 3% of output live and about 1.5% at a normal install.
5. **Packet bytes, safest first:** same-packet dedupe and symbols (built), then the index and step-scoped hand-offs (your decisions). The lean frame adds only about 1 KB live over symbols and carries S-6 risk: optional, last. Savings are fixture-dependent: a small bug fix gets -3% whole-packet bytes and +6% head bytes until offsets land.
6. **Improve is 49% of time and output:** merge the stop rule (about 4 min net, vendored runtime, your go) and the hook (merged), add a route card, pilot smaller handoffs and a script-written pass tail.
7. **Script-owned fields:** gate vocabulary printed in the packet so the model stops reading ShipLoop source (120 of 387 turns); values marked copied, run or derived.
8. **Wording last and screened:** inducing duties first, then one concise-language line (1 to 3% of wall time at best).
9. **Harness:** heartbeat and timing, a verified resume line, host probes, platform learnings to `references/platforms/`, a domain-word lint, the generic case split.
10. **Cost and risk:** 36 until-loop units; planning goes from 52.7 min to about 35 to 41 min, not 30 (30 needs D-7); nothing pushed or released without your go; main risks are the head budget, S-6 after a clear, and a battery sized by a blocked paired design (about 20 slices).

## 2. Evidence

Snapshots: S1 19:18 PDT (81 min), S2 20:10 (191 read_file calls), S3 21:05 (27,419 events), S4 21:14 (1,219 tool calls, 16 breaks), S5 plan-time recount (29,668 events), S6 red-team recount 22:04 (33,833 events, 1,503 tool calls, 14 auto_compact_completed). Sources under `/private/tmp/claude-501/-Users-dadleet-src-skill-craft/8acf399b-0cf4-40cc-bba3-bf238461db58/`: [P1] `tasks/wa0vht5yk.output`; [CS] `tasks/wv0l8do87.output`; [VS] `tasks/wxw3c2e09.output`; [IV] `tasks/wu2yl4iro.output`; [LL] `tasks/w5jtv04hx.output`; [RM] `scratchpad/reads-measurement.md`; [AU] `docs/shiploop-prompt-and-file-audit-2026-10-16.html` and `docs/experiments/shiploop-audit-20261016`; [RD] `scratchpad/plan-final/reference-design/`; [AM] `scratchpad/plan-final/audit-mapping/`; [EV] `scratchpad/sfchess/live2/events.jsonl` (read-only); [BR] tranche-1 commit messages; [LR] `test/shiploop_e2e/LEARNINGS.md` 2026-10-16; [CL] `test/shiploop_e2e/clear.py`; [RT] red-team probes `scratchpad/plan-final/redteam3/` (merge clone, `measure_heads.py`, `heads-*.json`, `full-*.json`, `steplan-head-163.txt`, `out-*.txt`).

1. **Time.** 80% of the first 86 min is model generation (about 22 min latency, 32 reasoning, 21 output); 5 to 6 compactions stall 6.5 to 10.1 min plus 9 to 17.8 min re-orientation; zero refused submissions; Improve is 49% of time and output. Preparation took 52.7 min (stage work 20.7, Improve 33.0), first accepted test-spec at 77.7 min. [LL, LR, VS]
2. **Ingest dominates (S4).** 5.09 MB of tool results: 75% `read_file`; printed `next`/`complete` heads 9.6% (63 calls, 488 KB); standing frame about 3.3%. The 16 breaks (12 compactions, 4 restarts) cost a mean 131 KB over 13 calls before the first productive action, 2.09 MB, 41%. [RD, EV]
3. **Re-reads (S5).** Packet files 40, Improve handoff 19, improve/SKILL.md 14, ADAPTER.md 12, shiploop/SKILL.md 8; `reference.md`, `context-index.md`, `status.md` 0. At S6 the packet file was read 46 times.
4. **The existing pointer is not followed.** "Run context index (... open it after compaction)" sits mid-packet: 0 opens in 16 breaks, none of 660 thought blocks names either file. Commands are followed: `next` within 12 calls on 13 of 14 breaks whose replayed prompt named it ("Full packet: <path>" read 23 times). **S6 recount: after the 14 in-session compactions (no harness prompt) `next` ran within 12 calls after 9 (64%); the first call after each of the last 9 compactions was the shiploop SKILL.md read (0 of the first 5).** The control already follows the recovery command two times in three, so the headroom for any pointer is about a third of breaks. [RD, EV, RT]
5. **Host fact.** Grok returned skill-directory markdown whole (17 of 17 offset reads ignored) and honoured offsets on scripts and run-directory files (164 of 164). So text at the top of a skill file does not shorten the read of it. [AM]
6. **Bytes are structural.** 17 live packets 660 KB; 65.5% repeat an earlier packet; quote region 43%; plan packet's uncut spec diff 22.1 KB, 20.7 KB of it the quote again; the model read about 6% of the quoted text; living files 16.3 / 14.2 / 5.8 KB against decision D1's 5.3 / 1.8 / 1.9. 97.6% of input tokens were cache reads: repeats cost context and compaction, not turn time. [CS]
7. **Paths.** 14% of packet bytes, 57% of the run-constant frame (3,797 of 6,699 B live); 22 to 23.5% of output (about 142k tokens) but only 82 commands are ShipLoop calls; the 116-char scratch prefix (about 14 normally) makes half an artifact. No file-tool call used a literal HOME/RUN/WORKTREE token: symbols save reading, not typing. [CS, VS, RD]
8. **Output and verbosity.** Reasoning 46%, paths 22%, envelope 4.8%, prose 23% (16% excess); about 71% of time is out of reach of wording; ceiling 3.4 min per 75; a general line loses to a specific duty. [VS]
9. **Improve.** 8 of 21 passes material, 10 changed nothing, 3 polish edits reset the two-clean-pass streak; "trivial and tree unchanged" replays to 6.7 min gross, about 4 net (n=5 stages). Handoffs 27 to 34 KB in the audit probe and 38 to 106 KB live; the host reads improve/SKILL.md (28,341) and ADAPTER.md (23,985) whole for two sections totalling 11,078 chars. [IV, AM, AU]
10. **The audit (1.4.0, 2686b427), three defects re-checked on the release branch by symbol:** `shiploop_reference.render` sets `"rules": guidance.COMMON.strip()` and never reads `planning_review`; `loops._implement_scope` returns "S1 to S2" while `IMPLEMENT_STEP_REVIEW_FOCUS` says "one step"; SKILL.md (80,439 chars) omits `scripts/shiploop-drive`. Also: 33 packets 375,278 chars (7 over 16,000); nine bound Improve handoffs 27 to 34 KB (276,270); three 5,000-char documents raise packets 12.2x and handoffs 5.6x. [AU, AM]
11. **Head and reads.** The printed head omits the stage's own input; 120 of 387 turns read ShipLoop's own text; 55 read validator source though `complete --check-only` passed first try 6 of 6. [P1]
12. **The S-6 probe is blind to reads:** `clear.py` counts only repeated state-changing calls. [CL]
13. **Tranche-1 measurements as built.** New-file diff pointer: ten fixture stages 362,660 to 273,444 chars (-24.6%, generated long-knowledge fixture; small homes byte-identical); PK3 symbols: node-fix-bug inline -4,507 chars (-2.9%), 11 real Salesforce packets 641,731 to 619,774 (-3.4%, about -2.0 KB per live packet); top-of-packet lines +171 (producer) and +344 (Improve) chars; credential-screen removal -35 to -43 chars per stage; hook: packets byte-identical; loop block: the seven looped stages' blocks +596 to +616 chars each. [BR]
14. **Run 2 ended BLOCKED** at W1 test: Grok's classifier refused `sf project deploy start`; resumed with `--permission-mode bypassPermissions`; the printed resume line omitted `--source checkout` (fixed in e64c1156). [LR]
15. **Merged-tree sizes (node-fix-bug, 163-char run dir, printed heads; [RT]).** Release 320a526e -> packets+loop f1df7d0e: step-plan 20,693 -> 21,944 (ask-agent 22,375 -> 23,626), test 15,746 -> 16,850, verify 15,936 -> 17,199, carry-forward 16,916 -> 18,183, implement 15,669 -> 15,801. Whole packets, inline: 173,193 -> 162,702 (packets) -> 167,535 (plus loop); four Improve packets 8,990 -> 10,686. Step-plan head parts: duties 8,108, template 1,702, RULES 1,422, Checked-by 1,254, loop block about 3,400, Progress view 582, callback 562.
16. **Card fit.** Card 4,416 chars (live) fits inline only when the head is at most 15,584: of the eight inner stages of node-fix-bug about 2 qualify (document, test-spec at the edge).
17. **Compaction summaries are not in `events.jsonl`** (only `auto_compact_started/completed`), so a replay of frozen summaries is impossible; the harness resume files (`resume-*.txt`) name `next`.

## 3. Principles

1. **Measure what the model ingests** (packets printed plus files opened, in characters unless a usage event gives tokens); label every figure with fixture, path length, unit, snapshot; never add unlike fixtures; claim no cache or latency saving from moving text. **Credit each saving once, to the change that removes the bytes still ingested** (a pointer or a top block earns nothing if the whole file is still read).
2. **Reads before packet bytes, bytes before words** (dedupe, symbols, indexes remove 30 to 60% of bytes on long homes; duty rewrites under 3%).
3. **Main tenet (S-6).** Context is cleared or compacted between stages, so every packet stands alone; repetition across packets is grounding unless a script proves a duplicate inside one packet. ShipLoop gets no compaction signal from a packet: no "unchanged since packet X", no lean-when-warm printing. The reader signals are the verb typed (`next`, `init`, `workspace start`, `resume` mean "orient me"; `complete` means "I finished a step in a live context") and, on Claude, a host hook event.
4. **A pointer is followed when it is a command or content the model needs to act.** First-read targets are small derived run-directory files (at most 4,600 chars); destinations for moved skill text are purpose-sized (at most 8 KB) because Grok returns skill markdown whole. **A pointer states only what the command does in every case.**
5. **Scripts own derivation, navigation, validation; hooks must see every command.** Commands stay literal, absolute, copy-ready, including the path the model must type to write a result and the Pause command. Symbols are defined once and never stand for a command, the Keepalive marker, "Full packet:", the Progress link, the loop Contract/Receipt/Start/Work lines, the `/improve` line, or the literal receipt in the `evidence_refs` template.
6. **Derived views are never a second cursor;** the card holds no stage, revision, action id or position; a derived file is rewritten whenever its rendered text differs from the file.
7. **Carriers are exempt from concision:** Improve handoff, lessons, `Key learnings:`/`Learned-from:`, honesty markers, `evidence_refs`, open-item owners, expected values, every reason a duty asks for.
8. **No cap, no model-facing clock;** stop rules are script-measured; one supported version (refuse old artifacts; a run in flight keeps its contract). Producer text and the card never name Improve; review checkpoints live in `reference.md#rules`, generated from the mode.
9. **Generic and orthogonal:** platform detail only in `references/platforms/`; fixtures synthetic and neutral; spec and architecture stay orthogonal.
10. **Head bytes are a budget:** every addition names a same-stage offset; when a head is over the host cut, only lines the full-packet file repeats may fall in the cut. **Quality first, then ingest, then time;** thresholds are the control's own spread; offline attribution per change, one live verification run per release.
11. **Exits are script-run.** A decision, a journal row or an evidence path is checked by a test or a script that exits non-zero without it.

### Where the sources disagreed (winner and why)
1. **Pointer target:** built `-packets-` pointer (46 KB `context-index.md`) versus the 4 KB card. Card wins: files are read whole and a break costs 131 KB.
2. **Your two options:** both, split by moment (script call delivers where it fits, pointer is the fallback, a Claude hook is a measured third); only commands are followed.
3. **Resume facts:** position in every packet versus a card without position: a static card, plus resume facts printed by `next` only, from receipts.
4. **Style-line site:** compaction study (under the header) versus verbosity study (the Fill line). Fill line with B0+ carve-outs unless the replay says otherwise.
5. **Order:** audit (three fixes first, one change at a time) versus four lanes versus your batch rule: audit's start, offline attribution per change, one live run per release, waves in 4.13.
6. **Index:** compaction row F versus the audit's "defer until consumer coverage is proven": Tier 2 with a coverage gate plus a seeded-omission test.
7. **Destinations of moved text:** audit ("existing references") versus Grok whole-file reads: new files of at most 8 KB.
8. **Handoff target:** 13 to 18 KB versus Code craft verbatim (about 14 KB with per-action facts): pilot A about 22 KB first.
9. **Stop rule, planning-review default:** keep `stage` as default; D-7 decides, and only `none` meets 30 minutes.
10. **Credential refusal and Loop Start line:** built, and your words asked for both; the credential removal and S-9 edit are merged on the release branch.
11. **Base branch:** the existing release branch, not a new branch off main.
12. **Card contents / double counting / delegated child:** card names stages only; compaction rows D and E, PK3 and the card are counted once; one lean frame for all, tested in arm A2.
13. **Who earns the recovery saving:** the first plan credited the card (0.8 MB ceiling); the evidence credits shrinking the entry card (3.5b), the Improve route card (6.1) and the built loop block. The card earns zero byte credit until measured.

## 4. Sequenced workstreams

Status: BUILT (on a branch or merged, to review), PART, NEW. Tiers: 0 measurement, 1 script-proven, 2 owner go, 3 deferred. Savings are not additive.

**Gates** (each exits 0; capture exit codes, never gate on `cmd | tail`):
- **G-SUITES**: `SHIPLOOP_PROGRESS=off python3 -B test/shiploop-$t.test.py` for t in packet-recut, step-packets, packet-bounds, packet-completeness, e2e-packet-anatomy, e2e-commit-counters, status-display, keepalive, narrative, reference, reference-routing, rehydration, navigator-contract, navigator-dry-run, guidance, quality, navigator-v4, delegation, improve-schedule, actual-improve-cli, chain, package-integrity, loops, test-loop, skill-calls and each suite the step touches.
- **G-QUICK**: `bash test/run-all.sh --group quick --changed-from <base>` and `--group shiploop-composition` (plain `quick` misses the packet suites); edits under `test/shiploop_e2e` also run the e2e family once (about 182 s).
- **G-RENDER**: `python3 test/shiploop_e2e/packets.py --offline node-fix-bug <dir>` (inline and ask-agent) at run dirs of about 83 and 163 chars and on the long-knowledge fixture, diffed with the previous render: every changed line is classified (same-packet duplicate, symbol substitution, moved to a named file, owner-approved); no head grows without its named same-stage offset; the head table is journaled.
- **G-LEDGER**: `python3 -B test/shiploop-packet-obligations.test.py` (from 1.1).
- **G-NOTE**: `changes/<leaf>/<slug>.md` with its bump; a dated journal row in `docs/shiploop-efficiency-journal.md` (status, snapshot, fixture, path length, unit, evidence path) checked by `python3 -B test/shiploop-efficiency-journal.test.py` (each step id has a row naming an existing evidence path); a commit message with key learning, numbers, evidence file, related commits (11f5a5b9, 398466a3, 2686b427, tranche commits) and the session's attribution line.
- **G-STD** = G-SUITES, G-QUICK, G-NOTE, plus G-LEDGER from 1.1 on. **G-S6** = the forced-clear battery row for the step (5.8) passes on the named hosts, decided by `test/shiploop_e2e/arms.py` (exits 0 only with a decision): zero redone state-changing calls, warm `next` calls not above control, orientation bytes and time to the first state-changing call not worse than control.

### W0. The three audit wording fixes (Tier 0, NEW)
Text is generated from recorded options and route via `stage_spec`. Where: `shiploop_reference.py`, `shiploop_prompts.py`, `shiploop_navigator.py`, `shiploop_stage_spec.py`, `loops._implement_scope`, SKILL.md. Saving none (removes false instructions to a cold reader). Risk low. Extra suite: no-model-launch. Audit validation V1.

**Step 0.1 Review schedule per mode**
- Work: in `shiploop_reference.render` build the review sentence of `rules` from `stage_spec.reviewed_stages(state["planning_review"])` (graph order) and the `with_improve("step")` rules, not `guidance.COMMON.strip()`; delete the dead `('*', ...)` swap row in `shiploop_prompts.py`; keep the schedule.
- Exit when ALL of these hold:
  1. A new case in `test/shiploop-reference.test.py` renders planning_review {stage, none} x delegation {inline, ask-agent}, asserts the listed stages equal `reviewed_stages(mode)` and that `none` lists release-plan and system-test-author only; it fails on 1a7c12d7 (recorded) and passes now.
  2. The navigator-contract pin that producers omit the sentence passes; G-STD.
- Repeat while any condition fails; no iteration limit.
- Stop blocked when the fix needs a schedule change (owner).

**Step 0.2 Aggregate chain wording on ask-agent**
- Work: where `shiploop_navigator.py` injects `IMPLEMENT_STEP_REVIEW_FOCUS` and in the implement Goal and Done-when (`shiploop_stage_spec.py`), print on ask-agent the aggregate id and accepted paths from `loops._implement_scope`; inline keeps per-step wording; `CODE_CRAFT` stays verbatim; no review per node.
- Exit when ALL of these hold:
  1. A new test finds "S1 to S2" and both paths in a two-step ask-agent handoff and neither "one step" nor "the step's paths" (fails on main); the inline handoff renders byte-identical.
  2. A chain stopped and recovered with `--restart-stopped` still imports exactly one aggregate review (chain, stopped-improve); G-STD.
- Repeat while any condition fails; no iteration limit.
- Stop blocked when the fix needs a review per node (owner) or would reword a contract in flight.

**Step 0.3 Launcher boundary sentence**
- Work: in `skills/shiploop/SKILL.md` scope "does not launch any model process" to the skill and navigator commands and name the optional outer driver `scripts/shiploop-drive` (`references/keepalive.md`); no behaviour change.
- Exit when ALL of these hold:
  1. `grep -n "shiploop-drive" skills/shiploop/SKILL.md` finds it beside the rule, enforced by a new assertion.
  2. no-model-launch and `node test/skill-frontmatter.test.js` exit 0; README.md and keepalive.md agree; G-STD.
- Repeat while any condition fails; no iteration limit.
- Stop blocked when the owner wants the boundary changed, not described.

### W1. The enabler: tranche-1 landing, measurement, ledger, complete budgeted head (Tier 0)
Head built by priority (P0 never dropped while it fits; P1 the stage's own input; P2 guide labels; P3 quote and hand-off blocks, largest first, one pointer line each); ledger rows carry `surface: head|file` and anchor tokens derived from source. Where: `test/shiploop_e2e/{packets.py, packet_anatomy.py, metrics.py, clear.py, arms.py}`, `shiploop_navigator.packet_head`, `PRINT_LIMIT`, `shiploop_protocol._fit`. Audit validation V2, V5.

**Step 1.0 Land tranche 1 on the release branch (BUILT; reconcile; NEW)**
- Work: on `feat/shiploop-eff-release-ca2c6e` merge `-stop-` (3b9ca9c9), `-packets-` (aeed522f), then `-loop-` (0d462ca4), one merge commit at a time with G-SUITES between (merge, never squash). Reconcile the red combination: (a) the symbols guard in `shiploop-packet-completeness` exempts the loop's BEGIN/END argument block and its Work/Contract/Receipt/start-command lines (literal by the contract and its hash) and still fails on every other literal HOME/RUN/WORKTREE/GUIDES path; (b) reorder `packet_head` so the loop block, callback, Keepalive marker and status end sit before the Progress view, footer sentences and Pause, and the Recovery command moves to the first lines (3.3 owns its wording); (c) replace the constant HOST_CUT in `PrintedHeadTests` by the per-stage head table of 1.2, recording the stages over the cut; do not trim an obligation to fit.
- Exit when ALL of these hold:
  1. `git merge-base --is-ancestor 3b9ca9c9 HEAD`, `aeed522f` and `0d462ca4` each exit 0.
  2. `python3 -B test/shiploop-packet-recut.test.py` (21 tests), `shiploop-packet-completeness` (41), `shiploop-loops` (33), `improve-runtime` (29), `shiploop-improve-schedule` (33), `shiploop-skill-calls` (28) exit 0; the failing counts of the unreconciled merge (2 and 68) are recorded.
  3. A test finds, for every stage x route, the loop Start/Contract/Receipt lines and the Keepalive marker inside the first 19,500 chars of the printed head at a 163-char run dir; the head table at 163 and 83 chars (node-fix-bug, inline and ask-agent) is journaled before and after; G-STD.
- Repeat while any condition fails; no iteration limit.
- Stop blocked when fitting needs an obligation lowered (owner: D-27).

**Step 1.1 Baseline, fixtures, ledger, journal**
- Work: `packets.py` `sections()` names the loop block, request, delivery and quote sections; `packet_anatomy.py` learns the References/READS layout; offline driver with real multi-step plans, an outer-offline mode (24 stages) and an Improve-handoff render; a generated long-knowledge fixture (about 16/14/6 KB, neutral text; reuse `docs/experiments/shiploop-eff-packets-20261016/`) and a small-home fixture; `packet_obligations.json` plus `test/shiploop-packet-obligations.test.py` registered in `test/suite_catalog.py`, with a refusal-route test per refusal; the A/A baseline (control twice per case and host); `test/shiploop-efficiency-journal.test.py`; the journal; the audit's probe scripts re-run with path constants parameterised.
- Exit when ALL of these hold:
  1. `packet_anatomy` leaves at most 5% unclassified bytes on the live packets in `scratchpad/pk/live/` (it was 49.3%).
  2. The obligation test exits 0 on unmodified code and non-zero when one anchor token is removed (mutation recorded).
  3. The audit probes reproduce 375,278 / 276,270 / 79,647 chars at 2686b427 within 1% and report the release-branch figures beside them; the A/A spread of each count metric is in the journal; the journal test and `python3 -B test/test-groups.test.py` exit 0; G-STD.
- Repeat while any condition fails; no iteration limit.
- Stop blocked when the A/A needs a live host whose quota or permission is unavailable.

**Step 1.2 Complete, budgeted head**
- Work: build `packet_head` by priority. P0: header, the first-lines Recovery pointer, top-of-packet lines, callback, goal, Done-when, Keepalive marker, status block, duties, RULES, Checked-by, template, outcomes, fill rule, loop Start and exits; lower in P0 and cut first: Progress view, footer sentences, Pause. P1: implement's Step line and later steps (id plus owned paths); work-item id, title and a 400-char excerpt for step-plan, implement, test, verify, carry-forward; validate-existing mismatch rows; test floors and Base-run rule; verify rerun list and lint mode; carry-forward queue-replacement rule; commit scope; Improve lessons. An **orient print** (3.4a) reserves the card's size before filling. Split `PRINT_LIMIT` from `protocol._fit`; keep a per-stage head allocation table in the journal.
- Exit when ALL of these hold:
  1. A head-completeness test with real steps asserts every P0 and P1 token in the printed head at a 163-char run dir for every stage x route; it fails on main for implement's Step line.
  2. The cut test: for every stage x route the first 19,500 chars hold every P0 token above the "cut first" group; only lines the full-packet file repeats can fall past 20,000.
  3. The head table (163 and 83 chars) is journaled with each stage's size, the stages over the cut (expected before 3.2/3.4b/8.2: step-plan inline 21,944, ask-agent 23,626) and the share of stages that fit a 4,416-char card; no head grew without a named offset against the post-1.0 baseline; G-RENDER; G-STD. The hard "every head <= 20,000 at 163" check is set at Step 8.5.
- Repeat while any condition fails; no iteration limit.
- Stop blocked when a P0 item cannot fit with every P3 block dropped and no offset exists (owner: D-27).

**Step 1.3 Reading-path accounting, host probes and the extended S-6 probe**
- Work: `metrics.py` reports four buckets (packet output; files opened by class: entry card, packet file, handoff, improve card, ADAPTER, references, run start/reference/index, knowledge, ShipLoop scripts; child handoffs; runtime output) in characters, warm apart from cold segments (first 12 calls after a break), compactions per 100 min, time to first productive action, check-only use, permission cancels, script latency (unknown is null), **warm `next` calls (not within 12 calls of a break or restart)**; `clear.py` adds orientation bytes by class and time to the first state-changing call; **`arms.py`** reads per-arm break records and applies the 8.5 rule on paired positions; **host probes**: printed output cut per host (print 40 KB of numbered lines, record what returns) for Claude, Codex and Grok; what each host re-reads or re-attaches after a compaction (first-call census per host); whether Claude's SessionStart accepts source `compact` and injects stdout, and what `hooks-list` shows on Grok and Codex.
- Exit when ALL of these hold:
  1. On a read-only copy of live2 `events.jsonl` the report reproduces evidence 3 and the S6 recount (14 compactions, SKILL.md first after the last 9, `next` within 12 calls after 9) within 1%.
  2. A fixture-stream test whose first post-clear call reads a 79,950-char file reports `orientation_bytes >= 79,950` while the S-6 verdict still counts only redone state-changing calls; a fixture break stream with an extra `next` counts one warm call.
  3. `arms.py` on two fixture arms prints a chosen arm and exits 0, and exits non-zero when the paired difference is inside the A/A spread; the probe table is journaled; G-QUICK; G-NOTE.
- Repeat while any condition fails; no iteration limit.
- Stop blocked when a host stream lacks a field (record "not measured"; do not infer).

### W2. Packet-local dedupe (Tier 1)
Nothing printed twice in one packet; a script proves the duplicate. Where: `shiploop_navigator.py` (`_spec_diff_lines`, `_followed_lines`, `_consumer_lines`), `shiploop_knowledge_home.py` (`READS`, `spec_diff`), `shiploop_consumer_delivery.py`. Saving: fixture ten stages 362,660 to 273,444; live plan -21.9 KB, test-strategy -16.4, test-spec -11.3, document and verify -16 each; about 77 KB of the 315.8 KB preparation total with 2.2. **Small homes: zero.** Risk very low; amend decision D3 so "uncut" means nothing is cut that is not printed in the same packet. Needs 1.0, 1.2.

**Step 2.1 Ledger review of the merged new-file diff pointer (BUILT: 0eeb68e2, merged by 1.0)**
- Work: review 0eeb68e2 and f3f6a6bc against the ledger; the wording is conditional (say "above" only where `READS` lists the file, else "open HOME/<file> (<size>)"); a lost obligation is reverted alone.
- Exit when ALL of these hold:
  1. `python3 -B test/shiploop-handoff.test.py` exits 0 (8 of 10 NewFileDiffPointerTests fail on 1a7c12d7, recorded).
  2. On the long-knowledge fixture each hand-off block is no larger than the branch's record (plan 28,734; test-strategy 26,044; product-acceptance 28,862; test-spec 28,532; document 37,898; verify 38,002; implement 15,297) and the small-home render is byte-identical; G-STD.
- Repeat while any condition fails; no iteration limit.
- Stop blocked when review finds a lost obligation only the owner can waive.

**Step 2.2 Remaining same-packet duplicates**
- Work: test-spec and system-test-author print `follows` as ids when quoted; drop "Current planning sources" unless a reconciliation exists; shorten "Last accepted transition" (summary only when it differs from the Done line, evidence as symbols, lessons one line each); the delivery block becomes an anchor line, obligation ids and standing exclusions (about 480 B) except in the stage set computed from `_OBSERVABLE_AT`/`_NEGATIVE_OBSERVABLE_AT` plus plan and system-test-author, which print it whole; the run-wide test-strategy source prints at system-test only; lint block = verdict, rule, waiver shape; "Later steps" = id plus owned paths; red and green leave implement; fix the false "(quoted below)".
- Exit when ALL of these hold:
  1. A test finds no 25-char-plus line twice in a packet's consumer block for every stage x route; `grep -rn "quoted below" skills/shiploop/scripts/` finds none where the file is not quoted below.
  2. A test asserts the stages printing the delivery block whole equal the computed set; consumer-delivery exits 0.
  3. "Last accepted" only: G-S6 rows at a boundary and inside a stage pass on Claude and Grok; G-RENDER; G-STD.
- Repeat while any condition fails; no iteration limit.
- Stop blocked when the "Last accepted" change fails the battery twice with different causes (owner: keep the block).

### W3. Symbols, commands and the centralised reference (Tier 1, S-6 gated)
Prose paths become symbols; one derived card is the run's master reference; the entry card gets a recovery block and a pilot split; the loop block states its call. Where: `shiploop_navigator.py` (`symbolic`, `_first_callback_lines`, `_submitted_result`, `emit`, `save`), `shiploop_reference.py` (`render_start`, `stale`), `shiploop_context_index.py` (`MAP_ROWS`), `shiploop_prompts.py` (`index_pointer`, `OWNER_RULE`), `shiploop_loops.py` (`invoke_lines`), SKILL.md. Saving: PK3 -2.0 KB per live packet (measured); typed path chars -12 to -15% (about 3% of output live, 1.5% normal); recovery reads are credited to 3.5b and 6.1, not to the card. Risk medium: a model skipping the card, the head budget, card and one-liner drift. Needs 1.0, 1.1, 1.2 (0.1 for 3.3). Audit validation V3, V4.

**Step 3.1 Symbols in prose (BUILT: aeed522f; finish)**
- Work: review aeed522f (GUIDES root, `prose_symbols` over a closed list of prose lines, guard in packet-completeness) and finish: CHILD root in Improve handoffs only; a per-host probe row (Codex reads through the shell, where `RUN/...` is literal); no `FEATURE/spec.md` lines left.
- Exit when ALL of these hold:
  1. A test plants a literal absolute path under each root in prose and the guard fails; with the change it prints as a symbol, while the callback, commands, Keepalive marker, "Full packet:", Progress link, template `evidence_refs` value, loop Work/Contract/Receipt/Start (inside the BEGIN/END block) and `/improve` line stay absolute.
  2. Every symbol used in any packet is defined in that packet's References block; `grep -rn "FEATURE/spec.md" skills/` finds none.
  3. G-RENDER: every changed line is a symbol substitution (measured -2.9% offline, about -2.0 KB per live packet); G-STD.
- Repeat while any condition fails; no iteration limit.
- Stop blocked when a host cannot resolve a symbol the model wrote (owner: drop that root).

**Step 3.2 Script-owned path handling and the command frame**
- Work: (a) `_submitted_result` (and the `final_result` read in `_derived_improve_receipt`) expands a leading HOME/RUN/WORKTREE/GUIDES root in `evidence_refs`, `assumptions[].evidence`, `unverified[].evidence` before every gate, stores the expanded text, and refuses an unknown root; the loop-receipt prefill stays the literal absolute path (`check_terminal` runs first); `--check-only` prints files written since the packet as a suggestion; (b) `complete` defaults `--result` to `RUN/inbox/<action>.md` (the script already refuses any other path); the printed callback keeps the **absolute** result path in "write the result to <abs>/inbox/<id>.md, then run `complete --run-dir=<RUN abs> --action=<id>`" (no symbol in the one path a host must write), so only the typed `--result=` flag goes; the **Pause command stays literal**; Halt shortens to "the Pause command with `halt`, terminal, only on the user's explicit stop"; (c) print `python3`, not `sys.executable`, in the red-check line (the loop branch already did it for the start command); (d) a RULES bullet: run ShipLoop and loop commands exactly as printed, no redirect, `;` chain, echo or wrapper variable.
- Exit when ALL of these hold:
  1. Through the real gate (callback-contract): `RUN/inbox/x.md` in `evidence_refs` is expanded and existence-checked; a missing one and an unknown root are refused.
  2. Every offline callback ends `--action=<id>` with no `--result`; `complete` without `--result` is accepted, with another path refused; `grep -n "sys.executable"` in `shiploop_loops.py` and `shiploop_navigator.py` finds none in a printed command; keepalive and status-display still bind; a test follows the printed Pause text literally through the status hook and the keepalive stop path.
  3. G-RENDER: Halt and the dropped `--result=` shrink the standing frame by at least 250 B per head at the live prefix, no literal command became symbolic, and the freed bytes are the named offsets in 1.2's table; G-STD.
- Repeat while any condition fails; no iteration limit.
- Stop blocked when a host rejects a callback without `--result` (owner: keep the flag).

**Step 3.3 The start-here card and the first-lines pointer (section 5)**
- Work: a pure `render_start(state, root, version)` beside `shiploop_reference.render`, written by `navigator.save()` with `status.md`, `context-index.md`, `reference.md`; **`emit()` rewrites any of the derived files when the freshly rendered text differs from the file** (not on version alone; fixes reference.md too); contents per 5.3, no position, no mention of the improve skill; the built pointer lines and `OWNER_RULE` placement replaced per 5.5 (the literal Recovery command moves to the first lines, one definition; the later Recovery line becomes a reference to it); `context-index.md` returns to being the record; `reference.md` intro reads "Long forms, by anchor. Orientation is start-here.md."
- Exit when ALL of these hold:
  1. `wc -c RUN/start-here.md` is at most 4,600 at a 163-char run dir and 4,200 at a normal install (draft: 4,416 and 3,998); a test fails on growth.
  2. A test finds the card byte-identical at every revision of a 24-stage walk for fixed options, its stage sequence equal to `stage_spec`'s for planning_review x delegation x backchain x lint, every symbol any packet uses defined in the card, the PK1 exhaustiveness test (every top-level entry of a populated run named) passing against the card, the host-authored `WORKTREE/SHIPLOOP.md` index and `reference.md#policies` named, and `grep -ic improve RUN/start-here.md` printing 0.
  3. The pointer sits directly under the header in every packet kind (producer, Improve, paused, halted, done) and names an existing file; rendered packets contain no "Run context index" line; a test changes the CLI root with the version unchanged and finds the card and reference.md rewritten; rehydration MasterIndexTests re-pointed; G-STD.
- Repeat while any condition fails; no iteration limit.
- Stop blocked when the owner rules the card should be the top of `reference.md` (D-21).

**Step 3.4a Verb-keyed orient print (S-6 gated)**
- Work: `emit(core, root, state)` gains an orient flag: `next`, `init`, `workspace start`, `resume` print `start-here.md` first and the head builder fills the rest under the 20,000 host cut with the status block before char 16,000 (P3 drops first, then P1 trims; only if P0 plus the card cannot fit does the print name the file instead); `complete` prints the packet only. Nothing is removed from any packet. Resume facts (at most 1.5 KB, `next` only, after the card): the exact `next_argv`/`done_argv` of an open loop or Improve receipt and the last check-only record.
- Exit when ALL of these hold:
  1. A test finds, for all 24 stages at 163 and 83 chars, the orient print at most 20,000 chars with the status block ending before char 16,000, the card present whenever P0 plus card fit, and the pointer text true in both forms; the status hook and keepalive `observe()` bind from a `next` and a `complete` print.
  2. The journal records the share of stages printing the card inline: if it is below 18 of 24 at a normal install, the card is split into an inline part of at most 3,000 chars (symbols, commands, standing rules) and a file-only rest, and the test is rerun.
  3. G-S6 arms A1 and A1c (5.8) pass on Claude and Grok at hello scale, at a boundary and inside a stage, with the resume prompt withheld (R0); warm `next` calls not above control; G-STD.
- Repeat while any condition fails; no iteration limit.
- Stop blocked when A1 fails S-6 twice with different causes: keep the pointer lines and the top block, ask the owner.

**Step 3.4b Lean frame (optional, last; built on its own commit)**
- Work: only after 3.7 shows the card is read: one symbol line replaces the References symbol block; the State/CLI locator/Scratch line goes (Scratch stays in RULES); the Repository index line stays as one clause; the Pause line stays literal; Halt as in 3.2. Re-measure the increment over PK3 on the merged tree. Built on a branch commit, merged only if arm A2 is selected.
- Exit when ALL of these hold:
  1. G-RENDER: the standing frame increment over PK3 is recorded at the live prefix and a normal install; if it is below 0.5 KB at a normal install, the step is deleted from the plan.
  2. Ledger rows exist for every line removed; G-S6 arm A2 passes; G-STD.
- Repeat while any condition fails; no iteration limit.
- Stop blocked when A2 fails S-6 twice with different causes: do not merge, ship 3.3 and 3.4a alone.

**Step 3.5 Entry card: recovery block, then the pilot split**
- Work: (a) a block of about 450 chars directly after the title of `skills/shiploop/SKILL.md` (5.5): resume from the run directory in your summary or handoff, run `next --run-dir`, otherwise list `.shiploop-runs/*/run/state.md`, use the only active run for this repo and with several record an open item instead of guessing; (b) pilot (credited with the recovery saving): keep binding, prerequisite checks, ownership, exact callback and recovery discipline, authority limits (target 25 to 30 KB, a projection); move by trigger into purpose-sized files of at most 8 KB in `skills/shiploop/references/` (parallel chain and ask-agent route, Backchain selection and passes, test-loop and confirmation, init-time options), each behind a one-line trigger, never into the existing 20 to 55 KB references; (c) SKILL.md becomes a ledger source: each moved paragraph has a row (obligation, old place, new home, trigger) or is deleted because the packet carries it; add the note naming the two programs to pre-approve.
- Exit when ALL of these hold:
  1. `grep -n "shiploop next --run-dir" skills/shiploop/SKILL.md | head -1` reports a line number at most 40; `wc -c skills/shiploop/SKILL.md` is at most 30,000 (after (b)) and each new file at most 8,192 (a test asserts both); every moved obligation has its ledger row; the block contains no "newest folder" fallback.
  2. Fresh-context start and resume pass inline and ask-agent; chain, Backchain and test-loop cases read their new file; entry-card bytes per break and the first call after a clear are not worse than control (1.3, same host).
  3. skill-frontmatter, package-integrity, marketplace-package exit 0; G-STD.
- Repeat while any condition fails; no iteration limit.
- Stop blocked on (b) until D-22; (a) may ship alone, with no byte credit.

**Step 3.6 Explicit Until Loop block (BUILT: 0d462ca4, merged by 1.0; your own words asked for it)**
- Work: review and finish: BEGIN and END marker lines around exactly the Work, Exit when, Repeat, Contract and Receipt lines; one literal start line per host; a result sentence naming the receipt; the resume line (a read packet leads with it, never a second start); contract JSON, its hash and the Improve start contract unchanged; report the block's bytes against the 1.2 table.
- Exit when ALL of these hold:
  1. Tests (loops, test-loop): both markers once per looped packet with exactly five argument fields between; the printed start command, run against the real runtime in a temp dir, makes the receipt active; paths are that action's.
  2. e2e counters, flow, `packet_anatomy` and the hooks still recognise the packet; the block's bytes (+596 to +616 per looped stage; step-plan inline +1,063 at first) are inside the 1.2 table; a Claude E2E on the two-line argument passes; G-STD.
- Repeat while any condition fails; no iteration limit.
- Stop blocked when the block cannot stay in the head budget without dropping a P0 item.

**Step 3.7 Forced-clear battery for W3**
- Work: run the 5.8 arms with `slice.py --case node-fix-bug` and forced clears at six fixed positions per slice (boundary and inside implement, test, verify, carry-forward, step-plan, one Improve window), a two-step ask-agent chain and an Improve-window compaction; Grok 4.7 medium and Claude Sonnet 5.5 in full, Codex a smoke slice (Sol for reviews, Luna E2E at xhigh); one Salesforce-scale slice up to the end of test-spec (no org access) or the fake-sf rehearsal; `arms.py` decides; rubric-eval (Opus 5.5 medium, one judge per round, blind to arm) adds evidence.
- Exit when ALL of these hold:
  1. Evidence exported under `docs/experiments/shiploop-eff-final-<date>/` holds, per arm and break position: calls and chars read before the first productive action, whether card, entry card, ADAPTER and packet file were opened, redone calls (zero), refusals per verb, warm `next` calls, typed path chars.
  2. `python3 test/shiploop_e2e/arms.py <evidence dir>` exits 0 and prints the selected arm (A1 or A1c alone if A2 fails S-6; A4 only on Claude and only if the probe passed; A2 only if it beats A1c on bytes without regression); the journal test finds the row.
- Repeat while any condition fails (add repeats sized from the A/A); no iteration limit.
- Stop blocked when a host or quota is unavailable or a run would disturb the owner's live E2E.

### W4. The quoted-knowledge index and the request (Tier 2, owner decisions)
A living file at or under a per-file size prints whole; above it, an index of headings, byte sizes and R/AD ids; the request gets a display index. Where: `shiploop_knowledge_home.py`, `shiploop_navigator.py` (`reads_lines`, `_consumer_lines`, `improve_handoff_text`). Saving, live with the diff pointer: test-strategy -32.1 KB, plan -51.3, step-plan -29.8, test-spec -29.8, prepare -13.5, implement -13.9; -184 KB of the 282 KB quote region plus about -150 KB in Improve handoffs. Risk moderate (the audit defers slicing until consumer coverage is proven). Needs 1.1, 1.2, 2.2, 3.7, D-1. Audit validation V3 on the 3 x 5,000-char fixture, V4.

**Step 4.1 Index above the per-file size (D-1)**
- Work: the size gate with an index of about 0.3 to 0.5 KB per large file; entries a step follows still arrive through `follows`; architecture.md stays whole at implement; Improve handoffs inherit; a manifest line instead of the 33 KB intake quote on a second run; a consumer-coverage derivation from `DUTIES` and `READS`; the threshold is per file and set from the live home sizes, not one global cliff at 6 KB.
- Exit when ALL of these hold:
  1. A small-home fixture (each file at most the threshold) renders byte-identical to base; on the 16/14/6 KB fixture per-stage savings are recorded and the index lists every heading.
  2. A coverage test: every section or R/AD id a stage's duties or reads name exists in the index; **a seeded-omission test**: a requirement placed only in an indexed section no duty names is still honoured by the stage (blind check of escaped requirement misses, rubric-eval).
  3. G-S6 rows "index route" and "reads original instead of index" pass, no new first-pass refusals; G-STD.
- Repeat while any condition fails; no iteration limit.
- Stop blocked until D-1 (it amends decision D1, whole-file quotation).

**Step 4.2 The request (4.2a Tier 1; 4.2b D-2)**
- Work: (a) write `RUN/request.md` with sentences S1..Sn as a display index and a script-measured notice (never a refusal) that every S-n appears in the intake summary; (b) on your go, print a pointer plus a required `constraints` list in non-mapping stages, keeping verbatim printing in intake, spec, plan and product-acceptance.
- Exit when ALL of these hold:
  1. The S-ids equal the sentence split of the stored request (test); the notice fires on a missing S-n and never refuses.
  2. (4.2b) request bytes drop about 4.8 KB per non-mapping stage and constraints survive a clear in the battery; G-STD.
- Repeat while any condition fails; no iteration limit.
- Stop blocked at 4.2b until D-2.

### W5. Step-scoped implement hand-offs (Tier 1)
Implement quotes the union of the step's criteria, the test cases whose criterion is in that list and every R/AD id its task and criteria name; item-set fallback; the item's AD entries or architecture.md stay. Where: `_consumer_lines`. Saving: S1 hand-offs 24.7 KB to about 1.2 KB; for k steps about (k-1)/k of 24.7 KB per item. Risk low (structured ids, fails toward more text). Needs 1.2, 2.2.

**Step 5.1 Step-scoped hand-offs**
- Work: implement the union rule and the fallback in `_consumer_lines`; "Later steps" stays id plus owned paths.
- Exit when ALL of these hold:
  1. A two-step test shows S1's hand-off at most 2 KB (was 24.7 KB), S2 unchanged where it serves C2 to C10, the item-set fallback when nothing resolves, and the implement Improve handoff inheriting the smaller block.
  2. G-S6 "implement boundary" and "implement inside" pass; a two-step ask-agent chain keeps the same accepted paths; G-STD.
- Repeat while any condition fails; no iteration limit.
- Stop blocked when a criterion cannot be resolved to an R/AD id (owner: add the id to the plan schema).

### W6. Improve: route card, handoff, hook, stop rule, pass tail
The script writes what it knows; the runtime ends a loop on a measured fact, never a count. Where: `skills/improve/references/shiploop-route.md` (new), `skills/improve/SKILL.md`, `shiploop_navigator.py` (`improve_handoff_text`, `improve_opening_text`, `_improve_commit`, `improve_start_contract`), `shiploop_protocol.py`, the hook and stop branches, `skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py`. Saving: per-pass write 4.3 to about 1.5 KB (about 14k output tokens, 1 to 2 min per 75, inside the prose ceiling); 26 git calls (6.0 min) fold into a digest; Improve context down up to 75% of 1.16 MB; stop rule 6.7 min gross, 4 net (n=5). Risk medium. Needs 1.0, 1.1, 1.3, 3.1, 3.3. Audit validation V4 with four Improve cases.

**Step 6.1 Route card and handoff pilot A (ships with the hook)**
- Work: (a) `skills/improve/references/shiploop-route.md` (about 5 KB) replaces about 55 KB of whole-file reads on the ShipLoop route (SKILL.md 28.4, review-policy 6.6, ADAPTER 24, callback-evidence 13.5); `improve/SKILL.md` becomes a router keeping "When this skill is invoked with the argument ShipLoop Improve: <handoff path>"; (b) in `improve_handoff_text` the script selects the conditional paragraphs the stage provably needs and moves the invariant ownership, recovery, commit and return policy (about 11.1 KB of the 33.7 KB implement handoff) to the route file; per-action facts, Code craft verbatim and exact return commands stay beside the action; a two-line head names the card and CHILD; short child dirs (`spec-1`). Pilot B (locators with sizes) only after A shows no loss. This step carries the ADAPTER-read credit.
- Exit when ALL of these hold:
  1. The route file is at most 8,192 bytes and each obligation of its four source documents has a ledger row.
  2. The implement handoff is at most pilot A's journal target (projection 22 KB); 13 to 18 KB only after B and the recorded Code craft reconciliation.
  3. The four pilot cases pass (stopped-child restart, commit-policy variants, two-step chain with aggregate scope, context loss mid-review), pass-1 defect catch equals control, and Improve-card plus handoff bytes read per Improve stage fall (1.3); G-STD plus improve-plugin, improve-runtime, skill-frontmatter, marketplace-package.
- Repeat while any condition fails; no iteration limit.
- Stop blocked when the target needs the Code craft decision changed (owner).

**Step 6.2 Skill-call hook (BUILT and MERGED on the release branch: 996a378c, c61e80e6, fix 5d028aee; Claude-only)**
- Work: verify, do not rebuild: a `PostToolUse` hook on the Skill tool appends to the bound run's `skill-calls.jsonl`; `complete` on an Improve stage refuses until the record holds an `improve` call made after the stage's `start.json` whose argument carries its handoff path or action id; no gate where no record can exist (other hosts, no hooks, `SHIPLOOP_KEEPALIVE=off`, ask-agent); a Codex/Cursor process started from a bound Claude shell is not gated (5d028aee).
- Exit when ALL of these hold:
  1. `python3 -B test/shiploop-skill-calls.test.py` exits 0 (28 tests, registered in `test/suite_catalog.py`) and its gate tests fail with the gate removed.
  2. A Claude node-fix-bug slice invokes the improve skill for 4 of 4 Improve stages (was 1 of 4) with Improve reads per stage recorded (after 6.1); packets render byte-identical; G-STD.
- Repeat while any condition fails; no iteration limit.
- Stop blocked until 6.1 is merged and you accept the Claude-only scope (D-24).

**Step 6.3 `improve-pass`: the script-written pass tail (two-step default)**
- Work: the model writes `review-<n>.md` (front matter classification, exit, continuation; Read/Found/Changed/Checked/Class; `## Handoff`) and a commit message with subject, `Key learnings:`, `Learned-from:`; a new `improve-pass` verb composes the commit, the done report and a digest from script facts, refuses pre-filled `checks.md` rows older than the last edit as evidence, and prints the exact runtime `done` command; register the verb in the status hook and keepalive verb sets (`PACKET_VERBS`, `COMMAND_RUN_DIR`, `DRIVING_COMMAND`) or exclude it deliberately; one concise-direction sentence in the opening and the handoff recipe. Single verb only on D-4.
- Exit when ALL of these hold:
  1. Through the real gate (actual-improve-cli): a review without `Key learnings:` and a stale `checks.md` row are refused and each named exit is submitted and accepted.
  2. A live-shaped Improve pass writes at most 1.5 KB of model output (was 4.3 KB) by the 1.3 buckets; `grep -n "improve-pass"` finds the verb in `shiploop_status_hook.py` and `shiploop_keepalive.py` or the journal records the exclusion; G-STD.
- Repeat while any condition fails; no iteration limit.
- Stop blocked at the single-verb variant until D-4.

**Step 6.4 Stop rule (BUILT: 60018152, 3b9ca9c9 on `-stop-`; merged by 1.0; upstream tag and re-vendor need your go)**
- Work: complete the loop when the model reports a pass trivial and satisfied, checks passed, and the content tree equals the tree after the previous pass (the start tree for pass 1); tree = Git tree plus the bytes of `RUN/inbox/<reviewed action>.md` (`candidate_paths`); a pass that changed the tree never ends the loop; a gate-2 start is refused when the tree cannot be measured; no count, no timer; the adaptation is recorded in `PROVENANCE.json` and upstreamed (`/Users/dadleet/src/until-loop-lab`, README first). The branch keeps the name `required_trivial_reviews` because the published plugin (0.8.3) refuses unknown contract fields; stage loops and the Backchain child use the published plugin, so state the version skew on hosts that hand the Improve loop to it (the import refuses older packets by name).
- Exit when ALL of these hold:
  1. improve-runtime, `bash test/improve.test.sh`, standalone-improve, stopped-improve, actual-improve-cli exit 0; cases cover trivial-unchanged at pass 1, edit-then-unchanged at pass 2, trivial-but-changed not completing, a candidate-file-only edit counting, A-B-A trees not clean, exit unmet or checks failed with an unchanged tree not completing.
  2. The replay of the live pass sequences stops spec after P7, test-strategy P2, plan P3, step-plan P1, test-spec P2 with all 8 material passes before their stop; the three audit cases show pass-1 defect catch equal to control.
  3. `test/shiploop_e2e/SPEC.md` S-10 carries the dated carve-out in the diff; notes under `changes/improve/` and `changes/shiploop/`; G-NOTE.
- Repeat while any condition fails; no iteration limit.
- Stop blocked until you approve the S-10 text, the upstream release and tag, and the re-vendor with the pending 0.8.0 pin (D-5, D-6).

**Step 6.5 Lean print of the Until Loop return (vendored; owner)**
- Work: the printed `done` return carries status, progress, instruction, `next_argv`, `done_argv` and the exit and repeat conditions; the full packet goes to the receipt; `_PACKET_KEYS` in `shiploop_loops.py` changes with it.
- Exit when ALL of these hold:
  1. A non-terminal `done` return is at most 3 KB on the live-shaped fixture (live: 19 to 22 KB, 29 returns, 163 KB).
  2. G-S6 "Improve compaction mid-pass" passes; improve-runtime, standalone-improve, actual-improve-cli exit 0; G-NOTE.
- Repeat while any condition fails; no iteration limit.
- Stop blocked until D-19 and D-5.

### W7. Script-owned fields and verified fixtures (Tier 1)
The script derives what it knows and prints the vocabulary its validators enforce; computed expected values are marked copied, run or derived. Where: `shiploop_navigator.py` (`_checked_line`, `_COMMON_GATES`), `shiploop_assumptions.py`, `shiploop_stage_spec.py`, `shiploop_item_scope.py`, new `shiploop_derivations.py`. Saving: part of 4 to 7 min per run plus about 90k tool-result tokens; derivations up to 8 to 9 min on cases with computed values (not additive with the stop rule). Needs 1.1, 1.2, 3.2.

**Step 7.1 Gate vocabulary in the packet, check-only first, derived bookkeeping**
- Work: (a) print the allowed `consumer` values, the credential-key shapes as guidance, the wrapper-versus-inner-object line, the headline limit and the HOME screen and id check in Checked-by, from the validators' own tables, each with its named offset; (b) one RULES line "write your best result, run `complete --check-only`, do not read ShipLoop scripts", kept only as a measured line; (c) derive intake `delivery_assessment` (the model supplies kind, expected, consumer), step-plan `absent` expectations, `paths` and `follows`, print the item context to about 4,000 chars and each step's commands; test-spec left out only via `no_test_item`; coverage-by-mention gates as counted notices first; prefill plan `assumptions`, product-acceptance `unverified`, release-verify `lessons`, the release-plan rollback recipe.
- Exit when ALL of these hold:
  1. A normal-run slice reads `shiploop_*.py` 0 times (97 reads, 482,103 chars at S3) by the 1.3 bucket.
  2. Through the real gate: every prefilled row can be overridden and no notice refuses; heads stay inside the 1.2 table; G-STD.
- Repeat while any condition fails; no iteration limit.
- Stop blocked when a derivation needs a judgement the script cannot prove (owner).

**Step 7.2 Derived-value provenance (needs a second-app proof)**
- Work: a shared rule in the spec, test-strategy, test-spec and step-plan duties: "Mark each expected value as copied (request or file), run (a tool printed it) or derived (you worked it out). A derived value a test will assert is computed by a script when you write it, with the command and output saved under RUN/scratch; otherwise it stays marked by-hand. Never settle a computed value by re-reading it."; optional `derivations` `{subject, basis observed|oracle|by-hand, ref, reason}` with its gate in `shiploop_derivations.py`; a focus line in the Improve opening only when by-hand rows exist.
- Exit when ALL of these hold:
  1. The gate refuses nothing when `derivations` is absent and refuses a `by-hand` row without a reason (test).
  2. A second non-chess app with computed values shows fewer spec-stage Improve minutes than control beyond the A/A spread; with no effect the step is removed; G-STD.
- Repeat while any condition fails; no iteration limit.
- Stop blocked until D-12.

### W8. Wording, the first-packet directive, the credential refusal
Fix defects and inducing duties first; then one screened line. Where: `shiploop_prompts.py` (`DUTIES`, `STAGE_RULES`, `CODE_CRAFT`, template placeholders, new `STYLE_RESULT`), `shiploop_stage_spec.py`, `shiploop_lint.py`, `shiploop_navigator.py`. Saving: wording alone under 3% of duty bytes; plan head 21.2 to about 15.7 KB only with 8.2; the style line 1 to 3% of wall time. Risk: about 230 literal pins match duty and Improve text: confirm the obligation is present, then convert the pin to a ledger token; never renumber duty items without moving `loops.WORK`. Needs 1.1, 1.2.

**Step 8.1 Defects with no design choice**
- Work: fix "(quoted below)" and the stale `FEATURE/spec.md` goal; the lint sentence "only the item's last step is gated" (every step gates); the unenforced "a list too large for the loop contract is refused"; the "test-author" refusal text; Work lines citing only part of the duty items; the false `_checked_line` ("prints every refusal first" while gates raise at the first fault); a script-written start-contract file for the optional Backchain child.
- Exit when ALL of these hold:
  1. `grep -rn "FEATURE/spec.md\|only the item's last step\|a list too large" skills/` finds none, and a test pairs each corrected sentence with the behaviour it describes through the real gate.
  2. G-STD.
- Repeat while any condition fails; no iteration limit.
- Stop blocked when a sentence describes behaviour the owner wants (change the code, not the text).

**Step 8.2 Duties that induce excess, summary placeholders, conditional blocks**
- Work: intake duty 1 "cover, do not copy; cite S<n>" (after 4.2a); spec positive/failure/boundary lines "only where each says something the others do not, otherwise `n/a: <reason>`"; test-spec states shared values once; step-plan duty 9 omits untouched topics; a step `task` cites ids; per-stage `summary` placeholder (for example `<decisions, defaults, open questions and owners that only this result records; not a restatement of the request, the spec or the files you wrote>`; intake `<one clause per request sentence S<n>: the outcome, boundary, default or open question it maps to>`); traps: `check` is safe to repeat locally with each step's commands printed, test-strategy "the host's tool listing is the probe", `--delivery-contract` only when the request or host asks (D-14), example ids `TC_1` with "choose ids legal in the runner's test names", scaffolding folded into the first step that uses it, prepare "start" means the no-op form. Tier 2 (D-18): the Backchain block moves to a reference.
- Exit when ALL of these hold:
  1. Each rewritten duty's ledger row is confirmed present (G-LEDGER) before its pin is converted.
  2. A replay on node-fix-bug and a second app gives an intake summary of at most one clause per S-n, none missing; the plan head is at most the 1.2 table's planned value; G-STD.
- Repeat while any condition fails; no iteration limit.
- Stop blocked at the Backchain move until D-18.

**Step 8.3 The first-packet concise-language directive (screened; section 6)**
- Work: one constant `STYLE_RESULT` (B0+) printed at one site chosen by the screen (the end of the "Fill the template:" line, or under the pointer lines as built); reuse it in the Improve opening and handoff recipe; never in the request or `STAGE_RULES`; SPEC clause S-16 in its own commit (D-8).
- Exit when ALL of these hold:
  1. Rung 0: the constant appears once per producer head and whole packet; heads within budget; delegation exits 0.
  2. The A/A sets n (detectable effect = 2.8 x CV x sqrt(2/n)); rung 1 writing-turn replay (at least 25 per arm): paired prose characters fall beyond the control spread, reasoning tokens do not rise, every canary holds.
  3. Rung 2 slice (node-fix-bug, node-add-function; Grok, Claude, Codex) on count metrics and canaries; rung 3 last: Salesforce chess to the end of test-spec; `arms.py` ships the line or ships nothing.
- Repeat while any condition fails (extend n, not the claim); no iteration limit.
- Stop blocked until D-8 and D-9.

**Step 8.4 Credential-pattern refusal removal (BUILT and MERGED: d4d08351, f1f38850, merge b6b290a7; S-9 edit and note fix in 320a526e)**
- Work: verify, do not rebuild: `_reject_credentials`, `_credential_refusal` and their call sites are gone; `workspace start` no longer screens the prompt; `shiploop_git.commit_paths` commits every given path (a path named like `.env` included; what keeps secrets out of the product commit is the review-return keep/exclude choice and the duty); display redaction on the progress page and lint output, positive guidance and "Name a credential by its alias or mechanism, never its value" stay; the second commit reverts alone to restore the commit-path guard.
- Exit when ALL of these hold:
  1. `grep -rn "sensitive_text\|_reject_credentials\|_credential_refusal" skills/shiploop/scripts/` finds only display helpers that refuse nothing.
  2. The acceptance tests (callback-contract, navigator-contract, knowledge, actual-improve-cli, packet-completeness, progress-data, return-review, test-loop, workspace) exit 0; `test/shiploop_e2e/SPEC.md` S-9 lists no credential screen.
  3. The change note states that the terminal status block, the narrative and run files print a submitted result as written; G-NOTE.
- Repeat while any condition fails; no iteration limit.
- Stop blocked: none (decided by your request). Cost to state at release: no guard now keeps a real secret out of a commit that a fast-forward return could put on your branch.

**Step 8.5 Head ceiling checkpoint (NEW)**
- Work: after 3.2, 3.4a/3.4b (if selected) and 8.2, set the hard ceiling from the 1.2 table: every head at most 20,000 chars at 163 chars except the owner-decided exceptions (D-27); then set the test constant to the measured maximum plus 10%.
- Exit when ALL of these hold:
  1. `python3 -B test/shiploop-packet-recut.test.py` exits 0 with the per-stage table in force; the exceptions list equals D-27's decision.
  2. G-RENDER shows no head above its journaled value; G-STD.
- Repeat while any condition fails; no iteration limit.
- Stop blocked when step-plan stays over the cut and D-27 is open.

### W9. Harness: owner-facing console, resume, permissions (Tier 1)
Record-only metrics and printed lines; nothing in a packet or status line names a limit. Where: `test/shiploop_e2e/run.py` (LiveView, `resume_command`, `--permission-mode`), `progress.py`, `metrics.py`. Saving: no model minutes; the planning decision becomes visible at 30 min; up to about 3 min of script time (runtime `done` averages 7.4 s over 29 calls, `next` 8.1 s). Needs 1.1.

**Step 9.1 Console heartbeat, script timing, planning clock (owner-facing only)**
- Work: the live view prints `think` every 30 s of silence, `compact start/done`, the stage and revision prefix, `perm cancelled <command>`, an accept line `accept <stage> +<min> | planning <min> (stage work x, Improve y)`, and once at 30 min "planning window open > 30 min: rethink planning (Improve share n%)"; profile the runtime `done` and `next`; a `planning_total` line prints the preparation window against 30 min after each verification run.
- Exit when ALL of these hold:
  1. A replay of the saved live2 stream prints a `think` line within 30 s of every silence over 60 s, one `compact` pair per compaction and the 30-minute line exactly once (fixture test); `grep -rn "planning window" skills/shiploop/` finds nothing.
  2. The journal names the slow call in `done`/`next`; the e2e family exits 0; G-NOTE.
- Repeat while any condition fails; no iteration limit.
- Stop blocked when the host stream lacks a field (record not measured).

**Step 9.2 Resume line and host permissions (verify what e64c1156 fixed)**
- Work: confirm `resume_command` carries `--source`, `--permission-mode`, `--keep-platform` and `--plugin-dir` where used, and that a checkout-source resume passes without the marketplace gate; record the mode in `result.json`; keep the allow-all-tools launch flag a flag, never a default; LEARNINGS notes that Grok's auto classifier refused an unrequested remote deploy and that `platform.host_allow` plus the bypass flag are the route (the brief dates the resume finding 2026-10-17; LEARNINGS records 2026-10-16).
- Exit when ALL of these hold:
  1. A harness test round-trips the printed resume command through the parser for marketplace, checkout and plugin-dir runs with identical arguments.
  2. `python3 test/shiploop_e2e/run.py --preflight-only --host all` exits 0 (owner-run if a login is needed); the e2e family exits 0; G-NOTE.
- Repeat while any condition fails; no iteration limit.
- Stop blocked when a host mode needs your login or approval.

**Step 9.3 Batch independent reads (experiment)**
- Work: one RULES line "read independent files in one turn"; A/B on turns per stage.
- Exit when ALL of these hold:
  1. Turns per stage fall beyond the A/A spread without more refusals (1.3, Grok and Claude); heads stay in budget; G-STD.
- Repeat while any condition fails (add repeats); no iteration limit; with no effect delete the line.
- Stop blocked when no host exposes parallel calls.

### W10. Platform learnings to `references/platforms/` and the domain-word lint (Tier 1)
Generic text stays generic; a denylist lint guards it. Where: `shiploop_prompts.py`, `shiploop_stage_spec.py`, `skills/shiploop/references/*`, `references/platforms/{salesforce,node-express}.md`, new `test/shiploop-domain-words.test.py` and `test/domain-words.json`. Saving about 2 to 6 min on deploy-and-test runs, 8 to 10 on Salesforce with the platform card. Risk: example ids are pinned by 8 suites. Needs 1.1, 8.1.

**Step 10.1 Move platform detail, add the lint**
- Work: to `salesforce.md` move tab visibility, the default `sourceApiVersion`, `sf apex run test` counting, `TC_n` ids, the `sf org open` route, the validate dry-run example, permission-set/App Launcher/tab examples and the `consumer_entry` lightning example; to `node-express.md` the `node --test` reporter example and `COUNT_RULE` wording; generic text says "choose ids legal in the runner's test names" with `TC_1`; the `sf` wrapper prints its allowed scope in `--help` and deny messages and no longer names its source path; `osascript` and `open` are guarded like `sf`; the lint denylists chess terms (FEN, perft, castling, Kiwipete), Salesforce terms (`sf `, sfdx, Apex, Lightning, Salesforce, "permission set", "App Launcher", lightning__Tab, CustomTab) and host automation (osascript, Safari, "Chrome --version"). A generic UI example (a page opened at a URL) stays in the generic text.
- Exit when ALL of these hold:
  1. `python3 -B test/shiploop-domain-words.test.py` exits 0, fails when a listed word is planted in `shiploop_prompts.py`, and is registered (`python3 -B test/test-groups.test.py` exits 0).
  2. `grep -rIl "Kiwipete\|perft\|Salesforce" skills/shiploop --include=*.py --include=*.md` lists only `references/platforms/` files; reference-routing exits 0 (the platform card is still reached); G-STD.
- Repeat while any condition fails; no iteration limit.
- Stop blocked if a generic runner example (Jest, pytest) must go (D-13: keep).

### W11. Generic E2E harness and case split (Tier 3 chore)
A registry supplies prompt, fixtures, guards and graders to a generic harness; a new program or platform becomes a case file. Where: `test/shiploop_e2e/` (`run.py`, `hosts.py`, `metrics.py`, `clear.py`, `slice.py`, `cases.json`). Saving none in minutes. Needs 9.1, 9.2.

**Step 11.1 Separate harness from case**
- Work: move case code under `test/shiploop_e2e/cases/<case>/`; case products are never committed. The platform-declared test adapter is D-25, outside this step.
- Exit when ALL of these hold:
  1. `python3 test/shiploop_e2e/run.py --help` and `slice.py --help` run, and `grep -rln "salesforce\|chess" test/shiploop_e2e/*.py` finds only the case-registry loader.
  2. The e2e family exits 0 once; `git status --short` shows no case product; G-NOTE.
- Repeat while any condition fails; no iteration limit.
- Stop blocked while a live E2E run is in flight (never touch its folder).

### Dependency graph and waves (4.13)
| Step | Needs | Parallel with | Gate |
|---|---|---|---|
| 0.1, 0.2, 0.3, 1.0, 1.1, 9.2 | none | each other | none |
| 1.2, 1.3, 2.1 | 1.0, 1.1 | each other, 8.1, 9.1, 7.2 | none |
| 2.2 | 1.2, 2.1 | 3.1, 3.6 | none |
| 3.1 | 1.0, 1.1, 1.2 | 2.2, 3.6, 4.2a | none |
| 3.2 | 3.1 | 2.2, 5.1 | none |
| 3.3 | 0.1, 3.2 | 7.1 | none |
| 3.4a | 3.3, 1.2, 1.3 | 3.5, 6.1 | S-6 battery (A1, A1c) |
| 3.4b | 3.4a | 3.5, 6.1 | S-6 battery (A2); own commit, merge only if selected |
| 3.5 | 0.3, 1.3, 3.3 | 3.4a, 6.1 | D-22 for the split |
| 3.6 | 1.0, 1.2 | 3.1, 2.2 | loop review |
| 3.7 | 3.4a, 3.5, 3.6, 6.1 (3.4b for A2) | 6.3 | none |
| 4.1 / 4.2a / 4.2b | 1.1, 1.2, 2.2, 3.7 / 1.1 / 4.2a | W3 | D-1 / none / D-2 |
| 5.1 | 1.2, 2.2 | 3.3, 3.4a | none |
| 6.1 | 1.0, 1.1, 1.3, 3.1, 3.3 | 3.4a, 3.5 | none |
| 6.2 / 6.3 | 6.1 / 6.1, 3.2 | each other, 7.1 | D-24 / D-4 for single verb |
| 6.4 | 1.0 | any W3 step | D-5, D-6 |
| 6.5 | 6.3, 6.4 | none | D-19, D-5 |
| 7.1 / 7.2 | 1.2, 3.2 / 1.1 | 3.3 / 1.2, 1.3 | none / D-12 |
| 8.1 | 1.1 | W2, W3 | none |
| 8.2 | 4.2a, 7.1, 8.1, 1.2 | 8.4 | D-18 for the Backchain move |
| 8.3 | 1.2, 3.2, 8.2 | 9.x | D-8, D-9 |
| 8.4 | 1.0 (merged; verify) | everything | none |
| 8.5 | 3.2, 3.4a, 8.2 (3.4b if selected) | 8.3 | D-27 |
| 9.1 / 9.3 | 1.1 / 1.1, 3.2 | any | none |
| 10.1 | 1.1, 8.1 | W3 | none |
| 11.1 | 9.1, 9.2 | none | no live run in flight |

Waves (a wave starts when every step it names has met its exit): 1: 0.1, 0.2, 0.3, 1.0, 1.1, 9.2. 2: 1.2, 1.3, 2.1, 8.1, 9.1, 7.2. 3: 2.2, 3.1, 3.6, 4.2a, 6.4 (finish and test), 10.1. 4: 3.2, 5.1. 5: 3.3, 7.1. 6: 3.4a, 3.5, 6.1, 3.4b (branch). 7: 3.7, 6.2 (verify), 6.3, 8.2. 8: 4.1, 4.2b, 6.5, 8.3, 8.4 (verify), 8.5, 9.3. 9: 11.1. Steps on the same file (`shiploop_navigator.py`, `shiploop_prompts.py`) merge one at a time with G-SUITES between. Critical path: 1.0, 1.1, 1.2, 3.1, 3.2, 3.3, 3.4a, 3.7, 4.1.

## 5. The centralised reference, answered

**5.0 Verdict.** Build it as a small recovery landing page, not as a device for thinning packets. Do both of your options, split by moment: the script call (option 2) is the **delivery** where the print has room; the pointer (option 1) is the **fallback**, written where a recovering model reads first and worded as a command; on Claude a SessionStart(compact) hook is a measured third route. Retarget the pointer already built (it names the 46 KB `context-index.md`).

**5.2 Your two options on the evidence.**
| | For | Against | Verdict |
|---|---|---|---|
| **1. First line: "read this file if you lack context or are unsure"; point to a file, let the model open subfiles** | It is what the model already does (opens one master file, then subfiles); today that master is the 80 KB skill card. Cheap. Works for a model that ignores commands. | The pointer that exists got 0 opens in 16 breaks (evidence 4): mid-packet, with a trigger the model cannot report, and a sentence in a packet reaches only a model that still holds the packet, while the first call after the last 9 compactions was the entry card. The built target is 46 KB and files are read whole. A bare pointer also fails S-6: a cleared model needs RUN, WORKTREE, HOME and the callback to act. | Keep, retargeted to a card of at most 4,600 chars, worded as a command, written in the first lines. |
| **2. "Call a script function that returns the state"** | Command-shaped pointers are followed: `next` ran within 12 calls after 9 of 14 in-session compactions with no pointer at all, and after 13 of 14 breaks whose prompt named it. `next` is the documented recovery command, rewrites the packet file, is a hook-visible `PACKET_VERBS` member and re-binds the Keepalive marker. | The 13 of 14 is largely the harness's resume prompt. Today `next` prints only the 14 to 20 KB head, and **card plus head fits under the 20,000 host cut in only about 2 of 8 stages of a small bug fix**. | Adopt as delivery with a head budget that reserves the card (3.4a); if fewer than 18 of 24 stages fit, split the card. |

Which existing command can return a small state card: `status` prints a 315-char block (`RUN/status.md` is 686 B), is read-only and not a `PACKET_VERBS` member, so it cannot re-bind the keepalive; `hook-status` prints one JSON line for hooks and the driver; `context --section navigator` prints the whole packet and writes no file; `next` (`emit`) rewrites the packet file. The carrier is `next`. Add no new state verb.

**5.3 The design: three run files, three jobs.**
- **`RUN/start-here.md` (new).** At most 4,600 chars at a 163-char run dir, 4,200 at a normal install (measured draft: 4,416 and 3,998). Symbols (CLI, RUN, WORKTREE, HOME, GUIDES with values); where things are (a paragraph from `shiploop_context_index.MAP_ROWS`, including the host-authored `WORKTREE/SHIPLOOP.md` and `reference.md#policies`); commands (the literal Recovery command, others composed from its prefix, Pause literal); standing rules; Until Loop mechanics (a Receipt that exists means the loop ran: use its `next_argv`, never start twice; a loop ends satisfied or blocked, never cancelled; if `complete` refuses, fix, restart with the same command, resubmit); the stage sequence for the recorded options, stage names only, no review markers and no word "improve"; the after-a-reset checklist. No stage, revision, action id or position. Rewritten whenever its rendered text differs from the file.
- **`RUN/reference.md` (existing, about 20.7 KB):** long forms by anchor; its review schedule is generated from the mode (0.1).
- **`RUN/context-index.md` (existing):** the run's record, opened to find an earlier decision, never for orientation; its PK1 map moves to the card.

Tiers, tested by S-6 (a model holding only this packet, or this packet plus the one file it names, knows what to do, how it is checked and where the run stands; ShipLoop learns nothing about warm or cold). **T1 stays in every printed packet:** header, the first-lines Recovery pointer, one-line symbol definition, literal callback with the absolute result path, goal, Done-when, Checked-by, duties, template, outcomes and fill rule, Keepalive marker, status block and narrative, RULES one-liners, loop Start, Contract, Receipt and exits, literal Pause, the stage's inputs. **T2 in the card:** full symbol table, layout, command table, standing rules, loop mechanics, stage sequence, reset checklist. **T3 by anchor or path when needed:** `reference.md` sections, `context-index.md`, guides, knowledge files, the packet file. Not moved by this design: the request (D-2), quotes (D-1), hand-offs (5.1), the delivery block (2.2).

**5.4 Same context versus fresh recovery: the verb (and on Claude a host event) is the signal.** `next`, `init`, `workspace start`, `resume` are typed by a model that wants orientation; `complete` by one that just finished a step.
| Situation | Holds | Gets |
|---|---|---|
| Same context, next stage | earlier packets and the card it read once | `complete` prints the packet (frame unchanged; lean frame only if 3.4b is selected) |
| Compaction in a session | a summary; observed order after the last 9 compactions: entry card (80 KB, whole on Grok), `next`, packet file at offsets, ADAPTER.md, improve/SKILL.md, handoff | the SKILL.md block points to `next`, **but the whole card is still ingested until 3.5b shrinks it**; `next` prints the card when it fits; the summary-carry sentence aims at the summary itself; on Claude arm A4 injects the card after the compaction |
| Fresh session resumed by the harness | a prompt naming `next` (4 of 4 restarts ran it first) | same call |
| Delegated or Improve child | only the handed text | the frame is enough to act (T1) plus the pointer and Recovery; the handoff head names the card; the Improve packet (at its floor) keeps the absolute path in its pointer |

Budget rule: the card is part of an orient print only if card plus head fits 20,000 chars with the status block before char 16,000; the head builder reserves room first (P3 drops, then P1 trims), and only if P0 plus the card cannot fit does the print name the file. Report the share of stages that fit. No cache credit.

**5.5 Exact text.**
First lines of every producer packet (replaces the two built lines, the later Recovery line and the mid-packet index line):
```
[inner stages only] Continue in this context: do this stage here and submit its callback yourself; never clear or hand it off.
ShipLoop navigator | <stage> | revision N
Resuming from a summary or lost context (not otherwise)? Run this first: python3 <CLI> next --run-dir=<RUN>
  It prints RUN/start-here.md (symbols, file map, commands, rules, stages) when this step leaves room, otherwise names it: read that file whole, once, then this step. Do not re-read the skill card.
RUN = <abs> · WORKTREE = <abs> (all product work; never a --result value) · HOME = WORKTREE/docs/shiploop
```
The Recovery command is defined once, here. Improve packets carry the absolute `start-here.md` path in the same position (they are at their floor). Wording arms: default (above), W-owner ("Read this file if you don't have context about prior paths and what you're doing, or if you're uncertain in any way"), W-necessity ("symbols are defined only in the card"; strongest compliance, fails S-6 unless the battery passes).

Block directly after the title in `skills/shiploop/SKILL.md` (about 450 chars): "Recovering after a reset, summary or compaction? Run python3 <this skill>/scripts/shiploop next --run-dir <the run directory named in your summary or handoff>. It prints the run's start-here card and the current step; follow that step's callback. If your summary names no run directory, list <repo-parent>/.shiploop-runs/*/run/state.md, use the only active run for this repo, and if there are several record an open item instead of guessing. Keep this command in any summary you write."

Head of each Improve `handoff.md` (about 160 chars): "Start here: RUN/start-here.md (symbols, commands, rules; read once). RUN = <abs>/run. CHILD = this file's directory; the handoff names child files by CHILD/." The packet sentence that calls references "for lookup" gains "except start-here.md, which is read whole once per context". Summary-carry sentence (arm A1c): "If this conversation is summarized, keep the Recovery command and this sentence in the summary."

**5.6 What a file cannot fix: the paths the model types.** About 338,000 absolute-path characters in about 1,600 occurrences (about 142k tokens, 23.5% of output at the live prefix; the 116-char scratch prefix appears 1,616 times, a normal install about 14, so about 12% of output is the normal-install share). The model expands a symbol and types the absolute path, so a card cuts reading, not typing. Levers, none needing the card:
| Lever | Typed path chars | Step |
|---|---|---|
| Default `--result` (the script already refuses any other path) | 7.7k, 2.3% | 3.2 |
| RUN-relative `evidence_refs` expanded by one reader (51 paths in 12 results) | in the adopted 12 to 15% | 3.2 |
| Shorter Improve child dir (avg 275 chars, 169 uses), `spec-1` names | about 15k, 4.5% | 6.1 |
| Fewer doc reads once the loop block and route card exist | about 14k, about 1% of output | 3.6, 6.1 |
| Shorter ids and run root | 20.8k (6.2%), 16.9k (5%) | D-11, not now |

Adopted set: 12 to 15% fewer typed path chars, which is **about 3% of output at the live prefix and about 1.5% at a normal install** (paths are 23.5% and about 12% of output). Rejected: a launcher or shell variable (the status hook's `_verb` needs a token whose basename is `shiploop` under `scripts/` and refuses pipes, redirects, chains; keepalive patterns need a literal `shiploop ... --run-dir`); relative paths or a stable cwd (fresh shell per call, 37 of 267 commands begin with `cd`, file tools need absolute paths, subagents reset cwd); a symlink alias (a new write grant); omitting `--run-dir` (loses the keepalive binding).

**5.7 Savings, honestly.**
- Frame: PK3 measured about -2.0 KB per live packet (-3.4% on 11 real packets, -2.9% offline). The lean frame (3.4b) adds an estimated 1.0 KB live / 0.5 KB normal over PK3 (about 22 KB per run, 0.4% of intake) and is deleted if the re-measure is below 0.5 KB at a normal install.
- `next` prints the card when it fits: about +1.4 KB live / +2.5 KB normal per orient print, 14 to 15 per run.
- Recovery reads (the larger lever, 2.09 MB over the breaks): credited **once**, to shrinking the entry card (3.5b: up to about 450 KB over the 9 card-first compactions at 80 KB to 30 KB), the Improve route card and built loop block (ADAPTER 11 x 24 KB, 6.1, 3.6) and the summary-carry sentence (arm A1c); the start-here card earns zero byte credit until the battery measures it (its value is orientation quality and a stable symbol table). Time (estimate, weight low): about 9 min per 3-hour run if the recovery calls fall as hoped.
- Planning time projection: 52.7 min today; stop rule about -4, pass tail -1 to -2, conciseness within the 3.4 min prose ceiling (not additive with the pass tail), gate vocabulary about -2, re-orientation -4.5 to -9 at 50% credit: about 35 to 41 min. `planning_review none` (D-7) is the only lever that reaches 30.

**5.8 How it is tested (blocked paired design).** Rung 0, no model: the 3.3, 3.4a and 1.0 tests, the head table, hooks bind, G-LEDGER. Arms (each an exact commit; the skill sha is pinned per arm): A0 control; A0' control again (A/A spread); A1 card, new first-lines pointer and SKILL.md block, nothing removed; A1c = A1 plus the summary-carry sentence; A2 = A1c plus the lean frame (3.4b); A4 = A1c plus a Claude SessionStart(compact) hook printing the card (only if the 1.3 probe shows the event injects). Wording sub-arms on A1: default, W-owner, W-necessity. Recovery conditions: R0 resume prompt withheld, R1 as today, R2 forced compaction or clear at six fixed positions per slice (boundary and inside implement, test, verify, carry-forward, step-plan, one Improve window; Grok lists `compact`, else kill and resume), R3 a fresh delegated child (two-step ask-agent chain) and a stopped-Improve-child restart. Cases: node-fix-bug, node-add-function, a second UI example, one Salesforce-scale slice up to the end of test-spec; Grok 4.7 medium and Claude Sonnet 5.5 in full, Codex a smoke slice. Budget: about 20 slices (2 slices x 6 positions x 5 arms x 2 hosts, plus smoke). Per break position: calls and chars read before the first productive action, which of card, entry card, ADAPTER and packet file were opened, index of the first `next`, redone state-changing work (zero allowed), refusals per verb, **warm `next` calls**, hook binding, typed path chars. Analysis: paired by position, sign test on count metrics, A/A as the spread; breaks within one run are not treated as independent. Decision (script `arms.py`): reject an arm with redone work, more refusals than the control spread, more warm `next` calls than control, a lost obligation or a flipped SPEC clause; then fewer bytes ingested and output tokens beyond the spread; then time. A1 or A1c alone if A2 fails S-6; A2 only if it beats A1c on bytes without regression; A4 only on Claude; if nothing beats control, ship nothing from this item and pursue 3.5b and 3.6.

## 6. The first-packet directive

**Why every packet.** A first-packet-only direction cannot work: the first compaction landed about 17 min in and the main tenet clears context between stages; the intake packet carries it too.

**Text (B0+, 258 chars).** "Use concise, but very technically accurate language: state each fact once, do not restate the packet or narrate intent; never shorten identifiers, paths, commands, expected values, required fields, reasons a duty asks for, or learnings. Prose only, not code." Kind lines: documents (207 chars) "Documents: state each requirement, decision and command once, in the section that owns it; leave out a template line that only repeats another line; keep exact values, reasons and planned-not-passed markers."; Improve (opening and handoff recipe) "evidence: the candidate id, what changed, each check with its exit code, the commit id, the remaining gap and the review file path; cite the review, do not copy it. handoff: live state only (open gaps, binding constraints, locators); drop what this packet already carries and what a committed file states. Commit-body learnings stay detailed."

**Placement.** One constant `STYLE_RESULT` in `shiploop_prompts.py`, printed at one site: the end of the "Fill the template:" line (`_outcome_shape_lines`) is recommended (printed in head-only and whole packets, beside the gated headline, the only style rule observed obeyed, and read when the model writes). Never in the request (it would become a requirement), `STAGE_RULES` (last in an 18 to 102 KB packet, missed in 2 of 10 stage reads), the skill card, a host prompt (lost at the first compaction; only the no-code control arm), or a hook for the style line (the writer must see it in every packet; the SessionStart(compact) hook of arm A4 carries the card only). The built site is `OWNER_RULE` under the header of every packet, Improve included (93 chars: "Owner rule: concise and exact; no restating. Keep every command, path, ID and expected value."). Its text lacks three carve-outs (reasons a duty asks for, learnings, prose only), and "no restating" can cut the carriers principle 7 protects. Replace its text with B0+ and screen the two sites in the replay; ship one, never both; if the replay cannot separate them take the Fill site.

**Honest effect.** 1 to 3% of wall time at best; ceiling 3.4 min per 75 (4.5%); about 71% of the time is reasoning, latency, compaction and tools; a bare line harvests 40 to 65% of the excess; cost about 65 tokens per packet. It cannot shorten reasoning, retyped paths, the envelope or validator-forced repeats, nor beat a specific duty, so the structure layer ships first (8.2 placeholders and duty fixes; 6.3 script-written Improve boilerplate, about 45% of the done-JSON excess).

**Hazards.** (1) A general line loses to a specific duty. (2) "Very technically accurate" invites qualifiers and extra verification: measure reasoning tokens. (3) Brevity can license dropping detail (retention 0.88 to 0.48): carve-outs, canaries, a retention rubric. (4) Gates read shape only, so a thin `summary`, `reason`, `oracle` or `evidence` passes unseen: the next stage after a clear needs decisions, defaults, open owners, Design basis; an Improve reviewer needs checkable `Read:`/`Checked:` lines; improve-commit needs `Key learnings:`/`Learned-from:`. (5) Opposing text exists ("as much detail as its significance requires", "explain original learnings fully", carry-forward "lessons, each in detail"): scope or delete it. (6) Head budget: +258 chars where test-spec has 324 spare and verify's head crosses 16,000: it lands only with an offset. (7) Hosts diverge (Grok followed only the gated headline): screen on all three. (8) Goodhart: characters fall when text moves to scratch: measure total and reasoning tokens.

**Test.** Arms: A control, D structure only (8.2 without the line), B0+ at the Fill site, B0+ at the header site. Rungs (8.3): rung 0 offline; A/A first (detectable effect = 2.8 x CV x sqrt(2/n): CV 10% needs 25 per arm for an 8% effect, 20% about 98, 30% about 220); rung 1 writing-turn replay of frozen units (intake, spec, step-plan, test-spec, one Improve pass with a seeded defect; frozen from saved transcripts, not from compaction summaries); rung 2 slice; rung 3 Salesforce chess last. Canaries: every R-id kept; computed expected values byte-identical; Confirm-by/pass-when shape and test commands verbatim; each open question and assumption has owner and consequence; honesty markers once; Key learnings and Learned-from in commit bodies; the handoff keeps the untracked-file constraint and the Retired line; `evidence_refs` absolute and existing; duty-required reasons and docstrings present; the seeded Improve defect caught in pass 1.

## 7. Per-packet table (24 stages plus Improve)

Bytes. "Live" = Salesforce run on the pre-11f5a5b9 renderer (outer, document, verify, carry-forward, validate-existing figures simulated or estimated); "offline" = node-fix-bug. ^ assumes D-2 (else add about 4.8 KB); ^ targets are not part of any total. "Kept" = analysts' obligation groups preserved; the exhaustive set is the ledger. Seven obligations hold at all 24 stages: callback, result shape, Checked-by, RULES, narrative, pause/recovery frame, HOME commit and close. The first-lines pointer replaces the old index line and Recovery line (net about -200 B live per packet; Improve packets +245 to 344 B, inside the ceilings). The plan reaches an "about 8 KB printed whole" core only for stages without large quotes; the rest needs D-1 and D-2. Head sizes at 163 chars are set from the 1.2 table, not from this column.

| # | Stage | Now | Target | Main changes (step) | Kept |
|---|---|---|---|---|---|
| 1 | intake | live 18.2 KB; head 8.7 (omits request); 2nd run 46.9 | ~14.6 whole; 2nd run ~15 | S-id index, duty 1 "cover, do not copy; cite S<n>" (4.2a, 8.2); derived `delivery_assessment` (7.1); summary placeholder; manifest line (4.1) | 12/12 |
| 2 | discovery | 31.6; head 12.7 | ~15.1^ (~19.9 head-only without) | delivery to anchor (2.2); guide links 4.1 to 1.2 KB (3.1); planning region out; conditional preface (8.2) | 12/12 |
| 3 | research | 29.1; head 10.2 | ~12.0^ (~16.8) | planning region 3.6 KB out; assumption row shape plan copies (2.2, 8.2) | 11/11 |
| 4 | spec | 30.5; head 12.3 | ~18.3; head ~14.5 | "read whole", FEATURE goal (8.1); `n/a: <reason>`, placeholder (8.2); derivations (7.2) | 12/12 |
| 5 | test-strategy | 64.1; head 13.3 | ~32.3^ (~37); ~16.5 with D-1 | diff 16.4 KB to pointer (2.1); probe by listing; id rule (8.2) | 10/10 |
| 6 | plan | 101.9; head 21.2 (22.7 live) over the cut | ~63 to 69; ~28.5 with D-1; head from the 1.2 table | diff 22 KB to pointer (2.1); duties -1.0 KB (8.2); coverage notice, prefill (7.1); Backchain after D-18 | 13/13 |
| 7 | prepare | 40.4; head 8.5 | ~25.0^ (~30); ~11.4 with D-1 | environment.md to index (4.1); "start" = no-op (8.2) | 8/8 |
| 8 | step-plan | live 77.2; offline 24.7, head 19.5 (21.9 merged at 163) | offline ~20.3; head ~19 at best (D-27) | head carries the work item (1.2); Checked-by -0.6 KB; derived rows (7.1); omit untouched topics (8.2) | 10/10 |
| 9 | test-spec | live 80.3; offline 14.0 (15.7) | offline ~12.8 whole | `follows` 11.4 KB to ids (2.2); lessons into head (1.2); left out by `no_test_item` (7.1) | 8/8 |
| 10 | validate-existing | offline 14.5; ~47 if issued | ~35; offline 12.2 | mismatches only, in the head (1.2) | 7/7 |
| 11 | implement | live 86.9/82.1; offline 18.3, head 14.8 | live ~67; offline ~19, head-only | Step line in head (1.2); hand-offs S1 24.7 to 1.2 KB (5.1); lint 3.1 to 0.3 (2.2); step commands (7.1) | 9/9 |
| 12 | test | live 78.7; offline 19.9 | live ~62; offline ~16.9 | floors, Base-run in head (1.2); identical commands once; counting rules -0.8 KB (8.2) | 9/9 |
| 13 | document | est. 80; offline 13.3 | ~48; offline 11.7 whole | spec diff scoped, -21 KB; commit scope in head; `no_document_item` (1.2, 2.2) | 8/8 |
| 14 | verify | est. 98; offline 20.1, head 15.3 (17.2 merged at 163) | ~64; offline ~17.5 | diff scoped; case table from records; rerun list in head (1.2, 2.2, 7.1) | 10/10 |
| 15 | carry-forward | est. 58; offline 22.1, head 15.9 (18.2 merged at 163) | ~22 live; offline ~17 | queue-replacement rule in head (1.2); skill recipe 3.3 to 1.8 KB; pending queue (2.2, 7.1) | 7/7 |
| 16 | system-test-author | 57.5; head 12.8 | ~54 | full delivery block; records in force by script; plan once (2.2, 7.1) | 10/10 |
| 17 | system-test | 41.9; head 12.1 | ~38 | full delivery block; rerun block tailored (2.2, 8.2) | 9/9 |
| 18 | product-acceptance | 75.9; head 12.9 | ~53 | full delivery block; diff 16.6 KB to pointer (2.1); `unverified` prefilled (7.1) | 10/10 |
| 19 | release-plan | 42.8; head 13.8 | ~37 | rollback prefilled; steps once; platform examples out (10.1, 7.1) | 9/9 |
| 20 | release-check | 38.0; head 9.9 | ~31 | recipes to verdict line; plan-return lines in head (7.1, 8.2) | 8/8 |
| 21 | release | 38.7; head 10.5 | ~32 | "changed since" as a fact; return commands in head (8.2) | 7/7 |
| 22 | release-verify | 46.2; head 12.4 | ~35 | diff to spec.md only; COUNT_RULE tailored; lessons prefilled (2.2, 7.1) | 9/9 |
| 23 | operations | 35.5; head 9.6 | ~30 | full delivery block; architecture.md named; recipes to verdict line (8.2) | 7/7 |
| 24 | handoff | 24.7; head 10.7 | ~17 | delivery obligations only; open items not re-listed (2.2, 7.1) | 7/7 |
| 25 | Improve | packet 2.3 to 3.2 (+245 to 344 B first lines); handoff 27 to 34 (probe), 38 to 106 live | packet <= 2.0 to 2.8 whole; handoff pilot A ~22, 13 to 18 only after B | route card, hook, pass tail, short dirs, head names the card (6.1 to 6.3); stop rule (6.4) | 7/7 |

## 8. Measurement and acceptance

**8.1 Audit validation order.** V1: fix the three defects with narrow mode and route assertions and the audit's suites, then the quick tier (W0). V2: measure the full reading path, tokens only from usage events or a named tokenizer, failures, rework and missed obligations beside size and time (1.3). V3: pilot one context change at a time, each with its own offline arm and battery row: card and pointer (3.3, 3.4a), entry card (3.5), Improve handoff (6.1), index (4.1). V4: compare a populated one-item run, a multi-step delegated chain and a context-loss/recovery case, recording task correctness, missed requirements, refused callbacks, rework, reads and tokens, elapsed time, same scope and authorization. V5: no loss of obligations before size or speed; no new caps; broad migration also needs release E2E checks.

**8.2 Metric classes.** Count and structural (resolvable at small n when large, analysed paired by position): reads of `shiploop_*.py`, bytes ingested per stage, compactions per 100 min, time to first productive action, warm `next` calls, Improve passes, first-pass refusals, turns per stage, head completeness and size. Paired prose (A/A and the power table of section 6): characters of targeted fields per frozen unit. Descriptive only: wall time and total tokens.

**8.3 Comparison matrix and expected effect by program type.**
| Layer | Programs | Metrics |
|---|---|---|
| Offline render (no model) | node-fix-bug, node-add-function, node-add-route, node-rename, inline and ask-agent; 24-stage outer mode; long-knowledge and small-home fixtures (small homes byte-identical); contract on and off; Improve handoff; run dirs of about 83 and 163 chars; the audit's five configurations x seven scenarios | bytes per stage, head versus cut, repeated share, typed-path census, ledger tokens |
| Writing-turn replay | frozen units from saved transcripts | paired prose characters, canaries |
| Slice (hours) | node-fix-bug, node-add-function; Grok, Claude, Codex | count metrics, canaries, refusals, redone work |
| Small full runs | hello, checkers, a second UI example; n=2 | planning window, Improve minutes, compactions, ShipLoop-owned reads, refusals |
| Platform case, last | Salesforce chess to the end of test-spec (about 85 min), a non-org app with computed values, an Apps Script case if available | all, plus escaped defects |

Expected by program type (projections until re-measured): small bug fix, whole packets about -3%, heads about +6% until 3.2/8.2 offsets, gains mostly Improve (stop rule, hook, route card); populated one-item run, dedupe and symbols -5 to -10%; long-knowledge home, -25% from the diff pointer, more with D-1; long Salesforce run, compaction and Improve levers dominate. Three labelled fixtures must move the same way: the audit dry run (33 packets, 375,278 chars), offline node-fix-bug (12 packets) and the live run (17 packets, 660 KB). Small-program bar: node-fix-bug offline total bytes and every head do not grow against the post-1.0 baseline.

**8.4 Domain-word lint** (10.1): `test/shiploop-domain-words.test.py` scans `skills/shiploop/` against `test/domain-words.json`; adding a word is one line.

**8.5 Decision rule.** (1) A material quality difference trumps; a failed canary, flipped SPEC clause, more refusals, more warm `next` calls, lower seeded-defect catch or blind rubric-eval preference for the control (Opus 5.5 medium, one judge per round) rejects or rescopes an arm. (2) Near-identical quality: fewer bytes ingested and output tokens (paired, interval from A/A-sized samples). (3) Then time. Thresholds are the control's own spread. `arms.py` applies the rule and prints the arm. Ship the structure package on this rule, the style line only if it passes, Improve text only if it beats B0+; if nothing beats control beyond the spread, ship structure only. The D-7 experiment compares `planning_review: stage` with W6 to W8 against `none`, counting escaped defects a blind downstream check by another model finds.

## 9. Rollout

- **One integration branch: the existing `feat/shiploop-eff-release-ca2c6e`** (320a526e). Do not create another off main. Work in child worktrees of it with a random suffix (`git -C /Users/dadleet/src/skill-craft worktree add .claude/worktrees/shiploop-eff-<step>-<hex6> -b feat/shiploop-eff-<step>-<hex6> feat/shiploop-eff-release-ca2c6e`, `<hex6>` from `openssl rand -hex 3`). Never `cd` into a repo and `git add -A`; stage `git -C <worktree> add -- <paths>`; confirm `git -C <path> rev-parse --show-toplevel`. Small committed steps, G-SUITES after each, land by merge or rebase, never squash. Remove a worktree and its branch in the turn it is merged.
- **Tranche-1 intake order** (merge commits, G-SUITES between): `-stop-` (green in the probe), `-packets-`, then `-loop-` (Step 1.0 reconciles the guard and the head); `-cred-` and `-hook-` are already merged. The packets pointer is retargeted in 3.3 before any release (unreleased, so no migration).
- **Notes and commits.** Every skill change adds `changes/<leaf>/<slug>.md` or a `No-Change-Note:` trailer; never edit `plugins/`, catalogs, `CHANGELOG.md`, `version:` fields or the README inventory; release only through `scripts/release.py` on your go (a shiploop release needs a `test/shiploop_e2e/LEARNINGS.md` entry since the last release or `No-E2E-Round:`); new test files go in `test/suite_catalog.py`. Prompt-change commits are verbose (key learning, numbers, evidence file, related commits) and end with the session's attribution line.
- **Journal.** `docs/shiploop-efficiency-journal.md` (status, snapshot, fixture, path length, unit, evidence path; superseded claims marked, not deleted), linking `docs/shiploop-eff-packets-pk-journal-2026-10-16.md`, `docs/shiploop-improve-stop-rule-journal-2026-10-16.md`, `docs/shiploop-skill-call-hook-journal-2026-10-16.md`, `docs/shiploop-until-loop-block-journal-2026-10-16.md`; evidence exported under `docs/experiments/`.
- **No push or release without your go;** one release for the script and text waves after one verification run, the vendored Until Loop change separately (D-16).
- **Live E2E runs unaffected.** Work only in worktrees; never write into a live run's folder, signal its processes, or touch `plugins/` or the installed plugin cache; never reword a loop contract of a run in flight; run verification as visible background tasks with `--resume-run` (they die near 30 min), skill sha pinned per arm; no Grok and Checkers concurrently, no mutation test of signalling code on real processes, no E2E until the live run ends, never `sf` or `sfdx`, never read `~/.sf` or `~/.sfdx`.

## 10. What NOT to do

- Do not rely on a pointer alone, a first-packet-only direction, a host prompt or `STAGE_RULES` for the recovery instruction or the style line; never put the style line in the request. Do not word a pointer to promise what the print does not do.
- Do not make `context-index.md` the first file a recovering model opens; do not point at an existing 20 to 55 KB reference as a destination for moved text; no first-read target over 4,600 chars.
- Do not put position in the card, add a state verb, or let a derived view become writable or go stale on a same-version install change.
- Do not add "unchanged since packet X" markers or guess warm versus cold from packet text; the verb (and a Claude hook event) is the only signal.
- Do not add an Improve cap, wall-clock limit, model-labelled "polish" exit or model-facing clock; do not skip a stage or an Improve on the model's word (`no_test_item`, `no_document_item` are script proofs).
- Do not name Improve in a producer packet or the card; do not give the Improve packet Goal, References, Rules, template, Checked-by, Done-when or guidance.
- Do not trim or digest the request unless you rule (D-2); do not replace living files with digests (an index of headings, sizes and ids is not one).
- Do not use shell variables, relative paths, a launcher, a symlink alias, a reader verb or an omitted `--run-dir` in printed commands; do not compose the Pause command from prose; do not symbolize the callback and its result path, Recovery, pause, halt, next, lint or improve commands, the Keepalive marker, "Full packet:", the Progress link, the literal receipt in `evidence_refs`, the loop Work/Contract/Receipt/Start lines or the `/improve` line.
- Do not tell a model to run `next` on "the newest run folder"; do not claim a saving for text that is still ingested whole.
- Do not lower `PRINT_LIMIT` or the hook window to 8,000; do not add to a head without a same-stage offset; do not merge a branch that turns a suite red without the reconciliation recorded.
- Do not remove Code craft from implement or the Improve handoff without a ruling; do not renumber duty items without moving `loops.WORK`; do not rewrite the roughly 230 text pins together with the text.
- Do not claim a cache or latency saving from moving text, sum unlike fixtures, or decide the style line on wall time or a three-run band; do not compress carriers; do not treat breaks inside one run as independent samples.
- Do not spend effort on discovery or verify wording (0 to 1% measured); do not copy live chess or Salesforce text into fixtures; do not regroup the 49 script files or merge the accepted-result map with the product-file READS map.
- No old-key alias (one documented exception: gate 2 keeps `required_trivial_reviews`, because the published until-loop plugin refuses unknown fields).

## 11. Open decisions for you

| # | Decision | Recommendation | Unblocks |
|---|---|---|---|
| D-1 | Amend D1 (whole-file quotation): whole at or under a per-file size, index above | Yes, behind the coverage gate, the seeded-omission test and the battery; small homes byte-identical; architecture.md whole at implement | 4.1 |
| D-2 | Request printing: verbatim in intake, spec, plan, product-acceptance; pointer plus `constraints` elsewhere | Ship request.md, S-ids and notice now (4.2a); keep full printing until the A/B and battery pass | 4.2b; ^ targets |
| D-3 | Until Loop block (your 2026-10-16 words asked for it; reverses the 2026-10-10 rule that loop mechanics live on the skill card) | Decided; keep a Claude E2E on the two-line argument | 3.6 |
| D-4 | May ShipLoop run the runtime's `done` itself? | No: two-step (`improve-pass` prints the `done` command) | 6.3 single verb |
| D-5 | Vendored until-loop changes: stop rule, lean print, `python3` argv, schema descriptions, `review_refs` | One upstream release, tag and re-vendor with the pending 0.8.0 pin | 6.4 release, 6.5 |
| D-6 | Dated S-10 carve-out for the stop rule (in the stop branch diff) | Yes, with the replay basis and the n=5 caveat | 6.4 |
| D-7 | Planning-review default | Keep `stage` as default; **this plan projects planning at about 35 to 41 min; `none` (about 20 min) is the only way to the 30-minute bar**; decide from the D-7 table before the verification run | the 30-minute claim |
| D-8 | SPEC S-16 (written output is dense) and exemptions | Land with the style decision, own commit | 8.3 |
| D-9 | Style line wording and site | B0+ at the Fill line, replacing the built `OWNER_RULE` text; screen both sites | 8.3 |
| D-10 | Credential-pattern refusal | Decided by your request and merged; the cost stands (no guard keeps a real secret out of a commit); confirm at release | none |
| D-11 | Shorter action ids and run-root name | Not now; revisit after gains are measured | optional |
| D-12 | Provenance in results, not spec.md; no NFR renumbering | Yes | 7.2 |
| D-13 | Keep generic runner examples (Jest, pytest) | Keep; denylist the analysts' list first | 10.1 |
| D-14 | `--delivery-contract` only when the request or host asks | Yes | 8.2 |
| D-15 | Split improve SKILL.md into router plus route card | Yes, with ledger rows and battery | 6.1 |
| D-16 | Release batching | One release for script and text after one verification run; vendored change separately | release |
| D-17 | Priority-ordered head builder | Yes | 1.2 |
| D-18 | Move the Backchain block to a reference | Yes, with a script-written start-contract file and battery | 8.2 part |
| D-19 | Lean print of the Until Loop return | Yes behind the main-tenet probe | 6.5 |
| D-20 | Batch-reads rule | Run the experiment; ship only if turns fall without more refusals | 9.3 |
| D-21 | Card as new `start-here.md` or the top of `reference.md` | New small file; `reference.md` long forms, `context-index.md` the record | 3.3 |
| D-22 | Split the 80 KB entry card (pilot) | Yes as a pilot; it is where the recovery-read credit lives; the top block ships regardless but earns no byte credit | 3.5 |
| D-23 | Integration branch | The existing `feat/shiploop-eff-release-ca2c6e`; merge packets, loop, stop per Step 1.0 | all |
| D-24 | The Skill-call hook gate is Claude-only | Accept; merged with the 5d028aee fix; confirm at release | 6.2 |
| D-25 | A platform-declared test adapter | A separate plan after this one | out of scope |
| D-26 | The owner rule and pointer on Improve packets (+245 to 344 B each) despite the 2026-10-11 minimal-Improve-packet rule | Keep the pointer (absolute path); drop the owner-rule line there if you prefer the minimal packet | 3.3 |
| D-27 | Step-plan printed head over the 20,000 host cut (merged: inline 21,944, ask-agent 23,626 at 163 chars) | Accept a cut tail that the file repeats (ordered so the loop Start and exits survive), with the 1.2 table; split the duties only if the battery shows harm | 1.0, 1.2, 8.5 |
| D-28 | A Claude SessionStart(compact) hook that prints the card after a compaction | Run arm A4 after the probe; ship Claude-only, like the Skill-call hook, if it wins | 3.7 |

Everything above is a plan. Facts are those read in code by symbol, rendered, measured in the red-team scratch probes, or taken from the cited study; the studies' numbers come from one Grok 4.7 medium run and stay projections until re-measured on the integration branch.
