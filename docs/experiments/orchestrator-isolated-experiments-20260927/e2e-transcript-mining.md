# ShipLoop E2E Tier-2 Evidence Mining Report

Read-only analysis of 5 ShipLoop end-to-end run outputs. Host = Grok, model =
`grok-4.7`, effort = medium, for all 5 runs. Versions and outcome:

| Run | Case | skill-craft / shiploop version | pass | elapsed | sessions/resumes | compactions |
|---|---|---|---|---|---|---|
| e2e-run6 | battleship (fresh build) | 1.4.0 / 0.37.0 | True | 1387s | 6 / 5 | 2 |
| e2e-run6b | battleship-scoring (follow-on to run6) | 1.4.0 / 0.37.0 | True | 1132s | 8 / 7 | 1 |
| e2e-run7 | battleship (fresh build) | 1.5.0 / 0.38.0 | True | 838s | 4 / 3 | 1 |
| e2e-run7b | battleship-scoring (follow-on to run7) | 1.5.0 / 0.38.0 | **False** | 1080s | 8 / 7 | 1 |
| e2e-run8b | add-scoring (follow-on to run7) | 1.6.0 / 0.39.0 | True | 19833s (~5.5h, mostly idle/queued) | 5 / 4 | 1 |

All 5 sibling `e2e-run*` directories were checked; only run1–run5 lack
`metrics.json`/`timeline.jsonl` (older format, pre-dates the packet-file
mechanism under test) and were excluded, matching the run list given.

## Summary table (all 5 runs combined unless noted)

