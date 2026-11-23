#!/usr/bin/env python3
"""What ShipLoop's end-of-item stages (each step's `document`, each item's `carry-forward`) did in recorded deliveries,
ShipLoop 2.4.0 and later (2026-11-20 on).  Read-only: run folders and product repositories are only read, Git is called
only as `git -C <repo> log/show/diff/diff-tree/ls-tree/cat-file/rev-parse/merge-base`.

Usage: python3 -I census.py OUT_DIR            (writes OUT_DIR/runs.txt, OUT_DIR/census.json, OUT_DIR/census.out)

Corpus.  Every folder under ~/e2e-runs*/ that holds an invocation.json and a ShipLoop run directory
(`.shiploop-runs/*/run/state.md`), whose invocation records ShipLoop 2.4.0 or later.  Left out, with the count printed:
the look-stage candidate trials (d20261122-236b00, d20261122-ccc2ff), Ratchet runs (no ShipLoop run directory),
copies of the skill-craft checkout inside run folders (apparatus-*, source-*), and step slices (seeded single-stage
runs; each one at 2.4.0 or later is a plan-only slice and is reported apart).

Where each field comes from (one delivery folder D, its run directory R = D/.shiploop-runs/<work-...>/run):
  version, driver     D/invocation.json `versions.shiploop_version`, `host`, `model`, `effort`
  build               `versions.local_head` diffed (canonical skill-craft repo) against the release commit of that
                      version, over skills/shiploop, skills/improve and skills/until-loop: "release" when identical
  order of events     R/state.md `history` (accepted results in order); the result of each action is
                      R/state.md `accepted[<action>]` (the same as R/results/<action>.md)
  queue               the accepted plan's `work_items`; carry-forward `work_items` replaces the future queue;
                      `add-work` (outer stages) appends (shiploop_navigator.py apply)
  document's own edits R/lint/<document action>.gate<N>.md (last N): "Scope: files changed since ... the tree this
                      stage began from"
  step's edits        R/iterations/<item>.json plans -> step base and commit; `git diff base commit -- docs/shiploop`
  knowledge commits   product repo (state.md `repo`, else D/work) subjects `docs(shiploop): record <run> knowledge
                      (at|after) <stage>`; carry-forward's own home edit is its `after carry-forward` commit
  final sizes         `git show HEAD:docs/shiploop/<file>` in the product repo; level-2 headings checked against
                      shiploop_knowledge_home.SECTIONS (unchanged 2.4.0 to 2.6.1); the commit that introduced each
                      unnamed heading by `git log -S`
  placement notices   lines "ShipLoop placement notice: " in D/events.jsonl (else D/transcript.md)
  Improve review      R/improve/<reviewed action>/passes.md (ShipLoop's own pass log)
  minutes             R/trace.jsonl command rows: the gap before a row belongs to the stage the run was in
                      (`stage[0]`), a review to the stage it reviews; gaps over 45 minutes and the spans when no host
                      ran (D/sessions.jsonl, one session's end to the next one's start) are left out
                      (docs/experiments/sdlc-structure-20261119/review_option_census.py)
"""
import collections
import datetime
import difflib
import json
import os
import pathlib
import re
import statistics
import subprocess
import sys
import time

HOME = pathlib.Path.home()
CANON = pathlib.Path("/Users/dadleet/src/skill-craft")
# The canonical repository's own entry parser (shiploop_knowledge_home._entries, current main), used only as an
# instrument to split spec.md into R-<n> entries and tell whether each sits under '## Retired'.  Nothing from a run
# folder is imported.
sys.path.insert(0, str(CANON / "skills" / "shiploop" / "scripts"))
import shiploop_knowledge_home as knowledge_home  # noqa: E402
EXCLUDED_FOLDERS = ("d20261122-236b00", "d20261122-ccc2ff")
PRUNE = {"build", "home", "work", "worktree", ".shiploop-runs", "node_modules", ".git", "review-export", "delivery",
         "packet-archive", "export", "deep", "deep-out", "judge", "look", "measure", "fix", "fixed-hidden", "delivered",
         "report", "report-draft", "instrument-checks", "quality"}
MIN_VERSION = (2, 4, 0)
IDLE = 45 * 60
LIVING = ("spec.md", "environment.md", "architecture.md")
RECORD_KEYS = (("spec", "spec.md"), ("architecture", "architecture.md"), ("environment", "environment.md"))
SECTIONS = {
    "spec.md": ("Requirements", "Non-functional requirements", "Retired"),
    "environment.md": ("Targets and runtimes", "Commands", "Skills", "Harnesses and suites", "ID convention",
                       "Access and accounts", "Platform facts"),
    "architecture.md": ("Stack", "Structure", "Conventions", "Interfaces and boundaries", "Real-boundary checks",
                        "Decisions", "Superseded"),
}
INNER = ("step-plan", "test-spec", "validate-existing", "implement", "test", "document", "carry-forward")
NOT_APPLICABLE = "Not applicable to this item"
KNOWLEDGE_SUBJECT = re.compile(r"^docs\(shiploop\): record (\S+) knowledge (at|after) ([a-z][a-z-]*)$")
STEP_SUBJECT = re.compile(r"^feat\((W\d+)/(S\d+)\): ")
STATE_BLOCK = re.compile(r"```shiploop-state\n(.*?)\n```", re.S)
PLACEMENT = "ShipLoop placement notice: "
KNOWLEDGE_NOTICE = "ShipLoop knowledge notice: "
GROUP_LABELS = {
    "e2e-runs/d20261122-b54ea4": "head-to-head clean 2.6.0",
    "e2e-runs/d20261122-360a9f": "head-to-head first runs 2.4.1",
    "e2e-runs/d20261122-cc457a": "roundtable 2.6.0",
    "e2e-runs/r-20261121-2c3d50": "defaults candidate (spec elaboration)",
    "e2e-runs/r-20261122-ffb3fb": "defaults candidate (spec elaboration)",
    "e2e-runs/r-20261122-8c4274": "answer-route candidate",
    "e2e-runs/r-20261122-8a73b9": "answer-route candidate",
    "e2e-runs/r-20261122-72ca72": "answer-route candidate",
    "e2e-runs/r-20261122-5d2cbc": "owner-notes candidate",
    "e2e-runs/spec-elaboration-20261120": "spec elaboration (stopped early)",
}


# --------------------------------------------------------------------------------------------------------- helpers

def vtuple(text):
    try:
        return tuple(int(part) for part in str(text).split("."))
    except ValueError:
        return None


def load_json(path):
    try:
        return json.loads(pathlib.Path(path).read_text(errors="replace"))
    except (OSError, ValueError):
        return None


def state_block(path):
    try:
        found = STATE_BLOCK.search(pathlib.Path(path).read_text(errors="replace"))
        return json.loads(found.group(1)) if found else None
    except (OSError, ValueError):
        return None


