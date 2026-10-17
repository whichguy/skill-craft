#!/usr/bin/env python3
"""Packet anatomy: bytes per section of a ShipLoop packet, per stage, from a directory of packets.

Phase 0 of the packet-compaction plan (docs/shiploop-packet-compaction-plan-2026-10-10.md): measure TODAY's print order
before changing it, so every later cut shows its saving.  Stdlib only.  No model calls, nothing written outside --out.

    python3 test/shiploop_e2e/packet_anatomy.py <run>/run/packets [<more dirs>] [--out DIR] [--label NAME]
    python3 test/shiploop_e2e/packet_anatomy.py --walk DIR [--case ID]  # no-model walk of the current engine (a cases.json prompt), then measure it
    python3 test/shiploop_e2e/packet_anatomy.py <text-dir> --glob '*.printed.txt'   # the heads of a packets.py --offline --text-dir render
    ... --max-unclassified 0.05    # exit 1 when more than that share of the bytes is unclassified (the tool no longer follows the engine)

A directory holds `nav-<id>.md` (a producer packet or, when its head line names the stage `improve`, the Improve stage's
packet: the Improve stage is an action of its own) and `nav-<id>-bind.md` (the Improve stage's packet that asks for
improve-bind).  A run of the older layout has `nav-<id>-improve.md` and `nav-<id>-improve-bind.md` beside the producer's.
The stage comes from the head line `ShipLoop navigator | <stage> | revision N`.

The classifier follows render(), packet_head() and _render_improve() in skills/shiploop/scripts/shiploop_navigator.py.  A
line is given to the section whose anchor it matches; a block section keeps the lines after its anchor up to its end rule.
A blank line belongs to the section before it.  What no anchor claims is reported as `unclassified`, with the largest such
lines, and is never folded into another section: sections plus unclassified always sum to the file's bytes.

It reads every layout a saved run can hold: the older packets (a context-index line, a progress snapshot), the 8-stage
packets with their quoted knowledge files, hand-offs and consumer-delivery block (the quoted body is the "  | " lines under
its label), the printed head (guidance, then References, the result template and the pointer lines, then the chrome) and
the layout of the efficiency plan (the pointer lines and the owner or style line before the callback, the loop block that
starts with the RUN line, the closing HEAD_END line).  A change to render() that adds a line shape fails
test/shiploop-e2e-packet-anatomy.test.py until a rule here claims it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

UNCLASSIFIED = "unclassified"
PREAMBLE = "delegation-preamble"

# The Improve stage's head also names the stage it reviews: "ShipLoop navigator | improve | revision N | the spec result".
HEAD_LINE = re.compile(r"^ShipLoop navigator \| (?P<stage>[^|]+?) \| revision (?P<revision>\d+)(?: \| [^|]+)?\s*$")


@dataclass(frozen=True)
class Rule:
    """One section anchor.  `kind` says how far the section reaches from the anchor line.

    line:    the anchor line only
    count:   the anchor line and n-1 more
    para:    up to and including the next blank line
    bullets: the anchor line and the "- " lines under it
    indent:  the anchor line and the lines indented by two spaces under it
    listing: the anchor line and the lines under it that are "- " bullets or indented by two spaces (a hand-off value)
    until:   up to and including the first line that matches `end`
    before:  up to the line before the first line that matches `end` (to the end of the file when none does)
    rest:    to the end of the file
    """

    section: str
    start: re.Pattern
    kind: str = "line"
    end: re.Pattern | None = None
    n: int = 1


def _r(section: str, start: str, kind: str = "line", end: str | None = None, n: int = 1) -> Rule:
    return Rule(section, re.compile(start), kind, re.compile(end) if end else None, n)


# Where a result-contract block ends: the next block that follows it in any layout.  The older layouts continue with the
# run context index or the step lines; the packets branch drops the index line, so the pass log, the progress view, the
# status block and the pointer lines end it too.
RESULT_END = (r"^(Run context index|This action's pass log|Step \S+ \(\d+ of \d+\)|Progress snapshot|Progress view:|Item plan:|"
              r"Considerations for this stage|Host-recorded labels|=== ShipLoop (status|narrative) ===|Full packet: |"
              r"Lost context, or unsure|Until Loop \()")

# Order matters: the first rule whose anchor matches a free line wins.  Section names are the report's columns.
RULES: tuple[Rule, ...] = (
    # --- head: stage line, callback, goal, done-when, checked-by, considerations (render(): _first_callback_lines, _goal_lines)
    _r("head", r"^ShipLoop navigator \|"),
    _r("head", r"^Delegation change:"),
    # The top block between the stage line and the callback (plan 6.1 orders 3 to 6): the recovery and packet-file pointer
    # lines (the packets branch's "Lost context, or unsure of anything about this run? Read ..." and the final layout's
    # "Lost context, or unsure? Run ..."), then the owner rule or the one-line style slot.  `Full packet:` stands before the
    # generic reading-list rule below, which would otherwise take its path.
    _r("pointer-lines", r"^(Lost context, or unsure|Full packet: |The duties and rules above are this stage's)"),
    _r("owner-rule", r"^(Owner rule:|Write concise but technically accurate language)"),
    _r("callback", r"^(Callback for this stage|Next command \(|Callback for this Improve child)"),
    _r("callback", r"^The opening file holds exactly these headings"),
    # The Improve packet's numbered instructions (round 2): run the improve skill, then the Improve stage's complete; an unbound
    # packet starts with the no-card notice and the improve-bind command, then the recovery command for the instruction.
    _r("callback", r"^(No Improve card is recorded|Then run the recovery command for the Improve instruction)"),
    _r("callback", r"^(1\. Run the improve skill on the|2\. When the improve skill has completed|ShipLoop could not start this review)"),
    _r("callback", r"^( {7}/improve | {3}\(the Skill tool, skill \"improve\")"),
    _r("goal", r"^(Goal:|Reviewing the returned .*Goal:)"),
    _r("done-when", r"^Done when", "bullets"),
    _r("checked-by", r"^Checked by:"),
    _r("considerations", r"^Considerations for this stage:", "bullets"),
    # --- the References block (_reference_lines): the symbols HOME, FEATURE, RUN and WORKTREE with the files under them,
    # the stage's consult note and what it builds on; it ends at the first line of another shape
    _r("references", r"^References \(", "before",
       r"^(?!(- |HOME = |FEATURE = |RUN = |WORKTREE = |Knowledge files: |Consult at this stage|Results this stage builds on))"),
    # --- an inner stage's Until Loop invoke block (shiploop_loops.invoke_lines): heading, argument, how to invoke, start, receipt rules
    _r("until-loop", r"^Until Loop \(this stage's work runs inside it", "para"),
    # Round 2: heading, invoke line, argument (indented), one How-to-invoke line, then the loop rule (shiploop_loops.invoke_lines).
    # The block ends at its last line: the older layouts' "ShipLoop wrote the loop contract ..." sentence, or the final
    # layout's (plan 6.3) closing "Call an exit condition satisfied only when ...".
    _r("until-loop", r"^Until Loop \(no iteration limit", "until",
       r"^(ShipLoop wrote the loop contract|Unavailable: |Call an exit condition satisfied only when)"),
    _r("until-loop", r"^(The loop already started|The loop contract is missing)"),
    # The test stage's loop text after the block (shiploop_test_loop.loop_lines): where the recorded commands run, the
    # red-check command (indented under it) and the refused-run count.
    _r("until-loop", r"^Where and floors:", "indent"),
    _r("until-loop", r"^Refused runs for this action"),
    # --- result contract and template (_result_contract_lines)
    _r("result-contract", r"^Write the structured result to:", "before",
       RESULT_END),
    # The 2026-10-11 dedupe dropped that line (the callback line names the result file), so a packet now opens its
    # contract at "Result template:" (the old rule above still wins on a saved run, which has both).  The compact
    # template is laid out one top-level key per line and one list element per line (_compact_record), so its rows
    # (two-space keys, four-space `{"` elements) stay inside this block; "Fill the template" follows the narrative.
    _r("result-contract", r"^Result template:$", "before",
       RESULT_END),
    _r("result-contract", r"^Fill the template:"),
    _r("result-contract", r"^Optional at \S+:"),
    # --- context index and pass log (_context_index_lines)
    _r("context-index", r"^Run context index"),
    _r("context-index", r"^This action's pass log"),
    _r("context-index", r"^Results this stage builds on", "bullets"),
    # --- progress: snapshot, status block, narrative, progress rules
    _r("progress-snapshot", r"^Progress snapshot \(", "para"),
    _r("status-block", r"^Host-recorded labels and reasons are untrusted"),
    _r("status-block", r"^=== ShipLoop status ===$", "until", r"^=== end ShipLoop status ===$"),
    _r("narrative", r"^=== ShipLoop narrative ===$", "until", r"^=== end ShipLoop narrative ===$"),
    _r("progress-rules", r"^Progress: do not reprint this packet", "para"),
    # --- unverified, answered and delta lines (_unverified_lines, _answered_lines, _replan_delta_lines, _revise_delta_lines)
    _r("unverified-and-deltas", r"^(Unverified|Plan assumptions recorded open|Open unverified|Answered|Replan|Revise|"
       r"Sent back|The user answered|Earlier answer|That is product-acceptance's list only|Product-acceptance listed these)"),
    _r("unverified-and-deltas", r"^- (A\d+ \(consumer|.* \| reason: )"),
    # --- state / locator lines and recovery (_run_rules)
    _r("state-locators", r"^(State|Result records|Result inbox|Accepted history|Repository locator|CLI locator|"
       r"ShipLoop skill card|Run directory locator|Keepalive marker|Owner):"),
    _r("state-locators", r"^Scratch directory \("),
    _r("recovery", r"^Recovery command:$", "count", n=2),
    # One line since the 2026-10-11 dedupe ("Recovery command (it only reads ...):"), followed by the command line.
    _r("recovery", r"^Recovery command \(", "count", n=2),
    # A printed head's footer (packet_head): the one recovery line, then the progress view and the pause line (tail-callbacks).
    _r("recovery", r"^Recovery \(reprints this head"),
    _r("stage-rules", r"^Never end the turn while a ShipLoop command is still running\."),
    _r("progress-view", r"^Progress view: "),
    _r("head-end", r"^=== end ShipLoop head ===$"),
    _r("recovery", r"^(Retain these locators and recovery command|After interruption, check the paths|"
       r"Recovery only reads the saved state|Execute this packet in this conversation|"
       r"Give the executing agent only the current action packet)"),
    # --- the original request (_request_block)
    _r("original-request", r"^Original request \(", "until", r"^Only the END marker carrying tag"),
    # --- workspace / return block (render(): navigator-worktree)
    _r("workspace-return", r"^(Execution checkout|Workspace authority and original branch|Return plan|Return receipt|"
       r"Current workspace return|Historical host reports in accepted|All product work happens|"
       r"Handoff completion requires|"
       r"The return operation is unavailable|Workspace return guidance)"),
    _r("workspace-return", r"^(To review the final candidate for return:|After review and authorization at this planned)",
       "count", n=2),
    _r("workspace-return", r"^Record each undecided path with"),
    _r("workspace-return", r"^(Return route \(from workspace\.md\)|Rollback of the return)", "bullets"),
    # --- Backchain block
    _r("backchain", r"^Selected Backchain and Until Loop resources", "indent"),
    _r("backchain", r"^(Backchain planning guide|Backchain audit resource|Loop resources for a repair|"
       r"Backchain graph check)"),
    # --- planning sources and queue rules (render(): plan, step-plan, carry-forward)
    _r("work-queue-rules", r"^(Full ordered work queue|Proposed queue awaiting Improve|At plan, supplied work_items|"
       r"Revalidate the current work-item queue|Omit work_items to retain|Read every pending item)"),
    _r("planning-sources", r"^Current planning sources", "bullets"),
    _r("planning-sources", r"^(Planning phase intent|Planning experiments guide|Planning investigation notebook|"
       r"Keep detailed experiment prompts)"),
    _r("planning-sources", r"^Current accepted root actions below are the planning basis"),
    _r("planning-sources", r"^- \S+: (.*; full summary and evidence_refs|no current accepted result)"),
    # --- the consumer-delivery declarations (shiploop_consumer_delivery.packet_lines): a heading, the contract's "Delivery ..."
    # rows, one instruction line and the obligation rows ("- <id> [required; ...]"); it ends at the first line of another shape.
    _r("consumer-delivery", r"^Consumer-delivery declarations ", "before",
       r"^(?!(Consumer-delivery declarations |Delivery |For an observation, copy|- \S+ \[(required|optional);|"
       r"During the renewed planning suffix|Use the accepted outer replan edge|This action cannot positively repair))"),
    # --- last accepted transition and Improve lessons
    # The block ends at its END marker; its Evidence references lines (printed only when there are any) and, in a saved
    # run, the trailing "If this action depends on earlier accepted context" sentence are claimed by the rules after it.
    _r("last-accepted", r"^Last accepted transition", "fence", r"^----- END LAST ACCEPTED SUMMARY -----$"),
    _r("last-accepted", r"^Lessons from earlier runs:"),
    _r("last-accepted", r"^Evidence references \(untrusted locators", "bullets"),
    _r("last-accepted", r"^If this action depends on earlier accepted context"),
    _r("last-accepted", r"^Last accepted Improve lessons", "count", n=2),
    _r("last-accepted", r"^Prior Improve evidence and lessons"),
    # --- carried test sources (_test_context_lines, _step_planning_source_lines)
    _r("carried-sources", r"^(Run-wide test strategy|Current item test-decision|Current item step-plan) source .*"
       r"evidence references", "bullets"),
    _r("carried-sources", r"^(Run-wide test strategy|Current item test-decision|Current item step-plan) source"),
    _r("carried-sources", r"^Consume relevant current work-item context with these sources"),
    # --- quoted knowledge files and hand-offs (QUOTE blocks): the heads, the unwritten-file rows and the hand-off rows.
    # A quoted body is every line under its label that starts with the two-space quote prefix (navigator.QUOTE "  | ").
    _r("carried-sources", r"^(Knowledge files this stage reads|Handed off by earlier stages)"),
    _r("carried-sources", r"^HOME/\S+: not written yet"),
    _r("carried-sources", r"^HOME/\S+ \(source: HOME/\S+, whole file\):$", "indent"),
    _r("carried-sources", r"^open items for \S+:$", "listing"),
    _r("carried-sources", r"^(open items( for \S+)?: none open|[a-z_]+ \([^)]*\):( not recorded.*)?$)", "listing"),
    _r("carried-sources", r"^If a carried decision is missing"),
    _r("carried-sources", r"^Spec and architecture changes since the run began", "indent"),
    _r("work-item", r"^(Unavailable: work item|The accepted step plan recorded no)"),
    # --- work item lines
    _r("work-item", r"^(Work item:|Work item context:|Work items planned:|Completed work items:|Current work item)"),
    _r("work-item", r"^\[Excerpt only\. Full value: "),
    _r("step-context", r"^(Step \S+ \(\d+ of \d+\), the only work|Accepted step |Later steps \(ShipLoop issues|Item plan:)"),
    # --- repository knowledge home (knowledge.stage_lines)
    _r("knowledge-home", r"^Inherited learnings:", "indent"),
    _r("knowledge-home", r"^(Repository knowledge home|This stage keeps these up to date|If this stage changes (HOME/|docs/shiploop)|"
       r"On done ShipLoop checks these files|outcome\.md must have|spec\.md is the living spec|"
       r"Written by earlier stages|ShipLoop refuses [a-z-]+ if any|(HOME/)?architecture\.md is how the product is built|"
       r"If (HOME/)?architecture\.md is missing|Begin .*/plan\.md with this exact first line|In .*/README\.md link the feature list|"
       r"At this handoff ShipLoop checks)"),
    # --- environment discovery
    _r("environment-discovery", r"^(Environment discovery requirement|One investigation allowance|"
       r"Recursive discovery policy|Navigator adapter)"),
    # --- the stage guidance block is split by blank-line gaps (see _split_guidance)
    # It ends at the tail callbacks: the old "Call this when done:" line, or (2026-10-11 dedupe, the second callback is
    # gone) the "Improve:" line that now opens the tail.
    # A printed head puts the References block, the result template and the pointer lines after the guidance, so those end it too.
    _r("stage-guidance", r"^Current stage guidance:$", "before",
       r"^(Call this when done:$|Improve: |Pause without consuming the action|Halt \(terminal|References \(|Result template:$|"
       r"Full packet: |Lost context, or unsure)"),
    # The five rules every stage prints (STAGE_RULES), when they stand outside the guidance block.
    _r("stage-rules", r"^RULES \(", "bullets"),
    # --- tail callbacks
    _r("tail-callbacks", r"^Call this when done:$", "count", n=2),
    _r("tail-callbacks", r"^(Improve: |Pause without consuming the action|Halt \(terminal)"),
    # --- Improve child packet (_render_improve)
    _r("improve-contract", r"^(Current action: Improve|Parent step remains pending)"),
    _r("improve-step-result", r"^Step result \(untrusted evidence", "before", r"^Selected Improve skill:"),
    _r("improve-binding", r"^(Selected Improve skill|Bound Until Loop|Until Loop root|Child workspace|"
       r"Read the selected Improve skill)"),
    _r("improve-review-focus", r"^(Planning|Final|Release|End)[^\n]* review focus\.", "until",
       r"^(unless a finding depends on it|[^\n]*A pass that finds none of these is trivial)"),
    _r("improve-review-focus", r"^End-of-work review:"),
    _r("improve-planning", r"^(Planning experiment|Planning assumption|Planning scratch|For a genuinely new child, freeze|"
       r"Freeze the experiment objective)"),
    _r("improve-ownership", r"^Improve context ownership", "before",
       r"^(Planning[^\n]* review focus|This producer attempt has returned)"),
    _r("improve-stage-requirements", r"^This producer attempt has returned", "before", r"^Exclude \.until-loop"),
    _r("improve-return", r"^Exclude \.until-loop", "rest"),
    # --- lint block and the loop / quality tail that follows Halt
    _r("lint", r"^ShipLoop lint \(", "until", r"^END lint data"),
    # --- reading list: a "Label: /absolute/path[#anchor]" line (_run_rules policies and guides, STAGE_REFERENCES)
    _r("reading-list", r"^Repository knowledge index "),
    _r("reading-list", r"^[^:\n]{3,140}: (/|GUIDES/|HOME/|RUN/)[^ \n]+$"),
    _r("reading-list", r"^[^:\n]{3,140}: [A-Za-z0-9_.-]+\.md$"),
    # One pointer line replaces every locator the packet's stage text does not name (2026-10-11 dedupe).
    _r("reading-list", r"^Every other policy and guide"),
)

# Parts of the stage-guidance block (guidance.prompt joins its parts with two blank lines): the first line decides.
GUIDANCE_PARTS: tuple[tuple[str, re.Pattern], ...] = (
    ("guidance-common", re.compile(r"^(Current stage guidance:|This packet assigns one script-selected)")),
    ("interaction-lifecycle", re.compile(r"^During discovery, research, spec development")),
    ("work-item-context", re.compile(r"^Where a plan creates or revises work")),
    ("planning-handoff", re.compile(r"^(Preserve this planning pass's key reference|Preserve this[^\n]* pass's)")),
    ("guidance-backchain", re.compile(r"^Follow the packet's Backchain planning guide")),
    ("guidance-test-facility", re.compile(r"^Use the packet's Reusable test facilities guide")),
    ("code-craft-rubric", re.compile(r"^Code craft\.")),
    ("progress-rules", re.compile(r"^Progress: do not reprint this packet")),
    # The one short list that replaced COMMON, PROGRESS_REPORTING and REQUIREMENTS_RULES (bullets begin "- " and
    # continue on lines indented by two spaces).
    ("stage-rules", re.compile(r"^(Rules for every stage|RULES \()")),
)
GUIDANCE_DUTY = "stage-duty"
POST_HALT_LOOP = "loop-and-quality-tail"

PATH = re.compile(r"(?<![\w/.-])/(?:Users|home|private|var|tmp|opt|usr|Volumes|mnt|root|workspace)/[^\s\"'`),;<>|\]\[]+")
ID = re.compile(r"nav-[0-9a-f]{32}")
REV = re.compile(r"\b(revision|rev=)\s?\d+")

SECTION_ORDER = (
    PREAMBLE, "head", "pointer-lines", "owner-rule", "callback", "goal", "done-when", "checked-by", "considerations", "references",
    "until-loop", "result-contract",
    "step-context",
    "context-index", "progress-snapshot", "status-block", "narrative", "unverified-and-deltas", "state-locators", "reading-list",
    "recovery", "original-request", "workspace-return", "backchain", "work-queue-rules", "planning-sources", "last-accepted",
    "carried-sources", "work-item", "knowledge-home", "environment-discovery", "guidance-common", GUIDANCE_DUTY,
    "interaction-lifecycle", "work-item-context", "planning-handoff", "guidance-backchain", "guidance-test-facility",
    "code-craft-rubric", "progress-rules", "stage-rules", "tail-callbacks", "lint", POST_HALT_LOOP, "improve-contract", "improve-step-result",
    "improve-binding", "improve-planning", "improve-review-focus", "improve-ownership", "improve-stage-requirements",
    "improve-return", "consumer-delivery", "progress-view", "head-end", UNCLASSIFIED,
)


def _split_guidance(lines: list[str]) -> list[tuple[str, str]]:
    """Give each line of a stage-guidance block to a part.  Parts are separated by two or more blank lines."""
    parts: list[list[str]] = [[]]
    blanks = 0
    for line in lines:
        if line.strip():
            if blanks >= 2 and parts[-1]:
                parts.append([])
            blanks = 0
        else:
            blanks += 1
        parts[-1].append(line)
    labelled: list[tuple[str, str]] = []
    for part in parts:
        first = next((line for line in part if line.strip()), "")
        name = next((section for section, pattern in GUIDANCE_PARTS if pattern.search(first)), GUIDANCE_DUTY)
        body = [line for line in part if line.strip()][1:2]
        if first == "Current stage guidance:" and body and re.match(r"\d+\. |Write no test code", body[0]):
            # Re-cut packets put the numbered duty straight under the heading (no blank-line gap): only the heading is
            # common guidance, the rest of the part is the stage's duty.
            labelled.extend((name if line.strip() == first else GUIDANCE_DUTY, line) for line in part)
            continue
        numbered = next((k for k, line in enumerate(part) if re.match(r"\d+\. ", line)), None) \
            if first == "Current stage guidance:" else None
        if numbered is not None:
            # A one-sentence opening under the heading, a blank line, then the numbered duties: the duties are the stage's.
            labelled.extend((name if k < numbered else GUIDANCE_DUTY, line) for k, line in enumerate(part))
            continue
        labelled.extend((name, line) for line in part)
    return labelled


def _block_end(rule: Rule, lines: list[str], i: int) -> int:
    """Index one past the last line of the block that starts at lines[i]."""
    n = len(lines)
    kind = rule.kind
    if kind == "line":
        return i + 1
    if kind == "count":
        return min(n, i + rule.n)
    if kind == "rest":
        return n
    if kind == "para":
        j = i
        while j < n and lines[j].strip():
            j += 1
        return min(n, j + 1)
    if kind in ("bullets", "indent", "listing"):
        prefix = ("- ", "  ") if kind == "listing" else ("- ",) if kind == "bullets" else ("  ",)
        j = i + 1
        while j < n and lines[j].startswith(prefix):
            j += 1
        return j
    if kind == "fence":
        # The last accepted transition: a saved run fences the summary (BEGIN ... END marker); the re-cut packet skips the
        # fence when the status block's Done line shows the same text, so the block is then only its lines up to a blank.
        for j in range(i + 1, n):
            if "BEGIN LAST ACCEPTED SUMMARY" in lines[j]:
                for k in range(j + 1, n):
                    if rule.end.search(lines[k]):
                        return k + 1
                return n
            if not lines[j].strip():
                return j
        return n
    if kind == "until":
        for j in range(i + 1, n):
            if rule.end.search(lines[j]):
                return j + 1
        return n
    if kind == "before":
        for j in range(i + 1, n):
            if rule.end.search(lines[j]):
                return j
        return n
    raise ValueError(kind)


def classify(text: str) -> list[tuple[str, int]]:
    """Return (section, bytes) for every line of a packet, in order.  The bytes sum to len(text.encode())."""
    raw = text.splitlines(keepends=True)
    lines = [line.rstrip("\r\n") for line in raw]
    sizes = [len(line.encode("utf-8")) for line in raw]
    labels: list[str | None] = [None] * len(lines)
    head = next((i for i, line in enumerate(lines) if HEAD_LINE.match(line)), None)
    start = 0
    if head:
        for i in range(head):
            labels[i] = PREAMBLE
        start = head
    i = start
    halted = False
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            labels[i] = labels[i - 1] if i and labels[i - 1] else UNCLASSIFIED
            i += 1
            continue
        if halted and not RULES_BY_SECTION["lint"].start.search(line):
            labels[i] = POST_HALT_LOOP
            i += 1
            continue
        rule = next((candidate for candidate in RULES if candidate.start.search(line)), None)
        if rule is None:
            labels[i] = UNCLASSIFIED
            i += 1
            continue
        stop = _block_end(rule, lines, i)
        if rule.section == "stage-guidance":
            for k, (name, _) in zip(range(i, stop), _split_guidance(lines[i:stop])):
                labels[k] = name
        else:
            for k in range(i, stop):
                labels[k] = rule.section
        if rule.section == "tail-callbacks" and line.startswith("Halt ("):
            halted = True
        i = stop
    return [(labels[k] or UNCLASSIFIED, sizes[k]) for k in range(len(lines))]


RULES_BY_SECTION = {rule.section: rule for rule in RULES}


def section_bytes(text: str) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for section, size in classify(text):
        totals[section] += size
    return dict(totals)


def unclassified_lines(text: str) -> list[tuple[int, str]]:
    raw = text.splitlines(keepends=True)
    out = []
    for (section, size), line in zip(classify(text), raw):
        if section == UNCLASSIFIED and line.strip():
            out.append((size, line.rstrip("\n")))
    return out


# --- paths ---------------------------------------------------------------------------------------------------------

def path_stats(text: str) -> dict:
    found = PATH.findall(text)
    return {"occurrences": len(found), "bytes": sum(len(p.encode("utf-8")) for p in found), "paths": found}


def path_roots(paths: list[str], min_count: int = 20, fan: float = 0.9) -> list[dict]:
    """Directory prefixes where the paths fan out: a prefix with >= min_count occurrences none of whose children holds
    `fan` of its occurrences.  Each path counts toward its deepest root.  Returns roots by bytes (length x repeats)."""
    counts: Counter = Counter()
    for path in paths:
        parts = path.rstrip("/").split("/")
        for k in range(2, len(parts)):
            counts["/".join(parts[:k])] += 1
    roots = []
    for prefix, count in counts.items():
        if count < min_count:
            continue
        depth = prefix.count("/") + 1
        children = [c for p, c in counts.items() if p.startswith(prefix + "/") and p.count("/") + 1 == depth + 1]
        if not children or max(children) < fan * count:
            roots.append(prefix)
    roots.sort(key=len, reverse=True)
    assigned: Counter = Counter()
    for path in paths:
        for root in roots:
            if path == root or path.startswith(root + "/"):
                assigned[root] += 1
                break
    return [{"root": root, "repeats": assigned[root], "bytes": len(root.encode()) * assigned[root]}
            for root in sorted(assigned, key=lambda r: -len(r.encode()) * assigned[r])]


# --- a directory of packets ----------------------------------------------------------------------------------------

STAGE_GROUPS = (
    ("intake", ("intake",)), ("discovery/research", ("discovery", "research")), ("spec/test-strategy", ("spec", "test-strategy")),
    ("plan", ("plan",)), ("prepare", ("prepare",)),
    ("step-plan/test-spec", ("step-plan", "test-spec")), ("validate-existing", ("validate-existing",)),
    ("implement", ("implement",)), ("test", ("test",)), ("document", ("document",)), ("verify", ("verify",)),
    ("carry-forward", ("carry-forward",)),
    ("system-test-author/system-test/product-acceptance", ("system-test-author", "system-test", "product-acceptance")),
    ("release-plan", ("release-plan",)), ("release-check/release/release-verify/operations",
                                           ("release-check", "release", "release-verify", "operations")),
    ("handoff", ("handoff",)), ("done", ("done",)),
)
GROUP_OF = {stage: group for group, stages in STAGE_GROUPS for stage in stages}
# The groups of the 17-stage inner loop (ShipLoop state version 4 and earlier), as the committed checkers-1 and battleship-1
# baselines (docs/experiments/packet-anatomy-20261010/) were grouped: a run of that loop is grouped with these, so its table
# stays comparable row by row with those baselines. A run is a 17-stage one when any packet names a stage only that loop had.
STAGE_GROUPS_V4 = (
    ("intake", ("intake",)), ("discovery/research", ("discovery", "research")), ("spec/test-strategy", ("spec", "test-strategy")),
    ("plan", ("plan",)), ("prepare", ("prepare",)), ("get-next-work-item", ("get-next-work-item",)),
    ("step-plan", ("step-plan",)), ("test-spec/test-author", ("test-spec", "test-author")),
    ("baseline/skill-assess/skill-validate", ("baseline", "skill-assess", "skill-validate")),
    ("test-red/green/refine/regression", ("test-red", "test-green", "test-refine", "regression")),
    ("implement", ("implement",)), ("document/static-checks/verify", ("document", "static-checks", "verify")),
    ("integrate/integration-verify/carry-forward", ("integrate", "integration-verify", "carry-forward")),
    ("system-test-author/system-test/product-acceptance", ("system-test-author", "system-test", "product-acceptance")),
    ("release-plan", ("release-plan",)), ("release-check/release/release-verify/operations",
                                           ("release-check", "release", "release-verify", "operations")),
    ("handoff", ("handoff",)), ("done", ("done",)),
)
V4_ONLY_STAGES = frozenset(s for _, stages in STAGE_GROUPS_V4 for s in stages) - frozenset(GROUP_OF) | {"select-work"}


def stage_groups(stages) -> tuple:
    """The stage groups of the run these stages come from: the 17-stage loop's when any of them only that loop had."""
    return STAGE_GROUPS_V4 if any(stage in V4_ONLY_STAGES for stage in stages) else STAGE_GROUPS


