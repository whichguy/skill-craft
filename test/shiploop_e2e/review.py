#!/usr/bin/env python3
"""Review one ShipLoop E2E run and propose skill improvements.

Reads a run.py output directory (result.json, transcript.md, stderr, the
product in work/ and its .shiploop run state), gives it to a reviewer model
with read-only instructions, and asks three questions:

  1. What were the key learnings about the skill that we could improve?
  2. Which considerations should the skill take into account but does not?
  3. What could be optimized without removing key functionality?

Discoveries may challenge the current design or reveal a missing expectation.
A fresh independent judge admits material improvements within current authority;
design challenges remain owner/investigation work. Writes review.json and review.md.

  python3 test/shiploop_e2e/review.py /tmp/shiploop-e2e/battleship-...
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import boundary
import hosts  # noqa: E402
import learning_records  # noqa: E402
import runrecord  # noqa: E402

SPEC = Path(__file__).resolve().parent / "SPEC.md"
SPEC_CLAUSE_IDS = set(re.findall(r"(?m)^\*\*(S-[1-9][0-9]*)\b", SPEC.read_text(encoding="utf-8")))
# The standing E2E specification is the premise: one copy, loaded, never restated.
PREMISE = ("Judge this run against the ShipLoop E2E specification below. Cite its clause IDs "
           "(S-1 ...) in every conformance finding; a proposal that weakens a clause does not preserve the "
           "premise. A genuinely novel challenge may have no clause ID only when it explains the gap and routes the "
           "idea to owner review or investigation.\n\n" + SPEC.read_text(encoding="utf-8"))

QUESTIONS = """\
1. learnings: What were the key learnings about the skill that we could improve?
2. missing_considerations: Are there considerations the skill should take into
   account but does not?
3. optimizations: What could be optimized (speed, cost, turns, prompt size,
   clarity, reliability) without removing key functionality?

Then, separately, about this E2E harness (not ShipLoop), answer in "harness":
4. learning_retention: Should the harness retain key learnings or keep state in
   a different way?
5. further_learning: Is there something more we could learn from during
   subsequent passes?
6. evaluation_criteria: Are more evaluation criteria needed to re-evaluate
   ShipLoop's efficacy?"""

SCHEMA = """\
{
  "outcome": "one sentence: did the run deliver the request, and how well",
  "version": 2,
  "learnings": [FINDING, ...],
  "missing_considerations": [FINDING, ...],
  "optimizations": [FINDING, ...],
  "discoveries": [DISCOVERY, ...],
  "harness": {
    "learning_retention": {"answer": "...", "proposals": ["..."]},
    "further_learning": {"answer": "...", "proposals": ["..."]},
    "evaluation_criteria": {"answer": "...", "proposals": ["..."]}
  }
}
FINDING = {
  "title": "short imperative title",
  "evidence": "what in the run shows this; quote transcript lines or cite files",
  "proposal": "the concrete change to the skill",
  "files": ["skills/shiploop/... paths the change touches"],
  "severity": "material" or "minor",
  "preserves_premise": true or false,
  "premise_note": "why the change keeps (or breaks) script-owned navigation"
}
DISCOVERY = {
  "id": "stable identifier, unique within this review",
  "title": "short finding name",
  "evidence": [{"reference": "run artifact path or transcript location",
                "observation": "what the evidence directly shows",
                "interpretation": "what that observation means for the mission"}],
  "mission_anchor": {"clause_id": "S-1 or null for a novel challenge",
                     "relationship": "supports, extends, challenges or novel",
                     "challenge": "why an existing clause is challenged or why no clause fits"},
  "materiality": "material or minor",
  "confidence": "high, medium or low; separate from materiality",
  "potential_impact": "the likely consequence if the finding is true",
  "alternatives": ["other plausible explanations or approaches"],
  "next_experiment": "the smallest next check that would resolve uncertainty",
  "target": "shiploop or harness",
  "files": ["candidate repository paths; required and in-scope for eligible findings"],
  "proposal": "the concrete change or investigation proposed",
  "implementation_eligible": true or false,
  "proposed_disposition": "implement, owner_review, investigate or defer",
  "same_as": "optional: the learning record (LR-...) this discovery recurs, from the records listed above"
}
There is no novelty quota: return an empty discoveries array when the run reveals none. A material design challenge is not a
rejection; route it to owner_review or investigate. Only an aligned discovery anchored to an existing clause may be
implementation_eligible."""

