#!/usr/bin/env python3
"""How much of a recursive session's final coverage was already worded in its first draft?

No model runs. For every graded specification of a multi-pass arm this takes the first thing the session wrote to
`spec.md` (Claude: the first Write; Codex: the first `cat > spec.md <<EOF` or `printf ... > spec.md`) and asks, for
each held-out nuance the judge finally marked `covered`, whether the judge's quoted words (or the covering clause's
own title) already stand in that first draft.

Read it as a bound, not a measurement of what each pass did: a nuance whose clause was reworded later is counted as
"added later" even if an earlier wording carried it, so the first-draft share is a LOWER bound and the later-pass
share an UPPER bound. It does not say what a single pass told to use every lens at once would have reached; only an
arm that does exactly that can.

Usage: python3 -I timeline.py ROUND [ROUND ...]     (writes evidence/<last round>/first-draft.txt and prints it)
"""
import json
import re
import shlex
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


def norm(text):
    return re.sub(r"\s+", " ", text.replace("`", "").replace("*", "")).strip().lower()


def claude_first_draft(stream):
    for line in stream.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        message = event.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        for block in content if isinstance(content, list) else []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                given = block.get("input") or {}
                target = str(given.get("file_path") or given.get("path") or "")
                if block.get("name") == "Write" and target.endswith("spec.md"):
                    return given.get("content") or ""
                heredoc = re.search(r"cat\s*>\s*(?:\./)?spec\.md\s*<<\s*'?\"?(\w+)'?\"?\n(.*?)\n\1",
                                    given.get("command") or "", re.DOTALL) if block.get("name") == "Bash" else None
                if heredoc:
                    return heredoc.group(2)
    return None


def codex_first_draft(stream):
    for line in stream.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        item = event.get("item") or {}
        if event.get("type") != "item.completed" or item.get("type") != "command_execution":
            continue
        command = item.get("command") or ""
        if "spec.md" not in command:
            continue
        try:
            script = shlex.split(command)[-1]
        except ValueError:
            script = command
        heredoc = re.search(r"cat\s*>\s*(?:\./)?spec\.md\s*<<\s*'?\"?(\w+)'?\"?\n(.*?)\n\1", script, re.DOTALL)
        if heredoc:
            return heredoc.group(2)
        if re.search(r">>?\s*'?(?:\./)?spec\.md'?\s*$", script.strip()) and script.lstrip().startswith("printf"):
            try:
                parts = shlex.split(script)
            except ValueError:
                continue
            payload = [p for p in parts[1:] if p not in ("%s", "%s\\n", ">", "spec.md", "./spec.md")]
            if payload:
                return max(payload, key=len)
    return None


def needles_for(verdict, final):
    out = []
    quote = norm(verdict.get("quote") or "")
    if quote:
        parts = [p.strip(" .,;:") for p in re.split(r"\.\.\.|…|\[\.\.\.\]", quote)]
        parts = [p for p in parts if len(p) >= 15]
        if parts:
            out.append(parts)
    for ident in re.findall(r"[UC]-\d+", verdict.get("where") or "")[:1]:
        heading = re.search(rf"^#+\s*{ident}:\s*(.+)$", final, re.MULTILINE)
        if heading and len(norm(heading.group(1))) >= 15:
            out.append([norm(heading.group(1))])
    return out


def holds(text, needles):
    body = norm(text)
    return any(all(part in body for part in needle) for needle in needles if needle)


def clauses(text):
    return len(set(re.findall(r"^#{2,4}\s*C-(\d+)\b", text, re.MULTILINE)))


def main():
    rounds = sys.argv[1:]
    if not rounds:
        print(__doc__)
        raise SystemExit(2)
    lines, pooled = [], defaultdict(lambda: defaultdict(int))
    lines.append(f"{'session':62s} {'clauses: first draft -> kept':>29s} {'covered':>8s} {'in first draft':>15s} "
                 f"{'only later':>11s} {'unplaced':>9s}")
    for round_name in rounds:
        for grade_file in sorted((HERE / "grades" / round_name).glob("*.json")):
            grade = json.loads(grade_file.read_text())
            slot = HERE / "results" / round_name / grade["slot"]
            _case, arm, driver = grade["slot"].split("__")
            if not (slot / "passes.md").is_file() or not (slot / "stream.jsonl").is_file():
                continue
            final = (slot / "spec.md").read_text()
            draft = (claude_first_draft if driver.startswith("sonnet") else codex_first_draft)(slot / "stream.jsonl")
            if not draft:
                lines.append(f"{round_name + '/' + grade['slot']:62s} first write of spec.md not found in the stream; left out")
                continue
            covered = [v for v in grade["verdicts"] if v.get("state") == "covered"]
            early = late = lost = 0
            for verdict in covered:
                needles = needles_for(verdict, final)
                if not holds(final, needles):
                    lost += 1
                elif holds(draft, needles):
                    early += 1
                else:
                    late += 1
            box = pooled[(arm, driver)]
            for key, value in (("covered", len(covered)), ("early", early), ("late", late), ("lost", lost),
                               ("draft_clauses", clauses(draft)), ("final_clauses", clauses(final)), ("n", 1)):
                box[key] += value
            lines.append(f"{round_name + '/' + grade['slot']:62s} {clauses(draft):13d} -> {clauses(final):<13d} "
                         f"{len(covered):8d} {early:15d} {late:11d} {lost:9d}")
    lines.append("")
    lines.append("POOLED, of the nuances finally covered whose covering words could be located in the kept file")
    for (arm, driver), box in sorted(pooled.items()):
        seen = box["early"] + box["late"]
        if not seen:
            continue
        lines.append(f"  {arm:20s} {driver:12s} sessions {box['n']}: clauses {box['draft_clauses']} -> "
                     f"{box['final_clauses']}; covered {box['covered']}, worded in the first draft {box['early']} "
                     f"({100 * box['early'] / seen:.0f}%), only later {box['late']} ({100 * box['late'] / seen:.0f}%), "
                     f"unplaced {box['lost']}")
    text = "\n".join(lines) + "\n"
    target = HERE / "evidence" / rounds[-1]
    target.mkdir(parents=True, exist_ok=True)
    (target / "first-draft.txt").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