| Question | Headline finding |
|---|---|
| Q1 head-only acting | 179 completed actions had a packet exposure; packet read before `complete` in 121 (68%), not read in 58 (32%). Of 121 reads, 100 were a targeted `grep` on the packet path, 9 were a full `read_file`, 12 were a `read_file` with a `limit=` (partial). **Zero** reads used a shell `cat`/`sed`/`head` on the packet — the "don't print it to the shell" rule was never violated. 4 stages (`select-work`, `baseline`, `test-author`, `test-red`) were **never** read before completion, in all 5/5 runs. `implement` steps: 9/14 read. |
| Q2 per-step implement cost | 14 implement actions total across 5 runs (2, 4, 2, 2, 4 per run — one per step of the single work item W1 in each run). Mean tool-output per implement action = 29,981 bytes; mean packet bytes = 9,459; mean reference/SKILL bytes = 8,968 (non-zero only in the 2 steps that happened to contain a mid-step auto-compaction). Range 215–167,178 bytes. |
| Q3 compaction recovery | 6 auto-compactions total. In 5/6, the first action after compaction was a fresh `shiploop next`/`status` call (all exit 0) followed immediately by a full re-read of `SKILL.md` (and 1–4 reference files, 48–91 KB). In 1/6 (run6, compaction #1) the model skipped the CLI call and went straight to re-reading the already-open packet file. No post-compaction command was refused. Session **resumes** (13 of 20 total end-of-session boundaries excluding the final one) almost always issued a `shiploop` command as the very first action of the new session, and it succeeded every time bar one that was itself cut off by another cancellation. |
| Q4 refusals & keepalive | 11 genuine ShipLoop-script refusals (exit≠0, ShipLoop-authored error text) across 5 runs: run6=4, run6b=4, run7=0, run7b=3, run8b=0. Longest consecutive same-action refusal streak = **1** everywhere (no action was ever refused twice in a row). Literal `"ShipLoop keepalive:"` text was **not found** anywhere in any transcript.md or events.jsonl (0/5 runs) — the only "keepalive" artifacts are the `Keepalive marker: SHIPLOOP-RUN run=... rev=...` line baked into every packet head, and the host-level hook-decision counts in `result.json.keepalive.decisions` (`allow` 5–9 times per run, plus one `continue` in run6). |
| Q5 truncation | 3 host-truncated tool outputs total (run6 ×2, run8b ×1; run6b/run7/run7b had none). None were a ShipLoop packet head or a packet-file read: they were a `node --test` run (20.5KB), a `pgrep "Google Chrome"` process listing (157.5KB), and a headless-Chrome launch command (28KB). |

---

## Method

`events.jsonl` is a flat stream of `tool_call` (request) and `tool_call_update`
(streamed/`completed` result) events, keyed by `toolCallId`, in chronological
order, plus `thought`/`text` (model reasoning/prose), `usage`, `end` (session
boundary, `stopReason` cancelled/end_turn), and `auto_compact_started`/
`auto_compact_completed`. I paired each `tool_call` with the text of its last
`completed` `tool_call_update` to build one ordered list of "calls" per run
(see Appendix for the exact script). ShipLoop packet **heads** were located by
matching `^ShipLoop navigator \| <stage> \| revision N` at the start of a
`run_terminal_command` output, together with the `Full packet: <path>` line
and the `--action=<id>` on the `Callback for this stage` / `Next command`
line. A confirmed, real finding from the traces: **the model never sees
step-specific content (e.g. "Step S2 (2 of 2)") in the printed head — that
text exists only inside the packet file itself**, confirmed by direct
comparison of a head (`events.jsonl` around run6 idx 632) against a full
packet read (idx 6411/6418).

I also confirmed that a `shiploop complete` call's own output doubles as the
**head-exposure for the next action** (auto-chaining) — e.g. run6 idx 919's
`complete --action=nav-45f1...` output begins a fresh
`ShipLoop navigator | discovery | revision 1` head. My "exposure" detector
therefore fires on both `next` and `complete` invocations, and windows are
`(first exposure of action X, first exit-0 `complete --action=X`)`.

---

## Q1 — Head-only acting

**Per-run tallies** (actions with a matched packet-exposure→completion window):

| Run | total actions | read before complete | not read | implement: total/read |
|---|---|---|---|---|
| e2e-run6 | 35 | 29 | 6 | 2/2 |
| e2e-run6b | 37 | 21 | 16 | 4/3 |
| e2e-run7 | 35 | 23 | 12 | 2/1 |
| e2e-run7b | 35 | 27 | 8 | 2/2 |
| e2e-run8b | 37 | 21 | 16 | 4/1 |
| **Total** | **179** | **121 (68%)** | **58 (32%)** | **14/9 (64%)** |

**Read-kind breakdown** (121 reads): `grep` on the packet path = 100, full
`read_file` (no `limit`) = 9, partial `read_file` with a `limit=` = 12
(limits seen: 200, 180, 120, 40, 30×2, 25, 12). **No** case used a shell
`cat`/`sed`/`head`/`tail` on a packet path in any of the 5 runs — the head's
instruction "Read it with a file-reading tool, not by printing it to the
shell" was followed 100% of the time it was followed at all. Note `grep` is
inherently a *partial* read (it returns only matching lines), so even the 121
"read" cases are mostly selective, not full-packet reads.

**Stages never read before completion, in all 5/5 runs (0/5 reads each):**
`select-work`, `baseline`, `test-author`, `test-red`.

Concrete example — `baseline` stage, run6, action `nav-d3bdfedf...`
(`events.jsonl` idx 207 exposure → idx 211 complete): the window between them
contains only an `improve-complete` call, a `node --test`/dependency-check
Bash block, and two `write` calls (a baseline note, then the result file) —
no `read_file`/`grep` targets the packet at
`.../packets/nav-d3bdfedf176946588c92f7f2f5666e9c.md` anywhere in the window.

Concrete example — `select-work` stage, run6, action `nav-8002b4ff...` (idx
176→178, only 1 intervening call): the model wrote
`"W1 is the only queued item and the plan still requires it... Nothing else
has to finish before W1."` directly, reasoning from already-known state
rather than reading the packet (there is only one work item, so the decision
is inferable without it).

Concrete example — `implement` steps 2–4 of 4 in run8b (`add-scoring`,
actions `nav-2c4e75ad...`, `nav-0548ba44...`, `nav-97dc88e4...`): only step 1
(`nav-07f34a8b...`) was read (via `grep` for `'Step S|S1|S2|this step'` on
its packet, idx 263). Steps 2, 3 and 4 each went straight from head-exposure
to `search_replace` edits and a Bash check to `complete`, with **no**
`read_file`/`grep` on their own packet file. Since each packet is
single-step content only (confirmed via run6 idx 6418: "Step S2 (2 of 2), the
only work for this packet"), this means the model implemented 3 later steps
of one item without ever seeing that step's own packet text — presumably
relying on the step-plan read earlier in the item's lifecycle.

---

## Q2 — Per-step implement cost

| Run | # implement actions (= steps, all in item W1) | total_bytes | packet_bytes | ref/SKILL bytes |
|---|---|---|---|---|
| e2e-run6 | 2 | 6,132 / 81,427 | 0 / 43,375 | 0 / 0 |
| e2e-run6b | 4 | 7,480 / 1,765 / 167,178 / 9,685 | 0 / 0 / 43,784 / 2,796 | 0 / 0 / 62,583 / 0 |
| e2e-run7 | 2 | 5,526 / 7,355 | 0 / 0 | 0 / 0 |
| e2e-run7b | 2 | 5,610 / 123,029 | 0 / 42,471 | 0 / 62,976 |
| e2e-run8b | 4 | 739 / 1,080 / 2,519 / 215 | 0×4 | 0×4 |

Aggregate over all 14 implement actions: **mean total tool-output bytes =
29,981** (min 215, max 167,178), **mean packet bytes = 9,459**, **mean
ref/SKILL bytes = 8,968**. Work items: every run in this fixture set has
exactly **one** work item (`W1`), so "steps per item" = the run's implement
count above (2–4); there is no multi-item run in this sample to compare
cross-item reuse.

Reference/SKILL-file re-reads are non-zero **only** in the two implement
windows that happened to contain a mid-step auto-compaction (run6b step 3,
run7b step 2) — the compaction forced a fresh `read_file` of the whole
`SKILL.md` (43–63KB) mid-step, which is counted here because the compaction
fell inside that step's expose→complete window. In run6, the equivalent
post-compaction recovery used a targeted `grep -A/-B` on `SKILL.md` (80 lines)
rather than a full `read_file`, so it shows 0 ref_bytes by this file-type
methodology even though the model *did* re-consult the skill card — see Q3.
Outside of compaction, **no implement step re-read a reference file or
SKILL.md** in this sample, so there is no evidence of same-item reference
re-reads across consecutive normal (non-compaction) steps — each step that
touched a reference did so once, coincident with a compaction, not
repeatedly.

---

## Q3 — Compaction recovery

6 `auto_compact_started`/`auto_compact_completed` pairs total (all at
`percentage: 80`): run6 ×2, run6b ×1, run7 ×1, run7b ×1, run8b ×1.

| Run | compaction # | first action after | SKILL/ref bytes re-read (first ~15 calls) | refused? |
|---|---|---|---|---|
| run6 | 1 (idx 6329/6330) | `read_file` on the packet **already open** before compaction (no fresh `shiploop` CLI call); model said *"I'll read the current packet and the HTTP tests, then implement only that step"* | 0 via `read_file` (but a `grep -A/-B 80` on `SKILL.md` followed) | no |
| run6 | 2 (idx 17290/17291) | `shiploop next --run-dir ...` | 48,394 (1 file: `testing-and-documentation.md` reference) | no, exit 0 |
| run6b | 1 (idx 7250/7251) | `shiploop ... --run-dir ...` | 62,583 (`SKILL.md`) | no, exit 0 |
| run7 | 1 (idx 7320/7321) | `shiploop ... --run-dir ...` | 91,017 (3 files: `SKILL.md`, `long-running-background-tasks/SKILL.md`, `workspace-lifecycle.md`) | no, exit 0 |
| run7b | 1 (idx 8727/8728) | `shiploop ... --run-dir ...` | 62,976 (`SKILL.md`, `testing-and-documentation.md`) | no, exit 0 |
| run8b | 1 (idx 10864/10865) | `shiploop ... --run-dir ...` | 73,922 (`SKILL.md`, `environment-lifecycle.md`, `improve/SKILL.md`, +) | no, exit 0 |

So in 5/6 cases the model re-issued a `shiploop` CLI command as the very
first action after compaction and it succeeded, immediately followed by a
full re-read of `SKILL.md` plus 0–2 reference cards (48–91KB). In the
remaining case (run6's first compaction, which landed mid-`implement`
between the packet's head-exposure and its completion) the model skipped the
CLI call entirely and re-read the packet it already had open, matching the
recovery guidance in the packet head ("Recovery ... reprints this head").

**Session resumes** (harness-restarted sessions, distinct from in-session
auto-compaction): of 20 session boundaries total across the 5 runs (13
excluding the final terminal one per run), the very first tool call of the
new session was a `shiploop <verb> --run-dir=...` invocation in the large
majority of cases, and it exited 0 in every case but one (run6b resume #6,
where the command itself was cut off by a later cancellation — `exit: None`,
not a refusal). In run6, the first two resumes issued exploratory `git`
checks before the first `shiploop` call, because those resumes occurred
during the run's early git-bootstrap trouble (before any ShipLoop run had
even started — see Q4/refusal at idx 585).

---

## Q4 — Refusals and keepalive

**Non-zero-exit ShipLoop-authored refusals** (exit≠0 *and* the command
invoked the `shiploop` script or its output is ShipLoop-authored error text —
this excludes incidental non-zero exits from unrelated shell commands that
merely contained the substring "shiploop" in a path):

| Run | i (events.jsonl idx) | verb | action | stage | exit | first line (≤20 words) |
|---|---|---|---|---|---|---|
| run6 | 585 | workspace | – | – | 2 | "ShipLoop workspace blocked: workspace root parent does not exist" |
| run6 | 11405 | (improve-carry) | – | – | 2 | "Do not repeat work or infer a terminal outcome. This rejected input..." |
| run6 | 14523 | (improve-sys-done) | – | – | 2 | "Do not repeat work or invoke a callback from this error packet." |
| run6 | 18439 | complete | nav-4ed2606c... | release-plan | 2 | "ShipLoop keeps this run's planning knowledge in the repository..." |
| run6b | 208 | workspace | – | – | 2 | "ShipLoop workspace blocked: workspace root parent does not exist" |
| run6b | 9038 | complete | nav-dc45f454... | implement | 2 | "ShipLoop navigator: result requires outcome and summary" |
| run6b | 15602 | complete | nav-00b1e628... | release-plan | 2 | "ShipLoop keeps this run's planning knowledge..." |
| run6b | 17246 | complete | nav-a787aac2... | handoff | 2 | "ShipLoop blocked: handoff requires a current workspace return..." |
| run7 | – | – | – | – | – | none |
| run7b | 4800 | complete | nav-8bab9a6f... | plan | 2 | "assumption A1 (probed) needs exactly check, evidence..." |
| run7b | 12296 | improve-start | nav-13abd0a6... | carry-forward | 1 | "Traceback (most recent call last):" (JSONDecodeError, matches metrics.json) |
| run7b | 15296 | complete | nav-7782d783... | release-plan | 2 | "ShipLoop keeps this run's planning knowledge..." |
| run8b | – | – | – | – | – | none |

Total = 11 (run6=4, run6b=4, run7=0, run7b=3, run8b=0). **Longest
consecutive run of refused callbacks for the same action = 1** in every run —
no action was ever refused twice in a row; each refusal was followed by a
corrected callback that succeeded. Note: `result.json`/`metrics.json`'s own
`shiploop_failures` list undercounts this (it records only run6=1, run6b=4,
run7=0, run7b=3, run8b=0 — it appears to key on a narrower text signature,
e.g. only the one run6 hit whose body contains the phrase "did not advance
the graph", missing the `workspace blocked` and `improve-*` JSON-error
refusals at idx 585/11405/14523). The events-based count above is the more
complete, directly-observed figure.

**Keepalive**: searching both `transcript.md` and `events.jsonl` for the
literal string `ShipLoop keepalive:` returns **zero matches in all 5 runs** —
this exact phrase is not present anywhere in the captured data, so Q4's
keepalive-quote request cannot be answered as literally posed. What *is*
present: (a) every packet head carries a line
`Keepalive marker: SHIPLOOP-RUN run=<id> rev=<n> dir=<path>` (121 occurrences
in run6 alone, one per head print — this is a stable machine marker, not a
prose notice), and (b) `result.json.keepalive.decisions` records the host
keepalive hook firing and allowing continuation 5–9 times per run (plus one
`continue` in run6), confirming the mechanism engaged but leaving no
transcript-visible text under that exact phrase.

---

## Q5 — Truncation

`result.json.cli.truncated_outputs` (cross-checked against
`metrics.json.truncated_outputs` counts, which agree: run6=2, run6b=0,
run7=0, run7b=0, run8b=1):

| Run | total_bytes | shown_chars | command (tail) | packet-related? |
|---|---|---|---|---|
| run6 | 20,492 | 17,978 | `... && node --test; echo EXIT:$?` | No |
| run6 | 157,509 | 20,472 | `pgrep -lf "Google Chrome" ...` | No |
| run8b | 28,067 | 16,736 | headless Chrome launch (`--remote-debugging-port=9223 about:blank`) | No |

None of the 3 truncated outputs across any run reference a `packets/` path or
contain `Full packet:` text — none were a ShipLoop packet head or a
packet-file read.

---

## Appendix: extraction script (Python, run per-run over `events.jsonl`)

```python
#!/usr/bin/env python3
"""Read-only evidence mining over ShipLoop E2E run outputs."""
import json, re, sys, os

BASE = ".../scratchpad"   # run6/6b/7/7b/8b live here
OUTDIR = ".../scratchpad/exp"

HEAD_RE = re.compile(r'^ShipLoop navigator \| ([a-zA-Z0-9_-]+) \| revision (\d+)', re.M)
FULLPKT_RE = re.compile(r'Full packet:\s*(\S+)')
CALLBACK_ACTION_RE = re.compile(r'Callback for this stage.*?--action=(\S+?)(?:\s|$)')
NEXTCMD_ACTION_RE = re.compile(r'Next command.*?--action=(\S+?)(?:\s|$)')
STATUS_ITEM_RE = re.compile(r'Where:\s+(.*)')

def load_events(run):
    path = os.path.join(BASE, run, "events.jsonl")
    events = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try: events.append(json.loads(line))
            except Exception: events.append({"type": "PARSE_ERROR"})
    return events

def final_text_for(events, i, tcid):
    """Last 'completed' update for this toolCallId, scanning forward."""
    text, raw = None, None
    for j in range(i + 1, min(i + 40, len(events))):
        e2 = events[j]
        if e2.get("toolCallId") == tcid and e2.get("type") == "tool_call_update":
            if e2.get("status") == "completed":
                try: text = e2["content"][0]["content"]["text"]
                except Exception: pass
                raw = e2.get("rawOutput")
                return text, raw, j
    return text, raw, None

def build_calls(events):
    """One entry per tool_call event, in original order, with resolved output."""
    calls = []
    for i, e in enumerate(events):
        if e.get("type") == "tool_call":
            tcid = e.get("toolCallId")
            text, raw, j = final_text_for(events, i, tcid)
            calls.append({"i": i, "j": j, "toolCallId": tcid,
                           "toolName": e.get("toolName"),
                           "rawInput": e.get("rawInput", {}),
                           "text": text or "", "raw": raw})
    return calls

# --- exposures: Bash calls whose output starts "ShipLoop navigator | <stage> | revision N"
#     and carries a "Full packet: <path>" line and "--action=<id>".
# --- completions: Bash calls invoking "shiploop ... complete ... --action=<id>" with exit 0.
# --- for each action, window = calls between its FIRST exposure and its completion;
#     Q1 read-hit = a read_file on packet_path (full, or partial via `limit=`),
#     or a grep/shell cat|sed|head|tail|less|more targeting packet_path within the window.
# --- Q2 sums bytes_of(call["text"]) for the window, and itemizes read_file calls whose
#     target_file is under /references/ or is SKILL.md.
# --- Q3 pairs auto_compact_started -> auto_compact_completed events, then scans forward
#     from the completion index for the first tool_call and for SKILL.md/reference reads
#     in the next ~80 tool_call events.
# --- Q4 flags Bash calls with exit not in (0, None) where the command contains
#     "/scripts/shiploop" (or a "$CLI" verb invocation) OR whose OUTPUT TEXT starts with
#     "ShipLoop" / contains a `"status":"error"` JSON blob / "did not advance the graph"
#     (this text-based check is what catches genuine ShipLoop-authored refusals and avoids
#     false positives from unrelated commands that merely have "shiploop" in a path).
# --- Q5 cross-references result.json's cli.truncated_outputs against "packets/" / "Full packet".
#
# Full runnable version (with the Q1-Q5 aggregation loops) is at:
#   /private/tmp/claude-501/-Users-dadleet-src-skill-craft/63442b14-c6e6-4557-9f89-335697027fa2/scratchpad/exp/analyze.py
```

## Caveats / inferred vs. observed

- All figures above are directly computed from `events.jsonl` (ground truth
  for what the host actually sent/received), not inferred from
  `transcript.md` (a truncated, human-readable projection of the same
  stream) or from `metrics.json` (shown to undercount `shiploop_failures`,
  see Q4).
- "Read before complete" via `grep` counts as a "read" per the task's own
  definition ("any tool call: file read tool, cat/sed/head/grep... on that
  path"), but a `grep` only returns matching lines, so most of the 121
  "reads" in Q1 are partial by construction, not full-packet reads — this is
  noted, not hidden, in the Q1 breakdown.
- Q2's "reference file" reuse check only found byte-level evidence tied to
  mid-step compactions; I cannot rule out reference re-reads that happened
  via `grep` (Q1 shows `grep` is the dominant read mechanism) rather than
  `read_file`, since my ref-byte itemization only counts `read_file` calls
  under `/references/` or named `SKILL.md`. This is flagged as a
  methodology gap rather than asserted as "zero reuse."
- Q3's "session resume" analysis is coarser than the compaction analysis: it
  reports whether the first call after a session boundary was a `shiploop`
  invocation and whether it exited 0, but does not itemize reference-file
  bytes read per resume (unlike compactions) — that would need the same
  window logic re-run per resume, which time did not permit at the same
  depth as the compaction analysis.
- run8b's `elapsed_seconds` of 19,833 (~5.5h) is far larger than its turn
  count would suggest (363 turns, similar to the other runs); this is very
  likely wall-clock time including harness queueing/idle gaps between
  sessions, not active model time — inferred, not directly evidenced in the
  data reviewed.
