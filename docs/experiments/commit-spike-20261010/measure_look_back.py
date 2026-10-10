#!/usr/bin/env python3
"""Measurement 2 of the 2026-10-10 commit spike: what a look-back block would add to a printed packet head.

The look-back in plan section 2.4 lists the latest commits and quotes the lessons sections of the latest
commits that record lessons. This script prototypes it, outside skills/, on real repositories:

  * the skill-craft repository (read-only git, any revision of the worktree),
  * the product repositories saved E2E runs built (the `work` checkout of each case),
  * the owner's backchain research repository (read-only),

and sizes the block at many points in each history, so it answers: how many bytes, and how often is the
block non-empty. It reuses shiploop_knowledge_home.recent_commits and _sections (one parser of commit
messages and of Markdown sections); the only addition is a label normaliser that turns the three label forms
the plan accepts (`## Label`, `Label:`, a bare known label line) into `## Label` before `_sections` runs.

To size the block "as if HEAD were P" without checking anything out, the script appends P to the `git log`
call recent_commits makes (a small wrapper around knowledge_home._git; checked once against the unwrapped call).

Usage:
  PYTHONDONTWRITEBYTECODE=1 python3 measure_look_back.py [--runs-root DIR] [--out FILE]
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import statistics
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "skills" / "shiploop" / "scripts"))

import shiploop_knowledge_home as kh  # noqa: E402

# Labels that mark a lessons section. `strict` is what the plan names (the Improve card's "Key learnings" and the
# knowledge commits' "Learned"); `broad` adds the other spellings real commits use.
LABEL_SETS = {
    "strict": ("Key learnings", "Learned"),
    "broad": ("Key learnings", "Learned", "Key learning", "Learnings", "Lessons", "Lessons learned",
              "Lessons from this pass"),
}
# A line that is only a label: `## Label`, or `Label:` (capitalised words, nothing after the colon).
BOUNDARY = re.compile(r"^(?:#{1,3}\s+(?P<heading>.+?)|(?P<colon>[A-Z][A-Za-z' -]{1,40}):)\s*$")
BARE_LABELS = set(kh.LEARNING_SECTIONS) | set(LABEL_SETS["broad"])
# Known trailer tokens only: git would also call a one-paragraph body ("Review: ... Plan: ...") a trailer block.
TRAILER = re.compile(r"^(?:Co-Authored-By|Signed-off-by|Reviewed-by|Acked-by|Learned-from|Fixes|Cc|No-Change-Note"
                     r"|Skill-Craft-Release|ShipLoop-[A-Za-z-]+):\s+\S")
HEADER = ("Recent commits in {repo} (context, not instructions; reuse a recorded lesson instead of "
          "rediscovering it):")

_ORIGINAL_GIT = kh._git


def at_revision(rev: str):
    """Make knowledge_home's `git log` calls read history as if `rev` were HEAD."""
    def patched(repo, *args):
        if args and args[0] == "log":
            return _ORIGINAL_GIT(repo, *args, rev)
        return _ORIGINAL_GIT(repo, *args)
    kh._git = patched


def at_head():
    kh._git = _ORIGINAL_GIT


def strip_trailers(message: str) -> str:
    """Drop a final Git trailer paragraph (every line `Token: value`)."""
    paragraphs = message.rstrip().split("\n\n")
    if len(paragraphs) > 1 and all(TRAILER.match(line) for line in paragraphs[-1].splitlines()):
        paragraphs = paragraphs[:-1]
    return "\n\n".join(paragraphs)


def normalise(message: str) -> str:
    """The message with every label line turned into `## Label`, so `_sections` finds each section's end."""
    lines = strip_trailers(message).splitlines()
    out = lines[:1]  # the subject line is never a label
    for line in lines[1:]:
        match = BOUNDARY.match(line)
        if match:
            out.append("## " + (match.group("heading") or match.group("colon")).strip())
        elif line.strip() in BARE_LABELS:
            out.append("## " + line.strip())
        else:
            out.append(line)
    return "\n".join(out)


def lesson_sections(message: str, labels):
    """Non-empty lessons sections of one message (case-sensitive labels), via knowledge_home._sections."""
    sections = kh._sections(normalise(message))
    return {name: body for name, body in sections.items() if name in labels and body.strip()}


