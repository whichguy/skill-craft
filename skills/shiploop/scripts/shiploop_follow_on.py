"""Script-owned checks and routing for what a delivered run leaves for a later run (the follow-on list).

The handoff's done result carries ``follow_on``: one entry for each leftover of the run, classified once (``CLASSES``),
each citing a record the run holds (``source``).  The model decides what belongs in the list and under which class.
ShipLoop refuses only mechanical faults when the result is submitted (a missing list, an entry without its five texts, a
class outside the vocabulary, a template placeholder left in, a source no record of the run holds, a ``gap`` without the
request sentence it maps to) and records and prints the rest: it cannot judge whether an entry is true or the list
complete.  An empty list says the run classified its leftovers and found none for a later run; a result without the key
says nothing (unmeasured is not zero).

A ``gap`` or a ``decision`` recommends a follow-on run: the script writes ``RUN/follow-on-request.md`` from the entries
and the done packet and the report print the command that starts it.  Nothing here starts a run, asks a person, adds a
limit or blocks ``done`` (design: docs/shiploop-follow-on-run-design-2026-10-31.md, sections 4.4 to 4.6).

Like ``unverified`` and the plan's assumption list, the stored shape is loose (a list of text mappings, so every saved
run loads whatever a later edit does to the field set) and the exact shape is held at the CLI gate only.
"""

from __future__ import annotations

import html
import re
import shlex
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import shiploop_git as git_tools
import shiploop_knowledge_home as knowledge
import shiploop_planning_revision as planning_revision
import shiploop_request as request_file
import shiploop_store as store
import shiploop_unverified as unverified

STAGES = frozenset(("handoff",))
FILE = "follow-on-request.md"
# What a leftover is.  Only a ``gap`` or a ``decision`` recommends a run; the rest are recorded and shown.
CLASSES = ("gap", "decision", "person", "capability", "extension", "debt", "note")
RECOMMEND = ("gap", "decision")
FIELDS = ("class", "statement", "source", "request_sentence", "needs")
# The one row the result template prints, to replace or delete.  A text that starts with "<" and ends with ">" is a
# placeholder, so a row edited in one field only is refused as the whole row copied is.
TEMPLATE_ROW = {
    "class": "<" + "|".join(CLASSES) + ">",
    "statement": "<what this run leaves for a later run>",
    "source": "<unverified:R-<n> | assumption:<id> | lessons.<learned|considerations|open_next> | result:<stage> | "
              "commit:<hash>>",
    "request_sentence": "<S<n> of the request a gap maps to; \"\" for any other class>",
    "needs": "<what closes it, and who answers or acts>",
}
SOURCES = ("unverified:R-<n> (a row of the unverified list), assumption:<id> (an assumption the run recorded), "
           "lessons.<learned|considerations|open_next> (release-verify's lessons), result:<stage> (a stage's accepted "
           "done result) or commit:<hash> (a commit of the repository)")
SHAPE = ("each entry is {class, statement, source, request_sentence, needs}: one of " + ", ".join(CLASSES) + "; what the "
         "run leaves for a later run; the record it comes from, one of " + SOURCES + "; the request sentence S<n> a "
         "gap maps to (\"\" for any other class); and what closes it")
_SENTENCE = re.compile(r"^S(\d{1,4})$")
_UNVERIFIED = re.compile(r"^unverified:(R-\d+)$")
_ASSUMPTION = re.compile(r"^assumption:(\S+)$")
_LESSONS = re.compile(r"^lessons\.(\w+)$")
_RESULT = re.compile(r"^result:([a-z-]+)$")
_COMMIT = re.compile(r"^commit:(\S+)$")


class FollowOnError(ValueError):
    """Raised when a follow-on list is missing, malformed, still the template, or cites a record the run lacks."""


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise FollowOnError(message)


def _is_placeholder(text: str) -> bool:
    """A template placeholder: the whole text wrapped in angle brackets; markup inside a sentence is not one."""
    text = text.strip()
    return text.startswith("<") and text.endswith(">")


def canonical(value: Any) -> list[dict[str, str]]:
    """The canonical list for a done result's ``follow_on`` field: shape only, so a saved result always loads."""
    _need(isinstance(value, list), "follow_on must be a list (empty when this run leaves nothing for a later run); "
          + SHAPE)
    rows = []
    for index, entry in enumerate(value):
        _need(isinstance(entry, Mapping) and all(isinstance(key, str) and isinstance(text, str)
                                                 for key, text in entry.items()),
              f"follow_on[{index}] must be an object of text values; " + SHAPE)
        rows.append({key: text.strip() for key, text in entry.items()})
    return rows


def recorded(state: Mapping[str, Any]) -> list[Mapping[str, str]] | None:
    """The list of the current accepted done handoff result; None when that result has none (unmeasured, not zero)."""
    action = planning_revision.current_actions(state).get((None, "handoff"))
    result = state.get("accepted", {}).get(action, {}) if action else {}
    entries = result.get("follow_on") if isinstance(result, Mapping) else None
    return list(entries) if isinstance(entries, list) else None