CATEGORIES = ("learnings", "missing_considerations", "optimizations")
# The keys every usable review carries (SCHEMA); an object without them is not a review.
REVIEW_KEYS = ("outcome", *CATEGORIES, "harness")
# About the harness itself; recorded in the learnings, never handed to the ShipLoop improver.
HARNESS_QUESTIONS = ("learning_retention", "further_learning", "evaluation_criteria")


DEFAULT_SKILL_ROOT = ROOT / "skills" / "shiploop"


def ran_source(run_dir: Path, given: Path | None = None) -> dict:
    """The ShipLoop source the run used, for the reviewer to read: `{"roots", "basis", "reason"}`.

    A root the caller passes is its own statement (iterate.py passes the worktree it built the run from). Otherwise the
    roots are `<plugin_dir>/skills/shiploop` of every launch record the run kept (invocation.json, then each resume), in
    launch order. When no record names one, or a named one is gone, the basis is ``mismatch``: the reviewer is given this
    checkout's skill and told it may not be what ran (2026-10-16 E2E audit: it used to be called the source that ran).
    """
    if given is not None:
        return {"roots": [given.resolve()], "basis": "given by the caller", "reason": None}
    named = []
    for _name, record in runrecord.launches(run_dir):
        plugin_dir = record.get("plugin_dir")
        if isinstance(plugin_dir, str) and plugin_dir and plugin_dir not in named:
            named.append(plugin_dir)
    roots = [Path(plugin_dir) / "skills" / "shiploop" for plugin_dir in named]
    missing = [str(root) for root in roots if not (root / "SKILL.md").is_file()]
    if roots and not missing:
        return {"roots": roots, "basis": "the run's launch records", "reason": None}
    reason = (f"the source the run's launch records name is gone: {', '.join(missing)}" if missing
              else "the run's launch records (invocation.json) name no plugin_dir")
    return {"roots": [DEFAULT_SKILL_ROOT], "basis": "mismatch", "reason": reason}


def source_line(source: dict) -> str:
    roots = ", ".join(str(root) for root in source["roots"])
    if source["basis"] == "mismatch":
        return (f"- Source mismatch: {source['reason']}. The ShipLoop skill source given here is this checkout's {roots} "
                "(SKILL.md, references/, scripts/), which may differ from what ran: say so before blaming the skill for "
                "anything that depends on the difference")
    label = "The ShipLoop skill source that ran" if len(source["roots"]) == 1 else (
        "The ShipLoop skill sources that ran, one per plugin its launches used, first launch first")
    return f"- {label}: {roots} (SKILL.md, references/, scripts/)"


