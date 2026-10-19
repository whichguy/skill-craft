"""Build the slot values for the two filled examples from the Battleship run's own records (analysis tool; version 2).

    python3 -I prep_values.py <inputs_dir> <packets_dir> <out_dir>

Every value comes from a retained run file: the accepted results (plan, step-plan, test-spec, prepare), HOME at the commit
the stage saw (2449835 before step-plan, fcd65c9 before implement S1), the run's paths, and the narrative the run printed.
The one exception is plan_concerns / step_concerns: the 2026-10-18 build has no concern rows (A1 is not built), so those
rows restate decisions the run recorded (AD-n, R-n) and mark the two concerns the run never decided as "no decision".
"""
import json
import re
import subprocess
import sys
from pathlib import Path

inputs, packets, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
BASE = "/Users/dadleet/e2e-runs/20261017/bs-sf-int-b7c77f"
RUN = BASE + "/.shiploop-runs/work-20261018-040601-5105d5/run"
WT = BASE + "/.shiploop-runs/work-20261018-040601-5105d5/worktree"
PLUG = BASE + "/home/.grok/installed-plugins/skill-craft-a90d33d5"
CLI = "python3 " + PLUG + "/skills/shiploop/scripts/shiploop"
LOOP = "python3 " + PLUG + "/skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py"
RUN_ID = "nav-905f77c61fae40e59df4ad5317656b66"


def result(name):
    t = (inputs / name).read_text()
    return json.loads(re.search(r"```shiploop-state\n(.*?)\n```", t, re.S).group(1))["result"]


def sections(text, level):
    parts = re.split(r"(?m)^(?=" + "#" * level + " )", text)
    return {p.split("\n", 1)[0][level + 1:].strip(): p for p in parts if p.startswith("#" * level + " ")}


def section(text, heading):
    m = re.search(r"(?ms)^## " + re.escape(heading) + r"\n(.*?)(?=^## |\Z)", text)
    return m.group(1).strip()


def commands_code(text):
    """## Commands, code only: each bullet that names a command (its label and the command) and each fenced command."""
    keep = []
    for line in text.splitlines():
        if line.startswith("- ") and "`" in line:
            label, _, rest = line[2:].partition(":")
            cmd = re.search(r"`([^`]+)`", rest or label)
            keep.append("- " + (label.strip() + ": " if rest else "") + (cmd.group(1) if cmd else ""))
    keep += ["$ " + f for f in re.findall(r"```sh\n(.*?)\n```", text, re.S)]
    return "\n".join(keep)


def common(action, rev, stage):
    return {
        "stage": stage, "revision": str(rev), "action": action,
        "next_command": f"{CLI} next --run-dir={RUN}",
        "pause_command": f"{CLI} pause --run-dir={RUN} '--reason=<who asked and why>'",
        "callback_command": f"{CLI} complete --run-dir={RUN} --action={action}",
        "packet_abs": f"{RUN}/packets/{action}.md", "inbox_abs": f"{RUN}/inbox/{action}.md",
        "keepalive_marker": f"SHIPLOOP-RUN run={RUN_ID} rev={rev} dir={RUN}",
        "loop_start_command": f"{LOOP} start --receipt {RUN}/loops/{action}-terminal.json < {RUN}/loops/{action}-contract.json",
        "receipt_abs": f"{RUN}/loops/{action}-terminal.json", "run_dir": RUN, "guides_dir": PLUG + "/skills/shiploop/references",
        "worktree": WT, "contract_abs": f"{RUN}/loops/{action}-contract.json", "loop_error": "",
    }


# Version 2 prints the loop argument from the contract ShipLoop wrote (loops.invoke_lines), with the two engine changes the
# template migration makes: the Work line cites the template's Method items instead of today's duty items, and N5 renames
# revise to send-back. Exit conditions are stage_spec's, verbatim from the contract.
METHOD_ITEMS = {"step-plan": ("duty items 1-12", "Method items 1-9"), "implement": ("duty items 1-7", "Method items 1-5")}