def packet_kind(name: str, stage: str | None = None) -> str:
    """producer, improve or improve-bind: by the file name in the older layout, by the head line's stage `improve` (and a
    `-bind` file name) in the layout where the Improve stage is an action of its own."""
    stem = name[:-3] if name.endswith(".md") else name
    if stem.endswith("-improve-bind") or (stage == "improve" and stem.endswith("-bind")):
        return "improve-bind"
    return "improve" if stem.endswith("-improve") or stage == "improve" else "producer"


def read_packets(directories: list[Path], pattern: str = "*.md") -> list[dict]:
    packets = []
    for directory in directories:
        for path in sorted(Path(directory).glob(pattern)):
            text = path.read_text(encoding="utf-8", errors="replace")
            head = next((HEAD_LINE.match(line) for line in text.splitlines() if HEAD_LINE.match(line)), None)
            stage = head.group("stage") if head else "unknown"
            packets.append({"file": path.name, "kind": packet_kind(path.name, stage), "stage": stage, "text": text,
                            "bytes": len(text.encode("utf-8"))})
    return packets


def _normal(line: str) -> str:
    return REV.sub(r"\1 N", ID.sub("nav-ID", line))


def shared_lines(packets: list[dict], threshold: float = 0.8) -> dict[int, int]:
    """Per packet index: bytes (with newline) of lines that occur in at least `threshold` of the packets given."""
    present: Counter = Counter()
    for packet in packets:
        present.update({_normal(line) for line in packet["text"].splitlines() if line.strip()})
    need = threshold * len(packets)
    out = {}
    for k, packet in enumerate(packets):
        out[k] = sum(len(line.encode()) + 1 for line in packet["text"].splitlines()
                     if line.strip() and present[_normal(line)] >= need)
    return out