def reviewer_prompt(run_dir: Path, skill_root: Path | dict, prior_learnings: str = "", records: str = "") -> str:
    source = skill_root if isinstance(skill_root, dict) else {"roots": [skill_root], "basis": "given by the caller",
                                                              "reason": None}
    prior = (f"""
Git learning context from earlier iterations. Recent messages are not a complete history review. Build on accepted decisions:
check whether this run confirms, contradicts or moves past them, and do not re-report a
finding that was already applied unless this run shows it did not work. A quoted candidate proposal is not an applied fix:
follow its explicit disposition and the measured evidence, including DROP, rejection and unknown outcomes.

{prior_learnings.strip()}
""" if prior_learnings.strip() else "")
    # Read alongside the commit messages, never in their place (SPEC Purpose, owner decision D2).
    recorded = (f"""
The learning records so far (test/shiploop_e2e/learning-records.jsonl): each lesson's status. When a discovery is the
same lesson as a record listed here, set its `same_as` to that record's id instead of reporting it as new; do not
propose a settled record again unless this run shows new evidence.

{records.strip()}
""" if records.strip() else "")
    return f"""You are reviewing one end-to-end run of the ShipLoop skill so the skill can be improved.
Do not modify any file. Read only.

{PREMISE}
{prior}{recorded}
The run: a headless agent was started in an empty directory and asked to run ShipLoop
on the request in {run_dir / 'prompt.txt'}.
- Graded result: {run_dir / 'result.json'}
- Readable transcript (messages, tool calls, outputs): {run_dir / 'transcript.md'}
- Raw event stream: {run_dir / 'events.jsonl'}; host stderr: {run_dir / 'stderr.txt'}
- The product: {run_dir / 'work'}; the ShipLoop run directory is named by result.json
  shiploop.run_dir (it may sit beside work/, in an external workspace root)
- Where ShipLoop spent turns and time per accepted stage (cost is whole-run only), its failed
  commands, truncations and compactions: {run_dir / 'metrics.json'}. Its `unmeasured` map names
  every counter this host's events cannot show (a null or an empty list there is not a zero)
{source_line(source)}

If result.json has a follow_on block, this run added a feature in a copy of an earlier
run's repository (follow_on.prior). Then also judge retention: did ShipLoop find and use
the earlier docs/shiploop/ spec, environment and test-strategy notes and extend the
existing modules and tests, or did it rediscover or rebuild beside them? Compare its
turns and cost with the earlier run.

Answer, from evidence in this run:
{QUESTIONS}

Also produce version 2 discoveries. Review conformance against the specification and record material evidence-backed
observations that reveal something useful beyond, or in tension with, its explicit clauses. Separate what the run shows
(`observation`) from what you infer (`interpretation`). Materiality is impact; confidence is how sure you are. Do not lower
materiality merely because confidence is low. Novel challenges may have `clause_id: null`; explain why in `challenge` and
route them to `owner_review` or `investigate`. Do not reject a challenge just because it questions a design clause. Set
`implementation_eligible` true only for an aligned ShipLoop change that cites an existing clause and proposes `implement`.
Eligible findings must name one or more candidate paths under skills/shiploop/, changes/shiploop/, or ShipLoop's own tests.
If eligibility is false, `files` may be empty and the proposal may be an investigation. Harness discoveries must have target
`harness` and cannot be implementation-eligible for ShipLoop.

Prefer few, well-evidenced findings over many speculative ones. Mark a finding
"material" only when it would change the outcome, cost or reliability of a run like
this one. Set preserves_premise=false for anything that moves navigation into the model. Do not invent a discovery to fill
the array.

End your reply with exactly one ```json fenced block matching:
{SCHEMA}
"""


def last_commit_messages(repo: Path, count: int = 3, *, record_id: str | None = None) -> str:
    """Recent full messages, substantive anchors and older messages for a selected lesson, including empty commits.

    Read messages only: historical diffs can expose withheld acceptance checks. Relevant history beyond a record's exact
    identity still needs the constructor's review; recent commits alone are never labelled complete.
    """
    def git(*args: str) -> str:
        return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout

    recent = git("log", f"-{count}", "--format=%H").split()
    messages = git("log", f"-{count}", "--format=commit %H%n%B")
    context = ("Git messages can quote UNADOPTED proposals. Read each explicit disposition: a candidate author's claims "
               "are not proof of adoption or a verified improvement.\n\n"
               "Recent commit messages (not complete history):\n\n" + messages)
    seen = set(recent)
    # Terminal notes must not displace the last comparison or the source decision. Read messages, never old patches.
    subjects = [line.split("\x00", 1) for line in git("log", "--format=%H%x00%s").splitlines()]
    comparison = next((sha for sha, subject in subjects if subject.startswith("test(e2e): qualified cycle for ")), None)
    if comparison is None:
        comparison = next((sha for sha, subject in subjects
                           if subject.startswith("test(shiploop): record E2E iteration ")), None)
    if comparison and comparison not in seen:
        context += "\nLatest compared-cycle or run-learning message:\n\n" + git(
            "show", "--no-patch", "--format=commit %H%n%B", comparison)
        seen.add(comparison)
    for sha in git("log", "--format=%H", "--", "skills/shiploop/").split():
        message = git("show", "--no-patch", "--format=commit %H%n%B", sha)
        if re.search(r"^Skill-Craft-Release:", message, re.MULTILINE):
            continue  # a generated version bump is not the underlying source decision
        if sha not in seen:
            context += "\nLatest ShipLoop source decision message:\n\n" + message
            seen.add(sha)
        break
    if not record_id:
        return context
    related = git("log", "--fixed-strings", f"--grep={record_id}", "--format=%H",
                  "HEAD", "--glob=refs/shiploop-loop/*").split()
    exact_record = re.compile(r"(?<![A-Za-z0-9_-])" + re.escape(record_id) + r"(?![A-Za-z0-9_-])")
    older = []
    for sha in related:
        if sha in seen:
            continue
        seen.add(sha)
        message = git("show", "--no-patch", "--format=commit %H%n%B", sha)
        if exact_record.search(message):
            older.append(message)
    if older:
        context += (f"\nOlder messages matching learning record {record_id}. Private refs can include unadopted candidates; "
                    "read their decisions before reusing their proposals:\n\n" + "\n".join(older))
    return context


