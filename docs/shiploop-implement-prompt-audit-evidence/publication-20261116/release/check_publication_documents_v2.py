"""Read-only evidence, current-source excerpt and Markdown-link audit."""
from pathlib import Path
from urllib.parse import unquote
import ast
import hashlib
import json
import re
import subprocess
import sys

repo = Path(sys.argv[1]).resolve()
packet = repo / "docs/shiploop-implement-prompt-audit-evidence/publication-20261116"
plan_path = repo / "docs/shiploop-implement-step-fix-plan-2026-10-17.md"


def git(*args):
    return subprocess.check_output(["git", "-C", str(repo), *args])


def read(path):
    return json.loads((packet / path).read_text())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


verification = read("verification.json")
assert verification["status"] == "PUBLISHED_VERIFIED"
release = verification["release"]
head = release["head"]
assert git("rev-parse", head + "^{tree}").decode().strip() == release["tree"]
assert verification["publication"]["head"] == head
assert verification["publication"]["status"] == "pushed"
assert verification["package"]["status"] == verification["native_install"]["status"] == "PASS"
assert verification["checkout_round"]["status"] == "PASS"
assert verification["checkout_round"]["checks_passed"] == verification["checkout_round"]["checks_required"] == 5
for key in ("candidate", "main"):
    run = verification["ci"][key]
    assert run["status"] == "PASS" and run["head"] == head and run["tier"] == "full"
    assert run["attempt"] == 1 and run["required_suite_omissions"] == 0
    assert run["executions"] == run["distinct_suites"] + run["repeated_suites"]
    assert run["jobs"] == len(run["groups"]) + 7
    assert run["artifacts"] == len(run["groups"]) + 4
    assert run["url"] == f"https://github.com/whichguy/skill-craft/actions/runs/{run['id']}"
assert verification["ci"]["candidate"]["event"] == "workflow_dispatch"
assert verification["ci"]["main"]["event"] == "push"

mapping = read("source-map.json")
assert mapping["source_head"] == head and mapping["source_tree"] == release["tree"]
assert [r["id"] for r in mapping["recommendations"]] == [f"R{i:02}" for i in range(1, 23)]
assert {r["id"] for r in mapping["considerations_and_rules"]} == (
    {f"C{i}" for i in range(1, 9)} | {f"CC{i}" for i in range(1, 15)})
assert [r["id"] for r in mapping["t_acceptance_crosswalk"]] == [f"T{i}" for i in range(1, 53)]
anchors = [a for row in mapping["recommendations"] + [mapping["schedule"], mapping["qualification_transport"]]
           for a in row["anchors"]] + [row["anchor"] for row in mapping["considerations_and_rules"]]
sources = {}
for anchor in anchors:
    path = anchor["path"]
    if path not in sources:
        sources[path] = git("show", head + ":" + path)
        assert sources[path] == (repo / path).read_bytes(), path
    raw = sources[path]
    lines = raw.decode().splitlines(keepends=True)
    assert 1 <= anchor["start"] <= anchor["end"] <= len(lines), anchor
    excerpt = "".join(lines[anchor["start"] - 1:anchor["end"]])
    assert excerpt == anchor["excerpt"], (path, anchor["symbol"])
    assert sha(excerpt.encode()) == anchor["excerpt_sha256"]
    assert sha(raw) == anchor["source_sha256"] and anchor["revision"] == head
assert mapping["coverage"]["anchor_count"] == len(anchors)
assert mapping["coverage"]["source_file_count"] == len(sources)
comparison = read("anchor-changes.json")
assert comparison["current_source"] == head
assert comparison["old_anchor_count"] == 234
assert comparison["new_anchor_count"] == len(anchors)
assert comparison["old_anchor_count"] - comparison["deleted"] + comparison["added_replacements"] == len(anchors)
assert comparison["exact_excerpts_retained"] + comparison["materially_changed"] + comparison["deleted"] == 234
r13 = next(row for row in mapping["recommendations"] if row["id"] == "R13")
assert any("multibyte" in str(value) or "long" in str(value) for value in r13["acceptance"])
assert any("RUN/fields" in str(value) or "safe" in str(value) for value in r13["acceptance"])
assert any("Plan graph format" in a["symbol"] and "Plan graph format" in a["excerpt"] for a in r13["anchors"])
assert any("backchain_passes" in a["excerpt"] and "BACKCHAIN_PASSES_REASON" in a["excerpt"] for a in r13["anchors"])
pair = next(a for a in anchors if a["symbol"] == "answer_key and matching_yes")
for name in ("answer_key", "matching_yes"):
    nodes = [n for n in ast.parse(sources[pair["path"]].decode()).body
             if isinstance(n, ast.FunctionDef) and n.name == name]
    assert len(nodes) == 1 and pair["start"] <= nodes[0].lineno <= nodes[0].end_lineno <= pair["end"]
for symbol in ("CodexHost.argv", "CodexHost.prepare"):
    anchor = next(a for a in anchors if a["symbol"] == symbol)
    classes = [n for n in ast.parse(sources[anchor["path"]].decode()).body
               if isinstance(n, ast.ClassDef) and n.name == "CodexHost"]
    assert len(classes) == 1
    methods = [n for n in classes[0].body if isinstance(n, ast.FunctionDef) and n.name == symbol.split(".")[1]]
    assert len(methods) == 1 and (anchor["start"], anchor["end"]) == (methods[0].lineno, methods[0].end_lineno)