def measure(packets: list[dict], label: str) -> dict:
    """The whole report for one run's packets (a JSON-ready dict)."""
    shared_all = shared_lines(packets)
    by_kind: dict[str, list[int]] = defaultdict(list)
    for k, packet in enumerate(packets):
        by_kind[packet["kind"]].append(k)
    shared_group = {}
    for kind, indexes in by_kind.items():
        sub = shared_lines([packets[k] for k in indexes])
        shared_group.update({indexes[j]: value for j, value in sub.items()})
    group_of = {stage: group for group, stages in stage_groups(p["stage"] for p in packets) for stage in stages}
    rows = []
    all_paths: list[str] = []
    unclassified_by_line: Counter = Counter()
    for k, packet in enumerate(packets):
        text = packet["text"]
        sections = section_bytes(text)
        assert sum(sections.values()) == packet["bytes"], (packet["file"], sum(sections.values()), packet["bytes"])
        paths = path_stats(text)
        all_paths.extend(paths["paths"])
        for size, line in unclassified_lines(text):
            unclassified_by_line[_normal(PATH.sub("<path>", line))[:110]] += size
        rows.append({"file": packet["file"], "kind": packet["kind"], "stage": packet["stage"],
                     "group": group_of.get(packet["stage"], packet["stage"]), "bytes": packet["bytes"],
                     "sections": sections, "pathBytes": paths["bytes"], "pathOccurrences": paths["occurrences"],
                     "sharedAll80Bytes": shared_all[k], "sharedKind80Bytes": shared_group[k]})
    total = sum(row["bytes"] for row in rows)
    section_total: dict[str, int] = defaultdict(int)
    for row in rows:
        for name, size in row["sections"].items():
            section_total[name] += size
    roots = path_roots(all_paths)
    return {
        "label": label, "packets": len(rows), "totalBytes": total,
        "producers": len(by_kind["producer"]), "improves": len(by_kind["improve"]) + len(by_kind["improve-bind"]),
        "sectionBytes": dict(sorted(section_total.items(), key=lambda kv: -kv[1])),
        "unclassifiedBytes": section_total.get(UNCLASSIFIED, 0),
        "unclassifiedShare": round(section_total.get(UNCLASSIFIED, 0) / total, 4) if total else 0,
        "unclassifiedTop": [{"bytes": size, "line": line} for line, size in unclassified_by_line.most_common(15)],
        "pathBytes": sum(row["pathBytes"] for row in rows),
        "pathShare": round(sum(row["pathBytes"] for row in rows) / total, 4) if total else 0,
        "pathOccurrences": sum(row["pathOccurrences"] for row in rows),
        "distinctPaths": len(set(all_paths)),
        "pathRoots": roots[:12], "distinctRoots": len(roots),
        "sharedAll80Bytes": sum(row["sharedAll80Bytes"] for row in rows),
        "sharedAll80Share": round(sum(row["sharedAll80Bytes"] for row in rows) / total, 4) if total else 0,
        "sharedKind80Bytes": sum(row["sharedKind80Bytes"] for row in rows),
        "sharedKind80Share": round(sum(row["sharedKind80Bytes"] for row in rows) / total, 4) if total else 0,
        "rows": rows,
    }