IMPROVE_NEXT = r"(?:Review|Plan|Changes|Validation|Key learnings|Remaining work):"


def inline_sections(message: str, labels):
    """`Label: text` forms the label-only extractor misses: a label at a line start or after a space, text up to the
    next Improve label, a blank line or the end. Real improve-commit messages are often one paragraph like this."""
    body = strip_trailers(message)
    found = {}
    for label in labels:
        match = re.search(r"(?:^|(?<=\s))" + re.escape(label) + r":[ \t]+(.+?)(?=\s" + IMPROVE_NEXT + r"|\n\s*\n|\Z)",
                          body, re.S | re.M)
        if match and match.group(1).strip():
            found[label] = match.group(1).strip()
    return found


def lessons_inline_aware(message: str, labels):
    """The plan's label-only sections when present, else the inline forms."""
    return lesson_sections(message, labels) or inline_sections(message, labels)


# What counts as "records lessons". strict/broad read label-only sections (the plan's extractor); inline_aware also
# reads `Key learnings: text` written inside a paragraph, which is how many real improve-commit messages are formed.
EXTRACTORS = {
    "strict_sections": lambda message: lesson_sections(message, LABEL_SETS["strict"]),
    "broad_sections": lambda message: lesson_sections(message, LABEL_SETS["broad"]),
    "strict_inline_aware": lambda message: lessons_inline_aware(message, LABEL_SETS["strict"]),
}


def has_inline_form(message: str) -> bool:
    """`Key learning: text` on one line: a lesson the label-only extractor does not read."""
    return bool(re.search(r"(?m)^(Key learnings?|Learned|Learnings|Lessons?)( [A-Za-z]+)*:\s+\S", strip_trailers(message)))


def commits_at(repo: Path, rev: str, count: int):
    """(full id, message) of the newest `count` commits as if `rev` were HEAD; message is what recent_commits read."""
    at_revision(rev)
    try:
        entries = kh.recent_commits(repo, count)
        ids = _ORIGINAL_GIT(repo, "rev-list", "-" + str(count), rev).stdout.split()
    finally:
        at_head()
    out = []
    for entry, full in zip(entries, ids):
        short, _, message = entry.partition(" ")
        out.append((full, message))
    return out


def quote(lines):
    return ["    | " + line for line in lines]


def block_plan(repo: Path, commits, extract, window):
    """Plan section 2.4: the 2 latest commits as subject lines, lessons sections quoted for lesson-bearing ones."""
    if not commits:
        return HEADER.format(repo=repo).split(" (")[0] + ": none yet."
    lines = [HEADER.format(repo=repo)]
    latest = commits[:2]
    bearing = [(full, message, extract(message)) for full, message in commits[:window]]
    bearing = [row for row in bearing if row[2]][:2]
    shown = {full for full, _m in latest} | {full for full, _m, _s in bearing}
    for rank, (full, message) in enumerate(commits):
        if full not in shown:
            continue
        sections = extract(message)
        tags = (["latest"] if rank < 2 else []) + (["records lessons"] if full in {b[0] for b in bearing} else [])
        lines.append("- " + full + " " + message.splitlines()[0] + ("  [" + ", ".join(tags) + "]" if tags else ""))
        if full in {b[0] for b in bearing}:
            for name, body in sections.items():
                lines += quote([name + ":"] + body.splitlines())
    if not bearing:
        lines.append("(no commit in the newest " + str(window) + " records lessons)")
    return "\n".join(lines)


def block_full(repo: Path, commits, extract, window):
    """The brief's block: the 2 latest messages in full, then the lessons sections of the 2 latest lesson-bearing commits."""
    if not commits:
        return HEADER.format(repo=repo).split(" (")[0] + ": none yet."
    lines = [HEADER.format(repo=repo)]
    full_shown = set()
    for full, message in commits[:2]:
        full_shown.add(full)
        lines.append("- " + full)
        lines += quote(message.splitlines())
    bearing = [(full, message, extract(message)) for full, message in commits[:window]]
    for full, message, sections in [row for row in bearing if row[2]][:2]:
        if full in full_shown:
            continue  # already printed whole
        lines.append("- " + full + " " + message.splitlines()[0] + "  [records lessons]")
        for name, body in sections.items():
            lines += quote([name + ":"] + body.splitlines())
    return "\n".join(lines)