def recommended(entries: Sequence[Mapping[str, str]]) -> list[Mapping[str, str]]:
    """The entries that recommend a follow-on run: every ``gap`` and every ``decision``."""
    return [row for row in entries if str(row.get("class", "")).strip() in RECOMMEND]


def _holds(state: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, set[str]]:
    """The records of the run an entry's source can name, by kind."""
    history = state.get("history") or ()
    accepted = state.get("accepted", {})
    rows = list(unverified.current_list(state)[2] or ())
    if isinstance(result.get("unverified"), list):
        rows += [row for row in result["unverified"] if isinstance(row, Mapping)]
    found: dict[str, set[str]] = {
        "unverified": {str(row.get("requirement", "")).strip() for row in rows},
        "assumption": set(),
        "lessons": set(),
        "result": {str(row.get("stage")) for row in history if row.get("outcome") == "done"},
    }
    for row in history:
        record = accepted.get(row.get("action"), {})
        if not isinstance(record, Mapping) or row.get("outcome") != "done":
            continue
        for item in record.get("assumptions") or ():
            if isinstance(item, Mapping) and isinstance(item.get("id"), str):
                found["assumption"].add(item["id"])
        lessons = record.get("lessons")
        if row.get("stage") == "release-verify" and isinstance(lessons, Mapping):
            found["lessons"] |= {name for name, _label in knowledge.LESSON_FIELDS
                                 if isinstance(lessons.get(name), str) and lessons[name].strip()}
    return found


def _check_source(state: Mapping[str, Any], held: Mapping[str, set[str]], label: str, source: str) -> None:
    """The source names a record the run holds: git decides a commit, never the typed text."""
    fault = (f"{label}.source {source!r} resolves to no record of this run; name one of " + SOURCES)
    for pattern, kind in ((_UNVERIFIED, "unverified"), (_ASSUMPTION, "assumption"), (_LESSONS, "lessons"),
                          (_RESULT, "result")):
        found = pattern.fullmatch(source)
        if found is not None:
            _need(found.group(1) in held[kind], fault)
            return
    found = _COMMIT.fullmatch(source)
    _need(found is not None, fault)
    _full, why = git_tools.resolve_commit(Path(str(state["repo"])), found.group(1))
    _need(not why, f"{label}.source commit {found.group(1)} {why}")


def check_submitted(state: Mapping[str, Any], stage: str, result: Any) -> None:
    """Refuse a submitted done handoff result without a usable list; runs at the CLI gates only."""
    if stage not in STAGES or not isinstance(result, Mapping) or result.get("outcome") != "done":
        return
    _need("follow_on" in result, f"a done {stage} result lists follow_on: a list, empty when this run leaves nothing "
          "for a later run; " + SHAPE)
    entries = result["follow_on"]
    _need(isinstance(entries, list), "follow_on must be a list (empty when this run leaves nothing for a later run); "
          + SHAPE)
    held = _holds(state, result)
    count = len(request_file.sentences(state["prompt"]))
    for index, entry in enumerate(entries):
        label = f"follow_on[{index}]"
        _need(isinstance(entry, Mapping) and set(entry) == set(FIELDS),
              f"{label} needs exactly {', '.join(FIELDS)}; {SHAPE}")
        for name in FIELDS:
            text = entry[name]
            _need(isinstance(text, str), f"{label}.{name} must be text")
            _need(bool(text.strip()) or name == "request_sentence", f"{label}.{name} must be nonempty text")
            _need(not _is_placeholder(text), f"{label}.{name} is still a template placeholder: replace it, or delete "
                  "the row when this run leaves nothing for a later run")
        kind = entry["class"].strip()
        _need(kind in CLASSES, f"{label}.class {kind!r} is not one of {', '.join(CLASSES)}")
        sentence = entry["request_sentence"].strip()
        _need(bool(sentence) or kind != "gap", f"{label} is a gap, and a gap maps to a sentence of the request: set "
              f"request_sentence to S<n> (RUN/{request_file.REQUEST_FILE} numbers them S1..S{count}); a leftover "
              "that maps to none is a decision, an extension or a note")
        number = _SENTENCE.fullmatch(sentence) if sentence else None
        _need(not sentence or (number is not None and 1 <= int(number.group(1)) <= count),
              f"{label}.request_sentence {sentence!r} is not a sentence of the request (S1..S{count}, "
              f"RUN/{request_file.REQUEST_FILE})")
        _check_source(state, held, label, entry["source"].strip())


def _text(value: Any) -> str:
    return " ".join(str(value).split())