# --- markdown ------------------------------------------------------------------------------------------------------

def _k(n: float) -> str:
    return f"{n / 1000:.1f}K"


def group_table(report: dict, kind: str = "producer", top: int = 12) -> str:
    """Per stage group, mean bytes per packet and the top sections, as markdown."""
    rows = [r for r in report["rows"] if r["kind"] == kind or (kind == "improve" and r["kind"] == "improve-bind")]
    if not rows:
        return f"(no {kind} packets)\n"
    order = [group for group, _ in stage_groups(r["stage"] for r in report["rows"])]
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r["group"]].append(r)
    names = [g for g in order if g in groups] + sorted(g for g in groups if g not in order)
    mean_sections: dict[str, float] = defaultdict(float)
    for r in rows:
        for s, b in r["sections"].items():
            mean_sections[s] += b / len(rows)
    shown = [s for s, _ in sorted(mean_sections.items(), key=lambda kv: -kv[1])[:top]]
    if UNCLASSIFIED not in shown:
        shown.append(UNCLASSIFIED)
    out = ["| stage group | n | mean bytes | " + " | ".join(shown) + " | other sections | path % | shared>=80% % |",
           "|---|--:|--:|" + "--:|" * (len(shown) + 3)]
    for name in names + ["ALL " + kind]:
        members = groups[name] if name in groups else rows
        n = len(members)
        mean = sum(r["bytes"] for r in members) / n
        cells = []
        used = 0.0
        for s in shown:
            value = sum(r["sections"].get(s, 0) for r in members) / n
            used += value
            cells.append(f"{value:.0f} B" if s == UNCLASSIFIED else _k(value))
        other = mean - used
        path = sum(r["pathBytes"] for r in members) / sum(r["bytes"] for r in members)
        shared = sum(r["sharedKind80Bytes"] for r in members) / sum(r["bytes"] for r in members)
        out.append(f"| {name} | {n} | {_k(mean)} | " + " | ".join(cells) + f" | {_k(other)} | {path:.0%} | {shared:.0%} |")
    return "\n".join(out) + "\n"


