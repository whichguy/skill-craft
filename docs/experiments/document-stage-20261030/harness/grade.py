"""Score one document-stage arm against its scenario's planted defects (deterministic checks only).

    python3 -I grade.py <arm dir> [<arm dir> ...]   # arm dir holds worktree/, run/ and arm.json {"scenario": ...}

Each check is a named boolean; `bloat` numbers are reported, not scored.  The judge pass grades what regexes cannot.
"""

import json
import re
import subprocess
import sys
from pathlib import Path


def sh(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True)


def added_lines(tree, path):
    out = sh(f"git diff --no-color -U0 HEAD -- '{path}'", tree).stdout
    if not out and not (tree / path).exists():
        return []
    if not out:  # untracked file: every line is added
        tracked = sh(f"git ls-files --error-unmatch '{path}'", tree).returncode == 0
        return [] if tracked else (tree / path).read_text().splitlines()
    return [l[1:] for l in out.splitlines() if l.startswith("+") and not l.startswith("+++")]


def removed_lines(tree, path):
    out = sh(f"git diff --no-color -U0 HEAD -- '{path}'", tree).stdout
    return [l[1:] for l in out.splitlines() if l.startswith("-") and not l.startswith("---")]


def read(tree, rel):
    p = tree / rel
    return p.read_text() if p.exists() else ""