def loop_argument(action, stage):
    c = json.loads(Path(f"{RUN}/loops/{action}-contract.json").read_text())
    old, new = METHOD_ITEMS[stage]
    work = c["work"].replace(old, new)
    repeat = (c["repeat_condition"].replace("Stop blocked and report revise", "Stop blocked and report send-back")
              .replace("the stage then reports revise", "the stage then reports send-back"))
    if stage == "implement":
        repeat = E3_REPEAT_STEP
    return "\n".join(["----- BEGIN until-loop ARGUMENT -----", "Work: " + work, "Exit when ALL of these hold:",
                      c["exit_condition"], repeat, f"Contract: {RUN}/loops/{action}-contract.json",
                      f"Receipt: {RUN}/loops/{action}-terminal.json", "----- END until-loop ARGUMENT -----"])


# E3 (plan 8.5): loops.REPEAT_STEP with the N5 names and one route per cause.
E3_REPEAT_STEP = ("Repeat while an exit condition is unmet (the Proof fails, a new lint finding stands on a changed line, a "
                  "criterion is not yet shown) and a justified investigation or fix remains; there is no iteration limit. "
                  "Stop blocked when none remains: report blocked when a person or an outside service must act (access, "
                  "authority, a decision); report send-back, with the blocker and the attempts made, when the step is proven "
                  "unachievable as planned (it contradicts a requirement, a decision, the item or a protected file; it needs a "
                  "tool that is absent; or it would exceed the item), or when the same underlying failure persists after 7 "
                  "genuine fix attempts. Never stop cancelled: a user's stop is the ShipLoop packet's pause command.")


# N2: the last two commits that are not ShipLoop bookkeeping (its knowledge records and leftover commits), from a HEAD.
BOOKKEEPING = re.compile(r"^(docs\(shiploop\): record .* knowledge|chore\(shiploop\): commit files written)")


def recent_commits(head, count=2):
    out = subprocess.run(["git", "-C", WT, "log", "--format=%h%x1f%s%x1f%b%x1e", head], capture_output=True, text=True,
                         check=True).stdout
    rows = []
    for rec in out.split("\x1e"):
        parts = rec.strip("\n").split("\x1f")
        if len(parts) < 3 or BOOKKEEPING.match(parts[1]):
            continue
        lines = [l for l in parts[2].strip().splitlines() if l.strip()]
        learning = next((l.split(":", 1)[1].strip() for l in lines if l.startswith("Key learnings:")), lines[0] if lines else "")
        rows.append({"short": parts[0], "subject": parts[1], "learning": learning})
        if len(rows) == count:
            break
    return rows


def narrative(packet):
    t = (packets / packet).read_text()
    return t[t.index("=== ShipLoop narrative ==="):t.index("=== end ShipLoop narrative ===") + len("=== end ShipLoop narrative ===")]


plan = result("plan.result.md")
sp = result("step-plan.result.md")
ts = result("test-spec.result.md")
prep = result("prepare.result.md")
w1 = plan["work_items"][0]

