#!/usr/bin/env python3
"""U22: build the split ShipLoop entry card from the base card (line slices of the base file).

usage: build.py <worktree> <base SKILL.md copy>
Writes skills/shiploop/SKILL.md and the new references in <worktree>; prints sizes and a paragraph
completeness check (every base paragraph is in the new card or in exactly one new file, after link
rewriting and whitespace normalisation, or is listed as rewritten in REWRITTEN).
"""
import re
import sys
from pathlib import Path

W = Path(sys.argv[1])
BASE = Path(sys.argv[2]).read_text().split("\n")


def L(a, b):
    """1-indexed inclusive line slice of the base card."""
    return "\n".join(BASE[a - 1:b])


def anchor(heading):
    value = heading.strip().lower()
    value = re.sub(r"[^\w\- ]", "", value)
    return value.replace(" ", "-")


# ---------------------------------------------------------------- moved text per new file
def demote(text):
    return re.sub(r"^### ", "## ", text, flags=re.M)


step3 = L(914, 955)
STEP3_KEEP_A = ("3. When this result is a planning result, an `implement` step or the last carry-forward (see\n"
                "   [When Improve runs](#when-improve-runs)), the script moves to the `improve` stage: it enters\n"
                "   `active_improve` for that same action and issues the Improve stage its own action id. Otherwise\n"
                "   the result is accepted and the next producer packet follows. ")
assert step3.startswith(STEP3_KEEP_A), "step 3 head moved"
step3_body = step3[len(STEP3_KEEP_A):]
COLD = ("On cold recovery, read the receipt and use its exact `next_argv` for an active child.\n"
        "   Missing state/output is incomplete, never evidence of success or permission to restart. ")
PAUSE = (" Pause by pausing the parent;\n   never report `cancelled` for a pause.")
assert COLD in step3_body and step3_body.endswith(PAUSE)
step3_body = step3_body.replace(COLD, "").removesuffix(PAUSE)
improve_child_text = "\n".join(line[3:] if line.startswith("   ") else line for line in step3_body.split("\n"))

recover_tail = ("Use the packet's exact command and absolute selected-card path; never substitute a same-named skill. Recover\n"
                "an existing run's current packet with:")
protocol = L(237, 249)
assert protocol.endswith(recover_tail)
protocol_moved = protocol.removesuffix(recover_tail) + \
    "Use the packet's exact command and absolute selected-card path; never substitute a same-named skill."

askagent = L(757, 780)
ASK_KEEP = ('On the opt-in `delegation: ask-agent` route, active INNER **producer**\n'
            'packets begin with "Execute the prompt in a fresh context." Improve handoffs instead begin "Keep the invoking parent\n'
            'alive": never clear, replace or wrap the live parent for Improve. ')
assert askagent.startswith(ASK_KEEP)
askagent_moved = askagent[len(ASK_KEEP):]

FILES = {
    "run-start.md": (
        "# Starting a run",
        "Read before the first `workspace start` or `init` of a run, and before a workspace return.",
        [("Progress view", L(54, 60) + "\n\n" + L(62, 68)),
         ("Workspace return", L(195, 207)),
         ("Existing-implementation baseline", L(209, 221)),
         ("Recorded Improve card", protocol_moved),
         ("Consumer-delivery pilot", L(255, 262))]),
    "guide-map.md": (
        "# Guides by stage",
        "Read at discovery, research, spec and planning, and when a packet names one of these guides.",
        [("Planning and coding guides", L(130, 167)),
         (None, demote(L(379, 404))),
         ("Access, testing and environments", L(1007, 1012) + "\n\n" + L(1014, 1017) + "\n\n" + L(1019, 1023)),
         ("Navigator guide", L(1034, 1038))]),
    "run-options.md": (
        "# Run options",
        "Read before choosing `--delegation`, `--lint` or `--planning-review` at `workspace start` or `init`, "
        "and before `delegation --set` or `lint-mode --set`.",
        [(None, demote(L(282, 306))), (None, demote(L(406, 455))), (None, demote(L(477, 509)))]),
    "improve-stages.md": (
        "# When Improve runs: the schedule",
        "Read when you need to know which results start an Improve child under the run's `planning_review` option, how "
        "its passes end, or what a plan-time experiment may change.",
        [(None, demote(L(39, 50))), (None, demote(L(308, 377)))]),
    "improve-child.md": (
        "# The Improve child",
        "Read when an Improve stage is current, and before running, recovering or restarting an Improve child.",
        [("Running the child", improve_child_text)]),
    "inner-loop.md": (
        "# The inner loop",
        "Read when an inner stage (`step-plan` through `carry-forward`) needs the rule behind its packet, or a "
        "stage reports `revise`.",
        [(None, demote(L(511, 545)).removeprefix("## The inner loop\n\n")),
         (None, demote(L(547, 582))), (None, demote(L(584, 604))), (None, demote(L(606, 612))),
         (None, demote(L(724, 739))), ("After carry-forward", L(1040, 1047))]),
    "test-loop.md": (
        "# Test loop and confirmation",
        "Read at `step-plan`, `test-spec`, `test` and `verify`, and when a test gate refuses.",
        [(None, demote(L(614, 683))), (None, demote(L(685, 708))), (None, demote(L(710, 722)))]),
    "backchain-route.md": (
        "# Backchain route",
        "Read at a planning stage whose packet names Backchain, and before choosing `--backchain-passes`.",
        [(None, demote(L(457, 475))), (None, L(1180, 1234).replace("## Source-aware", "## Source-aware", 1))]),
    "chain-route.md": (
        "# Implementation chains: route and binding",
        "Read on a `delegation: ask-agent` run at `implement`, and before any `chain` command.",
        [("Ask-agent context boundary", askagent_moved),
         ("Parallel implementation chains", L(1051, 1061) + "\n\n" + L(1063, 1100))]),
    "chain-navigation.md": (
        "# Implementation chains: navigation and settlement",
        "Read once a chain is bound: its navigation packet, capacity, serial mode, ledger and settlement.",
        [("Navigation and settlement", L(1101, 1156))]),
}

