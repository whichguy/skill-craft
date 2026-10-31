#!/usr/bin/env python3
"""The purpose check (SPEC Change admission, Purpose, amended 2026-10-30; S-13): in a qualified iteration a candidate
is registered only after it shows it serves its one learning record and nothing else.

The script part, no model, on the candidate's commits against the loop tip (``script_check``):
- every changed file is the candidate's (``boundary.candidate_path``); one outside it rejects;
- no added line names a probe's product (``probe_terms.json``; ``skills/shiploop/README.md`` is exempt);
- the commits carry exactly one ``Learning-Record:`` trailer value, the record the candidate was made for;
- changed files beyond the record's ``files``, ``changes/shiploop/`` and ShipLoop's own tests are ``extra_files``: the
  review weighs them, they do not reject by themselves.

The review part (``review``): a fresh session on the judge's role profile, in Codex's read-only sandbox, given only the
record, its anchor clause's text, the prediction and the diff, never the run evidence, so it judges purpose, not
outcome. It answers, per changed file, whether the change serves the record, and a verdict: ``aligned``, ``extra``
(some of it does not serve the record) or ``misaligned``. An unusable review rejects: the check fails closed.

    python3 test/shiploop_e2e/purpose_check.py --repo WORKTREE --base TIP --head CANDIDATE --record LR-... [--script-only]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import boundary  # noqa: E402
import hosts  # noqa: E402
import learning_records  # noqa: E402

TERMS = HERE / "probe_terms.json"
SPEC = HERE / "SPEC.md"
TRAILER = re.compile(r"^Learning-Record:[ \t]*(\S+)[ \t]*$", re.M)
OWN_TESTS = ("test/shiploop-", "test/shiploop_", "test/fixtures/shiploop-", "test/experiments/shiploop_")
VERDICTS = ("aligned", "extra", "misaligned")
MAX_DIFF = 60_000  # characters of diff a review is given; a larger candidate is not one record's change


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


# The user's git config must not change how the diff is read: fixed prefixes, unquoted paths, no rename folding (a
# rename out of the harness is a deletion there and an addition here, and the deletion must be seen).
DIFF = ("-c", "core.quotePath=false", "-c", "diff.noprefix=false", "-c", "diff.mnemonicPrefix=false", "diff",
        "--no-renames", "--no-color", "--no-ext-diff", "--src-prefix=a/", "--dst-prefix=b/")


def load_terms(path: Path = TERMS) -> dict:
    data = json.loads(path.read_text())
    return {"terms": {case: [re.compile(p, re.I) for p in patterns] for case, patterns in data["terms"].items()},
            "exempt": set(data.get("exempt") or []), "known": data.get("known") or []}


def added_lines(repo: Path, base: str, head: str) -> list[tuple[str, str]]:
    """(path, text) of every line the commits base..head add."""
    # A line is a file header only before its first hunk: inside a hunk, an added line that reads "++ b/x" is
    # "+++ b/x" and must not be taken for the next file's header.
    found, path, in_hunk = [], None, False
    for line in _git(repo, *DIFF, "--unified=0", f"{base}..{head}").split("\n"):
        if line.startswith("diff --git "):
            path, in_hunk = None, False
        elif not in_hunk and line.startswith("+++ "):
            path = line[len("+++ b/"):].rstrip("\t") if line.startswith("+++ b/") else None
        elif line.startswith("@@"):
            in_hunk = True
        elif in_hunk and line.startswith("+") and path is not None:
            found.append((path, line[1:]))
    return found


def probe_hits(added: list[tuple[str, str]], terms: dict) -> list[dict]:
    hits = []
    for path, text in added:
        if path in terms["exempt"]:
            continue
        for case, patterns in terms["terms"].items():
            for pattern in patterns:
                if pattern.search(text):
                    hits.append({"path": path, "case": case, "term": pattern.pattern, "line": text.strip()[:160]})
    return hits


def record_trailers(repo: Path, base: str, head: str) -> list[str]:
    """Every ``Learning-Record:`` value in the commit messages of base..head, in order."""
    found = []
    for sha in _git(repo, "rev-list", "--reverse", f"{base}..{head}").split():
        found += TRAILER.findall(_git(repo, "log", "-1", "--format=%B", sha))
    return found


def script_check(repo: Path, base: str, head: str, record: str, record_files: list[str] | None = None,
                 terms: dict | None = None) -> dict:
    terms = terms or load_terms()
    changed = [path for path in _git(repo, *DIFF, "--name-only", "-z", f"{base}..{head}").split("\0") if path]
    problems = []
    outside = [path for path in changed if not boundary.candidate_path(path)]
    if not changed:
        problems.append("the candidate changes nothing")
    if outside:
        problems.append("changes outside the candidate: " + ", ".join(outside))
    hits = probe_hits(added_lines(repo, base, head), terms)
    if hits:
        problems.append("added lines name a probe's product (S-13): "
                        + "; ".join(f"{hit['path']}: {hit['term']} ({hit['case']})" for hit in hits[:5]))
    trailers = record_trailers(repo, base, head)
    if set(trailers) != {record}:
        problems.append(f"the commits must carry exactly one Learning-Record trailer, {record}; found "
                        + (", ".join(sorted(set(trailers))) or "none"))
    allowed = set(record_files or [])
    extra = [path for path in changed if boundary.candidate_path(path) and path not in allowed
             and not path.startswith("changes/shiploop/") and not path.startswith(OWN_TESTS)]
    return {"passed": not problems, "problems": problems, "changed": changed, "probe_hits": hits,
            "trailers": trailers, "extra_files": extra}


def clause_text(clause_id: str | None, spec: Path = SPEC) -> str:
    """The SPEC paragraph that defines a clause (``**S-n ...``), or a note that the record has no clause."""
    if not clause_id:
        return "(the record anchors to the mission, not to a clause)"
    match = re.search(rf"(?ms)^\*\*{re.escape(clause_id)}\b.*?(?=^\s*$)", spec.read_text(encoding="utf-8"))
    return match.group(0).strip() if match else f"({clause_id} is not in SPEC.md)"


def review_prompt(record: dict, anchor: str, prediction: dict | None, diff: str) -> str:
    return f"""You are checking whether one candidate change to the ShipLoop skill serves its stated purpose, and nothing