def totals_table(report: dict) -> str:
    total = report["totalBytes"]
    out = ["| section | bytes | share |", "|---|--:|--:|"]
    for name, size in report["sectionBytes"].items():
        out.append(f"| {name} | {size:,} | {size / total:.1%} |")
    out.append(f"| **all** | {total:,} | 100% |")
    return "\n".join(out) + "\n"


def render_markdown(report: dict) -> str:
    total = report["totalBytes"]
    lines = [f"# Packet anatomy: {report['label']}", "",
             f"{report['packets']} packets ({report['producers']} producer, {report['improves']} Improve), {total:,} bytes "
             f"(mean {total // max(1, report['packets']):,}).", "",
             "Generated by `test/shiploop_e2e/packet_anatomy.py`; sections follow today's print order "
             "(see the module docstring). Sections plus `unclassified` sum to the file bytes.", "",
             "## Whole run, bytes per section", "", totals_table(report),
             f"Unclassified: {report['unclassifiedBytes']:,} bytes ({report['unclassifiedShare']:.1%}).", ""]
    if report["unclassifiedTop"]:
        lines += ["Largest unclassified line shapes (bytes summed over the run):", ""]
        lines += [f"- {u['bytes']:,} B: `{u['line']}`" for u in report["unclassifiedTop"][:8]] + [""]
    lines += ["## Absolute paths", "",
              f"- {report['pathBytes']:,} bytes ({report['pathShare']:.1%} of all bytes) in {report['pathOccurrences']:,} "
              f"occurrences of {report['distinctPaths']:,} distinct paths.",
              f"- {report['distinctRoots']} path roots (a directory prefix where paths fan out, 20+ repeats); the largest:", "",
              "| root | repeats | root bytes (length x repeats) |", "|---|--:|--:|"]
    lines += [f"| `{r['root']}` | {r['repeats']} | {r['bytes']:,} |" for r in report["pathRoots"]]
    lines += ["", "## Lines shared across packets", "",
              f"- Lines identical (action id and revision normalised) in at least 80% of all {report['packets']} packets: "
              f"{report['sharedAll80Bytes']:,} bytes ({report['sharedAll80Share']:.1%}).",
              f"- Same rule within a kind (producer packets among producer packets, Improve among Improve): "
              f"{report['sharedKind80Bytes']:,} bytes ({report['sharedKind80Share']:.1%}).", "",
              "## Producer packets by stage group (mean per packet, top sections)", "", group_table(report, "producer"),
              "## Improve packets by stage group (mean per packet, top sections)", "", group_table(report, "improve")]
    return "\n".join(lines)


