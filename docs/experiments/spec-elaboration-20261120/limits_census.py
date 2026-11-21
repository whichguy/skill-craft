#!/usr/bin/env python3
"""Two readings of deliveries that already ran, with no model call (journal sections 27 and 28).

For every archived ShipLoop delivery under the given roots that has a work tree and a final report:

1. the limits the built product enforces that the run added (size, length and count caps, "too large" refusals,
   named maxima), from the added lines of the work tree's diff against the run's baseline, tests and docs left out;
2. whether each is in the specification the spec stage wrote, in a test the run wrote, and in the final report;
3. what the specification left open (open gaps, assumptions) and what the final report lists as open items.

The limit finder is a word and pattern match and over-collects on purpose: its candidates are printed so that each
can be read. Nothing is written but the output file.

    python3 -I limits_census.py [--out FILE] ROOT [ROOT ...]
"""
import html
import json
import re
import subprocess
import sys
from pathlib import Path

CODE = re.compile(
    r"(length|size|bytelength|bytes|count|chars?)\s*(>=?|<=?)\s*\(?\s*([0-9][0-9_]*(?:\s*\*\s*[0-9_]+)*)"
    r"|\b(?:MAX|LIMIT)[A-Z0-9_]*\s*[=:]\s*([0-9][0-9_]*(?:\s*\*\s*[0-9_]+)*)"
    r"|\b(?:max|limit)[A-Za-z]*\s*[=:]\s*([0-9][0-9_]*(?:\s*\*\s*[0-9_]+)*)"
    r"|\b413\b|too (?:large|long|many)|payload too|at most [0-9]|no more than [0-9]"
    r"|requiredText\([^)]*,\s*([0-9]+)\)|\.slice\(0,\s*([0-9]{2,})\)", re.IGNORECASE)
SPEC_LIMIT = re.compile(r"limit|maximum|at most|no more than|too (?:large|long|many)|\b413\b|up to [0-9]|cap\b|bound", re.IGNORECASE)
SKIP = re.compile(r"^(docs/|test/|tests/|__tests__/|provider/|records/|node_modules/)|\.md$|\.test\.|\.spec\.|package-lock", re.IGNORECASE)


def git(work, *args):
    done = subprocess.run(["git", "-C", str(work), *args], capture_output=True, text=True, check=False)
    return done.stdout if done.returncode == 0 else ""


def exists(work, ref):
    return subprocess.run(["git", "-C", str(work), "cat-file", "-e", ref], capture_output=True, check=False).returncode == 0


def mentions(numbers, text):
    """True when one of the numbers stands in the text as a number of its own; None when there is no number to look for."""
    if not numbers:
        return None
    flat = text.replace(",", "").replace("_", "")
    return any(re.search(rf"(?<![0-9]){re.escape(n)}(?![0-9])", flat) for n in numbers)


def value(expr):
    """The number a literal like `64 * 1024` stands for, or None."""
    try:
        n = 1
        for part in expr.replace("_", "").split("*"):
            n *= int(part.strip())
        return n
    except (ValueError, AttributeError):
        return None


def added_lines(work, base):
    """(path, line) for each added line of the work tree against the baseline, in product files and in test files."""
    product, tests, path = [], [], None
    for line in git(work, "diff", "--unified=0", base, "HEAD").splitlines():
        if line.startswith("+++ b/"):
            path = line[6:]
        elif line.startswith("+") and not line.startswith("+++") and path:
            if re.search(r"^(test|tests|__tests__)/|\.test\.|\.spec\.", path):
                tests.append((path, line[1:]))
            elif not SKIP.search(path):
                product.append((path, line[1:]))
    return product, tests


def report_text(path):
    t = Path(path).read_text(errors="replace")
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", t, flags=re.DOTALL)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))


def section(text, start, ends):
    i = text.find(start)
    if i < 0:
        return ""
    j = min([text.find(e, i + len(start)) for e in ends if text.find(e, i + len(start)) > 0] or [len(text)])
    return text[i:j]