# ---------------------------------------------------------------- step-plan W1 (revision 10)
home_a = inputs / "home-2449835"
spec_a, arch_a, env_a = ((home_a / f).read_text() for f in ("spec.md", "architecture.md", "environment.md"))
reqs = [h for h in sections(spec_a, 3)]
arch3 = sections(arch_a, 3)
decisions = [h for h in arch3 if h.startswith("AD-")]
procedures = [h for h in arch3 if not h.startswith("AD-") and " " not in h]
checks = [h for h in arch3 if not h.startswith("AD-") and " " in h]
card = (inputs.parent / "card-salesforce.md").read_text() if (inputs.parent / "card-salesforce.md").exists() else ""
tap = re.search(r"(?s)(ShipLoop judges a focused Apex test.*?carry the proof\.)", card)
CONCERNS = [
    ("ui", "yes", "simple 10x10 grid, New game button, static in-flight cue", "AD-6, R-9", "step-plan"),
    ("api", "yes", "SLBattleController @AuraEnabled newGame and fire return the game JSON; engine static", "R-8, AD-2", "step-plan"),
    ("messaging", "no", "request and response only", "AD-3", "-"),
    ("state", "yes", "caller-held game JSON; Apex stores nothing", "AD-1, AD-5", "step-plan"),
    ("migrate-before", "no", "new project, no stored data", "AD-5", "-"),
    ("migrate-after", "no", "nothing to contract", "AD-5", "-"),
    ("switchover", "yes", "deploy, then assign SLBattle_Access; the test org is the delivery org", "R-2", "release-plan"),
    ("concurrency", "yes", "no decision recorded (a click while a call is pending; New game during a pending fire)", "R-9", "step-plan"),
    ("platform-services", "yes", "LWC, Apex and a permission set; no custom store", "AD-2", "step-plan"),
    ("scale", "yes", "no SOQL or DML; 100 shots in one transaction", "R-11", "test"),
    ("security", "yes", "least-privilege permission set; no credential printed", "R-12, AD-2", "step-plan"),
    ("observability", "no", "no server state; a failed call surfaces as AuraHandledException", "AD-3", "-"),
    ("config", "yes", "API 68.0 pinned in sfdx-project.json", "R-1", "step-plan"),
    ("performance", "yes", "inside the R-11 limits", "R-11", "test"),
    ("accessibility", "yes", "no decision recorded (names for 100 cell buttons; status as text)", "R-9", "step-plan"),
]
sp_values = common("nav-03cbb489abfe48ce8bf8ab1cfb207729", 10, "step-plan")
sp_values.update({
    "progress": narrative("11-step-plan.packet.md"),
    "item_id": w1["id"], "item_pos": "1 of 1", "item_title": w1["title"], "item_context": w1["context"],
    "open_assumptions": [{"id": a["id"], "assumption": a["assumption"], "check": a.get("check", ""),
                          "reason": a.get("reason", "")} for a in plan["assumptions"]
                         if a.get("disposition") == "open" and a.get("consumer") == w1["id"]],
    "plan_concerns": [dict(zip(("concern", "applies", "decision", "anchor", "owner_stage"), c)) for c in CONCERNS if c[1] == "yes"],
    "spec_toc": "KNOWLEDGE/spec.md: " + " · ".join(reqs),
    "arch_toc": ("KNOWLEDGE/architecture.md: " + " · ".join(decisions) + "; Real-boundary checks: " + " · ".join(checks)
                 + "; Procedures: " + ", ".join(procedures)),
    "env_commands": commands_code(section(env_a, "Commands")),
    "env_skills": section(env_a, "Skills"),
    "platform_card": "GUIDES/platforms/salesforce.md",
    "platform_testing": " ".join(tap.group(1).split()) if tap else "",
    "revisit_block": "",
    "recent_commits": recent_commits("2449835"),
    "done_next": "issues test-spec for " + w1["id"], "stop_outcomes": "blocked",
    "last_summary": "prepare (done): " + prep["summary"],
    "source_results": [{"label": "plan", "path": "RUN/results/nav-723e52564fb0414fb9351ed4164c4a32.md"},
                       {"label": "prepare", "path": "RUN/results/nav-efea99357d1d42569d26ae3f529d51a5.md"},
                       {"label": "test-strategy", "path": "RUN/results/nav-088f95cdd24f443eb6f9ad95232a38dd.md"}],
    "last_accepted": "prepare, done, nav-efea99357d1d42569d26ae3f529d51a5",
})
import shlex
INSTALL = {"run": len(shlex.quote(RUN)), "root": len(shlex.quote(PLUG)), "cli": len(shlex.quote(CLI[len("python3 "):]))}
SP_LOCATORS = {"env_commands": "KNOWLEDGE/environment.md ## Commands", "spec_toc": "KNOWLEDGE/spec.md", "arch_toc": "KNOWLEDGE/architecture.md",
               "platform_testing": "GUIDES/platforms/salesforce.md", "last_summary": "RUN/results/nav-efea99357d1d42569d26ae3f529d51a5.md",
               "open_assumptions": "RUN/results/nav-723e52564fb0414fb9351ed4164c4a32.md, field assumptions",
               "env_skills": "KNOWLEDGE/environment.md ## Skills", "revisit_block": "the accepted step-plan result and the send-back result (RUN/results/)"}