def stats(values):
    values = sorted(values)
    if not values:
        return None
    quarter = lambda q: values[min(len(values) - 1, int(q * (len(values) - 1) + 0.5))]  # noqa: E731
    return {"n": len(values), "min": values[0], "p25": quarter(0.25), "median": statistics.median(values),
            "p75": quarter(0.75), "max": values[-1]}


def measure_repo(repo: Path, points, window_names=(10, 500), extractors=None):
    """Block bytes at the given revisions, for each extractor and both block shapes."""
    result = {"points": len(points)}
    for label_name, labels in (extractors or EXTRACTORS).items():
        plan_bytes, full_bytes, plan_nonempty, full_nonempty, plan_empty = [], [], [], [], []
        nonempty = {window: 0 for window in window_names}
        for rev in points:
            commits = commits_at(repo, rev, 500)
            plan = len(block_plan(repo, commits, labels, 10).encode("utf-8"))
            full = len(block_full(repo, commits, labels, 10).encode("utf-8"))
            plan_bytes.append(plan)
            full_bytes.append(full)
            has = any(labels(message) for _f, message in commits[:10])
            (plan_nonempty if has else plan_empty).append(plan)
            if has:
                full_nonempty.append(full)
            for window in window_names:
                if any(labels(message) for _f, message in commits[:window]):
                    nonempty[window] += 1
        result.setdefault("_raw", {})[label_name] = {
            "plan": plan_bytes, "full": full_bytes, "plan_nonempty": plan_nonempty, "plan_empty": plan_empty,
            "full_nonempty": full_nonempty}
        result[label_name] = {
            "plan_format_bytes": stats(plan_bytes), "full_messages_bytes": stats(full_bytes),
            "plan_format_bytes_when_lessons_in_newest_10": stats(plan_nonempty),
            "plan_format_bytes_when_none_in_newest_10": stats(plan_empty),
            "full_messages_bytes_when_lessons_in_newest_10": stats(full_nonempty),
            "block_has_lessons_within_newest_10": nonempty[10], "block_has_lessons_within_newest_500": nonempty[500],
        }
    return result


def history(repo: Path):
    out = subprocess.run(["git", "-C", str(repo), "rev-list", "HEAD"], capture_output=True, text=True, check=False)
    return out.stdout.split()


def count_lessons(repo: Path, total: int):
    """Over the whole history: commits per label set, per label, and inline-only forms."""
    at_head()
    entries = kh.recent_commits(repo, total)
    messages = [entry.partition(" ")[2] for entry in entries]
    per_label = {}
    for message in messages:
        for name in lesson_sections(message, LABEL_SETS["broad"]):
            per_label[name] = per_label.get(name, 0) + 1
    newest = {name: next((i for i, m in enumerate(messages) if fn(m)), None) for name, fn in EXTRACTORS.items()}
    window = {str(size): {name: sum(1 for m in messages[:size] if fn(m)) for name, fn in EXTRACTORS.items()}
              for size in (10, 100, 500)}
    return {
        "newest_lesson_commit_index_at_head": newest,
        "lesson_commits_in_newest": window,
        "commits": len(messages),
        "with_lessons_strict": sum(1 for m in messages if lesson_sections(m, LABEL_SETS["strict"])),
        "with_lessons_broad": sum(1 for m in messages if lesson_sections(m, LABEL_SETS["broad"])),
        "with_lessons_strict_inline_aware": sum(1 for m in messages if EXTRACTORS["strict_inline_aware"](m)),
        "mention_key_learnings_anywhere": sum(1 for m in messages if "Key learnings" in m),
        # Of the commits that say "Key learnings": written as a label-only section (the plan's extractor reads it) or only
        # inside a paragraph ("Review: ... Key learnings: ... Remaining work: ..."), which a label-only gate would refuse.
        "key_learnings_as_label_only_section": sum(1 for m in messages if "Key learnings" in lesson_sections(m, ("Key learnings",))),
        "key_learnings_only_inside_a_paragraph": sum(
            1 for m in messages if "Key learnings" in m and "Key learnings" not in lesson_sections(m, ("Key learnings",))),
        # ... of which a line that starts "Key learnings: <text>" (text on the same line) and the ones that sit mid-paragraph.
        "key_learnings_line_start_with_text_only": sum(
            1 for m in messages if "Key learnings" in m and "Key learnings" not in lesson_sections(m, ("Key learnings",))
            and re.search(r"(?m)^Key learnings:[ \t]+\S", strip_trailers(m))),
        "key_learnings_mid_paragraph_only": sum(
            1 for m in messages if "Key learnings" in m and "Key learnings" not in lesson_sections(m, ("Key learnings",))
            and not re.search(r"(?m)^Key learnings:[ \t]+\S", strip_trailers(m))),
        "inline_form_only": sum(1 for m in messages if has_inline_form(m) and not lesson_sections(m, LABEL_SETS["broad"])),
        "with_body": sum(1 for m in messages if len(m.strip().splitlines()) > 1),
        "subject_only": sum(1 for m in messages if len(m.strip().splitlines()) == 1),
        "per_label_broad": per_label,
    }