def git(repo, *args):
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, errors="replace",
                          check=False, env={**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_PAGER": "cat"})
    return done.stdout if done.returncode == 0 else None


def flat(text):
    return " ".join(str(text or "").split())


def median(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def pct(part, whole):
    return f"{part} of {whole} ({100.0 * part / whole:.0f}%)" if whole else f"{part} of 0"


def fmt(value, digits=1):
    return "-" if value is None else f"{value:.{digits}f}"


# ------------------------------------------------------------------------------------------------------- discovery

def find_invocations():
    for root in sorted(HOME.glob("e2e-runs*")):
        if not root.is_dir():
            continue
        for current, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in PRUNE and not d.startswith(("apparatus-", "source-", "."))
                       and not (d.startswith("prior") and False)]
            if "invocation.json" in files:
                yield pathlib.Path(current)


def release_commits():
    out = git(CANON, "log", "--format=%H%x09%s", "origin/main") or ""
    found = {}
    for line in out.splitlines():
        sha, _, subject = line.partition("\t")
        hit = re.match(r"release: .*\bshiploop (\d+\.\d+\.\d+)", subject)
        if hit:
            found[hit.group(1)] = sha     # the log is newest first; the oldest commit naming a version wins
    return found


BUILD_CACHE = {}


def build_kind(head, version, releases):
    key = (head, version)
    if key in BUILD_CACHE:
        return BUILD_CACHE[key]
    if not head:
        value = {"kind": "unknown", "files": [], "why": "no local_head recorded"}
    elif version not in releases:
        value = {"kind": "unknown", "files": [], "why": "no release commit for " + str(version)}
    elif git(CANON, "cat-file", "-e", head + "^{commit}") is None:
        value = {"kind": "unknown", "files": [], "why": "build commit not in the canonical repository"}
    else:
        names = (git(CANON, "diff", "--name-only", releases[version], head, "--",
                     "skills/shiploop", "skills/improve", "skills/until-loop") or "").split()
        value = {"kind": "release" if not names else "release+changes", "files": names,
                 "release_commit": releases[version]}
    BUILD_CACHE[key] = value
    return value


def run_dirs(folder):
    pointer = load_json(folder / "shiploop-run.json") or {}
    named = pointer.get("run_dir")
    found = sorted(p.parent for p in folder.glob(".shiploop-runs/*/run/state.md"))
    if named and (pathlib.Path(named) / "state.md").exists():
        return [pathlib.Path(named)], [p for p in found if p != pathlib.Path(named)]
    return found, []


# ------------------------------------------------------------------------------------------- knowledge text labels

# The record's words, read clause by clause (a clause ends at . ; : or a dash).  A clause says a change when it has a
# change word that is not negated ("no lines added"), not a reference to another step or an earlier stage ("were
# recorded in S1", "already recorded") and not future or conditional ("may be revised").  The record says-changed
# when any clause does; says-unchanged when none does and some clause gives a no-change cue; otherwise unclear.
# Changes the step's own implement or test stage made count as the step's ("AD-7 added at implement"): the record
# speaks for the step (its result-template placeholder: "the lines this step added ... or why none").
_NOW_VERB = (r"now (?:\w+ )?(?:point|name|list|hold|record|say|state|describe|include|carr|cite|show|has|have|give|"
             r"mark|read|match|contain|cover|refer|document|note|link|map|tie|use|spell|own|report|distinguish)\w*")
CHANGE_WORDS = re.compile(
    r"\b(add(?:ed|s|ing)?|gain(?:ed|s)?|recorded|records|updated?|updates|marked|corrected|replaced|renamed|moved|"
    r"removed|documented|placed|refined|narrowed|extended|expanded|noted|appended|inserted|rewr(?:ote|itten)|revised|"
    r"clarified|filled|wrote|(?:re)?organi[sz]ed|restructured|consolidated|renumbered|" + _NOW_VERB + r"|new lines?|lines? (?:inside|under|in|at|for|ending)|"
    r"(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+) (?:new |implemented |implementation |evidence )?lines?)\b|"
    r"\((?:W\d+/S\d+)\)", re.I)
STRONG_CHANGE = re.compile(r"\b(?:added|adds|gain(?:ed|s)|corrected|replaced|marked|moved|renamed|removed|updated|"
                           r"rewr(?:ote|itten)|appended|inserted|" + _NOW_VERB + r")\b|\((?:W\d+/S\d+)\)", re.I)
NO_CHANGE_CUE = re.compile(
    r"^\W*(?:no|none|nothing|unchanged|n/?a)\b|\b(?:already|remain(?:s|ed)?|still|unchanged|no change|no changes|"
    r"as (?:written|recorded|planned|accepted|built|designed|specified|documented|before)|without (?:a |any )?change|"
    r"no edits?|needed no|need no|not needed|no (?:\w+ )?(?:needed|required)|held|holds|hold\b|accurate|correct\b|"
    r"(?:without|with no|no) (?:\w+ ){0,2}(?:change|changes|amendments?|edits?)|confirmed|"
    r"match(?:es|ed)?|cover(?:s|ed)?|describes?|implemented as|followed|follows|kept|left as)\b", re.I)
VERDICT_UNCHANGED = re.compile(r"^\W*(?:no change|no changes|unchanged|none|nothing|no edits?|no updates?|"
                               r"no new (?:ad|commands?|harness\w*|facts?|decisions?|requirements?)\b)", re.I)
NEGATED = re.compile(r"\b(?:no|not|none|nothing|never|without)\s+(?:\w+\s+){0,3}?(?:(?:was|were|is|are|been)\s+)?"
                     r"(?:add(?:ed)?|record(?:ed)?|chang(?:e|ed)|updat(?:e|ed)|mark(?:ed)?|correct(?:ed)?|replac(?:e|ed)|"
                     r"mov(?:e|ed)|remov(?:e|ed)|document(?:ed)?|plac(?:e|ed)|refin(?:e|ed)|writ(?:e|ten)|edit(?:s|ed)?|"
                     r"lines?|new)\b", re.I)
REFERENCE = re.compile(r"\b(?:already\s+(?:\w+\s+)?\w+|previously\s+\w+|earlier|before this step|by an earlier|"
                       r"existing\s+(?:documented|recorded)\s+\w+|"
                       r"in an earlier|(?:the|existing|already)\s+recorded|"
                       r"(?:was|were|is|are|been) (?:\w+ )?(?:added|recorded|written|documented|noted|listed|placed)\s+"
                       r"(?:in|at|by|during)\s+(?:S\d+|W\d+|step \d|the (?:plan|spec|test-strategy|step-plan|"
                       r"prepare)|plan|spec|test-strategy|step-plan|prepare|discovery|research))\b", re.I)
FUTURE = re.compile(r"\b(?:may|might|will|would|could|should|must|to)\s+(?:be\s+|later\s+)?\w+(?:ed|en)\b|"
                    r"\b(?:until|once|when|if)\b", re.I)


# A product decision record outside the knowledge home ("decision 9 records ...", "recorded in ADR 9") is another file.
OTHER_RECORD = re.compile(r"\b(?:(?:product |repository |project )?(?:decision|ADR|decision record)\s+\d+(?:\s+in the [\w ]+?)?"
                          r"\s+(?:now\s+)?(?:records?|recorded|has|holds|captures|documents?|describes?)\b[^.;]*|"
                          r"(?:recorded|documented|captured)\s+(?:as|in)\s+(?:product |repository )?(?:decision|ADR)\s+\d+"
                          r"|(?:now\s+)?has the [\w ]+ in (?:ADR|decision) \d+)", re.I)


def _strip_non_changes(clause):
    stripped = OTHER_RECORD.sub(" ", clause)
    stripped = NEGATED.sub(" ", stripped)
    stripped = REFERENCE.sub(" ", stripped)
    return re.sub(r"\bas (?:written|recorded|planned|accepted|built|designed|specified|documented)\b", " ", stripped,
                  flags=re.I)


def clause_kind(clause):
    if not CHANGE_WORDS.search(clause):
        return "unchanged" if NO_CHANGE_CUE.search(clause) else "none"
    stripped = _strip_non_changes(clause)
    if not CHANGE_WORDS.search(stripped):
        return "unchanged"
    if FUTURE.search(clause) and not STRONG_CHANGE.search(stripped):
        return "none"
    if VERDICT_UNCHANGED.match(clause) and not STRONG_CHANGE.search(stripped):
        return "unchanged"
    return "change"


def label_record(text):
    """says-changed / says-unchanged / unclear, from the record's words (rules above; checked against the diffs).

    A record that opens with a no-change verdict ("No change: ...", "none: ...") needs a strong change word
    (added, gained, corrected, now names, a (Wn/Sm) mark ...) in a later clause to count as a change.
    """
    text = flat(text)
    if not text:
        return "empty"
    if text.startswith("Unchanged: ") and "ShipLoop recorded" in text:
        return "auto"
    clauses = [c for c in re.split(r"(?<=[.;:])\s+|\s+[—–]\s+|\s+-\s+", text) if c.strip()]
    verdict_unchanged = bool(VERDICT_UNCHANGED.match(text))
    kinds = []
    for clause in clauses:
        kind = clause_kind(clause)
        if kind == "change" and verdict_unchanged and not STRONG_CHANGE.search(_strip_non_changes(clause)):
            kind = "unchanged"
        kinds.append(kind)
    if "change" in kinds:
        return "says-changed"
    if "unchanged" in kinds or verdict_unchanged:
        return "says-unchanged"
    return "unclear"


# ------------------------------------------------------------------------------------------------------ per run

def _gate_files(record):
    block = str(record.get("block") or "")
    scope = re.search(r"Scope: (\d+) files? changed since the base[^\n]*\n((?:- [A-Z]\d* [^\n]+\n?)*)", block)
    if scope:
        files = []
        for line in scope.group(2).splitlines():
            parts = line[2:].split(" ", 1)
            if len(parts) == 2:
                files.append(parts[1].split(" -> ")[-1].strip())
        return files
    if re.search(r"Scope: 0 files", block) or "no files changed" in block.lower():
        return []
    return None


def lint_gate_scope(run, action):
    """Files the document stage itself changed (its last lint gate record with stage 'document': base "the tree this
    stage began from") and files its step review changed (last record with stage 'step review'); None when absent."""
    gates = sorted(run.glob(f"lint/{action}.gate*.md"),
                   key=lambda p: int(re.search(r"\.gate(\d+)\.md$", p.name).group(1)))
    own, review = None, None
    for path in gates:
        record = state_block(path) or {}
        stage = record.get("stage")
        entry = {"files": _gate_files(record), "base": str(record.get("base") or ""), "gate": path.name}
        if stage == "document" or (stage is None and "the tree this stage began from" in entry["base"]):
            own = entry
        elif stage == "step review" or "the tree the review began from" in entry["base"]:
            review = entry
    if own is None and review is None:
        return None
    return {**(own or {"files": None, "base": "", "gate": None}), "review_files": (review or {}).get("files"),
            "review_gate": (review or {}).get("gate")}


def passes_rows(path):
    rows = []
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError:
        return rows
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 8 and cells[1].isdigit():
            rows.append({"stage": cells[0], "pass": int(cells[1]), "label": cells[2], "tree": cells[3] == "y",
                         "result": cells[4] == "y", "edited": cells[5] == "y",
                         "lines": int(cells[6]) if cells[6].isdigit() else 0,
                         "seconds": float(cells[7]) if re.fullmatch(r"[\d.]+", cells[7]) else 0.0})
    return rows


def review_changed_lines(review_dir):
    out = []
    for path in sorted(review_dir.glob("reviews/review-*.md")):
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        hit = re.search(r"^Changed:\s*(.*)$", text, re.M)
        if hit:
            out.append(flat(hit.group(1))[:400])
    return out


def down_spans(folder):
    spans, ended = [], None
    try:
        rows = [json.loads(l) for l in (folder / "sessions.jsonl").read_text(errors="replace").splitlines() if l.strip()]
    except (OSError, ValueError):
        return spans
    for row in rows:
        moment = row.get("t")
        if row.get("row") == "end":
            ended = moment
        elif row.get("row") == "start" and isinstance(ended, (int, float)) and isinstance(moment, (int, float)):
            if moment > ended:
                spans.append((ended, moment))
            ended = None
    return spans


def stage_seconds(trace_rows, spans):
    """Seconds by stage (review:<stage> for a review), net of host-down spans; gaps over IDLE left out."""
    reviewed = {r.get("action"): r.get("reviewed") for r in trace_rows if r.get("kind") == "packet" and r.get("stage") == "improve"}
    commands = [r for r in trace_rows if r.get("kind") == "command" and isinstance(r.get("ts"), (int, float))]
    seconds, down, idle = collections.Counter(), collections.Counter(), 0.0
    for before, row in zip(commands, commands[1:]):
        gap = row["ts"] - before["ts"]
        if gap < 0:
            continue
        if gap > IDLE:
            idle += gap
            continue
        lost = sum(max(0.0, min(end, row["ts"]) - max(begin, before["ts"])) for begin, end in spans)
        stage = row.get("stage")
        stage = stage[0] if isinstance(stage, list) else stage
        if stage == "improve":
            cursor = row.get("cursor")
            action = cursor[0] if isinstance(cursor, list) else row.get("action")
            stage = "review:" + str(reviewed.get(action) or "?")
        if stage:
            seconds[str(stage)] += gap
            down[str(stage)] += lost
    net = {k: seconds[k] - down.get(k, 0.0) for k in seconds}
    return net, sum(down.values()), idle


def read_trace(run):
    rows = []
    try:
        for line in (run / "trace.jsonl").read_text(errors="replace").splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        pass
    return rows


def notices(folder):
    """Unique ShipLoop placement and knowledge notice lines the host was shown (events.jsonl, else transcript.md)."""
    found = {"placement": set(), "knowledge": set()}
    source = None
    for name in ("events.jsonl", "transcript.md"):
        path = folder / name
        if not path.exists():
            continue
        source = name
        try:
            with path.open(errors="replace") as handle:
                for raw in handle:
                    if PLACEMENT not in raw and KNOWLEDGE_NOTICE not in raw:
                        continue
                    texts = []
                    if name.endswith(".jsonl"):
                        try:
                            stack = [json.loads(raw)]
                        except ValueError:
                            stack = [raw]
                        while stack:
                            item = stack.pop()
                            if isinstance(item, dict):
                                stack.extend(item.values())
                            elif isinstance(item, list):
                                stack.extend(item)
                            elif isinstance(item, str) and (PLACEMENT in item or KNOWLEDGE_NOTICE in item):
                                texts.append(item)
                    else:
                        texts.append(raw)
                    for text in texts:
                        for line in text.splitlines():
                            for prefix, key in ((PLACEMENT, "placement"), (KNOWLEDGE_NOTICE, "knowledge")):
                                at = line.find(prefix)
                                # A real notice names an absolute path under docs/shiploop right after the prefix;
                                # ShipLoop's own guidance quotes the prefix in prose and in grep examples, which are not
                                # notices.
                                if at >= 0 and re.match(re.escape(prefix) + r"/\S+/docs/shiploop/[a-z.]+\.md ", line[at:]):
                                    found[key].add(flat(line[at:])[:900])
        except OSError:
            continue
        if found["placement"] or found["knowledge"]:
            break
    return found, source


def headings(text):
    out, fence = [], False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fence = not fence
            continue
        if fence:
            continue
        hit = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if hit:
            out.append((len(hit.group(1)), hit.group(2).strip()))
    return out


def classify_headings(name, text):
    named = SECTIONS[name]
    level2 = [title for level, title in headings(text) if level == 2]
    matched = collections.defaultdict(list)
    unnamed = []
    for title in level2:
        word = next((w for w in named if title.lower().startswith(w.lower())), None)
        if word is None:
            unnamed.append(title)
        else:
            matched[word].append(title)
    repeats = {w: t for w, t in matched.items() if len(t) > 1}
    missing = [w for w in named if w not in matched]
    return {"level2": len(level2), "unnamed": unnamed, "repeats": repeats, "missing_named": missing}


def stage_of_subject(subject):
    hit = KNOWLEDGE_SUBJECT.match(subject)
    if hit:
        return "knowledge " + hit.group(2) + " " + hit.group(3)
    if STEP_SUBJECT.match(subject):
        return "step commit (implement/test/document + step review)"
    if subject.startswith("chore(shiploop): commit files written after the last work item"):
        return "chore after the last item"
    if subject.startswith("base:") or "baseline" in subject.lower():
        return "base"
    return "other (Improve review or host commit)"


STEP_MARK = re.compile(r"\(W\d+/S\d+\)")
ANY_MARK = re.compile(r"\((?:W\d+(?:/S\d+)?)\)|\bW\d+\b")
SATISFIED_WORDS = re.compile(r"\b(satisf\w*|met\b|meets?\b|met by|pass(?:es|ed)?\b|implemented|verified|observed|"
                             r"holds?\b|done\b|delivered|in place|covered by|proved|confirmed)", re.I)
GAP_WORDS = re.compile(r"\b(gap|open\b|not yet|pending|unverified|missing|to do|todo|not covered|still to|deferred|"
                       r"outstanding|due at|unresolved|not met|fails?\b|blocked|later item|owner|not observed|"
                       r"untested|remains? (?:open|unverified|unproven))", re.I)


def appended_kind(line):
    gap, met = bool(GAP_WORDS.search(line)), bool(SATISFIED_WORDS.search(line))
    return "open-gap" if gap else ("satisfied" if met else "other")


STATUS_LINE = re.compile(r"^\W*(?:basis|pending|met\b|met by|met so far|observed|implemented|status|evidence|satisfied|"
                         r"confirmed|verified|done|open gap|gap|proved|covered|tested|checked|built|not yet|still to)", re.I)
TEST_ID = re.compile(r"\b(?!(?:R|AD|RB|S|W)-\d)[A-Z][A-Z0-9]{0,5}(?:[-_.][A-Z]{0,3}\d+)+(?:\s*\([a-z]\))?")


def _replaced_pairs(a, b):
    """(old line, new line or None) for each line an edit replaced or deleted, plus the inserted new lines."""
    pairs, inserted = [], []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "insert":
            inserted += [line for line in b[j1:j2] if line.strip()]
        elif tag in ("delete", "replace"):
            olds = [line for line in a[i1:i2] if line.strip()]
            news = [line for line in b[j1:j2] if line.strip()] if tag == "replace" else []
            for index, line in enumerate(olds):
                pairs.append((line, news[index] if index < len(news) else None))
            inserted += news[len(olds):]
    return pairs, inserted


def spec_change(before, after):
    """How one edit changed spec.md, entry by entry (R-<n> spans from shiploop_knowledge_home._entries):

    appended   an existing entry gained new lines (an insert; it may also have class b lines)  (coordinator's class a)
    rewritten  an existing entry lost or changed a line (whitespace-only excluded)             (class b); each changed
               line is a step line (it carries a step mark '(Wn/Sm)'), an unmarked status/basis/evidence line
               (starts Basis, Pending, Met, Observed, Implemented ...), or contract text (any other unmarked line:
               the requirement statement and its acceptance lines); 'ids_removed' counts changed lines that lost
               test-ID tokens (TC-1, DUE-01, TC_1_1 ...)
    added      an entry ID the old file did not hold                                           (class c)
    retired    an entry that was live and now sits under a '## Retired' heading               (class d)
    removed    an entry ID that disappeared; unretired: back out of Retired
    outside    changed non-blank lines that belong to no entry (headings, preamble, notes)
    """
    before, after = before or "", after or ""
    old = knowledge_home._entries(before, "R") if before.strip() else {}
    new = knowledge_home._entries(after, "R") if after.strip() else {}
    out = {"appended": {}, "rewritten": {}, "added": [], "retired": [], "removed": [], "unretired": [],
           "whitespace_only": [], "outside": []}
    for ident, entry in new.items():
        if ident not in old:
            out["added"].append(ident + (" (under Retired)" if entry.retired else ""))
            continue
        prior = old[ident]
        if not prior.retired and entry.retired:
            out["retired"].append(ident)
        if prior.retired and not entry.retired:
            out["unretired"].append(ident)
        if prior.text == entry.text:
            continue
        a, b = prior.text.splitlines(), entry.text.splitlines()
        pairs, inserted = _replaced_pairs(a, b)
        real = [(o, n) for o, n in pairs if n is None or flat(o) != flat(n)]
        if pairs and not real and not inserted:
            out["whitespace_only"].append(ident)
            continue
        if real:
            def kind(old, new):
                heading_old, heading_new = re.match(r"^(#+)\s+(.*)$", old.strip()), re.match(r"^(#+)\s+(.*)$", (new or "").strip())
                if heading_old and heading_new and flat(heading_old.group(2)) == flat(heading_new.group(2)):
                    return "heading level"
                return ("step line" if STEP_MARK.search(old) else
                        "status/basis/evidence" if STATUS_LINE.search(old) else "contract text")
            kinds = collections.Counter(kind(o, n) for o, n in real)
            words = []
            for o, n in real:
                if kind(o, n) in ("contract text", "status/basis/evidence"):
                    ow, nw = flat(o).split(), flat(n).split()
                    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ow, nw, autojunk=False).get_opcodes():
                        if tag != "equal":
                            words.append(f"-[{' '.join(ow[i1:i2])[:120]}] +[{' '.join(nw[j1:j2])[:120]}]")
            out["rewritten"][ident] = {
                "was": [flat(o)[:240] for o, _ in real], "now": [flat(n)[:240] for _, n in real if n],
                "deleted": sum(1 for _, n in real if n is None),
                "step_lines": kinds["step line"], "status_lines": kinds["status/basis/evidence"],
                "contract_lines": kinds["contract text"], "heading_level_lines": kinds["heading level"],
                "requirement_lines": kinds["status/basis/evidence"] + kinds["contract text"],
                "word_changes": words[:12],
                "ids_removed": sum(1 for o, n in real if len(TEST_ID.findall(o)) > len(TEST_ID.findall(n or ""))),
                "heading_changed": bool(a and b and a[0] != b[0])}
        if inserted:
            out["appended"][ident] = [{"line": flat(x)[:240], "kind": appended_kind(x), "marked": bool(ANY_MARK.search(x))}
                                      for x in inserted]
    out["removed"] = [ident for ident in old if ident not in new]
    spans = set()
    for entry in list(old.values()) + list(new.values()):
        spans.update(line for line in entry.text.splitlines() if line.strip())
    a, b = before.splitlines(), after.splitlines()
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag != "equal":
            out["outside"] += [flat(x)[:200] for x in a[i1:i2] + b[j1:j2] if x.strip() and x not in spans]
    out["classes"] = [name for name, key in (("a appended", "appended"), ("b rewritten", "rewritten"), ("c added", "added"),
                                             ("d retired", "retired"), ("removed", "removed"), ("unretired", "unretired"),
                                             ("outside entries", "outside")) if out[key]]
    return out