def render_markdown(review: dict) -> str:
    outcome = review.get("outcome", "")
    if not isinstance(outcome, str):
        outcome = "Invalid outcome payload."
    lines = ["# ShipLoop E2E review", "", outcome, ""]
    for category in CATEGORIES:
        lines += [f"## {category.replace('_', ' ').capitalize()}", ""]
        findings = review.get(category)
        if not isinstance(findings, list):
            lines.append(f"- Invalid {category} payload: expected a list.")
            lines.append("")
            continue
        for finding in findings:
            if not isinstance(finding, dict):
                lines.append(f"- Invalid finding payload: {finding!r}")
                continue
            premise = "keeps premise" if finding.get("preserves_premise") else "BREAKS PREMISE (rejected)"
            lines += [f"- **{finding.get('title')}** ({finding.get('severity')}, {premise})",
                      f"  - Evidence: {finding.get('evidence')}",
                      f"  - Proposal: {finding.get('proposal')}"]
            files = finding.get("files")
            if isinstance(files, list) and all(isinstance(path, str) for path in files) and files:
                lines.append(f"  - Files: {', '.join(files)}")
            elif files:
                lines.append("  - Files: invalid payload")
        lines.append("")
    if review.get("version") == 2:
        lines += ["## Discoveries", ""]
        discoveries = review.get("discoveries")
        if not isinstance(discoveries, list):
            discoveries = []
            lines.append("- Invalid discoveries payload: expected a list.")
        for finding in discoveries:
            if not isinstance(finding, dict):
                lines.append(f"- Invalid discovery payload: {finding!r}")
                continue
            anchor = finding.get("mission_anchor") if isinstance(finding.get("mission_anchor"), dict) else {}
            anchor_text = anchor.get("clause_id") or "novel challenge"
            lines.append(f"- **{finding.get('id')}** ({finding.get('materiality')}, {finding.get('confidence')} confidence; "
                         f"{finding.get('target')}; anchor {anchor_text})")
            lines.append(f"  - Eligibility: {finding.get('implementation_eligible')}; proposed disposition: "
                         f"{finding.get('proposed_disposition')}")
            if finding.get("title"):
                lines.append(f"  - {finding['title']}: {finding.get('proposal')}")
            if finding.get("potential_impact"):
                lines.append(f"  - Potential impact: {finding['potential_impact']}")
            if finding.get("alternatives"):
                lines.append(f"  - Alternatives: {finding['alternatives']}")
            if finding.get("next_experiment"):
                lines.append(f"  - Next experiment: {finding['next_experiment']}")
            files = finding.get("files")
            if isinstance(files, list) and files:
                lines.append(f"  - Files: {', '.join(str(path) for path in files)}")
            evidence_items = finding.get("evidence")
            if not isinstance(evidence_items, list):
                evidence_items = []
            for evidence in evidence_items:
                if isinstance(evidence, dict):
                    lines.append(f"  - Evidence ({evidence.get('reference')}): {evidence.get('observation')}")
                    lines.append(f"    - Interpretation: {evidence.get('interpretation')}")
            if anchor.get("challenge"):
                lines.append(f"  - Challenge: {anchor['challenge']}")
        if isinstance(review.get("discoveries"), list) and not review["discoveries"]:
            lines.append("- No discoveries reported.")
        lines.append("")
    harness = review.get("harness") if isinstance(review.get("harness"), dict) else {}
    lines += ["## Harness", ""]
    for key in HARNESS_QUESTIONS:
        row = harness.get(key) if isinstance(harness.get(key), dict) else {}
        lines.append(f"- **{key.replace('_', ' ').capitalize()}:** {row.get('answer', 'not answered')}")
        proposals = row.get("proposals")
        lines += [f"  - {proposal}" for proposal in proposals] if isinstance(proposals, list) else []
    lines.append("")
    return "\n".join(lines)


def actionable(review: dict) -> list[dict]:
    """Material findings that keep the premise, in question order."""
    return [dict(finding, category=category) for category in CATEGORIES
            for finding in review.get(category) or []
            if isinstance(finding, dict) and finding.get("severity") == "material"
            and finding.get("preserves_premise") is True]


