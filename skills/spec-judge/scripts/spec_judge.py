#!/usr/bin/env python3
"""Grade a spec against the repository it describes: over-spec and under-spec.

    spec_judge.py sample --repo REPO --spec SPEC [--architecture FILE] --out DIR [--n 40] [--seed 1]
    spec_judge.py score --out DIR

`sample` does the mechanical half and draws the samples the judge verdicts:
it checks every requirement (`R-n`) cites `path:line` anchors that resolve in
REPO, then writes DIR/sample.json with N random requirement IDs, N test names
from the repository's own test files, N/2 source files and the architecture
checklist. The judging model follows prompts/judge.md and writes
DIR/verdicts.json. `score` checks every sampled item got exactly one verdict
and writes DIR/grade.json:

- over-spec  = the spec states what the repository does not support:
  unanchored requirements (mechanical) and sampled requirements judged
  wrong or partial;
- under-spec = the repository does or promises what the spec does not
  state: sampled tests, source files and README sections judged missing or
  partly covered (internal plumbing and non-requirement prose excluded);
- architecture = checklist items answered and true.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import subprocess
import sys
from pathlib import Path

ARCHITECTURE = [
    "entry points: where a request, command or input enters",
    "modules and the responsibility each owns",
    "data flow for the main use case, end to end",
    "key dependencies and what each is used for",
    "configuration: options, their sources and precedence",
    "error handling: how failures surface to a caller",
    "extension points and public contracts other code relies on",
    "conventions a change must follow (layering, naming, style)",
    "build, test and release: the commands and what they check",
    "decisions: non-obvious design choices and their rationale",
]
TEST_NAME = re.compile(r"""\b(?:it|test|describe)(?:\.\w+)?\(\s*(['"`])((?:(?!\1).){3,160})\1""")
TEST_FILE = re.compile(r"(^|/)(test|tests|__tests__|spec)/|\.(test|spec)\.[cm]?[jt]sx?$")


def test_names(repo: Path) -> list[dict]:
    files = subprocess.run(["git", "-C", str(repo), "ls-files"], capture_output=True, text=True).stdout.split()
    names = []
    for f in files:
        if TEST_FILE.search(f) and re.search(r"\.[cm]?[jt]sx?$", f):
            text = (repo / f).read_text(errors="replace")
            names += [{"test": m.group(2), "file": f} for m in TEST_NAME.finditer(text)
                      if not m.group(0).lstrip().startswith("describe")]
    return names


SOURCE = re.compile(r"\.(ts|tsx|js|jsx|mjs|cjs|py|go|rs)$")


def source_files(repo: Path) -> list[str]:
    files = subprocess.run(["git", "-C", str(repo), "ls-files"], capture_output=True, text=True).stdout.split()
    return [f for f in files if SOURCE.search(f) and not TEST_FILE.search(f)
            and not re.search(r"(^|/)(docs?|examples?|scripts|bench\w*|fixtures?)/|\.d\.ts$|config", f)]


def anchors(repo: Path, spec: str) -> dict:
    """Over-spec, mechanical: does every requirement cite path:line anchors that resolve?"""
    blocks = re.split(r"(?m)^(?=#+\s*R-\d+\b|\s*[-*]?\s*\**R-\d+\b)", spec)
    total = anchored = resolved = 0
    unanchored, broken = [], []
    for block in blocks:
        m = re.match(r"\s*#*\s*[-*]?\s*\**(R-\d+)", block)
        if not m:
            continue
        total += 1
        cites = re.findall(r"([\w./@-]+\.\w+):(\d+)(?:-(\d+))?", block)
        if not cites:
            unanchored.append(m.group(1))
            continue
        anchored += 1
        ok = True
        for path, start, end in cites:
            f = repo / path
            n = len(f.read_text(errors="replace").splitlines()) if f.is_file() else -1
            if n < 0 or int(start) > n + 1 or (end and int(end) > n + 1):
                ok = False
                broken.append(f"{m.group(1)} {path}:{start}")
        resolved += ok
    return {"requirements": total, "anchored": anchored, "all_anchors_resolve": resolved,
            "unanchored": unanchored[:30], "broken": broken[:30]}




def readme_sections(repo: Path) -> list[dict]:
    """README sections (heading + line), a primary source of purpose and requirements."""
    readme = next((p for p in sorted(repo.iterdir()) if p.name.lower().startswith("readme")), None)
    if readme is None:
        return []
    sections = []
    for number, line in enumerate(readme.read_text(errors="replace").splitlines(), 1):
        m = re.match(r"^#{1,4}\s+(.+)", line)
        if m:
            sections.append({"section": m.group(1).strip(), "at": f"{readme.name}:{number}"})
    return sections


def cmd_sample(args) -> int:
    rng = random.Random(args.seed)
    spec = args.spec.read_text()
    ids = sorted(set(re.findall(r"\bR-\d+\b", spec)), key=lambda s: int(s[2:]))
    if not ids:
        raise SystemExit(f"no requirement IDs (R-n) in {args.spec}")
    tests, sources, docs = test_names(args.repo), source_files(args.repo), readme_sections(args.repo)
    # Same-named tests in one file are one item to a judge: sample each (name, file) once.
    tests = list({(t["test"], t["file"]): t for t in tests}.values())
    sample = {"repo": str(args.repo.resolve()), "spec": str(args.spec.resolve()),
              "architecture_file": str(args.architecture.resolve()) if args.architecture else None,
              "requirements": sorted(rng.sample(ids, min(args.n, len(ids))), key=lambda s: int(s[2:])),
              "tests": rng.sample(tests, min(args.n, len(tests))),
              "sources": sorted(rng.sample(sources, min(max(1, args.n // 2), len(sources)))),
              "readme": rng.sample(docs, min(max(1, args.n // 2), len(docs))) if docs else [],
              "architecture": ARCHITECTURE,
              "totals": {"requirements": len(ids), "tests": len(tests), "sources": len(sources),
                         "readme_sections": len(docs)},
              "anchors": anchors(args.repo, spec)}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "sample.json").write_text(json.dumps(sample, indent=2) + "\n")
    print(json.dumps({"sampled": {k: len(sample[k]) for k in ("requirements", "tests", "sources", "readme", "architecture")},
                      "totals": sample["totals"], "anchors": {k: v for k, v in sample["anchors"].items()
                                                               if not isinstance(v, list)}}))
    return 0


def cmd_score(args) -> int:
    sample = json.loads((args.out / "sample.json").read_text())
    verdicts = json.loads((args.out / "verdicts.json").read_text())
    # Tests are keyed by name and file: the same name often appears in several files.
    keys = {"requirements": ("id", sample["requirements"]),
            "tests": (("test", "file"), [(t["test"], t["file"]) for t in sample["tests"]]),
            "sources": ("file", sample["sources"]),
            "readme": ("section", [d["section"] for d in sample["readme"]]),
            "architecture": ("item", sample["architecture"])}
    problems, tallies = [], {}
    for section, (key, wanted) in keys.items():
        got = [tuple(v.get(k) for k in key) if isinstance(key, tuple) else v.get(key)
               for v in verdicts.get(section, [])]
        missing = [w for w in wanted if got.count(w) < wanted.count(w)]
        duplicated = sorted({g for g in got if got.count(g) > wanted.count(g)}, key=str)
        if missing:
            problems.append(f"{section}: no verdict for {missing[:5]}")
        if duplicated:
            problems.append(f"{section}: more than one verdict for {duplicated[:5]}")
        tallies[section] = {}
        for v in verdicts.get(section, []):
            tallies[section][v.get("verdict")] = tallies[section].get(v.get("verdict"), 0) + 1
    req, tst, src, doc, arc = (tallies[k] for k in ("requirements", "tests", "sources", "readme", "architecture"))
    anchors_ = sample["anchors"]

    def share(part: int, whole: int) -> float:
        return round(part / whole, 3) if whole > 0 else 0.0

    grade = {
        "complete": not problems, "problems": problems, "totals": sample["totals"], "tallies": tallies,
        "over_spec": {
            "unanchored": share(anchors_["requirements"] - anchors_["anchored"], anchors_["requirements"]),
            "broken_anchors": share(anchors_["anchored"] - anchors_["all_anchors_resolve"], anchors_["requirements"]),
            "unsupported": share(req.get("wrong", 0) + req.get("partial", 0),
                                 len(sample["requirements"]) - req.get("unverifiable", 0))},
        "under_spec": {
            "tests_missing": share(tst.get("missing", 0) + tst.get("partly", 0),
                                   len(sample["tests"]) - tst.get("internal", 0)),
            "sources_missing": share(src.get("missing", 0) + src.get("partly", 0),
                                     len(sample["sources"]) - src.get("internal", 0)),
            "readme_missing": share(doc.get("missing", 0) + doc.get("partly", 0),
                                    len(sample["readme"]) - doc.get("not-a-requirement", 0))},
        # Orthogonality: the spec must survive a stack change, the architecture a spec change.
        "leakage": {
            "spec_names_implementation": share(sum(1 for v in verdicts.get("requirements", []) if v.get("leaks")),
                                               len(sample["requirements"])),
            "architecture_restates_behaviour": share(sum(1 for v in verdicts.get("architecture", [])
                                                         if v.get("restates_behaviour")), len(sample["architecture"]))},
        "architecture_true": share(arc.get("answered-true", 0), len(sample["architecture"]))}
    (args.out / "grade.json").write_text(json.dumps(grade, indent=2) + "\n")
    print(json.dumps(grade))
    return 0 if grade["complete"] else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample")
    s.add_argument("--repo", type=Path, required=True)
    s.add_argument("--spec", type=Path, required=True)
    s.add_argument("--architecture", type=Path)
    s.add_argument("--out", type=Path, required=True)
    s.add_argument("--n", type=int, default=40)
    s.add_argument("--seed", type=int, default=1)
    c = sub.add_parser("score")
    c.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    return cmd_sample(args) if args.cmd == "sample" else cmd_score(args)


if __name__ == "__main__":
    raise SystemExit(main())