# This run predates the T-D2 producer bounds: its plan wrote a 3,308-character context, which the plan gate would refuse
# at 2,500. The illustration renders the real value and says so (bound_overrides, reported in the render report).
# The concern rows are an illustration (A1 is not built) and also run over the 1,200 bound the plan gate would enforce.
concern_rows = "\n".join("- {}: {}; {} ({}; owner {})".format(*c) for c in CONCERNS if c[1] == "yes")
SP_OVERRIDES = {"item_context": max(2500, len(w1["context"])), "plan_concerns": max(1200, len(concern_rows))}
(out / "step-plan.values.json").write_text(json.dumps({"install": INSTALL, "locators": SP_LOCATORS,
                                                        "flags": {"loop_started": False, "loop_unavailable": False, "revisit": False, "inline": True, "worktree_run": True},
                                                        "bound_overrides": SP_OVERRIDES, "slots": sp_values}, indent=1))

# ---------------------------------------------------------------- implement S1 (revision 14)
home_b = inputs / "home-fcd65c9"
spec_b, arch_b, env_b = ((home_b / f).read_text() for f in ("spec.md", "architecture.md", "environment.md"))
s1 = sp["steps"][0]
crit = {c["id"]: c["text"] for c in sp["criteria"]}
named = sorted({int(n) for cid in s1["criteria"] for n in re.findall(r"R-(\d+)", crit[cid])})
spec3 = sections(spec_b, 3)


def first_sentences(text, n, limit):
    parts = re.split(r"(?<=[.!?])\s+", " ".join(text.split()))
    out = " ".join(parts[:n])
    return out if len(out) <= limit else out[: limit - 1].rsplit(" ", 1)[0] + "…"


def rule_text(heading_body):
    head, body = heading_body.split("\n", 1)
    body = body.split("Acceptance:")[0].strip()
    body = re.sub(r"^(Add|Change)\. ", "", body)
    body = re.sub(r"^Source: the request\. ", "", body)
    return head.strip()[4:] + ": " + first_sentences(body, 2, 300)


reqs_by_value = "\n".join(rule_text(spec3[h]) for h in spec3 if re.match(r"R-(\d+) ", h)
                          and int(re.match(r"R-(\d+) ", h).group(1)) in named)
arch3b = sections(arch_b, 3)


def decision_line(h, body):
    body = body.split("\n", 1)[1].strip()
    m = re.search(r"Choice: (.*?\.)( Why:|$)", body.replace("\n", " "))
    first = m.group(1) if m else re.split(r"(?<=\.) ", body.replace("\n", " "))[1]
    return h + ": " + first_sentences(first, 1, 200)


