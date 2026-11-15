"""Check R08's pinned evidence and plan links; this executes no runtime tests.

Run from any checkout containing these documents: python3 -B <this-file>.
The source map intentionally detects drift from its recorded implementation.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
from urllib.parse import unquote

EVIDENCE = Path(__file__).resolve().parent
REPO = EVIDENCE.parents[2]
PLAN = REPO / "docs/shiploop-implement-step-fix-plan-2026-10-17.md"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    source = json.loads((EVIDENCE / "source-map.json").read_text())
    revision = source["source_head"]
    rows = source["recommendations"]
    assert [row["id"] for row in rows] == [f"R{i:02}" for i in range(1, 23)]
    assert {row["id"] for row in source["considerations_and_rules"]} == (
        {f"C{i}" for i in range(1, 9)} | {f"CC{i}" for i in range(1, 15)})
    assert source["schedule"]["id"] == "Improve-schedule"
    anchors = [a for row in [*rows, source["schedule"]] for a in row["anchors"]]
    anchors += [row["anchor"] for row in source["considerations_and_rules"]]
    files = {}
    for anchor in anchors:
        path = anchor["path"]
        if path not in files:
            current = (REPO / path).read_bytes()
            pinned = subprocess.check_output(["git", "-C", str(REPO), "show", f"{revision}:{path}"])
            assert current == pinned, ("working/pinned mismatch", path)
            files[path] = current
        raw = files[path]
        assert digest(raw) == anchor["source_sha256"], path
        lines = raw.decode().splitlines(keepends=True)
        assert 1 <= anchor["start"] <= anchor["end"] <= len(lines), path
        excerpt = "".join(lines[anchor["start"] - 1:anchor["end"]])
        assert excerpt == anchor["excerpt"] and digest(excerpt.encode()) == anchor["excerpt_sha256"], path
        assert anchor["revision"] == revision, path

    text = PLAN.read_text()
    assert text.startswith("Execute: ask\n")
    assert re.findall(r"^### (R\d\d) —", text, re.M) == [row["id"] for row in rows]
    assert re.findall(r"^\| (T\d+) \|", text, re.M) == [f"T{i}" for i in range(1, 53)]
    links = 0
    for document in [PLAN, EVIDENCE / "README.md"]:
        content = document.read_text()
        assert len(re.findall(r"^```", content, re.M)) % 2 == 0, document
        for target in re.findall(r"\]\(([^\s)]+)\)", content):
            if target.startswith(("https://", "http://", "mailto:")):
                continue
            path, _, fragment = unquote(target).partition("#")
            destination = (document.parent / path).resolve() if path else document
            assert destination.is_file(), (document.name, target)
            if re.fullmatch(r"L\d+", fragment):
                assert 1 <= int(fragment[1:]) <= len(destination.read_text().splitlines()), target
            elif fragment and destination.suffix == ".md":
                headings = {re.sub(r"[^\w\- ]", "", h.lower()).replace(" ", "-")
                            for h in re.findall(r"^#+ (.+)$", destination.read_text(), re.M)}
                assert fragment in headings, target
            links += 1

    outcomes = json.loads((EVIDENCE / "worker/outcomes.json").read_text())
    for result in outcomes:
        prefix = EVIDENCE / "worker" / Path(result["log_prefix"]).name
        raw = prefix.with_suffix(".stdout").read_text() + prefix.with_suffix(".stderr").read_text()
        assert re.search(r"Ran " + str(result["tests"]) + r" tests? in", raw), prefix
        if result["exit_code"] == 0:
            assert re.search(r"^OK$", raw, re.M), prefix
        else:
            assert "FAILED (" in raw, prefix
            for key in ("failures", "errors"):
                if result[key]:
                    assert f"{key}={result[key]}" in raw, prefix
    red = [r for r in outcomes if Path(r["log_prefix"]).name in ("fail-first-0", "fail-first-corrected")]
    green = [r for r in outcomes if r["exit_code"] == 0]
    assert sum(r["failures"] for r in red) == 20 and not any(r["errors"] for r in red)
    assert sum(r["tests"] for r in green) == 9
    final = json.loads((EVIDENCE / "acceptance.json").read_text())
    assert final["source_head"] == revision and final["status"] == "PASS"
    assert len(final["suites"]) == 9 and len(final["independent_checks"]) == 3
    assert len(final["selected_checks"]) == 8
    assert sum(sum(r["tests"]) for r in final["selected_checks"]) == 121
    for result in final["suites"] + final["selected_checks"] + final["independent_checks"]:
        assert result["exit_code"] == 0, result["command"]
        raw = (EVIDENCE / result["stdout"]).read_text() + (EVIDENCE / result["stderr"]).read_text()
        if result in final["suites"] + final["selected_checks"]:
            assert [int(n) for n in re.findall(r"Ran (\d+) tests? in", raw)] == result["tests"], result["command"]
            assert result["tests"] and re.search(r"^OK(?: \(.*\))?$", raw, re.M), result["command"]
    identity = json.loads((EVIDENCE / "source-identity.json").read_text())
    assert identity["source_head"] == revision
    for name, snapshot in identity["snapshots"].items():
        assert snapshot["head_before"] == snapshot["head_after"]
        assert snapshot["status_before"] == snapshot["status_after"] == ""
        assert snapshot["hashes_unchanged"] and snapshot["tracked_source_files"] >= 5590
    assert identity["snapshots"]["release"]["head_before"] == revision
    invariant = identity["invariance"]
    old = invariant["earlier_head"]
    assert old == identity["snapshots"]["earlier"]["head_before"]
    assert invariant["current_head"] == revision
    tested = invariant["latest_tested_head"]
    assert tested == identity["snapshots"]["current"]["head_before"]
    tree = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", f"{revision}:skills/shiploop/scripts"]).decode().strip()
    assert tree == invariant["runtime_scripts_tree"]
    assert len(invariant["r08_changed_paths"]) == 11
    for row in invariant["unchanged_files"] + invariant["lint_verified_files"]:
        raw = subprocess.check_output(["git", "-C", str(REPO), "show", f"{revision}:{row['path']}"])
        assert digest(raw) == row["sha256"], row["path"]
    repair = identity["test_repair"]
    assert repair["hashes_unchanged"] and repair["tracked_source_files"] >= 12403
    for row in repair["final_files"]:
        assert digest((REPO / row["path"]).read_bytes()) == row["sha256"]
    lint_head = identity["snapshots"]["lint"]["head_before"]
    integration = identity["snapshots"]["integration"]["head_before"]
    assert repair["base_head"] == integration
    for result in final["suites"] + final["selected_checks"] + final["independent_checks"]:
        assert result["source_head"] in (old, tested, revision, integration, lint_head)
        receipt = json.loads((EVIDENCE / result["receipt"]).read_text())
        assert receipt["status"] == "PASS" and receipt["exit_code"] == result["exit_code"]
        assert receipt["command"] == result["command"]
        assert receipt["unittest_totals"] == result["tests"]
        if result in final["selected_checks"] + final["independent_checks"]:
            assert result["source_head"] in (tested, revision, integration, lint_head)
    assert json.loads((EVIDENCE / "review/final-review-exit.json").read_text())["exit_code"] == 0
    assert (EVIDENCE / "review/final-review.md").read_text().strip()
    print(json.dumps({"result": "PASS", "source_head": revision, "recommendations": 22,
                      "considerations": 8, "craft_rules": 14, "acceptance_references": 52,
                      "verified_anchors": len(anchors), "verified_files": len(files),
                      "verified_local_links": links, "new_methods": 9, "affected_full_suites": 9, "additional_selected_method_executions": 121,
                      "full_suite_tests": sum(sum(r["tests"]) for r in final["suites"]),
                      "scope": "Document, source and retained receipt consistency; no new runtime execution",
                      "visual_render_checked": False}, indent=2))


if __name__ == "__main__":
    main()
