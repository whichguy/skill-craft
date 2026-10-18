"""Assemble SP/insights2/packets-audit.json from the measurements and the authored review (analysis tool).

    python3 -I assemble.py <insights2_dir>
"""
import glob
import json
import re
import sys
from pathlib import Path

I = Path(sys.argv[1])
D = I / "packets-data"
SP = I.parent
R = "/Users/dadleet/src/skill-craft/.claude/worktrees/shiploop-eff-int-c5f79b"
RUN = "/Users/dadleet/e2e-runs/20261017/bs-sf-int-b7c77f/.shiploop-runs/work-20261018-040601-5105d5/run"

measure = json.loads((D / "bs-measure.json").read_text())
printed = json.loads((D / "printed-measure.json").read_text())
rewrites = json.loads((D / "rewrites.json").read_text())
duty_items = json.loads((D / "duty-items.json").read_text())
render = {t: json.loads((D / f"{t}.render-report.json").read_text()) for t in ("step-plan", "implement")}
validate = {f"{v}/{t}": json.loads((D / f"validate-{v}-{t}.json").read_text())
            for v in ("templates", "tight") for t in ("step-plan", "implement")}

# printed heads: one row per (revision, stage), with the host's truncation record
heads = []
seen = set()
for f in sorted(glob.glob(str(D / "printed" / "r0*.txt"))):
    name = Path(f).name
    rev, stage = name[1:4], name.split("-", 1)[1].rsplit("-", 1)[0]
    if (rev, stage) in seen or stage in ("improve", "done"):
        continue
    seen.add((rev, stage))
    t = Path(f).read_text()
    m = re.search(r"showing first/last ([\d.]+) KB of ([\d.]+) KB", t)
    heads.append({"revision": int(rev), "stage": stage, "printed_chars": len(t),
                  "host_cut": bool(m), "total_kb": float(m.group(2)) if m else None,
                  "carries": {"duties": "Current stage guidance" in t, "result_template": "Result template" in t,
                              "references_symbols": "References (symbols" in t,
                              "knowledge_toc": "Knowledge files this stage reads" in t,
                              "handoffs_by_value": "Handed off by earlier" in t, "loop_argument": "BEGIN until-loop" in t}})

per_packet = [{"packet": r["packet"], "file_chars": r["chars"], "groups": r["groups"],
               "chars_identical_in_all_33": r["chars_in_all_packets"],
               "chars_in_half_or_more": r["chars_in_half_or_more_packets"]} for r in measure["rows"]]
top_lines = [{"packets": c, "line_chars": n, "total_chars": c * n, "starts": s[:110]}
             for c, n, s in measure["top_repeated_lines"][:24]]


def pct(part, whole):
    return round(100 * part / whole, 1)


ft, fg = measure["total_chars"], measure["groups_total"]
pt, pg = printed["total"], printed["agg"]