decisions_by_value = "\n".join(decision_line(h, arch3b[h]) for h in arch3b if h.startswith("AD-"))
commands = section(env_b, "Commands")
im_values = common("nav-2a6055a02c0845838f348ae058d7d65d", 14, "implement")
im_values.update({
    "lint_command": f"{CLI} lint --run-dir={RUN} --action=nav-2a6055a02c0845838f348ae058d7d65d",
    "progress": narrative("16-implement.packet.md"),
    "item_id": "W1", "step_id": s1["id"], "step_n": "1", "step_total": str(len(sp["steps"])),
    "step_task": s1["task"],
    "step_criteria": [{"id": c, "text": crit[c]} for c in s1["criteria"]],
    "step_criteria_ids": ", ".join(s1["criteria"]),
    "step_check": s1["check"],
    "step_deps": "none", "step_skills": "none", "accepted_steps": "none (S1 is the first step)",
    "test_spec_result": "RUN/results/nav-ec9a068812f245398a414b6fb80f4ea9.md",
    "recent_commits": recent_commits("fcd65c9"),
    "item_other_reqs": ", ".join(r for r in sp["follows"] if r.startswith("R-") and int(r[2:]) not in named) or "no other requirement",
    "send_back_target": "step-plan", "send_backs_left": "2 of 2",
    "done_next": "commits the step and issues step " + sp["steps"][1]["id"], "stop_outcomes": "blocked or send-back",
    "anchor_ids": ", ".join("R-%d" % n for n in named) + "; " + ", ".join(sorted({d for d in sp["follows"] if d.startswith("AD-")}, key=lambda x: int(x[3:]))),
    "later_steps": [{"id": s["id"], "criteria": ", ".join(s["criteria"]), "task_start": s["task"][:160].rsplit(" ", 1)[0] + "…"} for s in sp["steps"][1:]],
    "plan_result": "RUN/results/nav-03cbb489abfe48ce8bf8ab1cfb207729.md",
    "step_cases": [{"id": c["id"], "criterion": c["criterion"], "requirement": c.get("requirement", "")}
                   for c in ts["test_cases"] if c["criterion"] in s1["criteria"]],
    "step_requirements": reqs_by_value,
    "item_decisions": decisions_by_value,
    "arch_structure": section(arch_b, "Structure"),
    "env_commands": commands_code(section(env_b, "Commands")),
    "step_concerns": [{"concern": "state", "check": "S1 Proof; fleet, miss and hit at test"},
                      {"concern": "config", "check": "S1 Proof (sourceApiVersion 68.0)"},
                      {"concern": "security", "check": "S1 Proof (no System.debug); hiddenShips at test"}],
    "step_cards": [{"locator": "GUIDES/coding-practices.md#schema-and-storage (state)"}],
    "revisit_block": "",
    "fix_attempts": "7",
    "source_results": [{"label": "step-plan", "path": "RUN/results/nav-03cbb489abfe48ce8bf8ab1cfb207729.md"},
                       {"label": "test-spec", "path": "RUN/results/nav-ec9a068812f245398a414b6fb80f4ea9.md"},
                       {"label": "validate-existing", "path": "RUN/results/nav-366008403f6f4e4c806304d9afc97344.md"}],
    "last_accepted": "validate-existing, done, nav-366008403f6f4e4c806304d9afc97344",
})
IM_LOCATORS = {"step_requirements": "KNOWLEDGE/spec.md (R-n sections)", "item_decisions": "KNOWLEDGE/architecture.md ## Decisions",
               "arch_structure": "KNOWLEDGE/architecture.md ## Structure", "env_commands": "KNOWLEDGE/environment.md ## Commands",
               "step_concerns": "RUN/results/nav-03cbb489abfe48ce8bf8ab1cfb207729.md, field concerns",
               "step_cards": "GUIDES/coding-guidance.md (Conditional index)", "later_steps": "RUN/results/nav-03cbb489abfe48ce8bf8ab1cfb207729.md, field steps",
               "step_cases": "RUN/results/nav-ec9a068812f245398a414b6fb80f4ea9.md, field test_cases"}
# Over the T-D2 producer bounds in this pre-T-D2 run (step-plan would refuse them): S1's task and Proof, and its criteria.
crit_rows = "\n".join("  " + c + ": " + crit[c] for c in s1["criteria"])
IM_OVERRIDES = {k: n for k, n, b in (("step_task", len(s1["task"]), 700), ("step_check", len(s1["check"]), 600),
                                     ("step_criteria", len(crit_rows), 1200)) if n > b}
(out / "implement.values.json").write_text(json.dumps({"install": INSTALL, "locators": IM_LOCATORS,
                                                        "flags": {"loop_started": False, "loop_unavailable": False, "code_step": True, "revisit": False, "worktree_run": True},
                                                        "bound_overrides": IM_OVERRIDES, "slots": im_values}, indent=1))
print("overrides:", SP_OVERRIDES, IM_OVERRIDES)
print("named R-n for S1:", named)
print("sizes:", {k: len(json.dumps(v)) for k, v in im_values.items() if len(json.dumps(v)) > 600})