# --- no-model walk of the current engine -----------------------------------------------------------------------------

WALK_SCRIPT = r'''
import json, subprocess, sys
from pathlib import Path
scripts, cli, run_dir, card = sys.argv[1], sys.argv[2], Path(sys.argv[3]), sys.argv[4]
sys.path.insert(0, scripts)
import shiploop_navigator as nav, shiploop_store as store
def shiploop(*args):
    done = subprocess.run([sys.executable, cli, *args], capture_output=True, text=True)
    if done.returncode:
        raise SystemExit("shiploop " + " ".join(args[:2]) + " failed: " + (done.stderr or done.stdout)[-1500:])
visits = 0
while True:
    state = store.read_record(run_dir / "state.md")
    if state["status"] != "active":
        break
    action, stage = str(nav.current_action(state)["id"]), nav.current_stage(state)
    shiploop("next", f"--run-dir={run_dir}")                       # writes packets/<action>.md
    result = {"outcome": "done", "summary": "Synthetic: the no-model walk records this stage without doing it."}
    if stage == "plan":
        result["work_items"] = [{"id": "W1", "title": "The whole request"}]
    state = nav.apply(state, action, result)
    if state["active_improve"] is not None:
        nav.save(run_dir, state)
        shiploop("next", f"--run-dir={run_dir}")                   # the Improve stage's packet that asks for improve-bind
        stage_action = state["active_improve"]["improve_action"]   # the Improve stage's own id: what its commands name
        shiploop("improve-bind", f"--run-dir={run_dir}", f"--action={stage_action}", f"--skill-card={card}")
        shiploop("next", f"--run-dir={run_dir}")                   # the Improve stage's packet once ShipLoop has started it
        state = store.read_record(run_dir / "state.md")
        state = nav.finish_improve(state, action, {"summary": "Synthetic Improve receipt from the no-model walk."})
    nav.save(run_dir, state)
    visits += 1
    if visits > 200:
        raise SystemExit("walk did not end")
print(json.dumps({"visits": visits, "status": state["status"]}))
'''