def validity(parsed: dict | None, process: dict) -> dict:
    """Whether a review can be used at all: ``valid``, or ``failed``, ``timed_out`` or ``invalid`` with the reason.

    Only a valid review counts (its findings, or its having none): a reviewer that failed or timed out, returned no JSON,
    or returned JSON without the review's structure (``{"learnings": []}`` alone, say) says nothing about the run, so it
    must never read as a clean review (2026-10-16 E2E audit, docs/experiments/shiploop-e2e-audit-20261016/grading/).
    """
    status = process.get("status")
    if status == "timeout":
        return {"status": "timed_out", "reason": f"the reviewer timed out after {process.get('elapsed_seconds')} s"}
    if status != "exited":
        return {"status": "failed", "reason": f"the reviewer process {status} (rc {process.get('returncode')})"}
    if process.get("returncode") != 0:
        return {"status": "failed", "reason": f"the reviewer exited with rc {process.get('returncode')}"}
    if parsed is None:
        return {"status": "invalid", "reason": "the reviewer returned no JSON"}
    if not isinstance(parsed, dict):
        return {"status": "invalid", "reason": "the reviewer JSON is not an object"}
    version = parsed.get("version", 1)
    if isinstance(version, bool) or version not in (1, 2):
        return {"status": "invalid", "reason": f"unsupported review version {version!r}"}
    problems = [key for key in REVIEW_KEYS if key not in parsed]
    problems += [f"{key} is not a list" for key in CATEGORIES if key in parsed and not isinstance(parsed[key], list)]
    if "outcome" in parsed and not isinstance(parsed["outcome"], str):
        problems.append("outcome is not text")
    if "harness" in parsed and not isinstance(parsed["harness"], dict):
        problems.append("harness is not an object")
    if version == 2:
        if not isinstance(parsed.get("outcome"), str) or not parsed["outcome"].strip():
            problems.append("outcome is not non-empty text")
        if "discoveries" not in parsed or not isinstance(parsed.get("discoveries"), list):
            problems.append("discoveries is not a list")
        for category in CATEGORIES:
            findings = parsed.get(category)
            if isinstance(findings, list):
                for index, finding in enumerate(findings):
                    problems.extend(_legacy_finding_problems(finding, f"{category}[{index}]"))
        discoveries = parsed.get("discoveries")
        if isinstance(discoveries, list):
            ids = set()
            for index, finding in enumerate(discoveries):
                problems.extend(_discovery_problems(finding, index))
                if isinstance(finding, dict):
                    ident = finding.get("id")
                    if isinstance(ident, str):
                        if ident in ids:
                            problems.append(f"discoveries[{index}].id is duplicated")
                        ids.add(ident)
    if problems:
        result = {"status": "invalid", "reason": "the review JSON is invalid: " + ", ".join(problems)}
        if version == 2:
            result["discovery_qualified"] = False
        return result
    result = {"status": "valid", "reason": None}
    if version == 2:
        result["discovery_qualified"] = True
    return result


def _nonempty_text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _eligible_candidate_path(value: str) -> bool:
    return (boundary.candidate_path(value) and not value.startswith("/") and "\\" not in value
            and ".." not in PurePosixPath(value).parts)


def _legacy_finding_problems(finding, where: str) -> list[str]:
    if not isinstance(finding, dict):
        return [f"{where} is not an object"]
    problems = []
    for key in ("title", "evidence", "proposal", "premise_note"):
        if not _nonempty_text(finding.get(key)):
            problems.append(f"{where}.{key} is not non-empty text")
    files = finding.get("files")
    if not isinstance(files, list) or any(not isinstance(path, str) for path in files):
        problems.append(f"{where}.files is not a list of text paths")
    if finding.get("severity") not in ("material", "minor"):
        problems.append(f"{where}.severity is not material or minor")
    if not isinstance(finding.get("preserves_premise"), bool):
        problems.append(f"{where}.preserves_premise is not boolean")
    return problems