def one(run):
    result = json.loads((run / "result.json").read_text())
    work = run / "work"
    rundir = min(run.glob(".shiploop-runs/*/run"))
    base = (rundir / "run-baseline.txt").read_text().split()[0]
    log = git(work, "log", "--reverse", "--format=%H %s").splitlines()
    spec_path = next((p for p in ("docs/shiploop/spec.md", "KNOWLEDGE/spec.md") if exists(work, f"HEAD:{p}")), None)
    spec_commit = next((entry.split()[0] for entry in log if "knowledge after spec" in entry), None)
    if not spec_commit and spec_path:  # no commit is named for the spec stage: the first one that holds the file
        spec_commit = next((entry.split()[0] for entry in log if exists(work, f"{entry.split()[0]}:{spec_path}")), None)
    request = (run / "prompt.txt").read_text(errors="replace") if (run / "prompt.txt").is_file() else ""
    spec_then = git(work, "show", f"{spec_commit}:{spec_path}") if spec_commit and spec_path else ""
    spec_now = git(work, "show", f"HEAD:{spec_path}") if spec_path else ""
    product, tests = added_lines(work, base)
    test_text = "\n".join(text for _, text in tests)
    rep = report_text(rundir / "report.html")
    found = []
    for path, line in product:
        m = CODE.search(line)
        if not m:
            continue
        num = next((value(g) for g in m.groups()[2:] if g and value(g) is not None), None)
        if m.group(1) and num is not None and num < 2:
            continue  # `length > 0`, `count < 1`: emptiness, not a cap
        nums = {str(num)} if num is not None else set()
        if num and num % 1024 == 0:
            nums |= {str(num // 1024)}
        before = git(work, "show", f"{base}:{path}")
        found.append({"path": path, "line": line.strip()[:150], "value": num, "in_spec": mentions(nums, spec_then + spec_now),
                      "in_test": mentions(nums, test_text), "in_report": mentions(nums, rep),
                      "in_request": mentions(nums, request), "was_there": bool(before) and m.group(0) in before})
    open_items = section(rep, "Open items", ("System tests", "Lessons", "Unverified request outcomes", "Follow-on"))
    return {
        "run": str(run), "case": result.get("case"), "model": result.get("model"), "effort": result.get("effort"),
        "outcome": result.get("outcome_class"),
        "spec_words_at_spec": len(spec_then.split()), "spec_words_final": len(spec_now.split()),
        "spec_open_gaps": len(re.findall(r"open gap", spec_then, flags=re.IGNORECASE)),
        "spec_assumptions": len(re.findall(r"assum", spec_then, flags=re.IGNORECASE)),
        "spec_limit_lines": [row.strip()[:170] for row in spec_then.splitlines() if SPEC_LIMIT.search(row)],
        "product_lines_added": len(product), "limits": found,
        "report_words": len(rep.split()),
        "report_open_item_ids": sorted(set(re.findall(r"\b(A\d+)\b", open_items)), key=lambda x: int(x[1:])),
        "report_mentions_limit": len(re.findall(r"limit|maximum|too large|at most", rep, flags=re.IGNORECASE)),
        "report_unverified": section(rep, "Unverified request outcomes", ("Follow-on", "Workspace return"))[:220],
    }


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--out=")), None)
    runs = []
    for root in args:
        for report in sorted(Path(root).expanduser().glob("**/.shiploop-runs/*/run/report.html")):
            run = report.parents[3]
            if (run / "work" / ".git").exists() and (run / "result.json").is_file() and run not in runs:
                runs.append(run)
    rows, lines = [], []
    for run in runs:
        try:
            rows.append(one(run))
        except (OSError, ValueError, KeyError, IndexError, StopIteration) as problem:  # one unreadable folder must not hide the rest
            lines.append(f"SKIPPED {run}: {problem}")
    lines.append(f"{len(rows)} deliveries with a work tree and a final report")
    lines.append("limits = candidate lines the run added that were not in the product before (by number: in spec / in a test / in the report);")
    lines.append("a number match is loose for small numbers, so the lines themselves are listed below for reading")
    lines.append(f"{'case':16} {'model':13} {'eff':6} {'out':6} spec@spec gaps assum  limits(in spec/test/report)  assumptions-in-report  run")
    for r in rows:
        lim = [item for item in r["limits"] if not item["was_there"]]
        seen = {k: sum(1 for item in lim if item[k]) for k in ("in_spec", "in_test", "in_report")}
        lines.append(f"{str(r['case'])[:16]:16} {str(r['model'])[:13]:13} {str(r['effort'])[:6]:6} {str(r['outcome'])[:6]:6} "
                     f"{r['spec_words_at_spec']:>7}w {r['spec_open_gaps']:>4} {r['spec_assumptions']:>5}  "
                     f"{len(lim):>3} ({seen['in_spec']}/{seen['in_test']}/{seen['in_report']})".ljust(92)
                     + f"{len(r['report_open_item_ids']):>3}   {r['run'].replace(str(Path.home()) + '/', '')}")
    lines.append("")
    for r in rows:
        lines.append(f"== {r['run'].replace(str(Path.home()) + '/', '')}  ({r['case']}, {r['model']} {r['effort']}, {r['outcome']})")
        lines.append(f"   spec at the spec stage: {r['spec_words_at_spec']} words; limit lines in it: {len(r['spec_limit_lines'])}")
        for row in r["spec_limit_lines"][:6]:
            lines.append(f"      spec: {row}")
        for item in r["limits"]:
            lines.append(f"   code {item['path']}: {item['line']}   [value {item['value']}; "
                         + ("already in the product before the run; " if item["was_there"] else "")
                         + f"in request {item['in_request']}, spec {item['in_spec']}, test {item['in_test']}, report {item['in_report']}]")
        lines.append(f"   report: {r['report_words']} words; open items {r['report_open_item_ids']}; 'limit' words {r['report_mentions_limit']}")
    text = "\n".join(lines)
    print(text)
    if out:
        Path(out).write_text(text + "\n")


if __name__ == "__main__":
    main()
