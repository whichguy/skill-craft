"""Rerun prompts built from the implemented ShipLoop text (worktree module), for the before/after comparison."""
import sys, json, pathlib, re, os
W = pathlib.Path(os.environ["SHIPLOOP_WT"]); SK = W / "skills" / "shiploop"
sys.path.insert(0, str(SK / "scripts"))
import shiploop_navigator_v3_prompts as p
assert "Compose before you build" in p.CODE_CRAFT and "State and information lifecycle" in p.INTERACTION_DESIGN
assert "record the open questions of its interaction" in p.DUTIES["intake"] and "primary-documentation source" in p.PLANNING_REVIEW_FOCUS
O = pathlib.Path("after/prompts")
# R0 code composition: reuse the E0 prompt shapes with the implemented CODE_CRAFT.
C = pathlib.Path("../compose-exp/prompts")
for s in ("S1", "S2"):
    base = (C / f"{s}-A.txt").read_text()
    start = base.index("Code craft. Write"); end = base.index("Return every file")
    (O / f"R0_{s}.txt").write_text(base[:start] + p.CODE_CRAFT + base[end:])
# R3 intake.
RT3 = {"GAS": "Google Apps Script web app project (clasp signed in, Workspace domain)", "SF": "Salesforce DX project with a connected org (LWC UI)", "CF": "Cloudflare Workers project (wrangler signed in)"}
for rt, env in RT3.items():
    old = pathlib.Path(f"prompts3/{rt}_intake_current.txt").read_text()
    i = old.index("Intake duty:\n") + len("Intake duty:\n"); j = old.index("Return the intake result")
    (O / f"R3_{rt}.txt").write_text(old[:i] + p.DUTIES["intake"] + old[j:])
# R4/R5 architecture: invite and solo with the implemented INTERACTION_DESIGN.
src = pathlib.Path("build4.py").read_text()
TASK = pathlib.Path("build.py").read_text().split('TASK = """')[1].split('"""')[0]
ns = {}; exec(src.split("LIFE2 =")[0].split("RUNTIMES =", 1)[0], ns)
RUNTIMES = eval(src.split("RUNTIMES = ")[1].split("\n}\n")[0] + "\n}")
REQ = eval(src.split("REQ = ")[1].split("\n}\n")[0] + "\n}")
for rt, env in RUNTIMES.items():
    for q in ("solo", "invite"):
        (O / f"R45_{rt}_{q}.txt").write_text(TASK.format(req=REQ[q], env=env, guide=p.INTERACTION_DESIGN))
# R6b planning review with the implemented focus.
errs = json.load(open("errors6b.json"))
for stem in errs:
    old = pathlib.Path(f"prompts6b/{stem}__focus-current.txt").read_text()
    (O / f"R6b_{stem}.txt").write_text(old.replace(p.PLANNING_REVIEW_FOCUS.replace(
        "- a claim about what the runtime, platform or a library can do that a decision\n  depends on, with no primary-documentation source or probe result: check it,\n  and correct the plan where it is wrong;\n", ""), p.PLANNING_REVIEW_FOCUS))
    assert "primary-documentation source" in (O / f"R6b_{stem}.txt").read_text()
# R7 layered GAS fixture, current wording, linking the implemented card.
old = pathlib.Path("prompts7/gas_current.txt").read_text()
old = re.sub(r"\S*/skills/shiploop(?=/references)", str(SK), old)
i = old.index("Discovery duty:\n") + len("Discovery duty:\n"); j = old.index("\nGuides named in this packet")
new = old[:i] + p.DUTIES["discovery"] + "\n" + p.INTERACTION_DESIGN + old[j:]
(O / "R7_gas.txt").write_text(new)
assert str(SK / "references/platforms/apps-script.md") in new
print(sorted(x.name for x in O.iterdir()))
