#!/usr/bin/env python3
"""A scripted stand-in for the model, for checking ratchet.py without a model call.

    python3 ratchet.py run --case selftest --host fake --fake selftest_fake.py --output DIR
    python3 selftest_fake.py DIR        # then: assert what the run above must have recorded

It plays every stage on a two-function calculator and misbehaves on purpose, once in each way the script guards:

  plan N    writes the plan
  build 1   builds `add` wrongly (so the tests have something to find) and writes an acceptance file it must not write
  tests 1   writes the acceptance tests, and edits the product, which the test owner may not do
  fix 1     fixes `add`, and weakens a frozen acceptance test
  delta 1   adds clause C-3, and rewrites clause C-1, which no stage may do
  build 2   builds C-3;  tests 2 pins it;  delta 2 finds nothing
"""
import json
import re
import sys
from pathlib import Path

SPEC = """# Specification

## Use cases

### U-1: a caller adds two numbers and doubles the sum
Flow: double(add(2, 3)) gives 10
Source: request

## Clauses

### C-1: add(a, b) returns the sum of two numbers
Observable: require('./calc.js').add(2, 3) is 5
Source: request

### C-2: double(a) returns twice a number
Observable: require('./calc.js').double(4) is 8
Source: request
"""
TEST = ("const assert = require('node:assert');\nconst calc = require('../calc.js');\nassert.strictEqual({call}, {want});\n"
        "console.log('{ident} passed');\n")


def act(role, work, prompt, number):
    work = Path(work)
    ratchet = work / "ratchet"
    ratchet.mkdir(exist_ok=True)
    found = re.search(r"ratchet/(?:build|tests|delta)-(\d+)\.md", prompt)
    cycle = int(found.group(1)) if found else 1
    if role == "spec":
        (ratchet / "spec.md").write_text(SPEC)
    elif role == "plan":
        with (ratchet / "plan.md").open("a") as handle:
            handle.write("## Approach\none file\n## Decisions\nnone\n## Nuances\nnone\n## Build order\ncalc.js\n## How we will know\nrun it\n")
    elif role == "build" and cycle == 1:
        (work / "calc.js").write_text("exports.add = (a, b) => a - b;\nexports.double = (a) => a * 2;\n")
        (work / "acceptance").mkdir(exist_ok=True)
        (work / "acceptance" / "sneaky.test.js").write_text("// a builder may not write acceptance tests\n")
        (ratchet / "build-1.md").write_text("## Done\nC-1, C-2\n## Not done\nnone\n## Discoveries\n- none\n")
    elif role == "build":
        with (work / "calc.js").open("a") as handle:
            handle.write("exports.negate = (a) => -a;\n")
        (ratchet / f"build-{cycle}.md").write_text("## Done\nC-3\n## Not done\nnone\n## Discoveries\nnone\n")
    elif role == "tests":
        tests = work / "acceptance"
        tests.mkdir(exist_ok=True)
        manifest_file = ratchet / "acceptance.json"
        manifest = json.loads(manifest_file.read_text()) if manifest_file.exists() else {}
        cases = ({"C-1": ("calc.add(2, 3)", "5"), "C-2": ("calc.double(4)", "8"), "U-1": ("calc.double(calc.add(2, 3))", "10")}
                 if cycle == 1 else {"C-3": ("calc.negate(4)", "-4")})
        for ident, (call, want) in cases.items():
            name = ident.lower().replace("-", "") + ".test.js"
            (tests / name).write_text(TEST.format(call=call, want=want, ident=ident))
            manifest[ident] = {"command": f"node acceptance/{name}"}
        manifest_file.write_text(json.dumps(manifest, indent=1) + "\n")
        if cycle == 1:
            (work / "calc.js").write_text("exports.add = (a, b) => 99;\nexports.double = (a) => a * 2;\n")  # not the test owner's to change
        (ratchet / f"tests-{cycle}.md").write_text("## Failing now\n- C-1: add(2, 3) gave -1\n## Discoveries\n- none\n")
    elif role == "fix":
        (work / "calc.js").write_text("exports.add = (a, b) => a + b;\nexports.double = (a) => a * 2;\n")
        with (work / "acceptance" / "c2.test.js").open("a") as handle:
            handle.write("// weakened\n")  # frozen: the gate must put it back
        (ratchet / "fix-1.md").write_text("## Fixed\n- C-1: add subtracted\n## Disputed\nnone\n## Discoveries\nnone\n")
    elif role == "delta" and cycle == 1:
        text = (ratchet / "spec.md").read_text().replace("returns the sum of two numbers", "returns something")
        text += "\n### C-3: negate(a) returns the number with its sign changed\nObservable: negate(4) is -4\nSource: discovery: the tests' report\n"
        (ratchet / "spec.md").write_text(text)
        (ratchet / "delta-1.md").write_text("Used add and double.\n- C-3: product keeps to it: no\n")
    elif role == "delta":
        (ratchet / f"delta-{cycle}.md").write_text("No delta.\n")


def verify(out):
    out = Path(out)
    record = json.loads((out / "run.json").read_text())
    roles = [row["label"] for row in record["sessions"]]
    expect = ["spec-1", "plan-1", "build-1", "tests-1-1", "fix-1", "delta-1", "plan-2", "build-2", "tests-2-1", "delta-2"]
    assert roles == expect, roles
    assert record["stop"] == "converged" and record["final_pass"] is True and record["clauses"] == 3 and record["use_cases"] == 1, record
    assert any("sneaky.test.js" in line for line in record["tamper"]), record["tamper"]
    assert any("c2.test.js" in line for line in record["tamper"]), record["tamper"]
    assert {"role": "tests", "paths": ["calc.js"]} in record["reverted"], record["reverted"]
    assert record["spec_violations"] == [{"stage": "delta", "cycle": 1, "changed_existing": ["C-1"]}], record["spec_violations"]
    assert record["cycles"][0]["first_gate_failing"] == ["C-1", "U-1"], record["cycles"][0]
    assert record["cycles"][1]["first_gate_failing"] == [] and record["cycles"][1]["new_clauses"] == ["C-3"], record["cycles"][1]
    spec = (out / "work" / "ratchet" / "spec.md").read_text()
    assert "returns the sum of two numbers" in spec and "### C-3" in spec, spec
    assert "weakened" not in (out / "work" / "acceptance" / "c2.test.js").read_text()
    assert not (out / "work" / "acceptance" / "sneaky.test.js").exists()
    labels = [row["label"] for row in record["snapshots"]]
    assert labels[:4] == ["base", "spec", "plan-1", "build-1"] and labels[-1] == "final", labels
    print(f"selftest ok: {len(roles)} sessions, {len(record['gates'])} gates, {len(record['snapshots'])} snapshots")


if __name__ == "__main__":
    verify(sys.argv[1])
