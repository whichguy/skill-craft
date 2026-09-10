# Review Converge: ShipLoop 0.8.29 issue-this-prompt / bound When done

**Target paths:** `skills/shiploop/`, `agents/shiploop.md`, `test/shiploop.test.sh`, `test/shiploop-walk-journal.test.sh`, `plugins/shiploop/`
**Test command:** `bash test/shiploop.test.sh && bash scripts/sync-plugin-views.sh --check shiploop`
**Started:** 2026-09-10          **Status:** active
**Round counter:** 2
**Consecutive clean rounds:** 1
**Known test-artifact paths:**
**Plan contract:** `/Users/dadleet/.grok/sessions/%2FUsers%2Fdadleet%2Fsrc%2Ftic-tac-toe-oneshot/01a0887a-7a47-7193-9d4a-ef855b5b2559/plan.md`
**Plan hash:** `2e94f53775101706fcc6c070afd0ba910ce31eda2e2a8659af78f772137332e3`
**Base ref:** `22a4137740fd38a9e40e30f2840b8aecb85eabcd`

## Stop-condition tracking
- consecutive-no-progress: 0
- consecutive-same-error: 0 (signature: none)

## Log
### Round 1 — 2026-09-10
**Review:** 1 material, 3 minor
**Material findings:**
- SKILL.md Closer still offered **Success (default): flagless `/shiploop complete`** as a host choice, independent of the printed When done line. Residual dest done requires `--improve`; parallel running requires `--id`. A host following Closer instead of When done would pick the wrong argv. [`skills/shiploop/SKILL.md` Closer] — docs/logic-flow
**Deferred (minor/P2):**
- [ ] P2: README exhaustive workflow and mermaid still say “packet” / “turn packet.” Host-facing SKILL/commands/agents do not. Overview grain. — docs
- [ ] P2: `implement.md` still says “prints the next packet.” Not a slash card. — docs
- [ ] P2: HOST_CONTINUE line 1 repeats `Issue this prompt.` after NEXT_LEAD. Intentional emphasis; noisy. — docs
**Git-history check:** Prior live ledger was Status `complete` for 0.8.19 residual dest-reread. Archived to `REVIEW_CONVERGE.archived-shiploop-0.8.19-residual-20260910.md` (gitignored). Last 10 subjects: `af9cc5d` 0.8.29 issue this prompt (this campaign land); `22a4137` leftover A/B wording (Base ref); `bc1b903` flagless complete; `d17d5a9` HOST FLAG merge only on merge; `e34d4f1` 0.8.27 infer complete. Those teach: closer copies must be paste-legal; HOST FLAG is operational; a default flagless closer fights dest done `--improve`. Do not re-open the archived 0.8.19 ledger.
**Plan:**
- P1: SKILL.md Closer and `commands/shiploop-complete.md` exec only the printed When done command; no independent flagless default
**Plan review:** native — keep leftover-commit / merge Git ran / `--clear` / `--blocked` hatches; do not bump version
**Implementation:** SKILL.md Closer, commands/shiploop-complete.md, plugin twin via native
**Lint:** skipped (none configured)
**Test result:** PASS
**Outcome:** fixed
**Error signature:** none
**Learnings:** 0.8.29 bound When done in the printer, then the skill Closer taught a second happy path (flagless complete). Hosts that read the skill card after compaction skip stdout. The printed line has to be the only closer home, including residual `--improve` and parallel `--id`.
**Anchor evidence:**
- A1 → `rg packet SKILL.md commands/ agents/shiploop.md` empty
- A2 → one `## Host loop`; command cards one-line
- A3 → NEXT_LEAD `Issue this prompt.`; HOST_CONTINUE two lines; closer_inner_a shared
- A8 → no `If produces is not true yet` in scripts/shiploop
- A9 → no SKILL_ROOT in scripts/shiploop
- A10 → residual When done `--improve`; bare complete rc=2
- A11 → walk-journal P1 `--id S1`/`--id S2`
**Consecutive clean rounds after this entry:** 0
**Committed:** yes
**Notes:** Fresh ledger after archive of 0.8.19 complete campaign. Pathspec-only.

### Round 2 — 2026-09-10
**Review:** 0 material, 3 minor (carried)
**Material findings:** none
**Deferred (minor/P2):**
- [ ] P2: README exhaustive workflow and mermaid still say “packet” / “turn packet.” Host-facing SKILL/commands/agents do not. Overview grain. — docs
- [ ] P2: `implement.md` still says “prints the next packet.” Not a slash card. — docs
- [ ] P2: HOST_CONTINUE line 1 repeats `Issue this prompt.` after NEXT_LEAD. Intentional emphasis; noisy. — docs
**Git-history check:** Round 1 landed `e8b7b94` (Closer execs printed When done only). `af9cc5d` 0.8.29 land. Re-read SKILL Closer: no independent flagless default. complete.md: run printed command only. Diff vs Base `22a4137` is 0.8.29 + closer-home. No new closer menu.
**Plan:** n/a (clean)
**Plan review:** n/a
**Implementation:** n/a
**Lint:** n/a
**Test result:** N/A (clean round)
**Outcome:** clean
**Error signature:** none
**Learnings:** The Closer default was the remaining second home. After round 1, When done is the only closer instruction on the skill card. Remaining packet wording is README/implement.md overview, not slash-path. First of two consecutive cleans.
**Anchor evidence:**
- A1 → still no packet in SKILL.md / commands / agents
- A2 → Host loop remains the procedure; Closer points at printed When done
**Consecutive clean rounds after this entry:** 1
**Committed:** yes
**Notes:** First clean. Suite deferred to second clean.