def spec_change_of_commit(repo, sha):
    before = git(repo, "show", f"{sha}^:docs/shiploop/spec.md")
    after = git(repo, "show", f"{sha}:docs/shiploop/spec.md")
    if after is None:
        return None
    return spec_change(before or "", after)


def classify_path(path):
    if path.startswith("docs/shiploop/"):
        return "home"
    lower = path.lower()
    if re.search(r"(^|/)(test|tests|__tests__|spec)/|\.test\.|_test\.|\.spec\.|test-support", lower):
        return "tests"
    if lower.endswith((".md", ".txt", ".rst", ".adoc")) or lower.startswith("docs/"):
        return "docs"
    return "code"


def read_run(folder, run, invocation, releases, now):
    state = state_block(run / "state.md")
    if state is None:
        return {"folder": str(folder), "run": str(run), "error": "state.md unreadable"}
    versions = invocation.get("versions") or {}
    version = versions.get("shiploop_version")
    build = build_kind(versions.get("local_head") or invocation.get("local_head"), version, releases)
    rel = str(folder.relative_to(HOME))
    group = "/".join(rel.split("/")[:2])
    history = state.get("history") or []
    accepted = state.get("accepted") or {}
    trace = read_trace(run)
    live = False
    try:
        live = (now - (run / "trace.jsonl").stat().st_mtime) < 20 * 60 and state.get("status") not in ("done", "blocked", "halted")
    except OSError:
        pass
    record = {
        "folder": str(folder), "run": str(run), "group": group, "label": GROUP_LABELS.get(group, ""),
        "case": invocation.get("case"), "host": invocation.get("host"), "model": invocation.get("model"),
        "effort": invocation.get("effort"), "version": version, "build": build["kind"], "build_files": build["files"],
        "build_head": versions.get("local_head"), "status": state.get("status"), "stage": state.get("stage"),
        "live": live, "planning_review": state.get("planning_review"),
        "follow_on": bool(invocation.get("follow_on")), "resumed": bool(invocation.get("resumed_run")),
        "owner_note_at": invocation.get("owner_note_at"), "run_id": state.get("run_id"),
        "first_at": next((r.get("at") for r in trace if r.get("at")), None),
    }
    record["driver"] = f"{record['host']} {record['model']} {record['effort'] or '-'}"

    # ---- plan and queue
    first_step_plan = next((i for i, h in enumerate(history) if h["stage"] == "step-plan"), len(history))
    plans = [h for h in history[:first_step_plan] if h["stage"] == "plan" and h["outcome"] == "done"]
    plan_row = plans[-1] if plans else next((h for h in history if h["stage"] == "plan" and h["outcome"] == "done"), None)
    plan_items = (accepted.get(plan_row["action"]) or {}).get("work_items") if plan_row else None
    record["plan_rows"] = sum(1 for h in history if h["stage"] == "plan")
    record["plan_items"] = len(plan_items) if isinstance(plan_items, list) else None
    record["plan_item_ids"] = [w.get("id") for w in plan_items] if isinstance(plan_items, list) else None
    items_order = []
    for h in history:
        if h["stage"] in INNER and h.get("workitem") and h["workitem"] not in items_order:
            items_order.append(h["workitem"])
    record["items_executed"] = items_order
    record["completed_items"] = list(state.get("completed_work_items") or [])
    record["final_queue_ids"] = [w.get("id") for w in state.get("work_items") or []]

    queue, completed = [], []
    carry, add_work = [], []
    for index, h in enumerate(history):
        result = accepted.get(h["action"]) or {}
        if h["stage"] == "plan" and h["outcome"] == "done" and isinstance(result.get("work_items"), list):
            queue = json.loads(json.dumps(result["work_items"]))
        if h["outcome"] == "add-work":
            added = result.get("work_items") or []
            add_work.append({"stage": h["stage"], "ids": [w.get("id") for w in added],
                             "titles": [flat(w.get("title"))[:120] for w in added], "summary": flat(result.get("summary"))[:300]})
            queue.extend(json.loads(json.dumps(added)))
        if h["stage"] == "carry-forward":
            item = h.get("workitem")
            ids = [w.get("id") for w in queue]
            pos = ids.index(item) if item in ids else None
            before = queue[pos + 1:] if pos is not None else []
            row = {"item": item, "action": h["action"], "outcome": h["outcome"], "index_in_run": len(carry) + 1,
                   "future_before": [w.get("id") for w in before], "supplied": "work_items" in result,
                   "skill": result.get("skill") if isinstance(result.get("skill"), dict) else None,
                   "skill_raw_type": type(result.get("skill")).__name__,
                   "summary": flat(result.get("summary"))[:600]}
            if h["outcome"] == "done" and "work_items" in result:
                after = result.get("work_items") or []
                bmap = {w.get("id"): w for w in before}
                amap = {w.get("id"): w for w in after}
                kept = [i for i in amap if i in bmap]
                row["future_after"] = [w.get("id") for w in after]
                row["added"] = [i for i in amap if i not in bmap]
                row["removed"] = [i for i in bmap if i not in amap]
                row["reordered"] = [i for i in [w.get("id") for w in before] if i in amap] != kept
                row["context_edited"] = [i for i in kept if flat(bmap[i].get("context")) != flat(amap[i].get("context"))]
                row["title_edited"] = [i for i in kept if flat(bmap[i].get("title")) != flat(amap[i].get("title"))]
                row["follows_edited"] = [i for i in kept if (bmap[i].get("follows") or []) != (amap[i].get("follows") or [])]
                row["added_titles"] = [flat(amap[i].get("title"))[:160] for i in row["added"]]
                row["unchanged"] = not (row["added"] or row["removed"] or row["reordered"] or row["context_edited"]
                                        or row["title_edited"] or row["follows_edited"])
                row["includes_current_or_done"] = [i for i in amap if i == item or i in completed]
                queue = queue[:pos + 1] + json.loads(json.dumps(after)) if pos is not None else queue + json.loads(json.dumps(after))
            if h["outcome"] == "done":
                completed.append(item)
                row["future_left"] = len(queue) - (queue.index(next(w for w in queue if w.get("id") == item)) + 1) if item in [w.get("id") for w in queue] else None
            carry.append(row)
    record["carry_forward"] = carry
    record["add_work"] = add_work
    record["queue_matches_state"] = [w.get("id") for w in queue] == record["final_queue_ids"]

    # ---- step plans, send-backs, documents
    step_plans = collections.defaultdict(list)
    sendbacks, documents = [], []
    docs_since_plan = collections.Counter()
    current_plan = {}
    outcomes = collections.Counter()
    for h in history:
        outcomes[(h["stage"], h["outcome"])] += 1
        item = h.get("workitem")
        result = accepted.get(h["action"]) or {}
        if h["stage"] == "step-plan" and h["outcome"] == "done":
            step_plans[item].append(len(result.get("steps") or []))
            docs_since_plan[item] = 0
            current_plan[item] = h["action"]
        elif h["stage"] == "document" and h["outcome"] == "done":
            docs_since_plan[item] += 1
            knowledge = result.get("knowledge")
            auto = flat(result.get("summary")).startswith(NOT_APPLICABLE)
            gate = lint_gate_scope(run, h["action"])
            doc = {"item": item, "step_index": docs_since_plan[item], "plan_action": current_plan.get(item),
                   "action": h["action"], "auto": auto,
                   "has_record": isinstance(knowledge, dict), "gate": gate, "labels": {}, "texts": {},
                   "stage_changed": {}, "review_changed": {}, "summary": flat(result.get("summary"))[:300]}
            for key, name in RECORD_KEYS:
                text = flat((knowledge or {}).get(key)) if isinstance(knowledge, dict) else ""
                doc["texts"][key] = text
                doc["labels"][key] = "auto" if auto else label_record(text)
                if gate and gate.get("files") is not None:
                    doc["stage_changed"][key] = ("docs/shiploop/" + name) in gate["files"]
                if gate and gate.get("review_files") is not None:
                    doc["review_changed"][key] = ("docs/shiploop/" + name) in gate["review_files"]
            documents.append(doc)
        if h["outcome"] == "send-back":
            sendbacks.append({"stage": h["stage"], "item": item, "late": bool(item and docs_since_plan[item] >= 1),
                              "documented_steps": docs_since_plan[item] if item else None,
                              "steps_in_plan": (step_plans[item][-1] if item and step_plans[item] else None),
                              "summary": flat(result.get("summary") or h.get("summary"))[:300]})
    record["step_plans"] = dict(step_plans)
    record["sendbacks"] = sendbacks
    record["documents"] = documents
    record["outcomes"] = {f"{s}|{o}": n for (s, o), n in outcomes.items()}

    # ---- product repository: knowledge commits, step diffs, final sizes, skills
    repo = pathlib.Path(str(state.get("repo") or ""))
    if not (repo / ".git").exists():
        repo = folder / "work"
    record["repo"] = str(repo)
    first_ts = next((r.get("ts") for r in trace if isinstance(r.get("ts"), (int, float))), None)
    log = git(repo, "log", "--format=%H%x09%ct%x09%s", "HEAD")
    commits = []
    if log is not None:
        for line in log.splitlines():
            parts = line.split("\t", 2)
            if len(parts) == 3:
                commits.append({"sha": parts[0], "t": int(parts[1]), "subject": parts[2]})
    commits.reverse()
    mine = [c for c in commits if first_ts is None or c["t"] >= first_ts - 120]
    record["repo_readable"] = log is not None
    record["commits_in_run"] = len(mine)
    by_stage = collections.Counter()
    home_by_stage = collections.Counter()
    cf_commits = []
    cf_accepts = [(r["ts"], a.get("action"), a.get("item")) for r in trace if r.get("kind") == "command"
                  and isinstance(r.get("ts"), (int, float))
                  for a in (r.get("accepted") or []) if a.get("stage") == "carry-forward" and a.get("outcome") == "done"]
    for commit in mine:
        label = stage_of_subject(commit["subject"])
        by_stage[label] += 1
        stat = git(repo, "show", "--numstat", "--format=", commit["sha"], "--", "docs/shiploop") or ""
        files = {}
        for line in stat.splitlines():
            parts = line.split("\t")
            if len(parts) == 3:
                files[parts[2]] = (int(parts[0]) if parts[0].isdigit() else 0, int(parts[1]) if parts[1].isdigit() else 0)
        commit["home_files"] = files
        if files:
            home_by_stage[label] += 1
        if label == "knowledge after carry-forward":
            near = min(cf_accepts, key=lambda acc: abs(acc[0] - commit["t"]), default=None)
            entry = {"sha": commit["sha"], "files": {k.rsplit("/", 1)[-1]: v for k, v in files.items()},
                     "cf_action": near[1] if near and abs(near[0] - commit["t"]) <= 300 else None,
                     "matched_accept_s": round(abs(near[0] - commit["t"]), 1) if near else None}
            if "spec.md" in entry["files"]:
                entry["spec_change"] = spec_change_of_commit(repo, commit["sha"])
            cf_commits.append(entry)
    record["commit_stages"] = dict(by_stage)
    record["home_commit_stages"] = dict(home_by_stage)
    record["cf_knowledge_commits"] = cf_commits
    by_action = {c["cf_action"]: c for c in cf_commits if c["cf_action"]}
    for row in carry:
        commit = by_action.get(row["action"])
        row["home_commit"] = ({"sha": commit["sha"], "files": commit["files"], "spec_change": commit.get("spec_change")}
                              if commit else None)
    record["cf_commits_unmatched"] = sum(1 for c in cf_commits if not c["cf_action"])

    # step-level home edits (implement + test + document + step review), from the item's iteration record
    steps_home = []
    for item in items_order:
        plans_record = (load_json(run / "iterations" / f"{item}.json") or {}).get("plans") or {}
        for plan_action, steps in plans_record.items():
            for step_id, step in (steps or {}).items():
                base, commit = step.get("base"), step.get("commit")
                if not (base and commit):
                    continue
                names = (git(repo, "diff", "--name-only", base, commit, "--", "docs/shiploop") or "").split()
                steps_home.append({"item": item, "step": step_id, "plan": plan_action, "number": step.get("number"),
                                   "commit": commit, "home": [n.rsplit("/", 1)[-1] for n in names]})
    record["steps_home"] = steps_home
    by_step = {(s["plan"], s["number"]): s for s in steps_home}
    for doc in documents:
        step = by_step.get((doc["plan_action"], doc["step_index"]))
        doc["step_commit"] = step["commit"] if step else None
        doc["step_changed"] = {key: name in step["home"] for key, name in RECORD_KEYS} if step else {}

    # final sizes and headings
    sizes = {}
    start_head = ((invocation.get("base") or {}).get("start_head") or (invocation.get("follow_on") or {}).get("start_head"))
    for name in LIVING:
        text = git(repo, "show", f"HEAD:docs/shiploop/{name}") if log is not None else None
        start = git(repo, "show", f"{start_head}:docs/shiploop/{name}") if start_head and log is not None else None
        if text is None:
            sizes[name] = None
            continue
        info = {"bytes": len(text.encode()), "lines": text.count("\n") + (0 if text.endswith("\n") else 1),
                "start_bytes": len(start.encode()) if start is not None else 0, **classify_headings(name, text)}
        introduced = {}
        for title in info["unnamed"]:
            found = git(repo, "log", "--reverse", "--format=%ct%x09%s", "-S", "## " + title, "HEAD", "--",
                        f"docs/shiploop/{name}") or ""
            first = found.splitlines()[0].split("\t", 1) if found.strip() else None
            if not first:
                introduced[title] = "unknown"
            elif first_ts is not None and int(first[0]) < first_ts - 120:
                introduced[title] = "before this run"
            else:
                introduced[title] = stage_of_subject(first[1])
        info["unnamed_introduced"] = introduced
        sizes[name] = info
    record["sizes"] = sizes
    skills_section = None
    env = git(repo, "show", "HEAD:docs/shiploop/environment.md") if log is not None else None
    if env:
        hit = re.search(r"^## Skills[^\n]*\n(.*?)(?=^## |\Z)", env, re.S | re.M)
        skills_section = flat(hit.group(1))[:300] if hit else None
    record["env_skills_section"] = skills_section
    added_skill_files = []
    if log is not None and mine:
        names = git(repo, "log", "--format=", "--name-only", "--diff-filter=A", f"{mine[0]['sha']}^..HEAD") \
            if len(mine) and git(repo, "rev-parse", "--verify", "-q", mine[0]["sha"] + "^") else \
            git(repo, "log", "--format=", "--name-only", "--diff-filter=A", "HEAD")
        added_skill_files = sorted({n for n in (names or "").split() if n.endswith("SKILL.md")})
    record["skill_files_added"] = added_skill_files

    # ---- notices the host was shown
    found, source = notices(folder)
    record["notice_source"] = source
    record["placement_notices"] = sorted(found["placement"])
    record["knowledge_notices"] = sorted(found["knowledge"])

    # ---- Improve reviews of document and carry-forward
    reviews = []
    for kind, actions in (("carry-forward", [c["action"] for c in carry]), ("document", [d["action"] for d in documents])):
        for action in actions:
            path = run / "improve" / action / "passes.md"
            rows = passes_rows(path)
            if not rows:
                continue
            entry = {"stage": kind, "action": action, "passes": len(rows), "edited": any(r["edited"] for r in rows),
                     "tree": any(r["tree"] for r in rows), "result": any(r["result"] for r in rows),
                     "lines": sum(r["lines"] for r in rows), "seconds": sum(r["seconds"] for r in rows),
                     "labels": [r["label"] for r in rows]}
            if kind == "carry-forward":
                entry["changed_text"] = review_changed_lines(path.parent)
                bind = state_block(run / "improve" / f"{action}-bind.md") or {}
                packets = [r for r in trace if r.get("kind") == "packet" and r.get("stage") == "improve"
                           and r.get("reviewed") == "carry-forward"]
                ids = {p.get("action") for p in packets}
                cmds = [r for r in trace if r.get("kind") == "command" and isinstance(r.get("cursor"), list)
                        and (r["cursor"][0] in ids)]
                start = min((p["ts"] for p in packets), default=None)
                end = max((r["ts"] for r in cmds), default=None)
                files = collections.Counter()
                review_commits = []
                if start and end:
                    for commit in mine:
                        if start - 2 <= commit["t"] <= end + 2 and stage_of_subject(commit["subject"]).startswith("other"):
                            names = (git(repo, "show", "--name-only", "--format=", commit["sha"]) or "").split()
                            row = {"subject": commit["subject"][:160], "files": names}
                            if "docs/shiploop/spec.md" in names:
                                row["spec_change"] = spec_change_of_commit(repo, commit["sha"])
                            review_commits.append(row)
                            for n in names:
                                files[classify_path(n)] += 1
                entry["review_commits"] = review_commits
                entry["review_file_kinds"] = dict(files)
                entry["bind_tree"] = bind.get("tree")
            reviews.append(entry)
    record["reviews"] = reviews

    # ---- minutes
    net, down, idle = stage_seconds(trace, down_spans(folder))
    record["seconds"] = {k: round(v, 1) for k, v in net.items()}
    record["down_s"] = round(down, 1)
    record["idle_s"] = round(idle, 1)
    return record