continuity = read("source-continuity.json")
assert continuity["release_source"] == head and len(continuity["prior_evidence"]) == 6
for row in continuity["prior_evidence"]:
    current = git("rev-parse", "HEAD:" + row["path"]).decode().strip()
    assert current == row["before_tree"] == row["release_tree"], row["path"]

assert read("attempts/source-preflight/handoff.json")["status"] == "FAIL"
assert read("attempts/source-release-validation/handoff.json")["status"] == "INCOMPLETE"
assert read("attempts/corrected-local-validation/handoff.json")["status"] == "INCOMPLETE"
assert read("retirement-source-qualification/handoff.json")["status"] == "FAIL"
assert read("retirement-source-qualification/handoff.json")["behavior_method_executions_passed"] == 75
assert read("retirement-mock-audit/handoff.json")["status"] == "PASS"
original_ci = read("attempts/candidate-full-ci/handoff.json")
assert original_ci.get("status", original_ci.get("result")) == "FAIL"
forward_ci = read("attempts/forward-release-full-ci/handoff.json")
assert forward_ci["status"] == "FAIL"
repair = read("card-metadata-fixture-repair/qualification-v1/handoff.json")
assert repair["red"]["failures"] == 1 and repair["red"]["errors"] == 0
assert repair["green"]["tests"] == 1 and repair["green"]["failures"] == repair["green"]["errors"] == 0
assert len(repair["controls"]) == 7 and repair["verification"]["other_164_methods_ast_identical"]
assert repair["verification"]["test_count_before"] == repair["verification"]["test_count_after"] == 165
assert read("card-fixture-local-validation/handoff.json")["status"] == "PASS"
assert continuity["generated_release"] == release["generated_release"]
assert continuity["post_generation_delta"] == []
assert release["head"] == release["generated_release"]
assert read("attempts/published-main-full-ci/handoff.json")["status"] == "FAIL"
assert verification["harness_repair"]["status"] == "PASS"
assert "CHANGES_REQUIRED" in (packet / "attempts/harness-timeout-source-review/review.md").read_text()
assert (packet / "harness-timeout-source-review-followup/review.md").read_text().startswith("**APPROVE**")
assert (packet / "preflight-review/review.md").read_text().startswith("APPROVE")
assert (packet / "fixture-review/review.md").read_text().startswith("APPROVE")

plan = plan_path.read_text()
assert len(re.findall(r"^### R\d\d\b", plan, re.M)) == 22
assert len(re.findall(r"^\| T\d+ \|", plan, re.M)) == 52
assert "P1, next | R15" in plan and "R17 can land independently" in plan
assert "Published on 2026-11-16" in plan and "source implementations pending publication" not in plan
assert "standalone Backchain skill to select" in plan
for kind in ("candidate", "main"):
    assert verification["ci"][kind]["url"] in plan

local_links = source_links = 0
for document in (plan_path, packet / "README.md"):
    for label, raw_target in re.findall(r"\[([^\]]*)\]\(([^)]+)\)", document.read_text()):
        if "://" in raw_target:
            continue
        target, _, fragment = unquote(raw_target.strip("<>")).partition("#")
        destination = (document.parent / target).resolve() if target else document
        assert destination.exists(), (document.name, raw_target)
        if fragment.startswith("L") and fragment[1:].isdigit():
            line = int(fragment[1:])
            assert 1 <= line <= len(destination.read_text().splitlines()), raw_target
            if destination.is_relative_to(repo):
                relative = str(destination.relative_to(repo))
                if relative.startswith(("skills/", "test/")):
                    assert any(a["path"] == relative and a["start"] <= line <= a["end"] for a in anchors), raw_target
                    visible = re.match(r"[^:]+:(\d+)\s", label)
                    if visible:
                        assert int(visible[1]) == line, (label, raw_target)
                    source_links += 1
        elif fragment:
            headings = {re.sub(r"[^\w\- ]", "", value.lower()).replace(" ", "-")
                        for value in re.findall(r"^#+ (.+)$", destination.read_text(), re.M)}
            assert fragment in headings, (document.name, raw_target)
        local_links += 1

for row in read("copied-evidence.json")["files"]:
    path = packet / row["path"]
    assert path.is_file() and sha(path.read_bytes()) == row["sha256"], row["path"]
for row in read("external-evidence.json")["files"]:
    path = Path(row["path"])
    assert path.is_file() and sha(path.read_bytes()) == row["sha256"], row["path"]
print(json.dumps({"status": "PASS", "release_source": head, "anchors": len(anchors),
    "source_files": len(sources), "recommendations": 22, "considerations": 8, "code_craft_rules": 14,
    "acceptance_rows": 52, "local_links": local_links, "source_links": source_links,
    "historical_evidence_unchanged": True, "failed_attempts_retained": True,
    "plan_sha256": sha(plan_path.read_bytes()), "readme_sha256": sha((packet / "README.md").read_bytes())}, indent=2))