else. Read only. Do not modify any file. Judge purpose, not whether the change works: that is measured separately.

The learning record the candidate was made for:
```json
{json.dumps(record, indent=2, ensure_ascii=False)}
```

The clause it anchors to:
{anchor}

What the candidate predicts it will change:
```json
{json.dumps(prediction, indent=2, ensure_ascii=False) if prediction else "(no prediction given)"}
```

The candidate's diff:
```diff
{diff}
```

For each changed file, say whether its change serves this record: "yes", "partly" or "no", and why. A change serves the
record when the record's lesson needs it; a refactor, a rename or a fix of something else does not, however good. Also
say whether the prediction follows from the anchor and the change (a prediction that any change would meet does not).
Then give a verdict: "aligned" (every change serves the record), "extra" (the record is served but some change does
not serve it) or "misaligned" (the change does not serve the record).

Return one JSON object in a single ```json fenced block:
{{"files": [{{"path": "...", "serves": "yes|partly|no", "why": "..."}}],
  "prediction_follows": true, "prediction_note": "...",
  "verdict": "aligned|extra|misaligned", "summary": "one sentence"}}
"""


def review(repo: Path, base: str, head: str, record: dict, prediction: dict | None, stage: Path, *,
           host: str | None = None, model: str | None = None, effort: str | None = None, codex_bin: str = "codex",
           timeout: int = 1200) -> dict:
    """The fresh purpose review; ``validity`` is valid only for a parsed verdict from an exited session."""
    diff = _git(repo, "diff", "--no-color", "--no-ext-diff", f"{base}..{head}")
    if len(diff) > MAX_DIFF:
        return {"verdict": None, "validity": {"status": "invalid",
                                              "reason": f"diff of {len(diff)} characters is larger than one record's change"}}
    role = hosts.resolve_role("judge", {"host": host, "model": model, "effort": effort})
    if role["host"] != "codex":
        return {"verdict": None, "validity": {"status": "failed",
                                              "reason": "the purpose review requires Codex read-only sandbox mode"}}
    agent = hosts.host("codex", codex_bin)
    stage.mkdir(parents=True, exist_ok=False)
    anchor = record.get("anchor") if isinstance(record.get("anchor"), dict) else {}
    argv = agent.argv(prompt=review_prompt(record, clause_text(anchor.get("clause_id")), prediction, diff),
                      prompt_file=stage / "prompt.txt", cwd=stage, model=role["model"], effort=role["effort"],
                      permission_mode="read-only", max_turns=None)
    try:
        argv[argv.index("-s") + 1] = "read-only"
    except ValueError:
        raise RuntimeError("CodexHost.argv did not provide the sandbox option the purpose review requires")
    process = hosts.run_agent(argv, stage, agent.env(stage / "home"), stage / "events.jsonl", stage / "stderr.txt",
                              timeout, translate=agent.translator())
    parsed = hosts.last_json_object(hosts.final_text(stage / "events.jsonl"))
    if process.get("status") != "exited" or not isinstance(parsed, dict) or parsed.get("verdict") not in VERDICTS:
        result = {"verdict": None, "process": process, "validity": {
            "status": "invalid", "reason": f"no usable verdict (process {process.get('status')})"}}
    else:
        result = {**parsed, "process": process, "validity": {"status": "valid", "reason": None}}
    result["driver"] = dict(role)
    (stage / "verdict.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def decide(script: dict, reviewed: dict | None) -> dict:
    """passed, retry (the record is served, with extra changes the improver may remove once) or rejected."""
    if not script["passed"]:
        return {"result": "rejected", "stage": "script", "reasons": script["problems"]}
    if reviewed is None:
        return {"result": "passed", "stage": "script", "reasons": ["script check only"]}
    if (reviewed.get("validity") or {}).get("status") != "valid":
        return {"result": "rejected", "stage": "review",
                "reasons": ["purpose review unusable: " + str((reviewed.get("validity") or {}).get("reason"))]}
    verdict = reviewed["verdict"]
    if verdict == "aligned":
        if reviewed.get("prediction_follows") is not True:
            # The review is also the only control on a prediction that any change would meet (plan: gamed predictions).
            return {"result": "rejected", "stage": "review", "reasons": [
                "the prediction does not follow from the anchor and the change: "
                + str(reviewed.get("prediction_note") or "the review did not say that it does")]}
        return {"result": "passed", "stage": "review", "reasons": [reviewed.get("summary") or "aligned"]}
    if verdict == "extra":
        return {"result": "retry", "stage": "review", "reasons": [reviewed.get("summary") or "extra changes",
                *[f"{row.get('path')}: {row.get('why')}" for row in reviewed.get("files") or []
                  if isinstance(row, dict) and row.get("serves") != "yes"]]}
    return {"result": "rejected", "stage": "review", "reasons": [reviewed.get("summary") or "misaligned"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--base", required=True, help="the loop tip")
    parser.add_argument("--head", required=True, help="the candidate commit")
    parser.add_argument("--record", required=True)
    parser.add_argument("--ledger", type=Path, default=learning_records.LEDGER)
    parser.add_argument("--prediction", type=Path)
    parser.add_argument("--stage", type=Path, help="where the review session works (required unless --script-only)")
    parser.add_argument("--script-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        record = learning_records.improver_view(args.record, args.ledger)
        script = script_check(args.repo, args.base, args.head, args.record, record["files"])
        reviewed = None
        if script["passed"] and not args.script_only:
            if args.stage is None:
                parser.error("--stage is required for the review")
            predicted = json.loads(args.prediction.read_text()) if args.prediction else None
            reviewed = review(args.repo, args.base, args.head, record, predicted, args.stage)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"purpose_check: {error}", file=sys.stderr)
        return 1
    decision = decide(script, reviewed)
    print(json.dumps({"script": script, "review": reviewed, "decision": decision}, indent=2))
    return {"passed": 0, "retry": 4}.get(decision["result"], 3)


if __name__ == "__main__":
    raise SystemExit(main())