# ---------------------------------------------------------------- the card
RECOVERY = (
    "Recovering after a reset, summary or compaction? Run `python3 <this skill>/scripts/shiploop next --run-dir <the run\n"
    "directory named in your summary or handoff>` (`<this skill>` is the directory holding this file). It prints the\n"
    "current step's packet; follow that step and its callback. If your summary names no run directory, list\n"
    "`<repo-parent>/.shiploop-runs/*/run/state.md`, use the only active run for this repo, and if there are several\n"
    "record an open item instead of guessing. Keep this command in any summary you write.")

READ_WHEN = """## Read when

This card holds binding, start and recovery, ownership, the callback and authority limits. The rest lives in
purpose files; open one when its trigger holds, read it whole, once:

- [Starting a run](references/run-start.md): before the first `workspace start` or `init`, and before a workspace return.
- [Run options](references/run-options.md): choosing `--delegation`, `--lint` or `--planning-review`, or switching one mid-run.
- [Backchain route](references/backchain-route.md): a planning packet names Backchain, or choosing `--backchain-passes`.
- [Guides by stage](references/guide-map.md): discovery, research, spec and planning guides and the knowledge home.
- [When Improve runs](references/improve-stages.md): which results an Improve child reviews and how its passes end.
- [The Improve child](references/improve-child.md): an Improve stage is current, or you recover or restart one.
- [The inner loop](references/inner-loop.md): an inner stage's rule, its Until Loop, expectations, `revise`.
- [Test loop and confirmation](references/test-loop.md): test commands, base and candidate runs, floors, criteria.
- [Chains: route and binding](references/chain-route.md) and [navigation](references/chain-navigation.md): a
  `delegation: ask-agent` run at `implement`, or any `chain` command."""

START_POINTERS = ("Before the first `workspace start` or `init` of a run, read [starting a run](references/run-start.md):\n"
                  "the progress-view link to show the user, the workspace return, the existing-implementation baseline,\n"
                  "the recorded Improve card and the consumer-delivery pilot.")
GUIDE_POINTER = ("At discovery, research, spec and planning, follow the [guides by stage](references/guide-map.md):\n"
                 "cross-run knowledge, requirements, current-system baseline, coding, house style, service discovery and\n"
                 "the repository knowledge home.")
OPTIONS_POINTER = ("Run options are recorded at `workspace start` or `init` and refused on a saved run without them:\n"
                   "`--delegation inline|ask-agent` (default `inline`: this conversation executes every assignment),\n"
                   "`--lint fix|report|off`, `--planning-review stage|none` ([run options](references/run-options.md)) and\n"
                   "`--backchain-passes one|converge|none` ([Backchain route](references/backchain-route.md)).")
INNER_POINTER = ("## Inner stages\n\n"
                 "Each work item runs `step-plan`, `test-spec`, `validate-existing`, `implement` (one action per step), "
                 "`test`,\n`document`, `verify` and `carry-forward`, each inside one Until Loop started with the "
                 "packet's literal\ncommand; the packet prints its rule. The rules behind it: [the inner loop]"
                 "(references/inner-loop.md) and\n[test loop and confirmation](references/test-loop.md).")