def jsdoc_before(text, anchor):
    """The JSDoc block (or comment lines) directly above the first line matching ``anchor``."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.search(anchor, line):
            j, block = i - 1, []
            while j >= 0 and (lines[j].strip().startswith(("*", "/**", "//", "*/")) or lines[j].strip() == ""):
                if lines[j].strip() == "" and block:
                    break
                block.insert(0, lines[j])
                j -= 1
            return "\n".join(block)
    return ""


def common(tree, run):
    checks, info = {}, {}
    checks["tests_pass"] = sh("npm test", tree).returncode == 0
    checks["no_commit"] = sh("git rev-list --count HEAD", tree).stdout.strip() == "1"
    result = read(run, "inbox/result.md")
    m = re.search(r"```shiploop-state\s*(\{.*?\})\s*```", result, re.S)
    parsed = None
    try:
        parsed = json.loads(m.group(1)) if m else json.loads(result)
    except Exception:
        pass
    checks["result_parses"] = isinstance(parsed, dict)
    know = (parsed or {}).get("knowledge") or {}
    checks["knowledge_three_keys"] = all(isinstance(know.get(k), str) and know.get(k).strip()
                                         for k in ("spec", "architecture", "environment"))
    spec_removed = removed_lines(tree, "docs/shiploop/spec.md")
    spec_added = [l for l in added_lines(tree, "docs/shiploop/spec.md") if l.strip()]
    checks["spec_add_only"] = not spec_removed
    checks["spec_lines_marked"] = all(re.search(r"\(W1/S1\)\s*$", l) for l in spec_added)
    info["spec_added"] = len(spec_added)
    md = [p for p in sh("git status --porcelain", tree).stdout.splitlines()]
    info["changed"] = md
    docs_added = 0
    for entry in md:
        rel = entry[3:]
        if rel.endswith(".md") and not rel.startswith("docs/shiploop/"):
            docs_added += len([l for l in added_lines(tree, rel) if l.strip()])
    info["product_md_lines_added"] = docs_added
    info["knowledge"] = know
    info["result_outcome"] = (parsed or {}).get("outcome")
    return checks, info


def s1(tree):
    c, i = {}, {}
    src = read(tree, "src/basket.js")
    # A purpose line is a comment above the class's own doc block, separated from it by a blank line, or an @file tag.
    lines = src.splitlines()
    cls = next((n for n, l in enumerate(lines) if l.startswith("class Basket")), len(lines))
    above = lines[:cls]
    blank_split = [n for n, l in enumerate(above) if not l.strip()]
    before_class_doc = above[:blank_split[-1]] if blank_split else []
    c["file_purpose_line"] = bool(re.search(r"@file|@module", src)) or any(
        l.strip().startswith(("/**", "//", "/*", "*")) and "use strict" not in l for l in before_class_doc)
    c["vacuous_docstrings_gone"] = not any(s in src for s in ("/** A basket of items. */", "/** Create a basket. */",
                                                               "/** Add an item. */"))
    c["restating_comments_gone"] = "// check the limit" not in src and "// if the basket is full throw" not in src
    ctor = jsdoc_before(src, r"^\s*constructor\(") + "\n" + jsdoc_before(src, r"^class Basket")
    add = jsdoc_before(src, r"^\s*add\(")
    c["ctor_doc_limit_and_typeerror"] = bool(re.search(r"TypeError", ctor)) and bool(re.search(r"limit", ctor))
    c["add_doc_count_and_rangeerror"] = bool(re.search(r"RangeError", add)) and bool(re.search(r"count|@returns?", add, re.I))
    comments = "\n".join(l for l in src.splitlines() if l.strip().startswith(("//", "*", "/*")))
    c["tombstone_count"] = bool(re.search(r"count", comments, re.I) and
                                re.search(r"drift|separate|one source|single source|do not|don't|never", comments, re.I))
    readme = read(tree, "README.md")
    caveat_text = comments + "\n" + readme
    c["caveat_items_public"] = bool(re.search(r"items", caveat_text) and
                                    re.search(r"bypass|directly|mutat|exceed|not enforced|read-only|readonly", caveat_text, re.I))
    c["readme_lists_basket"] = "basket.js" in readme
    arch_added = "\n".join(added_lines(tree, "docs/shiploop/architecture.md"))
    c["arch_records_departure"] = bool(re.search(r"AD-\d", arch_added) and re.search(r"TypeError", arch_added))
    env = read(tree, "docs/shiploop/environment.md")
    c["env_focused_command"] = "node --test test/basket.test.js" in env or "--test-name-pattern" in env
    c["env_no_transient"] = "probe-count" not in env and "scratch" not in env
    code = [l for l in src.splitlines() if l.strip() and not l.strip().startswith(("//", "*", "/*"))]
    i["basket_comment_lines"] = len([l for l in src.splitlines() if l.strip().startswith(("//", "*", "/*"))])
    i["basket_code_lines"] = len(code)
    return c, i


def s2(tree):
    c, i = {}, {}
    hits = sh("grep -rn getUser --exclude-dir=.git --exclude-dir=shiploop --exclude-dir=node_modules .", tree).stdout
    c["no_stale_getUser"] = hits.strip() == ""
    i["stale_hits"] = hits.strip().splitlines()
    c["readme_names_findUser"] = "findUser" in read(tree, "README.md")
    c["api_names_findUser"] = "findUser" in read(tree, "docs/api.md")
    c["arch_unchanged"] = not added_lines(tree, "docs/shiploop/architecture.md")
    src_added = added_lines(tree, "src/users.js") + added_lines(tree, "src/server.js")
    i["src_lines_added"] = len([l for l in src_added if l.strip()])
    return c, i


def s3(tree):
    c, i = {}, {}
    readme = read(tree, "README.md")
    docs = readme + "\n" + "\n".join(p.read_text() for p in (tree / "docs").rglob("*.md")
                                     if "shiploop" not in p.parts) if (tree / "docs").exists() else readme
    c["readme_start_command"] = "npm start" in readme or "node src/server.js" in readme
    c["readme_port"] = "PORT" in readme
    c["readme_health"] = "/health" in readme
    c["caveat_head_404"] = bool(re.search(r"HEAD", docs))
    server = read(tree, "src/server.js")
    c["createServer_doc_updated"] = bool(re.search(r"health", jsdoc_before(server, r"^function createServer"), re.I))
    env = read(tree, "docs/shiploop/environment.md")
    c["env_start_and_probe"] = ("npm start" in env or "node src/server.js" in env or "PORT" in env) and "/health" in env
    return c, i


SCENARIO = {"s1-basket": s1, "s2-rename": s2, "s3-health": s3}


def grade(arm: Path):
    meta = json.loads((arm / "arm.json").read_text())
    tree, run = arm / "worktree", arm / "run"
    checks, info = common(tree, run)
    c2, i2 = SCENARIO[meta["scenario"]](tree)
    checks.update(c2)
    info.update(i2)
    return {"arm": arm.name, **meta, "passed": sum(checks.values()), "total": len(checks), "checks": checks, "info": info}


if __name__ == "__main__":
    rows = [grade(Path(p)) for p in sys.argv[1:]]
    print(json.dumps(rows, indent=1))