audit = {
    "schema": "shiploop-packets-audit/v1",
    "date": "2026-10-18",
    "consumer": ("The owner, deciding plan revision 2 of docs/shiploop-run-insights-plan-2026-10-18.md (packet concision, "
                 "duty rewrites, template design); then the session that builds the units. Read with packets-audit.json's "
                 "templates/ files beside it."),
    "method": {
        "read_only": "Nothing under R or the run was edited; no ShipLoop command, test or sf command ran. Measurements are "
                     "scripts under SP/insights2/packets-tools/ reading the run's files and git history.",
        "sources": {
            "packets": "SP/report-bs/in/<NN>-<stage>.packet.md (byte-identical to RUN/packets/<action>.md; checked with cmp "
                       "for 11-step-plan)",
            "printed": "the shiploop CLI's printed output for each action, taken from the run's events.jsonl "
                       "(tool_call_update.rawOutput: output_for_prompt, total_bytes, truncated); only ShipLoop's own output "
                       "was read, no model reasoning",
            "code": "R/skills/shiploop/scripts (integration branch) and R/test; the fix plan "
                    "/Users/dadleet/src/skill-craft/docs/shiploop-implement-step-fix-plan-2026-10-17.md (commit 649b8d60, "
                    "branch shiploop/implement-prompt-2d6ecc, not on the integration branch)",
            "run_records": RUN + " (results, notes, loops) and git -C <worktree> show 2449835 / fcd65c9 for HOME as "
                           "step-plan and implement S1 saw it",
        },
        "tools": {
            "segment.py": "labels every packet line with the navigator block it came from (by line prefix; blocks of "
                          "shiploop_navigator._producer_blocks) and its tier (P0, P1, lookup, chrome, quoted, file)",
            "measure.py": "per-packet section sizes, cross-packet line repetition (action IDs normalised)",
            "tmpl.py": "prototype loader, validator and renderer for the strict template format proposed below",
            "prep_values.py": "slot values for the two filled examples, from the run's records",
            "rewrites.py": "the ten duty rewrites with exact printed 'before' text and sizes",
        },
        "units": "characters unless a field says bytes; the host cut is Grok's ~20,000 characters "
                 "(test/shiploop_head_budget.py HOST_CUT)",
    },

    "headline_findings": [
        "The printed text is mostly frame: in the 33 printed producer heads (563,438 characters) the instruction frame "
        f"(callback, recovery, goal and Checked by, Until Loop block, status, rules, chrome) is {pct(pg['frame'], pt)}%, the "
        f"stage method {pct(pg['method'], pt)}%, step and stage input {pct(pg['step+input'], pt)}%, quoted state only "
        f"{pct(pg['quoted'], pt)}%.",
        "By-value state is what the head drops first: 23 of 28 packets with quoted hand-offs printed none of them, 15 of 33 "
        "printed no References block (so RUN/HOME/GUIDES were undefined in the printed text), and every inner head cut "
        "W1's 3,308-character work item context to a 400-character excerpt.",
        "10 of 33 prints passed Grok's 20,000-character cut and lost their middle (7 of 8 implement prints, the revisit "
        "step-plan, verify, carry-forward): implement lost parts of duty items 5-7 and Code craft rules 1-2, the revisit "
        "step-plan lost the middle of duty 4's `check` rule. The head table's fixture (node-fix-bug) predicts implement at "
        "16,104; real step data put it at 19.5-24.8 KB.",
        "Consequence in the run: step-plan read spec.md, architecture.md and environment.md whole (48.7 KB) and ShipLoop's "
        "own scripts 29 times, and reached the plan and prepare results through RUN/inbox copies while the list naming them "
        "was not printed; implement S1 read architecture.md whole "
        "although its packet file quoted every AD-<n> by value.",
        "5,790 characters of every packet file are lines identical in all 33 packets (paths included); absolute paths alone "
        "are 9.3% of printed text. Each rule about check-only, recovery, pause and 'untrusted' input is stated 2-5 times per "
        "packet; step-plan states each structural rule three times (duty, exit condition, Checked by).",
        "25% of the planning duty text (12,340 of 48,737 characters across intake..test-spec) did not apply to the Battleship "
        "run (empty checkout, single-user stateless app): service, MCP, connected-knowledge, current-system, bootstrap, "
        "module-format and optional Backchain-child items.",
        "Ten duty items rewritten: 12,849 -> 6,874 characters (-46%) while adding the accepted plan units B1, B2, C1, A1, A4, "
        "G4, G6, H4.",
        "Strict templates (owner direction) are feasible and testable: the prototype renders step-plan and implement for "
        "Battleship S1 at 19,643 and 18,794 printed characters with the work item context, concern rows, ## Commands, the "
        "step's R-<n> and AD-<n> by value, where today's heads carried none of them.",
        "The template validator turns the 20,000-character budget into a build-time check: with today's producer data it "
        "refuses both templates (worst cases 21,204 and 20,660); with producer-side bounds (context 2,500, step task 700, "
        "Proof 600, criteria 1,200) implement passes at 18,760 and step-plan misses by 84.",
        "Recommendation: yes, migrate to one template per stage plus shared partials, with bounds enforced at the producing "
        "stage's gate, elastic input pools, gate IDs, and a byte-identical pilot of step-plan and implement first.",
    ],

    "measure": {
        "scope": "33 producer packets of the Battleship run (bs-sf-int-b7c77f, current integration build); the 18 Improve "
                 "parent packets (1,569-2,686 characters each) are excluded",
        "file_composition": {
            "total_chars": ft,
            "groups": {k: {"chars": v, "pct": pct(v, ft)} for k, v in fg.items()},
            "group_members": {
                "instruction_frame": "top (header, recovery, full-packet pointer, callback, owner rule), goal and Checked by, "
                                     "Until Loop block, status and narrative, RULES, progress view and pause, pass log and halt, "
                                     "delegation line",
                "stage_method": "Current stage guidance (DUTIES), Backchain line or stub, Code craft",
                "step_and_stage_input": "implement Step block, work item and its context excerpt, revisit, test rules, "
                                        "workspace return, lint command, Improve lessons",
                "result_contract": "Result template, allowed outcomes, fill rules",
                "locators": "References (symbols, cited guides), builds-on list, run context (state, CLI, request, test "
                            "strategy source)",
                "quoted_state": "knowledge file contents lists, hand-offs by value, last accepted transition, deltas and "
                                "HOME commit lines",
            },
            "per_packet": per_packet,
        },
        "printed_composition": {
            "prints": len(heads), "total_chars": pt,
            "groups": {k: {"chars": v, "pct": pct(v, pt)} for k, v in pg.items()},
            "frame_examples": {
                "02-discovery": "top 1,743 + goal 959 + status 1,001 + rules 539 + chrome 614 = 4,856 of 13,690",
                "11-step-plan": "top 1,744 + goal/Checked by 1,535 + loop 3,656 + status 949 + rules 539 = 8,423 of 19,726",
                "16-implement": "top 1,744 + goal 1,268 + loop 3,847 + status 415 + rules 539 = 7,813 of 19,530 (rev 16)",
                "24-test": "top 1,739 + goal 1,342 + loop 8,145 (the four recorded commands, the check row joining all four "
                           "step Proofs: about 3,300) + status 417 + rules 539 = 12,182 of 19,704",
            },
            "heads": heads,
        },
        "host_cut": {
            "rule": "Grok shows the first and last ~10 KB of a tool output above ~20 KB and elides the middle "
                    "(test/shiploop_head_budget.py; measured 2026-10-17). packet_head's required blocks are never dropped, "
                    "so a long required text is cut by the host instead.",
            "cut_prints": [{"revision": h["revision"], "stage": h["stage"], "total_kb": h["total_kb"]} for h in heads
                           if h["host_cut"]],
            "elided_kb_total": round(sum(h["total_kb"] - 19.6 for h in heads if h["host_cut"]), 1),
            "what_was_lost": {
                "implement rev 14 (S1)": "from duty item 5 ('completion uses it') to Code craft rule 2 ('...n reachable from "
                                         "outside its module'): the rest of item 5, items 6 (unachievable-as-planned "
                                         "triggers) and 7, the Code craft heading and rule 1",
                "implement rev 27 (S1 revisit, 24.2 KB)": "about 4.6 KB of duties and Code craft",
                "step-plan rev 23 (revisit)": "the middle of duty 4: from 'Tests are not a step' to 'skipping a missing file' "
                                              "(the `deps`/`check` rules the revise was about)",
                "verify rev 37, carry-forward rev 38": "the middle of their duties",
            },
            "fixture_gap": "test/shiploop_e2e/head_table.json (node-fix-bug fixture, reference install) records implement "
                           "head 16,104 and step-plan 19,961; with real step data the same heads printed 19,530-24,763 bytes",
        },
        "dropped_from_printed_head": {
            "handoffs_by_value": "23 of 28 files that hold them (plan, step-plan, test-spec, all 8 implement, test, document, "
                                 "verify, carry-forward, system-test, product-acceptance, release-plan, release-verify, handoff)",
            "references_block_with_symbol_definitions": "15 of 33",
            "knowledge_file_contents_list": "20 of 27",
            "results_this_stage_builds_on": "15 of 32",
            "work_item_context": "every inner head prints HEAD_CONTEXT_EXCERPT = 400 characters (file: 1,200) of W1's 3,308; "
                                 "the excerpt ends mid-word ('Scope: sfdx-proje') and drops scope, authority and the AD-5 "
                                 "correction",
            "mechanism": "shiploop_navigator._select_head keeps P0/P1 and then lookup, chrome and quoted blocks in print order "
                         "until HEAD_LIMIT; the first that does not fit ends the head, so quoted state (last in order) goes "
                         "first",
        },
        "reads_this_caused": {
            "11-step-plan": "read_file of HOME/spec.md, architecture.md, environment.md (48.7 KB as of 2449835) and the plan's "
                            "final result; 29 calls on ShipLoop's scripts, 12 of them read_file (11-step-plan.actions.md; "
                            "docs/experiments/run-analysis-2026-10-18/bs/analysis-bs-build-1.json); it reached the plan and prepare "
                            "results through RUN/inbox copies, not the RUN/results paths the unprinted builds-on list names",
            "16-implement": "read architecture.md whole (17,690) although the packet file quoted AD-1..AD-7 by value; "
                            "0 reads of the packet file although its head was cut mid-duties",
            "02-discovery": "7 whole guides, 154,386 bytes, on an empty checkout",
            "06-test-strategy": "6 whole guides, 165,381 bytes",
            "08-plan": "9 knowledge/run-note reads (125 KB as files now) and 10 ShipLoop script reads",
        },
        "cross_packet_repetition": {
            "identical_lines_per_packet": "5,790 characters of every packet file are lines present in all 33 packets "
                                          "(action IDs and revision normalised); 6,343-11,599 are in half or more",
            "share_of_all_file_text": pct(sum(r["chars_in_all_packets"] for r in measure["rows"]), ft),
            "top_repeated_lines": top_lines,
            "quoted_by_value_repeats": "W1's context excerpt 17 times (20,723); AD-5 body 14 times (14,896); AD-1..AD-7 and "
                                       "R-1..R-12 bodies 8-14 times each in every implement, test, document and verify file",
        },
        "restated_within_one_packet": [
            {"rule": "--check-only", "count": "4 in 11-step-plan, 2 in 16-implement, 4 in 24-test",
             "where": "Callback label, Checked by, loop Work, loop Repeat"},
            {"rule": "recovery", "count": "3", "where": "delegation line ('After lost context, run the Recovery command'), "
                                                       "'Lost context, or unsure? Run ...', 'Recovery command' + command"},
            {"rule": "pause / stop", "count": "5", "where": "loop 'Never stop cancelled ... pause command', Pause line, Halt "
                                                           "line, RULES, delegation"},
            {"rule": "untrusted / not instructions", "count": "8 in 11-step-plan, 10 in 16-implement",
             "where": "status, last accepted, evidence references, hand-offs, test strategy source, knowledge contents"},
            {"rule": "do only this stage", "count": "3", "where": "delegation line, Callback 'run once after its work', "
                                                                 "RULES"},
            {"rule": "step-plan structure (deps, check, criteria, test-only steps, check rows, expectations, skills)",
             "count": "3 each", "where": "duty items 4-7, exit conditions 2-7, Checked by"},
            {"rule": "implement: write no tests / start no later step", "count": "3",
             "where": "duty 1, Step block 'Later steps ... do not start them', loop Work"},
            {"rule": "implement: unachievable-as-planned triggers and 7 fix attempts", "count": "2",
             "where": "duty 6, loop Repeat"},
            {"rule": "implement: the Proof runs at done", "count": "4",
             "where": "Step block, duty 3, Checked by, exit 2"},
            {"rule": "Full packet pointer claims the file holds 'the knowledge files' contents'", "count": "1",
             "where": "_pointer_lines: the file holds a list of headings, not contents (inaccurate)"},
        ],
        "path_overhead": {"absolute_path_chars_in_printed": 53070, "pct_of_printed": 9.3,
                          "per_print": "1,374-2,076 characters: the run directory (96) 8-14 times, the plugin skills path "
                                       "(106) 3-7 times, the worktree (101) 0-2 times",
                          "note": "commands must stay literal (the hooks and the runtime read them); prose locators could "
                                  "use RUN/ once the symbols are defined in the printed text"},
        "boilerplate_vs_stage_specific": {
            "printed": f"stage-specific (method + step/input + result) {pct(pg['method'] + pg['step+input'] + pg['result'], pt)}%, "
                       f"frame {pct(pg['frame'], pt)}%, locators and quoted state {pct(pg['locators'] + pg['quoted'], pt)}%",
            "file": f"stage method {pct(fg['stage_method'], ft)}%; quoted state {pct(fg['quoted_state'], ft)}%; frame "
                    f"{pct(fg['instruction_frame'], ft)}%",
        },
        "generic_items_not_applying": {
            "context": "Battleship: an empty checkout (baseline commit only), one Salesforce org, a single-user stateless game "
                       "with no services, caches, async flows, stored data or internal vocabulary",
            "items": [
                {"stage": "discovery", "items": "5 specs, 6 skill links, 9 connected knowledge (MCP readers), 10 current-system "
                 "account, 11 service discovery (7 bullets), 13 interaction baseline", "chars": 2798,
                 "evidence": "02-discovery result summary ('No specs, skills, house style, CI, or local test runner'); "
                             "run/notes/discovery.md ('No MCP knowledge reader was required', 'Caching: none ... Not "
                             "applicable'); 7 whole guides read (154,386 bytes)"},
                {"stage": "research", "items": "6 vocabulary, 8 current-system gaps, 9 service choices", "chars": 831,
                 "evidence": "run/notes/research.md ('Not applicable: cache, async worker, extra observability sink')"},
                {"stage": "spec", "items": "8 service boundary contracts, 11 Backchain review (not requested)", "chars": 1176,
                 "evidence": "04-spec result: no service; 4 spec calls"},
                {"stage": "test-strategy", "items": "5 facilities, 7 service contracts, 8 baseline consumption (missing coverage)",
                 "chars": 1073, "evidence": "06-test-strategy result"},
                {"stage": "plan", "items": "4 baseline repair/bootstrap, 5 facility items, 12 service mapping, 13 CommonJS/ESM "
                 "module format (Apex), 19 optional Backchain child mechanics", "chars": 4212,
                 "evidence": "08-plan result summary; 19 says 'Nothing refuses a plan without it'"},
                {"stage": "prepare", "items": "4 blocked baseline", "chars": 334, "evidence": "10-prepare result"},
                {"stage": "step-plan", "items": "9 Plan record (skipped in all four step-plan results), 11 'Execution graph. "
                 "Record none' (inline)", "chars": 1916, "evidence": "run-insights plan section 1"},
            ],
            "total": "12,340 of 48,737 planning duty characters (25.3%), plus implement item 5 Services (292) and the "
                     "step-plan optional Backchain audit line (238)",
        },
    },

    "duty_review": {
        "criteria": "Each planning stage's DUTIES text, as printed in the Battleship packet, against: purpose stated; method "
                    "in order; what to read; what done means; how done is checked.",
        "per_stage": [
            {"stage": "intake", "duty_chars": 1562, "items": 8, "purpose": "yes (Goal)", "method_order": "checklist; fine",
             "reads": "the request, printed whole", "done": "3 done-when lines", "checked": "usual faults only",
             "verdict": "good (analysis directive 5)",
             "issues": ["item 1 restates SUMMARY_PLACEHOLDERS['intake'] ('as the template's summary says') - duplicated",
                        "item 3 source hints (teams, channels, private repositories) are generic for a self-contained "
                        "request - dead here; fold into item 2's open questions"]},
            {"stage": "discovery", "duty_chars": 5625, "items": 15, "purpose": "yes", "method_order":
             "item 1 'Baseline first' ordered; 2-15 a flat checklist with no applicability rule",
             "reads": "names 11 guides; the model read 7 whole (154 KB)", "done": "3 done-when lines (model-judged)",
             "checked": "usual faults only", "verdict": "wordy and unconditional (analysis directive 3)",
             "issues": ["items 9 and 11 (1,458) have no applicability gate - dead on an empty checkout (rewrite R5)",
                        "items 7 and 8 are meta-process rules that mean nothing without research-loop.md (44.8 KB)",
                        "items 10 and 13 both write RUN/notes/current-system-baseline.md - duplicated target",
                        "item 15 'reopen each locator as a fresh reader' cannot be checked",
                        "item 12 records identity; nothing keeps usernames and instance hosts out of HOME (plan A7)"]},
            {"stage": "research", "duty_chars": 3316, "items": 12, "purpose": "yes", "method_order": "1-2 ordered, rest a list",
             "reads": "intake/discovery results and notes", "done": "2 lines", "checked": "usual faults only",
             "verdict": "adequate (directive 5)",
             "issues": ["item 3 duplicates discovery item 8 (rewrite R9)",
                        "item 11 lets an assumption stay open that one allowed command settles (R9, plan G6)",
                        "items 6, 8, 9 unconditional enterprise/current-system/service items - dead here",
                        "item 10 interaction questions repeat intake 6, discovery 13, spec 9 and plan 8 (five stages)"]},
            {"stage": "spec", "duty_chars": 5731, "items": 12, "purpose": "yes", "method_order": "1 start, 2-9 content, 10 "
             "self-review, 11 Backchain, 12 evidence", "reads": "HOME/spec.md whole, research, discovery, baseline",
             "done": "4 lines", "checked": "lost R-<n>/AD-<n> IDs plus usual faults", "verdict": "good, but long",
             "issues": ["item 10 prints the 6-bullet planning review focus (1,382) to the producer; the walk leaves no trace "
                        "(plan G6: a 'Walked:' line)",
                        "item 9 restates INTERACTION_DESIGN; concurrency only as 'simultaneous changes' (rewrite R10, A4)",
                        "items 7 and 9 are two state items",
                        "item 11 Backchain review mechanics (886) for an optional route"]},
            {"stage": "test-strategy", "duty_chars": 6703, "items": 14, "purpose": "yes", "method_order": "loose",
             "reads": "HOME/spec.md and spec changes", "done": "4 lines incl. a 330-character probe rule",
             "checked": "usual faults only", "verdict": "wordy; misses the platform card (analysis directive 3)",
             "issues": ["items 1 and 2 share a source phrase and split one plan (rewrite R7)",
                        "item 4 is a 619-character noun list",
                        "item 11 accepts a file: stand-in as the probe of an authenticated entry (rewrite R8, H4)",
                        "no pointer to the platform card's runner and deploy rules (plan G1)",
                        "item 13 review focus (1,417) restates the Improve focus"]},
            {"stage": "plan", "duty_chars": 13129, "items": 19, "purpose": "yes",
             "method_order": "no: work-item content is spread over items 2, 3, 10, 14, 15 and 17 (item 2 forward-references "
                             "item 17)", "reads": "9 sources in item 1, no order of importance",
             "done": "3 lines", "checked": "assumption list shape, lost IDs, usual faults; the evidence-path and "
                                           "Superseded rules are not stated (plan E2)",
             "verdict": "too long to be read whole: the printed head (19,324) dropped every lookup and quoted block",
             "issues": ["item 19 (2,587, 20% of the duty) is optional Backchain-child mechanics (rewrite R3)",
                        "item 8 (2,464) restates INTERACTION_DESIGN and the UI ambition text step-plan 9 repeats (rewrite R4)",
                        "item 13 names CommonJS/ESM - platform detail in a generic duty (owner rule: platform detail only in "
                        "references/platforms/)",
                        "item 18 duplicates SUMMARY_PLACEHOLDERS['plan']",
                        "no concern map, activation, migration or API-caller decision (plan A1, A3, A5)"]},
            {"stage": "prepare", "duty_chars": 2124, "items": 7, "purpose": "yes", "method_order": "yes",
             "reads": "plan and HOME/environment.md", "done": "2 lines", "checked": "HOME file present, usual faults",
             "verdict": "good, one gap", "issues": [
                "item 3 checks only that runners start, not that each focused command runs the tree under test with a "
                "reporter ShipLoop reads (plan G1, C1)", "item 4 blocked-baseline repair is conditional text printed always"]},
            {"stage": "step-plan", "duty_chars": 8204, "items": 12, "purpose": "yes",
             "method_order": "ordered by result field (criteria, steps, commands, expectations, paths), not by work",
             "reads": "item 1 'reopen its context' while the head prints 400 of 3,308 characters; builds-on list not printed",
             "done": "7 exit conditions", "checked": "the longest Checked by line (structure gates)",
             "verdict": "directive 1 in the analysis: rules learned from ShipLoop's source, a contradiction for remote "
                        "targets, an ungated Plan record",
             "issues": ["item 4 `check`: contradiction for a remote-only target (rewrite R1, B1/B2)",
                        "item 5: no remote deploy rule, no criterion-paths rule (rewrite R6, C1/B2)",
                        "item 9 Plan record (1,833) skipped in all four results (rewrite R2, A1)",
                        "each structural rule stated three times (duty, exit, Checked by)",
                        "item 11 inline 'Record none' is a line telling the model to do nothing",
                        "item 2 repeats the harness decision that test-spec's summary and test's duty 2 also ask "
                        "('retain, refine or supersede' three times across the item)",
                        "path and expectation shape rules (exact files, no * across /) live only in source (plan E2)"]},
            {"stage": "test-spec", "duty_chars": 2343, "items": 8, "purpose": "yes", "method_order": "yes",
             "reads": "the step plan's focused IDs", "done": "3 exit conditions", "checked": "IDs match, open items' "
             "consumers, placeholders", "verdict": "compact and gated",
             "issues": ["item 2 puts surface, phase, setup, fixture, teardown, command row, suite and smoke membership 'in "
                        "those fields or the summary' - ambiguous where",
                        "item 7's open item has no example row or allowed values (plan E1)",
                        "no rule that a remote-resident ID gets red_na here (plan C1)"]},
        ],
        "cross_stage_duplicates": [
            "State and interaction lifecycle: intake 6, discovery 13, research 10, spec 9, plan 8 (INTERACTION_DESIGN worded "
            "five ways); step-plan 9 repeats plan 8's UI ambition sentence",
            "Planning review focus printed to producers at spec 10 and test-strategy 13 (1,382 and 1,417) and again to the "
            "Improve child (PLANNING_REVIEW_FOCUS)",
            "Recursive discovery policy and shared allowance: discovery 8 and research 3",
            "Harness 'retain, refine or supersede': test-strategy 4, step-plan 2, test-spec summary placeholder, test duty 2",
            "Backchain mechanics: spec 11 (886), plan 19 (2,587), step-plan optional audit line (238)",
        ],
        "dead_prose_in_source": [
            "shiploop_prompts.STEP_SIZING (883) and WORK_ITEM_CONTEXT (356): no reader in skills/ (git grep -w)",
            "SELECTED_CASE_RECONCILIATION (656) and TEST_DECISION_HANDOFF (356): read only by tests",
            "INTERACTION_DESIGN (3,095) and _PLANNING_HANDOFF: read only by the _check_swaps import guard; their text "
            "lives folded in the duties",
            "Stage rows' develop/test/deploy/tools fields: 51 strings, 4,247 characters, printed by no packet since the "
            "2026-10-11 re-cut (shiploop_navigator._goal_lines comment); stage_spec.develop() has no caller",
        ],
        "rewrites": rewrites,
        "rewrites_total": {"before_chars": sum(r["before_chars"] for r in rewrites),
                           "after_chars": sum(r["after_chars"] for r in rewrites)},
    },

    "template_option": {
        "owner_direction": "2026-10-18: be strict about scripts and steps; every stage's prompt is a template whose data the "
                           "script populates, including contents of files other stages produced; the template also carries "
                           "the exact result form the model fills.",
        "today": {
            "path": "emit -> render -> _render_lines/_producer_blocks (shiploop_navigator.py) builds about 30 blocks from "
                    "guidance.prompt_split (shiploop_prompts.py: duty() picks DUTIES[stage] then string surgery), "
                    "loops.invoke_lines, progress_lines, _result_contract_lines, _reference_global_lines, _consumer_lines, "
                    "handoff_lines, _run_context_lines and others; printed_text prints it whole under PRINT_LIMIT (16,000) "
                    "else packet_head -> _select_head keeps P0/P1 then lookup/chrome/quoted blocks until HEAD_LIMIT "
                    "(20,000; 19,500 when a required block is last)",
            "string_surgery": ["DUTIES placeholders <<backchain item>>, <<item commit rule>>",
                               "_INLINE_DUTY_PARAGRAPHS (step-plan, implement, verify paragraphs swapped by route)",
                               "_NO_REVIEW_SWAPS (planning review none)",
                               "_STEPS_WORDING / for_steps (ask-agent multi-step wording)",
                               "_PLAN_RECORD_INTERACTIONS removed when names_interactions is false",
                               "_one_step_carry_forward slicing by index of item headings",
                               "BACKCHAIN_STUB replacing the route paragraph",
                               "import-time guards: _check_swaps, _check_for_steps, the _INLINE_DUTY_PARAGRAPHS count check"],
            "prose_mass_in_python": {
                "method": "string literals of 40+ characters with 5+ spaces, docstrings excluded (ast); includes refusal "
                          "messages, so an upper bound for packet prose",
                "chars_by_module": {"shiploop_prompts.py": 150666, "shiploop_navigator.py": 63891,
                                    "shiploop_chain.py": 38521, "shiploop_stage_spec.py": 15245,
                                    "shiploop_test_loop.py": 11652, "shiploop_loops.py": 9736,
                                    "shiploop_workspace.py": 7906, "shiploop_lint.py": 6713,
                                    "shiploop_expectations.py": 5320, "shiploop_consumer_delivery.py": 5201,
                                    "shiploop_reference.py": 3927, "shiploop_knowledge_home.py": 2861},
                "one_packet_draws_from": "11-step-plan's lines came from at least 8 modules (prompts, navigator, loops, "
                                         "stage_spec, reference, knowledge_home, consumer_delivery, narrative/status_hook)",
            },
            "static_text_proposal": "fix plan section 3.6: static_text(name, section=None) in shiploop_reference.py reads "
                                    "references/<name> (implement-guidance.md, code-craft.md) word for word; a missing file "
                                    "or heading raises; no fallback. It moves fixed guidance out of Python but keeps the "
                                    "block assembly, tiers and string surgery in Python.",
        },
        "proposal": {
            "layout": "skills/shiploop/templates/<stage>.md (24, one per stage) + templates/partials/*.md (shared fixed "
                      "text: frame, rules, loop-invoke, loop-result, result-rules, appendix, code-craft, row formats). "
                      "Partials are verbatim text files too: no prose is built in Python.",
            "format": {
                "front_matter": "template, version, consumer (who reads the packet and the result, when), print_budget, "
                                "flags table, slots table (slot, kind, source, bound, over, pool), pools table, rows table "
                                "(row formats for block slots), result table (key, type, gate id)",
                "body": "fixed text with {{slot}}, {{> partial}}, {{#if flag}}...{{/if}} on declared boolean flags only "
                        "(no expressions); HTML comments are provenance notes and never print; '<!-- appendix' starts the "
                        "file-only part",
                "slot_kinds": {
                    "scalar": "an ID, count, path or literal value from state",
                    "cmd": "a literal command the CLI builds (callback, next, pause, lint, until-loop start); bound as "
                           "install lengths, e.g. cli+run+74",
                    "block": "rows rendered from state through a declared row format (step criteria, open items, concern "
                             "rows, dependencies)",
                    "include": "by-value content of an artifact an earlier stage produced: a result field "
                               "(result:plan.work_items[id=W1].context), a HOME section (home:environment.md#Commands), a "
                               "guide section (guide:platforms/<card>.md#Testing), whole or excerpted",
                },
                "bounds": "every slot declares a bound and an over policy: refuse (directive content: the producing "
                          "stage's gate enforces the same bound, so the render never cuts it), excerpt, toc (headings and a "
                          "locator), or a pool. An elastic pool ('rest>=1000') takes what the print budget leaves after "
                          "every other line, in body order, so lower-priority inputs become one-line pointers instead of "
                          "the host eliding the middle.",
                "result_side": "the template's Result form is the schema: its keys, allowed values and one example row "
                               "are fixed text; the result table maps each key to the gate that checks it; the gate parses "
                               "the same form (one source). Placeholders left in the form are refused (today's "
                               "HANDOFF_PLACEHOLDERS rule).",
            },
            "validator": [
                "build/test time: every {{slot}} and flag in the body (after partial expansion) is declared; every declared "
                "slot and flag is used; partials resolve; row formats exist; kinds and over policies are known; no refuse "
                "slot sits in a pool",
                "static budget: for every flag combination, fixed text + non-pooled bounds + pool minimums + one pointer "
                "allowance per pooled slot <= print_budget at the reference install (83/63/96)",
                "render time: a slot left unfilled, a value over a refuse bound, or a leftover '{{' raises naming the slot "
                "and its source",
                "packet = template + slot values: a test splits each rendered packet on the template's literal chunks "
                "(after flags and partials) and asserts they appear in order with only slot values between them, for "
                "every stage of the dry-run walk and the offline step slice, both routes",
                "gate IDs: each Gates line carries a gate id (comment); a test triggers each id through the real "
                "`complete` path (test the route) and asserts the template lists exactly the ids that stage can raise",
            ],
            "prototype_results": {
                "tool": "SP/insights2/packets-tools/tmpl.py (validate and render), values from prep_values.py",
                "step-plan": {"printed_chars": render["step-plan"]["printed_chars"],
                              "file_chars": render["step-plan"]["file_chars"],
                              "today_printed": 19726, "today_file": 28499,
                              "by_value_now": "work item context whole (3,308), 15 concern rows (1,362), ## Commands "
                                              "commands (963), symbols defined",
                              "by_value_today": "400-character context excerpt only",
                              "pointers_when_pool_spent": "platform card, open assumptions, R/AD headings, skills, last "
                                                          "summary"},
                "implement": {"printed_chars": render["implement"]["printed_chars"],
                              "file_chars": render["implement"]["file_chars"],
                              "today_printed": "21,600 bytes; host showed 20,339 characters, middle elided",
                              "today_file": 43918,
                              "by_value_now": "Step block (task, C1-C2, Proof with its directory, cases), 8 R-<n> rules "
                                              "(1,474), 7 AD-<n> choices (654), concern rows, Structure excerpt",
                              "by_value_today": "Step block only; the 16,809-character hand-off with R-n/AD-n stayed in "
                                                "the file"},
            },
            "static_budget": {
                "templates_as_delivered": {"step-plan": validate["templates/step-plan"]["max_printed"],
                                           "implement": validate["templates/implement"]["max_printed"],
                                           "verdict": "refused at 19,500: bounds accept the Battleship values (work item "
                                                      "context 3,308, task 1,130, Proof 973)"},
                "with_producer_bounds": {"step-plan": validate["tight/step-plan"]["max_printed"],
                                         "implement": validate["tight/implement"]["max_printed"],
                                         "bounds": "plan work item context 2,500; plan concern rows 1,200; step task 700; "
                                                   "step criteria 1,200; step Proof 600 (a longer probe goes in a script "
                                                   "file the Proof runs); progress 900",
                                         "verdict": "implement passes; step-plan misses by 84 (one more short cut in its "
                                                    "fixed text)"},
                "fixed_text": {"step-plan": "10,588-10,895", "implement": "8,029 without Code craft, 9,216 with the "
                               "one-clause-per-rule version, about 11,700 with the full rubric"},
                "lesson": "A strict static budget needs fixed text <= about 8-10K per stage and bounds enforced where data "
                          "is produced. Today the trade-off is hidden: the head drops by-value state and the host elides "
                          "the middle.",
            },
            "prose_that_moves": [
                {"from": "shiploop_prompts.py", "what": "DUTIES (24), STAGE_RULES, CODE_CRAFT, callback label and pointers, "
                 "SUMMARY_PLACEHOLDERS, ID_WORD_RULE, PROCEDURE_WALK, review focus lists, the inline/none/ask-agent "
                 "variants (become flags)", "to": "templates/<stage>.md and partials"},
                {"from": "shiploop_stage_spec.py", "what": "goal, done_when (exit conditions), outcomes text; the dead "
                 "develop/test/deploy/tools fields are deleted", "to": "each template's Goal and loop Exit lines; "
                 "stage_spec keeps structure only (edits, runs, reads, improve, outcomes)"},
                {"from": "shiploop_loops.py", "what": "BLOCK_HEADING, INVOKE_LINE, RESUME_LINE, FOLLOW_LINE, WORK, "
                 "REPEAT, RESULT_LINE, LOOP_RULE", "to": "partials loop-invoke, loop-result; Work/Exit/Repeat in each "
                 "stage template; the contract builder renders the same template text, so check_terminal's equality holds"},
                {"from": "shiploop_navigator.py", "what": "_checked_line/_stage_gates/_check_text (Gates), step_block, "
                 "_pointer_lines, _result_contract_lines, REFERENCES_HEAD, BUILDS_ON_HEAD, READS_HEAD, HANDOFF_HEAD, "
                 "HALT_LINE, _last_accepted_lines, _run_context_lines, _unverified_lines, _commit_scope_lines, "
                 "_revisit_lines, the improve hand-off text", "to": "templates and row partials; navigator keeps the slot "
                 "registry (name -> value function)"},
                {"from": "shiploop_test_loop.py, shiploop_workspace.py, shiploop_consumer_delivery.py, shiploop_lint.py, "
                 "shiploop_expectations.py, shiploop_knowledge_home.py, shiploop_reference.py, shiploop_narrative.py",
                 "what": "rule_lines, rerun_lines, observed_lines, return lines, delivery lines, lint command line, "
                 "result_lines, knowledge lines, RUN_RECORDS_LINE, the narrative", "to": "block slots with row partials"},
                {"from": "refusal messages (navigator gates)", "what": "out of scope for the pilot; later the same "
                 "template file can hold each gate id's refusal text so packet and refusal share words"},
            ],
            "prior_results_by_value": {
                "used_in_examples": ["result:plan.work_items[id].context", "result:plan.assumptions[open, consumer]",
                                     "result:plan.concerns[item] (A1)", "result:step-plan.steps[current].{task,check,deps,skills}",
                                     "result:step-plan.criteria[id in step]", "result:test-spec.test_cases[criterion in step]",
                                     "home:spec.md#R-n (first two sentences)", "home:architecture.md#AD-n (choice sentence)",
                                     "home:architecture.md#Structure", "home:environment.md#Commands (commands only)",
                                     "guide:platforms/<card>.md#Testing"],
                "rule": "bound at the producer: the stage that writes a field is refused when the field exceeds the bound "
                        "its consumers' templates declare, so a consumer never truncates a directive",
                "prerequisite": "platform cards need stable headings (the Salesforce card's testing rules sit under ## "
                                "Service discovery, so no section include can select them; plan G2)",
            },
            "tests_today_and_carry_over": [
                {"test": "test/shiploop_e2e/packet_obligations.json + test/shiploop-packet-obligations.test.py",
                 "pins": "29 rows, 64 anchors (40 in shiploop_prompts.py, 18 navigator, 3 loops, 1 status hook, 1 "
                         "narrative, 1 inner-loop.md); every anchor token must be in its source file and in the packets",
                 "carry_over": "rows unchanged; each moved anchor's source repoints to its template or partial "
                               "(obligations.source_violations already reads .md, e.g. inner-loop.md); the lost-token "
                               "mutation check is unchanged. Rewrite R2 replaces rows step-plan-scope and plan-record-*."},
                {"test": "test/shiploop_e2e/head_table.json, packet_head_table.json, render_diff.py, packet_changes.json",
                 "pins": "per-stage printed and whole sizes at the reference install; allowlisted added lines per unit",
                 "carry_over": "kept as measured regressions; the validator's static bound becomes the guarantee. Add a "
                               "live-data case (the retained Battleship and chess step plans) because node-fix-bug "
                               "under-predicts implement by 3.4-8.7 K"},
                {"test": "test/shiploop-head-order.test.py (714 lines)", "pins": "block order and tiers, callback third "
                 "line after the header, keepalive once, required tokens before 19,500, hooks read heads",
                 "carry_over": "hook tests unchanged; tier tests become printed-region versus appendix tests; "
                               "_select_head goes once every stage has a proven budget"},
                {"test": "test/shiploop-stage-spec.test.py", "pins": "every prose copy of GENUINE_FIX_ATTEMPTS",
                 "carry_over": "the fix_attempts scalar slot; the test reads templates"},
                {"test": "import-time guards in shiploop_prompts.py", "pins": "swap rows and inline paragraphs match once",
                 "carry_over": "replaced by the validator's flag enumeration"},
                {"test": "27 test files import shiploop_prompts; 9 index DUTIES[...]",
                 "carry_over": "read the template loader instead; assertions on wording become route tests where they "
                               "pin a gate (owner rule: test the route, not the wording)"},
            ],
            "risks": [
                {"risk": "head budget", "detail": "real data overflows the fixture-measured tables (10 of 33 prints cut); a "
                 "strict validator will refuse templates until producer bounds and shorter fixed text land",
                 "mitigation": "elastic pools, producer-side bounds, a live-data render case in CI"},
                {"risk": "obligations", "detail": "moving text drops a ledger token", "mitigation": "repoint anchors in "
                 "the same commit; the existing lost-token mutation check catches a miss"},
                {"risk": "main tenet", "detail": "excerpts and pointers can drop a needed fact, as the 400-character "
                 "context excerpt does today", "mitigation": "directive slots are refuse-class, bounded at the producer; "
                 "only supporting inputs pool"},
                {"risk": "loop contract equality", "detail": "check_terminal compares the contract with a rebuild from "
                 "state", "mitigation": "one renderer for packet and contract; one supported version (old runs refused)"},
                {"risk": "hooks", "detail": "status and keepalive hooks parse the callback position, keepalive line and "
                 "narrative markers", "mitigation": "frame partial keeps them byte-exact; head-order hook tests unchanged"},
                {"risk": "template logic creep", "detail": "conditions become a language", "mitigation": "declared "
                 "boolean flags only; the validator enumerates every combination"},
                {"risk": "gate drift", "detail": "Gates text written apart from gate code", "mitigation": "gate ids "
                 "triggered by route tests"},
                {"risk": "scope", "detail": "about 24 templates, Improve hand-offs and review focus, 27 test files",
                 "mitigation": "pilot two stages; byte-identical first"},
            ],
            "migration": [
                {"phase": 0, "do": "Loader, validator and slot registry; step-plan and implement templates that reproduce "
                 "today's packets byte for byte (render_diff: zero changed lines; head tables unchanged; ledger anchors "
                 "repointed). Proves the mechanism with no prompt change."},
                {"phase": 1, "do": "Pilot content in the same two templates: the frame, the concise methods (rewrites "
                 "R1, R2, R6), gates with ids, result forms, bounded includes, elastic pool; producer bounds on plan "
                 "(context, concern rows) and step-plan (task, Proof); a live-data render case from the retained "
                 "Battleship and chess runs; then the planned Battleship rerun measures reads of HOME and ShipLoop source."},
                {"phase": 2, "do": "The other inner stages (test-spec, validate-existing, test, document, verify, "
                 "carry-forward), then the prelude (with rewrites R3-R5, R7-R10), then outer stages, then Improve "
                 "hand-offs and review focus (fix plan 3.6's static_text becomes partial inclusion)."},
                {"phase": 3, "do": "Delete the Python prose and string surgery (_INLINE_DUTY_PARAGRAPHS, _NO_REVIEW_SWAPS, "
                 "_STEPS_WORDING, BACKCHAIN_STUB, prompt_split, dead constants and stage-row fields) and _select_head; "
                 "add the packet = template + slots test for every stage. One supported version: no dual path."},
            ],
            "recommendation": {
                "verdict": "yes",
                "reasons": [
                    "It fixes the measured failure mode: by-value state becomes the protected part of the packet and the "
                    "frame the bounded part, the inverse of today's head selection.",
                    "The budget becomes a build-time fact (validator) instead of a fixture measurement that real data "
                    "exceeded in 10 of 33 prints.",
                    "One source per fact: no string surgery, no import-time swap guards, gates listed once with ids.",
                    "The owner edits prompts as markdown; render_diff shows every packet a template edit changes.",
                    "The result form in the template is the gate's schema, which is the owner's 'template response'.",
                ],
                "conditions": [
                    "bounds enforced at the producing stage's gate (refuse-class slots never truncate)",
                    "elastic pools for supporting inputs, filled in priority order",
                    "a live-data render case in CI",
                    "byte-identical phase 0 before any wording change",
                    "no dual path after a stage moves",
                ],
                "owner_decisions": [
                    {"id": "T-D1", "question": "Code craft in the implement packet: full rubric (3,689; static budget "
                     "fails) or one clause per rule (1,188) with the full rubric in the step's Improve focus?",
                     "recommendation": "one clause per rule; the Improve review already carries the full text"},
                    {"id": "T-D2", "question": "Producer bounds: work item context 2,500, concern rows 1,200, step task "
                     "700, Proof 600 (longer probes in a script file)?", "recommendation": "yes"},
                    {"id": "T-D3", "question": "Shared partials (frame, rules, loop) or the shared text copied into each "
                     "of 24 templates?", "recommendation": "partials: one copy of each fact"},
                ],
            },
        },
    },
    "files": {
        "audit": str(I / "packets-audit.json"),
        "templates": [str(I / "templates" / n) for n in ("step-plan.template.md", "implement.template.md")],
        "filled_examples": [str(I / "templates" / n) for n in ("step-plan.filled.md", "implement.filled.md")],
        "partials": sorted(str(p) for p in (I / "templates" / "partials").glob("*.md")),
        "tools": sorted(str(p) for p in (I / "packets-tools").glob("*.py")),
        "data": sorted(str(p) for p in D.glob("*.json")),
    },
}
(I / "packets-audit.json").write_text(json.dumps(audit, indent=1, ensure_ascii=False))
print("written", len(json.dumps(audit)))
