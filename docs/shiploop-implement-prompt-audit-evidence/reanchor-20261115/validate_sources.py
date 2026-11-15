"""Validate this audit's pinned source map and document links, not runtime behavior.

Run from any checkout containing these documents: python3 -B <this-file>.
Prints a JSON receipt; does not alter the repository or its evidence files.
"""
from pathlib import Path
import ast
import hashlib
import json
import re
import subprocess
from urllib.parse import unquote


EVIDENCE = Path(__file__).resolve().parent
REPO = EVIDENCE.parents[2]
PLAN = REPO / "docs/shiploop-implement-step-fix-plan-2026-10-17.md"
SCHEDULE = REPO / "docs/shiploop-improve-schedule-proposal-2026-10-25.md"


def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args])


def digest(value):
    return hashlib.sha256(value).hexdigest()


def heading_ids(text):
    ids = set()
    for heading in re.findall(r"^#+ (.+)$", text, re.M):
        heading = re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
        ids.add(heading)
    return ids


def main():
    source = json.loads((EVIDENCE / "source-map.json").read_text())
    revision = source["source_head"]
    initial = source["initial_source_head"]
    rows = source["recommendations"]
    assert [row["id"] for row in rows] == [f"R{i:02}" for i in range(1, 23)]
    groups = source["considerations_and_rules"]
    assert {group["id"] for group in groups} == (
        {f"C{i}" for i in range(1, 9)} | {f"CC{i}" for i in range(1, 15)})
    assert source["schedule"]["id"] == "Improve-schedule"
    anchors = []
    for row in [*rows, source["schedule"]]:
        assert row["acceptance"] and row["anchors"] and row["remaining_action"], row["id"]
        anchors.extend(row["anchors"])
    anchors.extend(group["anchor"] for group in groups)
    files = {}
    for anchor in anchors:
        path = anchor["path"]
        current = (REPO / path).read_bytes()
        pinned = git("show", f"{revision}:{path}")
        assert current == pinned, ("working/pinned mismatch", path)
        assert digest(current) == anchor["source_sha256"], path
        lines = current.decode().splitlines(keepends=True)
        assert 1 <= anchor["start"] <= anchor["end"] <= len(lines), path
        excerpt = "".join(lines[anchor["start"] - 1:anchor["end"]])
        assert excerpt == anchor["excerpt"] and digest(excerpt.encode()) == anchor["excerpt_sha256"], path
        assert anchor["revision"] == revision, path
        files[path] = digest(current)
    for commit in source["history_read"]:
        git("cat-file", "-e", commit + "^{commit}")

    text = PLAN.read_text()
    assert re.findall(r"^### (R\d\d) —", text, re.M) == [row["id"] for row in rows]
    assert re.findall(r"^\| (T\d+) \|", text, re.M) == [f"T{i}" for i in range(1, 53)]
    assert text.startswith("Execute: ask\n")
    local_links = 0
    for document in [PLAN, SCHEDULE]:
        content = document.read_text()
        assert len(re.findall(r"^```", content, re.M)) % 2 == 0, document
        for target in re.findall(r"\]\(([^\s)]+)\)", content):
            if target.startswith(("https://", "http://", "mailto:")):
                continue
            path, _, fragment = unquote(target).partition("#")
            destination = (document.parent / path).resolve() if path else document
            assert destination.is_file(), (document.name, target)
            if re.fullmatch(r"L\d+", fragment):
                assert int(fragment[1:]) <= len(destination.read_text().splitlines()), target
            elif fragment and destination.suffix == ".md":
                assert fragment in heading_ids(destination.read_text()), (target, heading_ids(destination.read_text()))
            local_links += 1

    loops = (REPO / "skills/shiploop/scripts/shiploop_loops.py").read_text()
    syntax = ast.parse(loops)
    work = next(ast.literal_eval(node.value) for node in syntax.body
                if isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "WORK_STEP" for t in node.targets))
    proposed = ("Implement step {step}: satisfy {criteria}{serving} under {decisions}.\n"
                "Do duty items {items} of {run}/packets/{action}.md.\n"
                "Write no tests and start no later step.")
    assert len(work) == 364 and work in text
    assert len(proposed) == 161 and proposed in text
    prompts = (REPO / "skills/shiploop/scripts/shiploop_prompts.py").read_text()
    navigator = (REPO / "skills/shiploop/scripts/shiploop_navigator.py").read_text()
    for literal in ["Across every executed work item's change, trace\neach new or changed public entry point with a valid, a boundary and an invalid\ninput",
                    "release-check runs it once before the real deploy to prove it tells them apart",
                    'save its "not there yet" output']:
        assert " ".join(literal.split()) in " ".join(prompts.split()), literal
    assert "No push, deploy, install or credential access." in navigator
    protocol = ast.parse((REPO / "skills/shiploop/scripts/shiploop_protocol.py").read_text())
    message = "ShipLoop committed these files that were left uncommitted (no action needed): "
    assert any(isinstance(node, ast.Constant) and node.value == message for node in ast.walk(protocol))
    assert message in text

    tests = json.loads((EVIDENCE / "test-receipt.json").read_text())
    assert tests["expected_head"] == initial
    totals = []
    for check in tests["checks"]:
        assert check["exit_code"] == 0
        raw = (EVIDENCE / check["stdout"]).read_text() + (EVIDENCE / check["stderr"]).read_text()
        counts = [int(n) for n in re.findall(r"Ran (\d+) tests? in", raw)]
        assert counts == check["observed_unittest_totals"], check["command"]
        assert re.search(r"^OK$", raw, re.M), check["command"]
        totals.extend(counts)
    assert sum(totals) == 97
    assert tests["source_unchanged"] and not tests["pending_commands"] and tests["retries"] == 0
    unchanged = {}
    for path in ["skills", "test"]:
        before = git("rev-parse", f"{initial}:{path}").decode().strip()
        after = git("rev-parse", f"{revision}:{path}").decode().strip()
        assert before == after, path
        unchanged[path] = after
    probes = json.loads((EVIDENCE / "probe-results.json").read_text())
    assert probes["revision"] == initial
    assert all(c["verdict"]["status"] == "passed" for c in probes["cases"] if c["scenario"] == "mixed_pass_error")
    assert probes["candidate_old_verdict"]["reused"] and probes["step_old_verdict"]["reused"]
    assert probes["full_packet"]["whole_body_preserved"]
    print(json.dumps({"result": "PASS", "source_head": revision, "execution_revision": initial,
                      "recommendations": len(rows), "schedule": 1, "considerations": 8,
                      "craft_rules": 14, "acceptance_references": 52, "verified_anchors": len(anchors),
                      "verified_files": len(files), "verified_local_links": local_links,
                      "verified_decision_commits": len(source["history_read"]), "selected_tests": sum(totals),
                      "unchanged_execution_trees": unchanged, "work_characters": [len(work), len(proposed)],
                      "visual_render_checked": False,
                      "scope": "Document/source consistency and retained receipts; no additional runtime or live acceptance"}, indent=2))


if __name__ == "__main__":
    main()