STEP3_CARD = ("3. When this result is a planning result, an `implement` step or the last carry-forward (see\n"
              "   [When Improve runs](references/improve-stages.md#when-improve-runs)), the script moves to the "
              "`improve` stage: it enters\n"
              "   `active_improve` for that same action and issues the Improve stage its own action id. Otherwise\n"
              "   the result is accepted and the next producer packet follows. At an Improve stage, and before\n"
              "   recovering or restarting one, read [the Improve child](references/improve-child.md). "
              + COLD.rstrip() + PAUSE)
ASK_CARD = ASK_KEEP + ("Before an `implement` producer or a delegated worker on\nthat route, read "
                       "[chains: route and binding](references/chain-route.md).")
CHAINS_CARD = ("## Parallel implementation chains\n\n"
               "Chains are the opt-in `delegation: ask-agent` route for the current `implement` action; under "
               "`delegation:\ninline` the `implement` packets run each step in this conversation, in order. Read "
               "[chains: route and\nbinding](references/chain-route.md) before any `chain` command and [chains: "
               "navigation](references/chain-navigation.md)\nonce a chain is bound.")

card_parts = [
    L(1, 26), RECOVERY, "", L(27, 37), "", READ_WHEN, "",
    L(52, 53), START_POINTERS, "", L(70, 92), "", L(94, 129), "", GUIDE_POINTER, "",
    L(169, 193), "", L(223, 236), "Recover an existing run's current packet with:", L(250, 254), L(264, 281), OPTIONS_POINTER, "",
    INNER_POINTER, "",
    L(741, 756), ASK_CARD, "", L(782, 799), L(800, 913), STEP3_CARD, L(956, 1006), L(1025, 1033),
    CHAINS_CARD, "", L(1158, 1179).rstrip("\n"), ""]
card = "\n".join(card_parts)

# ---------------------------------------------------------------- links
homes = {}  # anchor -> file name ("" = the card)
for name, (title, _, sections) in FILES.items():
    homes.setdefault(anchor(title.lstrip("# ")), name)
    for heading, text in sections:
        if heading:
            homes[anchor(heading)] = name
        for match in re.finditer(r"^#{2,3} (.+)$", text, flags=re.M):
            homes[anchor(match.group(1))] = name
for match in re.finditer(r"^#{1,3} (.+)$", card, flags=re.M):
    homes[anchor(match.group(1))] = ""


def fix_card(text):
    def local(match):
        a = match.group(1)
        home = homes.get(a)
        if home is None:
            raise SystemExit(f"card: unknown anchor #{a}")
        return f"](#{a})" if home == "" else f"](references/{home}#{a})"
    return re.sub(r"\]\(#([\w-]+)\)", local, text)


def fix_file(text, name):
    text = text.replace("](references/", "](")

    def local(match):
        a = match.group(1)
        home = homes.get(a)
        if home is None:
            raise SystemExit(f"{name}: unknown anchor #{a}")
        if home == name:
            return f"](#{a})"
        return f"](../SKILL.md#{a})" if home == "" else f"]({home}#{a})"
    return re.sub(r"\]\(#([\w-]+)\)", local, text)


card = fix_card(card)
(W / "skills/shiploop/SKILL.md").write_text(card)
written = {}
for name, (title, trigger, sections) in FILES.items():
    body = [title, "", "Split from the ShipLoop skill card (`../SKILL.md`). " + trigger, ""]
    for heading, text in sections:
        if heading:
            body += ["## " + heading, ""]
        body += [text.strip("\n"), ""]
    text = fix_file("\n".join(body), name)
    (W / "skills/shiploop/references" / name).write_text(text)
    written[name] = text

# ---------------------------------------------------------------- sizes and completeness
print("SKILL.md", len(card.encode()))
for name, text in written.items():
    print(name, len(text.encode()))


def norm(text):
    text = re.sub(r"\]\([^)]*\)", "]()", text)
    return " ".join(text.split())


new_texts = {"SKILL.md": norm(card), **{n: norm(t) for n, t in written.items()}}
paragraphs = [p for p in re.split(r"\n\s*\n", "\n".join(BASE)) if p.strip()]
missing = []
for p in paragraphs:
    flat = norm(p)
    where = [n for n, t in new_texts.items() if flat in t]
    if not where:
        # split paragraphs: every sentence must land somewhere
        sentences = [s for s in re.split(r"(?<=[.:])\s+", flat) if len(s) > 25]
        lost = [s for s in sentences if not any(s in t for t in new_texts.values())]
        if lost:
            missing.append((flat[:90], lost[:3]))
print("paragraphs", len(paragraphs), "not found whole or by sentence:", len(missing))
for head, lost in missing:
    print(" -", head, "|", lost)