def _discovery_problems(finding, index: int) -> list[str]:
    where = f"discoveries[{index}]"
    if not isinstance(finding, dict):
        return [f"{where} is not an object"]
    problems = []
    ident = finding.get("id")
    if not isinstance(ident, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", ident):
        problems.append(f"{where}.id is not a stable identifier")
    for key in ("title", "potential_impact", "next_experiment", "proposal"):
        if not _nonempty_text(finding.get(key)):
            problems.append(f"{where}.{key} is not non-empty text")
    evidence = finding.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        problems.append(f"{where}.evidence is not a non-empty list")
    else:
        for evidence_index, item in enumerate(evidence):
            item_where = f"{where}.evidence[{evidence_index}]"
            if not isinstance(item, dict):
                problems.append(f"{item_where} is not an object")
                continue
            for key in ("reference", "observation", "interpretation"):
                if not _nonempty_text(item.get(key)):
                    problems.append(f"{item_where}.{key} is not non-empty text")
    anchor = finding.get("mission_anchor")
    clause = relationship = challenge = None
    if not isinstance(anchor, dict):
        problems.append(f"{where}.mission_anchor is not an object")
    else:
        clause = anchor.get("clause_id")
        relationship = anchor.get("relationship")
        challenge = anchor.get("challenge")
        if clause is not None and (not isinstance(clause, str) or clause not in SPEC_CLAUSE_IDS):
            problems.append(f"{where}.mission_anchor.clause_id is not a clause ID or null")
        if relationship not in ("supports", "extends", "challenges", "novel"):
            problems.append(f"{where}.mission_anchor.relationship is unsupported")
        if clause is None and (relationship not in ("challenges", "novel") or not _nonempty_text(challenge)):
            problems.append(f"{where}.mission_anchor without a clause must explain a novel challenge")
        if clause is not None and relationship == "novel":
            problems.append(f"{where}.mission_anchor cannot be novel and cite a clause")
        if relationship == "challenges" and not _nonempty_text(challenge):
            problems.append(f"{where}.mission_anchor challenge is not explained")
    if finding.get("materiality") not in ("material", "minor"):
        problems.append(f"{where}.materiality is not material or minor")
    if finding.get("confidence") not in ("low", "medium", "high"):
        problems.append(f"{where}.confidence is not low, medium or high")
    alternatives = finding.get("alternatives")
    if not isinstance(alternatives, list) or any(not _nonempty_text(value) for value in alternatives):
        problems.append(f"{where}.alternatives is not a list of non-empty text")
    target = finding.get("target")
    if target not in ("shiploop", "harness"):
        problems.append(f"{where}.target is not shiploop or harness")
    eligible = finding.get("implementation_eligible")
    if not isinstance(eligible, bool):
        problems.append(f"{where}.implementation_eligible is not boolean")
    disposition = finding.get("proposed_disposition")
    if disposition not in ("implement", "owner_review", "investigate", "defer"):
        problems.append(f"{where}.proposed_disposition is unsupported")
    files = finding.get("files")
    if not isinstance(files, list) or any(not isinstance(path, str) or not path.strip() for path in files):
        problems.append(f"{where}.files is not a list of non-empty paths")
    challenge_route = clause is None or relationship == "challenges"
    if eligible is True and (target != "shiploop" or clause is None or relationship not in ("supports", "extends")
                             or disposition != "implement"):
        problems.append(f"{where} claims implementation eligibility without an aligned clause and implement disposition")
    if eligible is True and isinstance(files, list) and (not files or any(not _eligible_candidate_path(path)
                                                                            for path in files if isinstance(path, str))):
        problems.append(f"{where} has no eligible candidate paths under the ShipLoop change boundary")
    if eligible is False and disposition == "implement":
        problems.append(f"{where} proposes implementation but is not implementation-eligible")
    if target == "harness" and eligible is True:
        problems.append(f"{where} targets the harness but claims ShipLoop implementation eligibility")
    if challenge_route and disposition not in ("owner_review", "investigate"):
        problems.append(f"{where} challenge must route to owner_review or investigate")
    same_as = finding.get("same_as")
    if same_as is not None and (not isinstance(same_as, str) or not learning_records.RECORD_ID.fullmatch(same_as)):
        problems.append(f"{where}.same_as is not a learning-record id (LR-YYYYMMDD-xxxxxx)")
    return problems


def counts_as_clean(verdict: dict) -> bool:
    """A valid v2 review, independently judged with no pending material discovery or actionable proposal."""
    validity = verdict.get("validity") or {}
    if validity.get("status") != "valid" or validity.get("discovery_qualified") is not True:
        return False
    judge = verdict.get("judge") or {}
    if (judge.get("validity") or {}).get("status") != "valid" or verdict.get("actionable"):
        return False
    discoveries = verdict.get("discoveries")
    return isinstance(discoveries, list) and not any(
        isinstance(finding, dict) and finding.get("materiality") == "material" for finding in discoveries)


def _assessment_paths(run_dir: Path, assessment_id: str | None) -> tuple[Path, Path, Path]:
    if assessment_id is None:
        return run_dir / "review", run_dir / "review.json", run_dir / "review.md"
    if not isinstance(assessment_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", assessment_id):
        raise ValueError("assessment_id must be 1-64 safe letters, digits, dots, underscores or hyphens")
    return (run_dir / f"review-{assessment_id}", run_dir / f"review-{assessment_id}.json",
            run_dir / f"review-{assessment_id}.md")


def review(run_dir: Path, *, host: str | None = None, model: str | None = None, effort: str | None = None,
           skill_root: Path | None = None, max_turns: int = 60, timeout: int = 1200,
           prior_learnings: str = "", grok_bin: str = "grok", claude_bin: str = "claude",
           codex_bin: str = "codex", assessment_id: str | None = None, records: str = "") -> dict:
    run_dir = run_dir.resolve()
    role = hosts.resolve_role("reviewer", {"host": host, "model": model, "effort": effort})
    agent = hosts.host(role["host"], {"grok": grok_bin, "claude": claude_bin, "codex": codex_bin}[role["host"]])
    stage, review_json, review_markdown = _assessment_paths(run_dir, assessment_id)
    stage.mkdir(exist_ok=False)
    env = agent.env(stage / "home")
    source = ran_source(run_dir, skill_root)
    argv = agent.argv(prompt=reviewer_prompt(run_dir, source, prior_learnings, records),
                      prompt_file=stage / "prompt.txt", cwd=run_dir, model=role["model"],
                      effort=role["effort"], permission_mode="auto", max_turns=max_turns)
    if role["host"] == "codex":
        try:
            sandbox_index = argv.index("-s")
        except ValueError as exc:
            raise RuntimeError("Codex reviewer requires an explicit read-only sandbox") from exc
        argv[sandbox_index + 1] = "read-only"
    process = hosts.run_agent(argv, run_dir, env, stage / "events.jsonl", stage / "stderr.txt", timeout,
                              translate=agent.translator())
    found = hosts.last_json_object(hosts.final_text(stage / "events.jsonl"))
    checked = validity(found, process)
    parsed = found if found is not None else {"outcome": f"reviewer produced no JSON ({process['status']})"}
    if checked["status"] != "valid" and not isinstance(parsed.get("outcome"), str):
        parsed["outcome"] = f"unusable review ({checked['status']}): {checked['reason']}"
    parsed["process"] = process
    parsed["driver"] = dict(role)
    parsed["validity"] = checked
    parsed["skill_source"] = {**source, "roots": [str(root) for root in source["roots"]]}
    parsed["review_receipt"] = {"stage_dir": str(stage.resolve()), "review_json": str(review_json.resolve()),
                                "review_markdown": str(review_markdown.resolve())}
    # An unusable review hands nothing on: its findings, if any, are not evidence the improver may act on.
    parsed["actionable"] = actionable(parsed) if checked["status"] == "valid" else []
    review_json.write_text(json.dumps(parsed, indent=2) + "\n")
    review_markdown.write_text(render_markdown(parsed))
    return parsed


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("run_dir", type=Path, help="a run.py output directory")
    p.add_argument("--host", choices=sorted(hosts.HOSTS))
    p.add_argument("--model")
    p.add_argument("--effort")
    p.add_argument("--skill-root", type=Path, help="the ShipLoop source the run used (default: the plugin_dir its launch "
                   "records name; where they name none that exists, this checkout's, reported as a source mismatch)")
    p.add_argument("--no-prior-learnings", action="store_true",
                   help="do not give the reviewer the last three commit messages or the learning records of this "
                   "checkout")
    args = p.parse_args(argv)
    prior = "" if args.no_prior_learnings else last_commit_messages(ROOT)
    records = "" if args.no_prior_learnings else learning_records.reviewer_view()
    result = review(args.run_dir, host=args.host, model=args.model, effort=args.effort,
                    skill_root=args.skill_root, prior_learnings=prior, records=records)
    print(Path(result["review_receipt"]["review_markdown"]).read_text())
    source = result["skill_source"]
    if source["basis"] == "mismatch":
        print(f"source mismatch: {source['reason']}; the reviewer read {', '.join(source['roots'])}")
    checked = result["validity"]
    print(f"review: {checked['status']}" + (f" ({checked['reason']})" if checked["reason"] else ""))
    print(f"actionable findings: {len(result['actionable'])}")
    return 0 if checked["status"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