def even_points(revs, k):
    if len(revs) <= k:
        return list(revs)
    return [revs[round(i * (len(revs) - 1) / (k - 1))] for i in range(k)]


def head_sizes(runs_root: Path):
    """Printed-head sizes from saved Claude runs: Bash tool results that start with the navigator head line."""
    per_run, pooled, without = {}, [], []
    for day in ("20261008", "20261009", "20261010"):
        for events in sorted(glob.glob(str(runs_root / day / "*" / "events.jsonl"))):
            names, sizes = {}, []
            for line in open(events, encoding="utf-8"):
                try:
                    obj = json.loads(line)
                except ValueError:
                    continue
                message = obj.get("message") if isinstance(obj, dict) else None
                content = message.get("content") if isinstance(message, dict) else None
                if not isinstance(content, list):
                    continue  # a Grok event line has no Claude-shaped tool_result blocks
                for block in content:
                    if block.get("type") == "tool_use":
                        names[block["id"]] = block.get("name")
                    elif block.get("type") == "tool_result" and names.get(block.get("tool_use_id")) == "Bash":
                        inner = block.get("content")
                        text = inner if isinstance(inner, str) else "".join(
                            part.get("text", "") for part in inner or [] if isinstance(part, dict))
                        if text.startswith("ShipLoop navigator |"):
                            sizes.append((len(text), len(text.encode("utf-8"))))
            if not sizes:
                without.append(str(Path(events).parent.relative_to(runs_root)))
            if sizes:
                per_run[str(Path(events).parent.relative_to(runs_root))] = {
                    "heads": len(sizes), "median_chars": statistics.median(s[0] for s in sizes),
                    "median_bytes": statistics.median(s[1] for s in sizes)}
                pooled += sizes
    return {"runs_without_claude_heads": without, "per_run": per_run, "pooled": {"heads": len(pooled),
                                           "chars": stats([s[0] for s in pooled]),
                                           "bytes": stats([s[1] for s in pooled])}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-root", default="/Users/dadleet/e2e-runs")
    parser.add_argument("--backchain", default="/Users/dadleet/src/backchain")
    parser.add_argument("--out", default=str(Path(__file__).resolve().parent / "look-back.json"))
    args = parser.parse_args()
    runs_root = Path(args.runs_root)

    # Equivalence check: the wrapped call at HEAD reads exactly what the unwrapped recent_commits reads.
    at_head()
    plain = kh.recent_commits(REPO, 10)
    at_revision("HEAD")
    wrapped = kh.recent_commits(REPO, 10)
    at_head()
    assert plain == wrapped, "the revision wrapper changed what recent_commits reads"

    repos = {}
    # (a) skill-craft: this worktree's history (origin/main when the worktree is on it).
    revs = history(REPO)
    entry = count_lessons(REPO, len(revs))
    entry["head"] = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    entry["sampling"] = {"full_history_10_even": measure_repo(REPO, even_points(revs, 10)),
                         "newest_100_10_even": measure_repo(REPO, even_points(revs[:100], 10)),
                         "newest_500_every_25th": measure_repo(REPO, revs[:500:25])}
    repos["skill-craft"] = entry

    # (c) the owner's research repository, read-only.
    backchain = Path(args.backchain)
    if (backchain / ".git").exists():
        revs = history(backchain)
        entry = count_lessons(backchain, len(revs))
        entry["sampling"] = {"full_history_10_even": measure_repo(backchain, even_points(revs, 10))}
        repos["backchain (owner research repo)"] = entry

    # (b) product repositories built by saved E2E runs: every commit as HEAD, since each is a moment a packet could print it.
    product = {}
    for work in sorted(glob.glob(str(runs_root / "2026100[89]" / "*" / "work")) + glob.glob(str(runs_root / "20261010" / "*" / "work"))):
        work_path = Path(work)
        if not (work_path / ".git").exists():
            continue
        revs = history(work_path)
        if len(revs) < 2:
            continue
        case = str(work_path.parent.relative_to(runs_root))
        entry = count_lessons(work_path, len(revs))
        # broad_sections equals strict_sections in every product repository (no other spelling is used), so it is left out.
        entry["every_commit_as_head"] = measure_repo(work_path, revs, extractors={
            name: EXTRACTORS[name] for name in ("strict_sections", "strict_inline_aware")})
        positions = {"strict_sections": [], "strict_inline_aware": []}
        for i, rev in enumerate(reversed(revs)):
            message = commits_at(work_path, rev, 1)[0][1]
            for name in positions:
                if EXTRACTORS[name](message):
                    positions[name].append(i + 1)
        entry["lesson_commit_positions_from_oldest"] = positions
        product[case] = entry
    # Pool every product repository's positions (each commit as HEAD) so the E2E distribution is exact, not a median of medians.
    pooled = {}
    for name in ("strict_sections", "strict_inline_aware"):
        raw = [e["every_commit_as_head"]["_raw"][name] for e in product.values()]
        flat = lambda key: [v for r in raw for v in r[key]]  # noqa: E731
        pooled[name] = {
            "positions": len(flat("plan")), "positions_with_lessons_in_newest_10": len(flat("plan_nonempty")),
            "plan_format_bytes": stats(flat("plan")), "full_messages_bytes": stats(flat("full")),
            "plan_format_bytes_when_lessons": stats(flat("plan_nonempty")),
            "plan_format_bytes_when_none": stats(flat("plan_empty")),
            "full_messages_bytes_when_lessons": stats(flat("full_nonempty"))}
    for entry in list(product.values()) + list(repos.values()):
        entry.get("every_commit_as_head", {}).pop("_raw", None)
        for sampled in entry.get("sampling", {}).values():
            sampled.pop("_raw", None)
    repos["e2e_products"] = product
    repos["e2e_products_pooled"] = pooled

    result = {
        "method": {
            "labels": LABEL_SETS, "window_scanned": 10, "window_plan_rule": 500,
            "extractors": {"strict_sections": "plan: label-only forms, labels Key learnings / Learned",
                           "broad_sections": "label-only forms, seven spellings",
                           "strict_inline_aware": "label-only sections, else `Label: text` inside a paragraph (the form many real improve-commit messages use)"},
            "block_shapes": {"plan_format": "plan 2.4: 2 latest subjects + quoted lessons sections of the 2 latest lesson-bearing commits",
                             "full_messages": "the brief: 2 latest full messages + lessons sections of the 2 latest lesson-bearing commits not already shown"},
            "ids": "full 40-hex ids (git rev-list); recent_commits itself prints %h",
            "header": HEADER, "quote_prefix": "    | ",
            "parser": "knowledge_home.recent_commits and knowledge_home._sections; label lines normalised to '## Label' first; a final trailer paragraph dropped",
            "not_modelled": "credential-line screening (plan F25); the 'none yet' line is counted for an unborn HEAD only",
        },
        "repos": repos,
        "printed_head": head_sizes(runs_root),
    }
    Path(args.out).write_text(json.dumps(result, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"repos": list(repos), "e2e_products": len(product), "out": args.out}))


if __name__ == "__main__":
    main()