# ------------------------------------------------------------------------------------------------------ reporting

class Out:
    def __init__(self):
        self.lines = []

    def __call__(self, *parts):
        self.lines.append(" ".join(str(p) for p in parts))

    def table(self, header, rows):
        widths = [max(len(str(c)) for c in col) for col in zip(header, *rows)] if rows else [len(h) for h in header]
        self(" | ".join(str(h).ljust(w) for h, w in zip(header, widths)))
        self("-+-".join("-" * w for w in widths))
        for row in rows:
            self(" | ".join(str(c).ljust(w) for c, w in zip(row, widths)))


def pools(records):
    """(title, key function) pairs used for every pooled table."""
    return (("ShipLoop version / build", lambda r: f"{r['version']} {r['build']}"),
            ("driver (host model effort)", lambda r: r["driver"]),
            ("build kind, all versions and drivers", lambda r: "all " + r["build"] + " builds"))


def report(records, excluded, slices, agg_text, out):
    # A run whose trace moved in the last 20 minutes and that has not finished may still be running: its counts would
    # change between two reads, so it is kept in census.json but left out of every pooled table below.
    live_runs = [r for r in records if not r.get("error") and r.get("live")]
    whole = [r for r in records if not r.get("error") and not r.get("live")]
    finished = [r for r in whole if r["status"] == "done"]
    out("ShipLoop end-of-inner-loop census, run " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M %Z").strip())
    out("Read-only over ~/e2e-runs*/; every count below names its denominator.  'release' = the build's ShipLoop,")
    out("Improve and Until Loop trees equal that version's release commit; 'release+changes' = a candidate or")
    out("unreleased build (files listed in section 0).")
    out("")
    out("== 0. Corpus ==")
    out(f"whole-delivery ShipLoop runs at 2.4.0 or later: {len(whole)} (finished, status done: {len(finished)}); "
        f"errors: {sum(1 for r in records if r.get('error'))}; possibly still running, left out: {len(live_runs)}")
    older = {k: v for k, v in excluded.items() if k.startswith("runs before 2.4.0")}
    if older:
        out(f"  left out: {sum(older.values())} runs before 2.4.0 (versions "
            f"{min(older, key=lambda k: vtuple(k[19:-1]) or ())[19:-1]} to {max(older, key=lambda k: vtuple(k[19:-1]) or ())[19:-1]}; "
            f"{older.get('runs before 2.4.0 (2.3.0)', 0)} of them 2.3.0, the version current on 2026-11-20 until 18:55 PST)")
    for reason, count in sorted(excluded.items(), key=lambda kv: -kv[1]):
        if reason not in older:
            out(f"  left out: {count} {reason}")
    out(f"  step slices at 2.4.0 or later (not counted as deliveries): {len(slices)}; their stages: "
        f"{dict(collections.Counter(s['stages'] for s in slices))}")
    rows = []
    by_group = collections.defaultdict(list)
    for r in whole:
        by_group[(r["group"], r["version"], r["build"])].append(r)
    for (group, version, build), group_rows in sorted(by_group.items()):
        drivers = collections.Counter(r["driver"] for r in group_rows)
        rows.append((group, GROUP_LABELS.get(group, ""), version, build, len(group_rows),
                     sum(1 for r in group_rows if r["step_plans"]), sum(r["status"] == "done" for r in group_rows),
                     sum(r["follow_on"] for r in group_rows),
                     "; ".join(f"{d} x{n}" for d, n in drivers.most_common())))
    out.table(("folder group", "label", "version", "build", "runs", "reached a step plan", "finished", "follow-on",
               "drivers"), rows)
    inner = [r for r in whole if r["step_plans"]]
    out(f"runs that reached the inner loop (an accepted step plan): {len(inner)} of {len(whole)}; the rest stopped "
        f"earlier (stop-at-stage experiments or unfinished): {len(whole) - len(inner)}")
    out("")
    out("Builds that differ from their release (ShipLoop/Improve/Until Loop files changed):")
    seen = set()
    for r in whole:
        key = (r["build_head"], r["version"])
        if r["build"] != "release" and key not in seen:
            seen.add(key)
            out(f"  {r['version']} head {str(r['build_head'])[:12]} ({r['group']}): {', '.join(f.replace('skills/', '') for f in r['build_files'])}")
    if live_runs:
        out(f"Left out of every table: {len(live_runs)} unfinished runs whose trace changed in the last 20 minutes "
            f"(possibly still running; their records are in census.json): "
            + ", ".join(f"{r['folder'].replace(str(HOME) + '/', '')} ({r['version']} {r['build']}, at {r['stage']})"
                        for r in live_runs))
    statuses = collections.Counter(r["status"] for r in whole)
    out(f"status of all {len(whole)} runs: {dict(statuses)}; stage reached by the unfinished: "
        f"{dict(collections.Counter(r['stage'] for r in whole if r['status'] != 'done'))}")
    out("")

    out("== 1. agg.py (2026-11-12, unchanged) on runs.txt ==")
    out(agg_text.rstrip())
    out("")

    reached = [r for r in whole if any(c["outcome"] == "done" for c in r["carry_forward"])]
    out("== 1b. Work items and the carry-forward queue ==")
    out(f"runs with a done carry-forward: {len(reached)} of {len(whole)} (finished {len(finished)})")
    for title, key in pools(whole):
        out(f"-- by {title} (runs with an accepted plan) --")
        groups = collections.defaultdict(list)
        for r in whole:
            if r["plan_items"] is not None:
                groups[key(r)].append(r)
        rows = []
        for name, group_rows in sorted(groups.items()):
            plan_dist = collections.Counter(r["plan_items"] for r in group_rows)
            exec_dist = collections.Counter(len(r["items_executed"]) for r in group_rows if r["status"] == "done")
            cfs = [c for r in group_rows for c in r["carry_forward"] if c["outcome"] == "done"]
            mid = [c for c in cfs if c.get("future_before")]
            supplied = [c for c in cfs if c["supplied"]]
            rows.append((name, len(group_rows), dict(sorted(plan_dist.items())), dict(sorted(exec_dist.items())),
                         len(cfs), len(mid), len(supplied),
                         sum(1 for r in group_rows if r["add_work"]),
                         sum(len(a["ids"]) for r in group_rows for a in r["add_work"])))
        out.table(("pool", "runs", "items in accepted plan", "items executed (finished)", "cf done",
                   "cf with a later item queued", "cf supplying work_items", "runs with add-work", "items added by add-work"),
                  rows)
    out("")
    out("Every carry-forward that supplied work_items (what it did to the future queue):")
    any_supplied = False
    for r in whole:
        for c in r["carry_forward"]:
            if c["outcome"] == "done" and c["supplied"]:
                any_supplied = True
                what = []
                for field in ("added", "removed", "context_edited", "title_edited", "follows_edited"):
                    if c.get(field):
                        what.append(f"{field} {c[field]}")
                if c.get("reordered"):
                    what.append("reordered")
                if c.get("includes_current_or_done"):
                    what.append(f"names current/done {c['includes_current_or_done']}")
                out(f"  {r['version']} {r['build']} | {r['driver']} | {r['folder'].replace(str(HOME) + '/', '')} | {c['item']}: "
                    f"before {c['future_before']} -> after {c.get('future_after')}: {'; '.join(what) or 'unchanged (re-submitted as it was)'}"
                    + (f" | added titles {c['added_titles']}" if c.get("added_titles") else ""))
    if not any_supplied:
        out("  none")
    out("Every add-work (outer stages adding items):")
    for r in whole:
        for a in r["add_work"]:
            out(f"  {r['version']} {r['build']} | {r['driver']} | {r['folder'].replace(str(HOME) + '/', '')} | at {a['stage']}: "
                f"{a['ids']} {a['titles']}")
    planned = [r for r in whole if r["plan_items"] is not None]
    mismatched = [r for r in planned if not r["queue_matches_state"]]
    out(f"queue replay (plan, then carry-forward replacements and add-work appends) agrees with state.md work_items in "
        f"{len(planned) - len(mismatched)} of {len(planned)} runs with an accepted plan"
        + (": differs in " + ", ".join(r["folder"].replace(str(HOME) + "/", "") for r in mismatched) if mismatched else ""))
    out("")

    out("== 2. Carry-forward skill decisions ==")
    for title, key in pools(whole):
        out(f"-- by {title} --")
        groups = collections.defaultdict(collections.Counter)
        for r in whole:
            for c in r["carry_forward"]:
                if c["outcome"] == "done":
                    decision = (c["skill"] or {}).get("decision") if c["skill"] else f"(no skill object: {c['skill_raw_type']})"
                    groups[key(r)][decision] += 1
        out.table(("pool", "done carry-forwards", "decisions"),
                  [(k, sum(v.values()), dict(v)) for k, v in sorted(groups.items())])
    reasons = [(r, c) for r in whole for c in r["carry_forward"] if c["outcome"] == "done" and c["skill"]]
    themes = (("one step / one item / single change", r"\b(?:one|single|a single) (?:step|item|route|feature|change|module|"
               r"implementation|focused|conventional|scoped|native|test)|\bone step in one item"),
              ("nothing repeated or recurring", r"\bno (?:\w+ )?(?:procedure|repeat\w*|recurr\w*)|\bnot? (?:repeat|recur)\w*|"
               r"repeated"),
              ("no repository skill or index", r"\bno (?:repository|repository-local|local) skill|\bno skill (?:index|directory)|"
               r"skill index|lists no skill|no skills?\b"),
              ("host skills inspected, none fits", r"\bhost(?:'s)? (?:\w+ )?skills?"),
              ("existing docs, tests or commands already cover it", r"\b(?:existing|already|documented|tests? (?:capture|carry)|"
               r"commands? (?:and tests )?capture)"),
              ("names the host's Plan Test skill", r"plan[- ]test"))
    out("reason themes (keyword rules; a reason can match several), of " + str(len(reasons)) + " reasons: "
        + "; ".join(f"{name} {sum(1 for _, c in reasons if re.search(rx, str(c['skill'].get('reason') or ''), re.I))}"
                    for name, rx in themes))
    out(f"decisions carrying a path, evidence or index: path {sum(1 for _, c in reasons if c['skill'].get('path'))}, "
        f"evidence {sum(1 for _, c in reasons if c['skill'].get('evidence'))}, index {sum(1 for _, c in reasons if c['skill'].get('index'))}")
    out(f"every decision with its reason ({len(reasons)}):")
    for r, c in reasons:
        s = c["skill"]
        out(f"  [{s.get('decision')}] {r['driver']} {r['case']} {c['item']}: {flat(s.get('reason'))[:260]}"
            + (f" | path {s.get('path')}" if s.get("path") else ""))
    added = [(r, f) for r in whole for f in r["skill_files_added"]]
    out(f"SKILL.md files added to a product by a run: {len(added)}" + (": " + "; ".join(f"{r['folder']}: {f}" for r, f in added) if added else ""))
    env_sections = collections.Counter("absent" if r["env_skills_section"] is None else
                                       ("empty" if not r["env_skills_section"] else "present") for r in finished)
    out(f"finished runs' environment.md '## Skills' section: {dict(env_sections)}; texts (first 120 characters, counts):")
    for text, n in collections.Counter((r["env_skills_section"] or "")[:120] for r in finished
                                       if r["env_skills_section"]).most_common(12):
        out(f"  x{n} {text}")
    out("")

    out("== 3. Steps, step-plan versions and send-backs ==")
    for title, key in pools(whole):
        out(f"-- by {title} --")
        groups = collections.defaultdict(list)
        for r in whole:
            groups[key(r)].append(r)
        rows = []
        for name, group_rows in sorted(groups.items()):
            finals = [v[-1] for r in group_rows for v in r["step_plans"].values() if v]
            versions = collections.Counter(len(v) for r in group_rows for v in r["step_plans"].values() if v)
            sb = collections.Counter(s["stage"] for r in group_rows for s in r["sendbacks"])
            late = sum(1 for r in group_rows for s in r["sendbacks"] if s["late"])
            rows.append((name, len(finals), dict(sorted(collections.Counter(finals).items())), dict(sorted(versions.items())),
                         dict(sb), late))
        out.table(("pool", "items planned", "steps in final plan", "step-plan versions per item", "send-backs by stage",
                   "after a documented step"), rows)
    out("Every send-back after a documented step:")
    lates = [(r, s) for r in whole for s in r["sendbacks"] if s["late"]]
    for r, s in lates:
        out(f"  {r['version']} {r['driver']} {r['folder'].replace(str(HOME) + '/', '')} {s['item']} at {s['stage']} "
            f"(steps {s['steps_in_plan']}, documented {s['documented_steps']}): {s['summary'][:220]}")
    if not lates:
        out("  none")
    out("")

    out("== 4. Document's knowledge record, per living file ==")
    docs = [(r, d) for r in whole for d in r["documents"]]
    out(f"document results (done): {len(docs)} in {len(whole)} runs; automatic N/A (ShipLoop recorded, not run): "
        f"{sum(d['auto'] for _, d in docs)}; without a knowledge record: {sum(not d['has_record'] for _, d in docs)}; "
        f"with a lint gate scope (document's own edits readable): {sum(1 for _, d in docs if d['gate'] and d['gate'].get('files') is not None)}")
    out("The says-changed / says-unchanged / unclear label comes from keyword rules on the record's words (label_record). "
        "They were written on 45 hand-labelled texts (tmp/label_cases.py, 45 of 45 after tuning) and checked on 45 other "
        "texts drawn at random (seed 20261122, tmp/heldout-check.json, hand labels by the census author): 35 of the 39 I "
        "could label firmly agreed at first.  Three later rules were suggested by those misses and by reading the "
        "record-versus-diff disagreements below ('without/with no ... change', a product decision record such as "
        "'decision 9 records ...' is another file, 'no new command:' opens a no-change verdict); with them 38 of 39.  So "
        "the held-out figure is no longer blind.  The diff tables below are the ground truth; the labels say what the "
        "record claims.")
    for title, key in pools(whole):
        out(f"-- what the record says, by {title} (says-changed / says-unchanged / unclear / auto) --")
        rows = []
        groups = collections.defaultdict(list)
        for r, d in docs:
            groups[key(r)].append(d)
        for name, ds in sorted(groups.items()):
            row = [name, len(ds)]
            for field, _ in RECORD_KEYS:
                c = collections.Counter(d["labels"][field] for d in ds)
                row.append(f"{c['says-changed']}/{c['says-unchanged']}/{c['unclear']}/{c['auto']}")
            rows.append(row)
        out.table(("pool", "documents", "spec", "architecture", "environment"), rows)
    out("-- who changed each living file within a step: the document stage itself (its lint gate scope), its step "
        "review (the review's gate scope), the whole step (step commit: implement + test + document + review) --")
    rows = []
    for field, name in RECORD_KEYS:
        own = [d for _, d in docs if field in d["stage_changed"]]
        rev = [d for _, d in docs if field in d["review_changed"]]
        step = [d for _, d in docs if field in d["step_changed"]]
        rows.append((name, pct(sum(d["stage_changed"][field] for d in own), len(own)),
                     pct(sum(d["review_changed"][field] for d in rev), len(rev)),
                     pct(sum(d["step_changed"][field] for d in step), len(step))))
    out.table(("living file", "document stage changed it", "its step review changed it", "the step changed it"), rows)
    steps = [s for r in whole for s in r["steps_home"]]
    out(f"step commits read: {len(steps)}; with no home file changed: {pct(sum(not s['home'] for s in steps), len(steps))}")
    for truth, label in (("stage_changed", "the document stage's own edit (gate scope)"),
                         ("step_changed", "the whole step's edit (step commit)")):
        out(f"-- agreement: what the record says against {label} --")
        rows = []
        for field, name in RECORD_KEYS:
            cell = collections.Counter()
            for _, d in docs:
                if field in d[truth]:
                    cell[(d["labels"][field], d[truth][field])] += 1
            n = sum(cell.values())
            rows.append((name, n, cell[("says-changed", True)], cell[("says-changed", False)], cell[("says-unchanged", True)],
                         cell[("says-unchanged", False)], cell[("unclear", True)], cell[("unclear", False)]))
        out.table(("file", "documents", "says changed & changed", "says changed & not", "says unchanged & changed",
                   "says unchanged & not", "unclear & changed", "unclear & not"), rows)
    out("-- boilerplate check: texts repeated verbatim across documents --")
    texts = collections.Counter((field, d["texts"][field]) for _, d in docs for field, _ in RECORD_KEYS if d["texts"][field])
    repeated = [(k, n) for k, n in texts.items() if n > 1]
    out(f"distinct record texts {len(texts)}; texts that occur more than once: {len(repeated)} "
        f"(covering {sum(n for _, n in repeated)} of {sum(texts.values())} field values)")
    for (field, text), n in sorted(repeated, key=lambda kv: -kv[1])[:15]:
        out(f"  x{n} {field}: {text[:160]}")
    lengths = {field: median([len(d["texts"][field]) for _, d in docs if d["texts"][field]]) for field, _ in RECORD_KEYS}
    out("median characters per field: " + ", ".join(f"{k} {fmt(v, 0)}" for k, v in lengths.items()))
    out("")
    out("-- carry-forward's own edit of the knowledge home (its 'knowledge after carry-forward' commit) --")
    for title, key in pools(whole):
        groups = collections.defaultdict(list)
        for r in whole:
            groups[key(r)].append(r)
        rows = []
        for name, group_rows in sorted(groups.items()):
            cfs = sum(1 for r in group_rows for c in r["carry_forward"] if c["outcome"] == "done")
            commits = [c for r in group_rows for c in r["cf_knowledge_commits"]]
            per_file = {n: sum(1 for c in commits if n in c["files"]) for n in LIVING}
            lines = {n: sum(sum(c["files"][n]) for c in commits if n in c["files"]) for n in LIVING}
            rows.append((name, cfs, len(commits), *(f"{per_file[n]} ({lines[n]} lines)" for n in LIVING)))
        out(f"by {title}:")
        out.table(("pool", "cf done", "cf knowledge commits", "spec.md", "environment.md", "architecture.md"), rows)
    stage_home = collections.Counter()
    for r in finished:
        for k, v in r["home_commit_stages"].items():
            stage_home[k] += v
    out("which commits change docs/shiploop (finished runs, commits made by the run): "
        + "; ".join(f"{k} {v}" for k, v in stage_home.most_common()))
    unmatched = sum(r.get("cf_commits_unmatched", 0) for r in whole)
    out(f"'knowledge after carry-forward' commits not matched to a carry-forward accept within 300 s: {unmatched}")
    out("")

    out("== 4c. Carry-forward and spec.md: how its own knowledge commit changed the spec (entries by "
        "shiploop_knowledge_home._entries) ==")
    out("classes (a carry-forward can be in several): (a) new lines inside an existing R-n; (b) an existing R-n line changed "
        "or deleted, split by the line changed: a step line (carries '(Wn/Sm)'), an unmarked status/basis/evidence line "
        "(Basis, Pending, Met, Observed ...), or contract text (the requirement statement or an acceptance line); 'IDs out' = "
        "carry-forwards whose changed lines lost test-ID tokens; (c) a new R-n; (d) an R-n moved under Retired; plus "
        "removed IDs and changes outside every entry.  Counts are carry-forwards (done), not lines.")
    for title, key in pools(whole):
        groups = collections.defaultdict(list)
        for r in whole:
            groups[key(r)].append(r)
        rows = []
        for name, group_rows in sorted(groups.items()):
            cfs = [c for r in group_rows for c in r["carry_forward"] if c["outcome"] == "done"]
            changes = [c["home_commit"]["spec_change"] for c in cfs if c.get("home_commit") and c["home_commit"].get("spec_change")]
            count = lambda k: sum(1 for s in changes if s[k])
            has = lambda field: sum(1 for s in changes if any(v[field] for v in s["rewritten"].values()))
            rows.append((name, len(cfs), len(changes), count("appended"), count("rewritten"), has("step_lines"),
                         has("status_lines"), has("contract_lines"), has("heading_level_lines"), has("ids_removed"),
                         count("added"), count("retired"), count("removed"), count("outside")))
        out(f"by {title}:")
        out.table(("pool", "cf done", "cf changed spec.md", "a new lines", "b changed lines", "b: step line",
                   "b: status/basis", "b: contract text", "b: heading level", "b: IDs out", "c new R-n", "d to Retired",
                   "R-n removed", "outside entries"), rows)
    appended = collections.Counter()
    marks = collections.Counter()
    for r in whole:
        for c in r["carry_forward"]:
            s = (c.get("home_commit") or {}).get("spec_change")
            for lines in (s or {}).get("appended", {}).values():
                for line in lines:
                    appended[line["kind"]] += 1
                    marks["marked" if line["marked"] else "no mark"] += 1
    out(f"appended lines by kind (keyword rules in census.py appended_kind): {dict(appended)}; item/step mark: {dict(marks)}")
    out("every carry-forward that changed spec.md:")
    listed = 0
    for r in whole:
        for c in r["carry_forward"]:
            s = (c.get("home_commit") or {}).get("spec_change")
            if not s:
                continue
            listed += 1
            parts = [", ".join(s["classes"]) or "no entry-level change"]
            if s["appended"]:
                parts.append("appended " + ", ".join(f"{k} +{len(v)}" for k, v in s["appended"].items()))
            for ident, v in s["rewritten"].items():
                parts.append(f"rewrote {ident} (step {v['step_lines']}, status {v['status_lines']}, contract "
                             f"{v['contract_lines']}, heading level {v['heading_level_lines']}, deleted {v['deleted']}, "
                             f"IDs out {v['ids_removed']}" + (", heading" if v["heading_changed"] else "")
                             + f"): was «{' / '.join(v['was'])[:220]}» now «{' / '.join(v['now'])[:220]}»"
                             + (f" words: {' ; '.join(v['word_changes'])[:400]}" if v["word_changes"] else ""))
            for k in ("added", "retired", "removed", "unretired", "whitespace_only"):
                if s[k]:
                    parts.append(f"{k} {s[k]}")
            if s["outside"]:
                parts.append(f"outside entries {len(s['outside'])} lines: «{' / '.join(s['outside'])[:200]}»")
            out(f"  {r['version']} {r['build']} | {r['driver']} | {r['folder'].replace(str(HOME) + '/', '')} | {c['item']}: "
                + " | ".join(parts))
    if not listed:
        out("  none")
    review_specs = [(r, rc) for r in whole for v in r["reviews"] if v["stage"] == "carry-forward"
                    for rc in v.get("review_commits") or [] if rc.get("spec_change")]
    out(f"carry-forward Improve review commits that changed spec.md: {len(review_specs)}")
    for r, rc in review_specs:
        s = rc["spec_change"]
        out(f"  {r['version']} {r['build']} | {r['driver']} | {r['folder'].replace(str(HOME) + '/', '')} | {rc['subject'][:90]}: "
            f"{', '.join(s['classes'])}"
            + "".join(f" | rewrote {i}: was «{' / '.join(v['was'])[:160]}» now «{' / '.join(v['now'])[:160]}»"
                      for i, v in s["rewritten"].items())
            + (f" | added {s['added']}" if s["added"] else "") + (f" | retired {s['retired']}" if s["retired"] else ""))
    out("")

    out("== 5. Final living files ==")
    out("finished runs that are not follow-ons (sizes in bytes at HEAD of the product; median [min-max]):")
    for title, key in pools(whole):
        groups = collections.defaultdict(list)
        for r in finished:
            if not r["follow_on"]:
                groups[key(r)].append(r)
        rows = []
        for name, group_rows in sorted(groups.items()):
            row = [name, len(group_rows)]
            for n in LIVING:
                values = [r["sizes"][n]["bytes"] for r in group_rows if r["sizes"].get(n)]
                row.append(f"{fmt(median(values), 0)} [{min(values) if values else '-'}-{max(values) if values else '-'}] n={len(values)}")
            rows.append(row)
        out(f"by {title}:")
        out.table(("pool", "runs", "spec.md", "environment.md", "architecture.md"), rows)
    follow = [r for r in finished if r["follow_on"]]
    if follow:
        out(f"follow-on runs (finished {len(follow)}): bytes at start -> end, medians: "
            + ", ".join(f"{n} {fmt(median([r['sizes'][n]['start_bytes'] for r in follow if r['sizes'].get(n)]), 0)} -> "
                        f"{fmt(median([r['sizes'][n]['bytes'] for r in follow if r['sizes'].get(n)]), 0)}" for n in LIVING))
    out("-- level-2 headings that match no named section (finished runs) --")
    rows = []
    for n in LIVING:
        have = [r for r in finished if r["sizes"].get(n)]
        with_unnamed = [r for r in have if r["sizes"][n]["unnamed"]]
        total = sum(len(r["sizes"][n]["unnamed"]) for r in have)
        repeats = sum(1 for r in have if r["sizes"][n]["repeats"])
        origin = collections.Counter(v for r in have for v in r["sizes"][n]["unnamed_introduced"].values())
        rows.append((n, len(have), pct(len(with_unnamed), len(have)), total, repeats, dict(origin)))
    out.table(("file", "runs", "runs with an unnamed heading", "unnamed headings", "runs repeating a named section",
               "commit that introduced each unnamed heading"), rows)
    titles = collections.Counter((n, t) for r in finished for n in LIVING if r["sizes"].get(n) for t in r["sizes"][n]["unnamed"])
    out("most common unnamed headings: " + "; ".join(f"{n} '{t}' x{c}" for (n, t), c in titles.most_common(20)))
    notes = [(r, p) for r in whole for p in r["placement_notices"]]
    out(f"placement notices shown to the host: {len(notes)} in {sum(1 for r in whole if r['placement_notices'])} of {len(whole)} runs "
        f"(source events.jsonl or transcript.md); by file: "
        f"{dict(collections.Counter(re.search(r'docs/shiploop/([a-z.]+)', p).group(1) if re.search(r'docs/shiploop/([a-z.]+)', p) else '?' for _, p in notes))}; "
        f"kinds: headings {sum('new headings' in p for _, p in notes)}, born retired/superseded "
        f"{sum(bool(re.search(r'under .(Retired|Superseded)', p)) for _, p in notes)}")
    cmd = [(r, k) for r in whole for k in r["knowledge_notices"] if "this carry-forward is accepted" in k]
    out(f"carry-forward command notices (a command that passed at test not named under Commands): {len(cmd)} in "
        f"{len({r['run'] for r, _ in cmd})} runs")
    out("")

    out("== 6. Carry-forward's Improve review (last item) and minutes ==")
    for title, key in pools(whole):
        groups = collections.defaultdict(list)
        for r in whole:
            for v in r["reviews"]:
                if v["stage"] == "carry-forward":
                    groups[key(r)].append(v)
        rows = []
        for name, vs in sorted(groups.items()):
            edited = [v for v in vs if v["edited"]]
            rows.append((name, len(vs), pct(len(edited), len(vs)), sum(v["tree"] for v in vs), sum(v["result"] for v in vs),
                         fmt(median([v["lines"] for v in edited]), 0), fmt(median([v["seconds"] for v in vs]), 0)))
        out(f"by {title}:")
        out.table(("pool", "cf reviews", "edited anything", "tree changed", "result changed", "median lines when edited",
                   "median review seconds (pass log)"), rows)
    kinds = collections.Counter()
    for r in whole:
        for v in r["reviews"]:
            if v["stage"] == "carry-forward" and v["edited"]:
                for k in v.get("review_file_kinds") or {}:
                    kinds[k] += 1
    out(f"files in the edited carry-forward reviews' own commits, by kind (reviews touching each kind): {dict(kinds)}")
    out("what each editing carry-forward review says it changed:")
    for r in whole:
        for v in r["reviews"]:
            if v["stage"] == "carry-forward" and v["edited"]:
                out(f"  {r['version']} {r['build']} | {r['driver']} | {r['case']} | {v['lines']} lines, {v['labels']}: "
                    + " || ".join(t[:300] for t in v["changed_text"] if not t.lower().startswith("none"))[:600])
    doc_reviews = [v for r in whole for v in r["reviews"] if v["stage"] == "document"]
    out(f"document (step) reviews: {len(doc_reviews)}; edited anything {pct(sum(v['edited'] for v in doc_reviews), len(doc_reviews))}")
    out("-- minutes (finished runs; gaps over 45 min and host-down spans left out) --")
    for title, key in pools(whole):
        groups = collections.defaultdict(list)
        for r in finished:
            groups[key(r)].append(r)
        rows = []
        for name, group_rows in sorted(groups.items()):
            def m(r, k):
                return r["seconds"].get(k, 0.0) / 60
            totals = [sum(r["seconds"].values()) / 60 for r in group_rows]
            cf = [m(r, "carry-forward") for r in group_rows]
            cfr = [m(r, "review:carry-forward") for r in group_rows]
            doc = [m(r, "document") for r in group_rows]
            docr = [m(r, "review:document") for r in group_rows]
            items = sum(max(1, len(r["items_executed"])) for r in group_rows)
            all_s = sum(sum(r["seconds"].values()) for r in group_rows)
            share = lambda k: 100.0 * sum(r["seconds"].get(k, 0.0) for r in group_rows) / all_s if all_s else 0.0
            rows.append((name, len(group_rows), fmt(median(totals)), fmt(median(cf), 2), fmt(median(cfr), 2),
                         fmt(sum(cf) / items, 2), f"{share('carry-forward'):.1f}% + {share('review:carry-forward'):.1f}%",
                         fmt(median(doc), 2), fmt(median(docr), 2), f"{share('document'):.1f}% + {share('review:document'):.1f}%"))
        out(f"by {title}:")
        out.table(("pool", "runs", "median run min", "median cf min", "median cf review min", "cf min per item",
                   "cf + review share", "median document min", "median doc review min", "document + review share"), rows)
    out("")
    return out


def main(argv):
    out_dir = pathlib.Path(argv[0]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    releases = release_commits()
    now = time.time()
    records, excluded, slices = [], collections.Counter(), []
    only = [part for part in os.environ.get("CENSUS_ONLY", "").split(",") if part]   # calibration: a few folders
    for folder in find_invocations():
        rel = str(folder.relative_to(HOME))
        if only and not any(part in rel for part in only):
            continue
        if any(part in rel for part in EXCLUDED_FOLDERS):
            if list(folder.glob(".shiploop-runs/*/run/state.md")):
                excluded["look-stage candidate trial runs (d20261122-236b00, -ccc2ff)"] += 1
            continue
        invocation = load_json(folder / "invocation.json") or {}
        version = (invocation.get("versions") or {}).get("shiploop_version")
        primary, others = run_dirs(folder)
        if not primary:
            if version and vtuple(version) and vtuple(version) >= MIN_VERSION and not invocation.get("seeded"):
                excluded["2.4.0+ invocations with no ShipLoop run directory"] += 1
            continue
        if not version or not vtuple(version) or vtuple(version) < MIN_VERSION:
            excluded[f"runs before 2.4.0 ({version})" if version else "runs with no ShipLoop version recorded"] += 1
            continue
        if invocation.get("seeded") or invocation.get("kind") == "step-slice":
            for run in primary + others:
                state = state_block(run / "state.md") or {}
                stages = tuple(sorted({h["stage"] for h in state.get("history") or []} & set(INNER))) or ("no inner stage",)
                plan = next((state["accepted"].get(h["action"]) for h in state.get("history") or []
                             if h["stage"] == "plan" and h["outcome"] == "done"), None)
                slices.append({"folder": str(folder), "stages": stages,
                               "plan_items": len(plan.get("work_items") or []) if isinstance(plan, dict) else None})
            continue
        for run in primary:
            records.append(read_run(folder, run, invocation, releases, now))
        if others:
            excluded["extra run directories beside the delivery's own run (shiploop-run.json names another)"] += len(others)
    records.sort(key=lambda r: (r.get("group", ""), r.get("folder", "")))
    # runs.txt follows the 2026-11-12 selection rule (a run directory with a results/ folder), which agg.py needs.
    counted = [r for r in records if not r.get("error") and not r.get("live")]
    with_results = [r for r in counted if (pathlib.Path(r["run"]) / "results").is_dir()]
    (out_dir / "runs.txt").write_text("\n".join(r["run"] for r in with_results) + "\n")
    agg = pathlib.Path("/Users/dadleet/src/skill-craft/docs/experiments/step-boundary-replan-20261112/agg.py")
    done = subprocess.run([sys.executable, "-I", str(agg), str(out_dir / "runs.txt")], capture_output=True, text=True)
    agg_text = (f"runs.txt: {len(with_results)} of the {len(counted)} counted runs (the rest have no results/ folder: "
                + ", ".join(r["folder"].replace(str(HOME) + "/", "") for r in counted if r not in with_results)
                + ")\nall runs.txt runs:\n" + done.stdout
                + (("agg.py stderr: " + done.stderr[-2000:]) if done.returncode else ""))
    finished_list = out_dir / "tmp" / "runs-finished.txt"
    finished_list.parent.mkdir(exist_ok=True)
    finished_list.write_text("\n".join(r["run"] for r in with_results if r["status"] == "done") + "\n")
    done2 = subprocess.run([sys.executable, "-I", str(agg), str(finished_list)], capture_output=True, text=True)
    agg_text += "\nfinished runs only:\n" + done2.stdout + (("agg.py stderr: " + done2.stderr[-2000:]) if done2.returncode else "")
    exact = [r for r in with_results if r["status"] == "done" and r["build"] == "release"]
    exact_list = out_dir / "tmp" / "runs-finished-release.txt"
    exact_list.write_text("\n".join(r["run"] for r in exact) + "\n")
    done3 = subprocess.run([sys.executable, "-I", str(agg), str(exact_list)], capture_output=True, text=True)
    agg_text += ("\nfinished runs of exact release builds only:\n" + done3.stdout
                 + (("agg.py stderr: " + done3.stderr[-2000:]) if done3.returncode else ""))
    plan_slices = [s for s in slices if s["plan_items"] is not None]
    agg_text += (f"\nplan-only step slices at 2.4.0+ (platform-knowledge candidate build): {len(plan_slices)}; work items "
                 f"in their accepted plan: {dict(collections.Counter(s['plan_items'] for s in plan_slices))}")
    text = report(records, excluded, slices, agg_text, Out())
    (out_dir / "census.out").write_text("\n".join(text.lines) + "\n")
    (out_dir / "census.json").write_text(json.dumps({"made": datetime.datetime.now().isoformat(timespec="seconds"),
                                                     "excluded": excluded, "slices": slices, "runs": records},
                                                    indent=1, default=str))
    print("\n".join(text.lines))


if __name__ == "__main__":
    main(sys.argv[1:])