def walk(out: Path, plugin_scripts: Path | None = None, case: str = "hello") -> Path:
    """Run a request through the CURRENT engine with synthetic results (no model), writing every packet.

    Mirrors test/shiploop_e2e/run.py seed_run: `workspace start` in a throwaway git repository, then a loop that applies a
    synthetic done result per stage; at a reviewed stage it also prints the Improve stage's two packets (before and after its card is bound).
    The request is the prompt of ``case`` in cases.json (any case: the walk's results are synthetic, so no product is
    favoured). Returns the run's packets directory."""
    import os
    import subprocess

    root = Path(__file__).resolve().parents[2]
    scripts = plugin_scripts or root / "skills" / "shiploop" / "scripts"
    card = root / "skills" / "improve" / "SKILL.md"
    out.mkdir(parents=True, exist_ok=True)
    work = out / "work"
    work.mkdir(exist_ok=True)
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    identity = ["-c", "user.name=packet anatomy walk", "-c", "user.email=walk@example.invalid"]
    (work / "README.md").write_text("# No-model walk\n")
    for args in (["init", "-q"], ["add", "README.md"], [*identity, "commit", "-qm", "seed: baseline"]):
        subprocess.run(["git", "-C", str(work), *args], check=True, capture_output=True, text=True, env=env)
    cli = scripts / "shiploop"
    workspace = out / ".shiploop-runs" / "walk"
    cases = json.loads((Path(__file__).resolve().parent / "cases.json").read_text(encoding="utf-8"))
    if case not in cases:
        raise SystemExit(f"walk: no case {case!r} in cases.json (cases: {', '.join(sorted(cases))})")
    prompt = cases[case]["prompt"]
    started = subprocess.run([sys.executable, str(cli), "workspace", "start", f"--repo={work}", f"--workspace-root={workspace}",
                              "--delegation=inline", f"--prompt={prompt}"], capture_output=True, text=True, env=env)
    if started.returncode:
        raise SystemExit("walk: workspace start failed: " + (started.stderr or started.stdout)[-2000:])
    run_dir = workspace / "run"
    done = subprocess.run([sys.executable, "-c", WALK_SCRIPT, str(scripts), str(cli), str(run_dir), str(card)],
                          capture_output=True, text=True, env=env)
    if done.returncode:
        raise SystemExit("walk failed: " + (done.stderr or done.stdout)[-2000:])
    return run_dir / "packets"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("packets", nargs="*", type=Path, help="directories of packet .md files (one run per --label)")
    ap.add_argument("--label", default=None, help="name of the measured run (default: the first directory's name)")
    ap.add_argument("--out", type=Path, help="write <label>.json and <label>.md here instead of printing")
    ap.add_argument("--walk", type=Path, metavar="DIR",
                    help="first run a no-model walk of the current engine under DIR, then measure its packets")
    ap.add_argument("--case", default="hello", help="the cases.json case whose prompt the walk submits (default: hello)")
    ap.add_argument("--glob", default="*.md", help="which files of a directory are packets (default: *.md; a packets.py --text-dir render: '*.printed.txt')")
    ap.add_argument("--max-unclassified", type=float, metavar="SHARE",
                    help="exit 1 when more than this share of the bytes (0.05 is 5%%) is unclassified")
    args = ap.parse_args(argv)
    directories = list(args.packets)
    label = args.label
    if args.walk:
        directories.append(walk(args.walk, case=args.case))
        label = label or "no-model-walk-current-engine"
    if not directories:
        ap.error("give a packet directory or --walk DIR")
    packets = read_packets(directories, args.glob)
    if not packets:
        ap.error(f"no packet files ({args.glob}) found")
    report = measure(packets, label or directories[0].name)
    markdown = render_markdown(report)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / f"{report['label']}.json").write_text(json.dumps(report, indent=1) + "\n")
        (args.out / f"{report['label']}.md").write_text(markdown)
        print(f"wrote {args.out / (report['label'] + '.md')} and .json: {report['packets']} packets, "
              f"{report['totalBytes']:,} bytes, unclassified {report['unclassifiedShare']:.1%}")
    else:
        print(markdown)
    if args.max_unclassified is not None and report["unclassifiedShare"] > args.max_unclassified:
        print(f"unclassified {report['unclassifiedShare']:.1%} is over {args.max_unclassified:.1%}: extend RULES in packet_anatomy.py",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