def request_text(entries: Sequence[Mapping[str, str]], *, run_dir: str, lessons_subject: str) -> str:
    """The follow-on run's request: each gap and decision with its source, what keeps working, and where the earlier run's
    record is; empty when no entry recommends a run.  Plain text for a command substitution: the shell never re-reads it."""
    chosen = recommended(entries)
    if not chosen:
        return ""
    lines = ["Follow up an earlier ShipLoop run of this project: it left the findings below for a later run.",
             "Close each finding, using the earlier run's record where one is named."]
    for row in chosen:
        kind = _text(row.get("class", ""))
        sentence = _text(row.get("request_sentence", ""))
        label = ("Gap, " + sentence + " of the earlier request" if kind == "gap" and sentence
                 else "Gap" if kind == "gap" else "Decision to settle with the requester")
        lines.append(f"- {label}: {_text(row.get('statement', ''))} Needs: {_text(row.get('needs', ''))}. "
                     f"Recorded in {_text(row.get('source', ''))}.")
    lines += [("Everything the project already does must keep working. Keep the decisions in the living spec and "
               "architecture unless a finding above says otherwise, and run the existing tests first."),
              "The earlier run's request is in " + str(Path(run_dir) / request_file.REQUEST_FILE)
              + (f"; its lessons commit is {lessons_subject!r}." if lessons_subject else ".")]
    return "\n".join(lines) + "\n"


def source_repo(state: Mapping[str, Any], root: Path | None) -> str:
    """The repository a follow-on run starts on: the original checkout of an isolated run, else the run's own."""
    if root is not None and state.get("execution_mode") == "navigator-worktree":
        try:
            found = store.read_record(Path(root).parent / "workspace.md").get("source_repo")
        except (OSError, ValueError, store.StorageError):
            found = None
        if isinstance(found, str) and found:
            return found
    return str(state["repo"])


def start_command(cli_word: str, repo: str, request_path: Path) -> str:
    """The command that starts the follow-on run; ``cli_word`` is the ShipLoop script as the shell reads it.  The
    request file's text is the prompt, by command substitution, so nothing the model wrote is parsed by the shell."""
    return " ".join(("python3", cli_word, "workspace", "start", "--repo", shlex.quote(repo))) \
        + ' --prompt="$(cat ' + shlex.quote(str(request_path)) + ')"'


def _counts(chosen: Sequence[Mapping[str, str]]) -> str:
    parts = []
    for kind in RECOMMEND:
        number = sum(1 for row in chosen if str(row.get("class", "")).strip() == kind)
        if number:
            parts.append(f"{number} {kind}" + ("" if number == 1 else "s"))
    return " and ".join(parts)


def done_lines(state: Mapping[str, Any], root: Path, cli: str) -> list[str]:
    """What the done packet says about the list: nothing for an empty or absent list."""
    entries = recorded(state)
    if not entries:
        return []
    chosen = recommended(entries)
    others = len(entries) - len(chosen)
    if not chosen:
        return [f"Follow-on: {len(entries)} " + ("entry is" if len(entries) == 1 else "entries are")
                + " recorded and none recommends a follow-on run (see the report)."]
    request = Path(root) / FILE
    more = (f" ({others} more " + ("entry is" if others == 1 else "entries are") + " recorded)") if others else ""
    return [f"Follow-on: a follow-on run is recommended by {_counts(chosen)}{more}.",
            (f"ShipLoop starts nothing: if the person wants that run, this command starts it from the request "
             f"ShipLoop wrote ({request}):"),
            start_command(shlex.quote(cli), source_repo(state, root), request)]


def html_section(state: Mapping[str, Any], root: Path | None) -> list[str]:
    """The report's section on the list; nothing before the handoff is accepted.  Every value is escaped."""
    if planning_revision.current_actions(state).get((None, "handoff")) is None:
        return []
    entries = recorded(state)
    if entries is None:
        note = ("<p>not recorded: this run's handoff result has no follow_on list, which is not the same as none.</p>")
    elif not entries:
        note = "<p>none listed: the handoff recorded nothing for a later run.</p>"
    else:
        heads = ("Class", "Statement", "Source", "Request sentence", "Needs")
        rows = ["<tr>" + "".join("<td>" + html.escape(str(row.get(name, ""))) + "</td>" for name in FIELDS) + "</tr>"
                for row in entries]
        note = ("<p>What the handoff recorded for a later run; a gap or a decision recommends a follow-on run.</p>\n"
                "<table><thead><tr>" + "".join("<th>" + head + "</th>" for head in heads) + "</tr></thead><tbody>\n"
                + "\n".join(rows) + "\n</tbody></table>")
        chosen = recommended(entries)
        if chosen:
            request = (Path(root) if root is not None else Path("RUN")) / FILE
            command = start_command('"$CLI"', source_repo(state, root), request)
            note += ("\n<p>A follow-on run is recommended by " + html.escape(_counts(chosen)) + ". ShipLoop wrote its "
                     "request to " + html.escape(str(request)) + " and starts nothing; to start it, run this with CLI "
                     "set to the ShipLoop script:</p>\n<pre>" + html.escape(command) + "</pre>")
    return ["<h2>Follow-on</h2>", note]


__all__ = (
    "CLASSES",
    "FIELDS",
    "FILE",
    "RECOMMEND",
    "SHAPE",
    "SOURCES",
    "STAGES",
    "TEMPLATE_ROW",
    "FollowOnError",
    "canonical",
    "check_submitted",
    "done_lines",
    "html_section",
    "recommended",
    "recorded",
    "request_text",
    "source_repo",
    "start_command",
)
