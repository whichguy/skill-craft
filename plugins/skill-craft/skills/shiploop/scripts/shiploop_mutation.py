"""The test stage's mutation check: do the item's focused tests catch a change to the lines the item changed?

Owner decision 2026-10-11: "We need to code tests after the build phase, not just run empty tests."  The test stage
writes its tests after implement, so on new code nothing can run on the base: a test of a file the item adds fails to
LOAD there, and ``shiploop_test_loop._judge_base`` counts that load failure as RED.  That rule stays (there is no
other base verdict for new code), but it proves nothing about the assertions: a test that only imports the new module
is RED on the base and green on the candidate.  This check is what proves the tests assert real behaviour.

After ``loop_run`` passes on the candidate, ShipLoop:

- lists the lines the item changed since its base (the preparatory commit if any, else the lint base) in files
  ``shiploop_item_scope.classify`` calls product code (``code``: never tests, docs or config);
- makes text mutants of single lines with language-agnostic operators (``OPERATORS``: comparisons, boolean literals,
  ``+``/``-`` between operands, integer literals n -> n+1), skipping comments and string contents where a cheap
  scan finds them;
- samples at most ``MUTANT_SAMPLE`` deterministically, spread across files and lines;
- in a temporary detached worktree of the candidate's working content (never the checkout), first runs the focused
  commands unmutated (a copy that is not green cannot judge anything), then applies each mutant alone and runs the
  focused commands.  A mutant is killed when any focused command exits non-zero (or times out: the change made the
  tests hang);
- refuses done only when at least one mutant ran and none was killed: the tests catch nothing.  No kill-rate
  threshold: equivalent mutants make a threshold refuse good tests, and the owner's rule is no invented thresholds.

The record ``tests/<action>-mutation<N>.md`` holds every mutant and the totals, passed or not (the E2E harness reads
the kill count as a measure).  A refused check counts in ``refused_runs`` with the base and candidate runs;
``count=False`` (the check) writes ``tests/<action>-mutation-check.md`` and never counts.

Known limits, the same as the base run's: ignored files other than the platform cards' dependency directories
(``dependency_directories``) are absent from the copy (so the unmutated run may fail there, and the check then records
that it could not judge and passes); a command that names the checkout by an absolute path runs the checkout, not the
copy.  The operators are textual, so a token inside a construct the cheap scan does not recognise (a regex literal, a
heredoc, a raw string with an unusual delimiter) can be mutated; such a mutant either breaks the file (killed) or
survives, and only a check with no kill at all refuses.
"""

from __future__ import annotations

import os
import re
import shlex
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Collection, Dict, List, Mapping, Optional, Sequence, Tuple

import shiploop_lint as lint
import shiploop_store as store
import shiploop_test_loop as test_loop

# At most this many mutants per check (owner brief 2026-10-11).
MUTANT_SAMPLE = 8
# One mutant's focused run is cut at the smaller of this and a multiple of the unmutated run's time.
MUTANT_TIMEOUT_SECONDS = 120.0
MUTANT_TIMEOUT_FACTOR = 3.0
MUTANT_TIMEOUT_SLACK_SECONDS = 10.0
SCHEMA = "shiploop-test-mutation/v1"
# A file larger than this is not mutated (a generated or vendored file, not something the item wrote by hand).
MAX_FILE_BYTES = 512 * 1024
# The platform cards (owner rule: platform detail lives only in the cards), one backticked item per bullet: a card's
# ``## Remote tests`` section lists the command prefixes that test a deployed copy of the product rather than the
# checkout, and its ``## Dependency directories`` section the ignored directories a runner is installed in.
PLATFORM_CARDS = Path(__file__).resolve().parent.parent / "references" / "platforms"
_CARD_BULLET = re.compile(r"^\s*[-*]\s+`([^`]+)`")


def _card_bullets(heading: str, cards: Path) -> List[Tuple[str, str]]:
    """(card name, item) for each backticked bullet a platform card lists under ``## <heading>``."""
    found: List[Tuple[str, str]] = []
    for card in sorted(Path(cards).glob("*.md")):
        section = card.read_text(encoding="utf-8").split("\n## " + heading, 1)
        if len(section) < 2:
            continue
        for line in section[1].split("\n## ", 1)[0].splitlines():
            match = _CARD_BULLET.match(line)
            if match:
                found.append((card.stem, " ".join(match.group(1).split())))
    return found


def remote_test_commands(cards: Path = PLATFORM_CARDS) -> List[Tuple[str, str]]:
    """(card name, command prefix) for each prefix a platform card lists under ``## Remote tests``."""
    return _card_bullets("Remote tests", cards)


def remote_only_extensions(cards: Path = PLATFORM_CARDS) -> Dict[str, List[str]]:
    """Per card stem, normalized lowercase file extensions (``.cls``) listed under ``## Remote-only source extensions``.

    When a mixed item skips remote commands from ``card``, files with these extensions execute only in that remote
    target and never in the remaining local runner, so mutating them locally would crowd out reachable local files."""
    found: Dict[str, List[str]] = {}
    for card, item in _card_bullets("Remote-only source extensions", cards):
        ext = item.strip().lower()
        if ext and not ext.startswith("."):
            ext = "." + ext
        if ext and ext not in found.setdefault(card, []):
            found[card].append(ext)
    return found


def dependency_directories(cards: Path = PLATFORM_CARDS) -> List[str]:
    """Every directory name a platform card lists under ``## Dependency directories``, once each, in card order.

    The base run's worktree and this check's copy hold only tracked files, so each listed directory that exists in the
    checkout is linked in from there and a runner installed in it can start.  A card lists only directories a command
    reads as input, never build output: a linked build directory would show the base the candidate's built product."""
    return list(dict.fromkeys(name for _card, name in _card_bullets("Dependency directories", cards)))


def remote_card(command: str) -> Optional[Tuple[str, str]]:
    """(card name, prefix) when ``command`` runs a test a platform card lists under ``## Remote tests``, else None."""
    text = " ".join(str(command).split())
    return next(((card, prefix) for card, prefix in remote_test_commands()
                 if re.search(r"(?:^|[\s;&|(])" + re.escape(prefix) + r"(?:$|\s)", text)), None)


def split_remote(commands: Sequence[Mapping[str, Any]], stateful: Collection[str] = ()) \
        -> Tuple[List[Mapping[str, Any]], List[str]]:
    """(the commands that run on the checkout, the remote ones left out) for the mutant runs (run-5 batch I2, F3).

    A mutant lives only in the checkout's copy, so a command that tests a deployed target beside local ones could never
    kill one; running it would only spend time.  Remote means a platform card's Remote tests, or a test-strategy
    target that keeps state (``stateful``)."""
    remote = [str(row.get("command", "")) for row in commands
              if remote_card(str(row.get("command", ""))) is not None or row.get("target") in stateful]
    return [row for row in commands if str(row.get("command", "")) not in remote], remote


def _remote_reason(commands: Sequence[Mapping[str, Any]]) -> Optional[str]:
    """Why the mutation check cannot judge these focused commands, when every one tests a deployed target a platform
    card names; ``None`` when any of them runs on the checkout.

    A mutant lives only in a temporary copy of the checkout; a command that tests the deployed product never sees it,
    so every mutant would survive and the check would refuse good tests (a live run, 2026-10-18: 0 of 8 killed)."""
    matched = []
    for row in commands:
        hit = remote_card(str(row.get("command", "")))
        if hit is None:
            return None
        matched.append(hit)
    card, prefix = matched[0]
    return ("its focused commands test a deployed target (platforms/" + card + ".md lists `" + prefix + "` under "
            "Remote tests), which a mutant in the checkout's copy never reaches")

# (name, pattern, replacement): each match of ``pattern`` in a line's code text (comments and strings masked) is one
# candidate mutant.  ``replacement`` is a string or a function of the matched text.
OPERATORS: Tuple[Tuple[str, str, Any], ...] = (
    ("comparison", r"===", "!=="),
    ("comparison", r"!==", "==="),
    ("comparison", r"(?<![=!<>])==(?!=)", "!="),
    ("comparison", r"!=(?!=)", "=="),
    ("comparison", r"(?<=\s)<=(?=\s)", ">"),
    ("comparison", r"(?<=\s)>=(?=\s)", "<"),
    ("comparison", r"(?<=\s)<(?=\s)", ">="),
    ("comparison", r"(?<=\s)>(?=\s)", "<="),
    ("boolean", r"\btrue\b", "false"),
    ("boolean", r"\bfalse\b", "true"),
    ("boolean", r"\bTrue\b", "False"),
    ("boolean", r"\bFalse\b", "True"),
    ("arithmetic", r"(?<=[\w)\]]) \+ (?=[\w(\[])", " - "),
    ("arithmetic", r"(?<=[\w)\]]) - (?=[\w(\[])", " + "),
    ("integer", r"(?<![\w.$])\d+(?![\w.])", lambda text: str(int(text) + 1)),
)
_COMPILED = tuple((name, re.compile(pattern), replacement) for name, pattern, replacement in OPERATORS)
_MASK = "\0"
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def mutation_path(action: str, number: int) -> str:
    """ShipLoop's mutation record number ``number`` of one test action (counted with the base and candidate runs)."""
    return test_loop.mutation_path(action, number)


def _mask(line: str, open_block: str) -> Tuple[str, str]:
    """The line with comments and string contents replaced by NUL, and the block still open at its end.

    ``open_block`` is the terminator of a construct the previous line left open (``*/``, a triple quote or a
    backtick), or empty.  A cheap scan, not a parser: ``#`` starts a comment at the line start or after whitespace,
    ``//`` anywhere outside a string.
    """
    out: List[str] = []
    i, n = 0, len(line)
    while i < n:
        if open_block:
            end = line.find(open_block, i)
            if end < 0:
                out.append(_MASK * (n - i))
                return "".join(out), open_block
            stop = end + len(open_block)
            out.append(_MASK * (stop - i))
            i, open_block = stop, ""
            continue
        if line.startswith("//", i) or (line[i] == "#" and (i == 0 or line[i - 1].isspace())):
            out.append(_MASK * (n - i))
            break
        if line.startswith("/*", i):
            open_block = "*/"
            out.append(_MASK * 2)
            i += 2
            continue
        if line.startswith('"""', i) or line.startswith("'''", i):
            open_block = line[i:i + 3]
            out.append(_MASK * 3)
            i += 3
            continue
        char = line[i]
        if char in "\"'`":
            j = i + 1
            while j < n and line[j] != char:
                j += 2 if line[j] == "\\" else 1
            if j >= n:
                out.append(_MASK * (n - i))
                return "".join(out), ("`" if char == "`" else "")
            out.append(_MASK * (j + 1 - i))
            i = j + 1
            continue
        out.append(char)
        i += 1
    return "".join(out), open_block


def candidates(text: str, lines: Sequence[int]) -> List[Dict[str, Any]]:
    """Every operator match on the given 1-based ``lines`` of ``text``, in line and column order."""
    wanted = set(lines)
    found: List[Dict[str, Any]] = []
    open_block = ""
    for number, line in enumerate(text.splitlines(), start=1):
        masked, open_block = _mask(line, open_block)
        if number not in wanted or not masked.strip(_MASK + " \t"):
            continue
        for name, pattern, replacement in _COMPILED:
            for match in pattern.finditer(masked):
                original = line[match.start():match.end()]
                new = replacement(original) if callable(replacement) else replacement
                found.append({"line": number, "column": match.start() + 1, "operator": name,
                              "original": original, "replacement": new,
                              "mutated": line[:match.start()] + new + line[match.end():]})
    found.sort(key=lambda row: (row["line"], row["column"]))
    return found


def sample(by_file: Mapping[str, Sequence[Dict[str, Any]]], size: int = MUTANT_SAMPLE) -> List[Dict[str, Any]]:
    """A deterministic sample of at most ``size`` mutants, spread across files (round robin) and within each file
    across its candidates (evenly spaced)."""
    files = sorted(path for path, rows in by_file.items() if rows)
    quota = {path: 0 for path in files}
    left = size
    while left and any(quota[path] < len(by_file[path]) for path in files):
        for path in files:
            if left and quota[path] < len(by_file[path]):
                quota[path] += 1
                left -= 1
    chosen: List[Dict[str, Any]] = []
    for path in files:
        rows, take = by_file[path], quota[path]
        for i in range(take):
            chosen.append({"file": path, **rows[(2 * i + 1) * len(rows) // (2 * take)]})
    return chosen


def _changed_lines(top: Path, base_tree: str, current: str, paths: Sequence[str]) -> Dict[str, List[int]]:
    """Per toplevel-relative path, the 1-based line numbers the current tree adds or changes against the base."""
    if not paths:
        return {}
    listed = lint._git(top, "diff", "--no-color", "--no-ext-diff", "--no-renames", "-U0", base_tree, current, "--",
                       *paths)
    test_loop._need(listed.returncode == 0, "cannot diff the item base for the mutation check: "
                    + listed.stderr.decode("utf-8", "replace").strip())
    lines: Dict[str, List[int]] = {}
    path = ""
    for raw in listed.stdout.decode("utf-8", "surrogateescape").splitlines():
        if raw.startswith("+++ "):
            target = raw[4:]
            path = target[2:] if target.startswith("b/") else ""
            continue
        hunk = _HUNK.match(raw)
        if hunk and path:
            start, length = int(hunk.group(1)), int(hunk.group(2) if hunk.group(2) is not None else 1)
            lines.setdefault(path, []).extend(range(start, start + length))
    return lines


def _current_tree(root: Path, base: Mapping[str, Any]) -> str:
    top = Path(base["toplevel"])
    index = Path(root) / "lint" / "tmp" / ("test-mutation-" + os.urandom(8).hex() + ".index")
    try:
        return lint.snapshot_tree(top, Path(root), index, prefix=str(base.get("prefix") or "."))
    finally:
        if index.exists():
            index.unlink()


def _focused(state: Mapping[str, Any], work_item: str) -> List[Dict[str, Any]]:
    return [row for row in test_loop.stage_commands(state, test_loop.STAGES[0], work_item)[0]
            if row["suite"] == "focused"]


def _run_focused(runner: Any, commands: Sequence[Mapping[str, Any]], cwd: Path, timeout: float,
                 environment: Mapping[str, str], clock: Callable[[], float]) -> Tuple[str, str, float]:
    """Run the focused commands until one fails: (``killed``|``survived``|``timeout``|``not-run``, by, seconds)."""
    started = clock()
    for row in commands:
        fields, _output = test_loop._run_command(runner, row["command"], cwd, timeout, environment, clock)
        status = fields.get("status")
        if status == "timeout":
            return "timeout", row["command"], clock() - started
        if status == "error":
            return "not-run", row["command"] + ": " + str(fields.get("stderr") or "")[:200], clock() - started
        if fields.get("exit") != 0:
            return "killed", row["command"], clock() - started
    return "survived", "", clock() - started


# Stylesheets carry no logic that text-mutating operators test, and executed test_commands scripts belong to the test
# harness rather than product code even when placed outside ``test/``.
NON_BEHAVIOURAL_STYLE_EXTENSIONS = frozenset({".css", ".scss", ".sass", ".less", ".styl"})
_TEST_SCRIPT_NAME = re.compile(r"(?:^|[._-])(?:test|tests|spec|check|checks|verify)(?:[._-]|$)", re.I)
_TEST_RUNNER_BINS = frozenset({"pytest", "jest", "vitest", "mocha", "ava", "tap"})


def _command_test_scripts(command: str) -> set[str]:
    """Repo-relative test/check script paths invoked by a step-plan test command."""
    import shiploop_item_scope as item_scope

    try:
        words = shlex.split(command)
    except ValueError:
        words = command.split()
    non_env = [w for w in words if "=" not in w or w.startswith("-")]
    first_bin = Path(non_env[0]).name.lower() if non_env else ""
    is_runner = (
        first_bin in _TEST_RUNNER_BINS
        or "--test" in words
        or any(words[i] == "-m" and words[i + 1] in ("unittest", "pytest") for i in range(len(words) - 1))
    )
    found: set[str] = set()
    for rel in item_scope.command_paths(command):
        norm = rel.lstrip("./")
        if is_runner or _TEST_SCRIPT_NAME.search(Path(norm).stem) is not None:
            found.add(norm)
    return found


def _executed_test_scripts(state: Mapping[str, Any], work_item: str) -> set[str]:
    """Every script path invoked by ``work_item``'s accepted focused or regression test commands."""
    _action, result = test_loop._step_plan(state, work_item)
    excluded: set[str] = set()
    for row in result.get("test_commands") or ():
        if isinstance(row, Mapping) and row.get("suite") in ("focused", "regression"):
            excluded.update(_command_test_scripts(str(row.get("command") or "")))
    return excluded


def _check(root: Path, state: Mapping[str, Any], work_item: str, action: str, *, base_commit: Optional[str],
           runner: Any, env: Optional[Mapping[str, str]], clock: Optional[Callable[[], float]]) -> Dict[str, Any]:
    """Make, run and judge the mutants; return the record (without attempt or counted)."""
    import shiploop_item_scope as item_scope  # imports shiploop_test_loop: resolved at call time

    record: Dict[str, Any] = {"schema": SCHEMA, "stage": test_loop.STAGES[0], "work_item": work_item,
                              "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                              "sample_size": MUTANT_SAMPLE, "mutants": [], "killed": 0, "survived": 0,
                              "not_run": 0}
    commands = _focused(state, work_item)
    remote = _remote_reason(commands) if commands else None
    if remote:
        record["skipped"] = remote
        return record
    commands, skipped = split_remote(commands, test_loop.stateful_targets(state))
    record["commands"] = [row["command"] for row in commands]
    if skipped:
        record["remote_commands_skipped"] = skipped
        if not commands:
            record["skipped"] = ("every focused command tests a deployed target or one that keeps state between runs, "
                                 "which a mutant in the checkout's copy never reaches")
            return record
    base = lint.read_base(root, work_item)
    if base is not None and base_commit:
        base = test_loop._at_commit(base, base_commit)
    if not commands or base is None:
        record["skipped"] = ("no focused command" if not commands
                             else "no item base was recorded (not a Git checkout, or the base was not captured)")
        return record
    top = Path(base["toplevel"])
    current = _current_tree(root, base)
    changes = test_loop._item_changes(root, base)
    excluded_scripts = _executed_test_scripts(state, work_item)
    skipped_cards = {hit[0] for cmd in skipped if (hit := remote_card(cmd)) is not None}
    ext_map = remote_only_extensions() if skipped_cards else {}
    remote_exts = {ext for card in skipped_cards for ext in ext_map.get(card, ())}
    all_product = [
        path for status, path in changes
        if status in ("A", "M", "T")
        and item_scope.classify(rel := test_loop._relative(path, base)) == "code"
        and rel not in excluded_scripts
        and Path(rel).suffix.lower() not in NON_BEHAVIOURAL_STYLE_EXTENSIONS
    ]
    if remote_exts:
        remote_product = [p for p in all_product if Path(test_loop._relative(p, base)).suffix.lower() in remote_exts]
        if remote_product:
            record["remote_files_skipped"] = [test_loop._relative(p, base) for p in remote_product]
        product = [p for p in all_product if Path(test_loop._relative(p, base)).suffix.lower() not in remote_exts]
    else:
        product = all_product
    record.update(base_tree=base.get("tree"), base_commit=base.get("commit"), candidate_tree=current,
                  product_files=[test_loop._relative(path, base) for path in product])
    by_file: Dict[str, List[Dict[str, Any]]] = {}
    texts: Dict[str, str] = {}
    for path, numbers in _changed_lines(top, str(base["tree"]), current, product).items():
        shown = lint._git(top, "cat-file", "blob", current + ":" + path)
        if shown.returncode != 0 or len(shown.stdout) > MAX_FILE_BYTES:
            continue
        try:
            texts[path] = shown.stdout.decode("utf-8")
        except UnicodeDecodeError:
            continue
        by_file[path] = candidates(texts[path], numbers)
    record["candidates"] = sum(len(rows) for rows in by_file.values())
    chosen = sample(by_file)
    if not chosen:
        if record.get("remote_files_skipped"):
            record["skipped"] = (
                "no local mutants: changed code files belong to skipped remote test runtime(s) ("
                + ", ".join(sorted(skipped_cards)) + ")"
            )
        else:
            record["skipped"] = "no mutants: no changed product line matched an operator"
        return record
    runner = lint.recovery_runner(root, action, "mutation") if runner is None else runner
    clock = clock or time.monotonic
    environment = dict(os.environ if env is None else env)
    tree = test_loop._BaseTree(root, {**base, "tree": current, "commit": ""}, [])
    try:
        with tree as cwd:
            record["cwd"] = str(cwd)
            status, by, seconds = _run_focused(runner, commands, cwd, test_loop.COMMAND_TIMEOUT_SECONDS, environment,
                                               clock)
            record["unmutated"] = {"status": "passed" if status == "survived" else status, "by": by,
                                   "seconds": round(seconds, 3)}
            if status != "survived":
                record["skipped"] = ("the unmutated copy did not pass its focused commands (" + status + ": " + by
                                     + "), so no mutant can be judged there")
                return record
            timeout = min(MUTANT_TIMEOUT_SECONDS, seconds * MUTANT_TIMEOUT_FACTOR + MUTANT_TIMEOUT_SLACK_SECONDS)
            for mutant in chosen:
                target = tree.tree / mutant["file"]
                original = target.read_bytes()
                lines = texts[mutant["file"]].splitlines(keepends=True)
                line = lines[mutant["line"] - 1]
                ending = line[len(line.rstrip("\r\n")):]
                lines[mutant["line"] - 1] = mutant["mutated"] + ending
                try:
                    target.write_bytes("".join(lines).encode("utf-8"))
                    status, by, seconds = _run_focused(runner, commands, cwd, timeout, environment, clock)
                finally:
                    target.write_bytes(original)
                row = {key: mutant[key] for key in ("file", "line", "column", "operator", "original", "replacement")}
                row["file"] = test_loop._relative(mutant["file"], base)
                row.update(status=status, seconds=round(seconds, 3))
                if by:
                    row["by"] = by
                record["mutants"].append(row)
    except (test_loop.TestLoopError, lint.LintError, OSError) as exc:
        record["skipped"] = "the temporary copy could not be made or used: " + str(exc)
        return record
    rows = record["mutants"]
    record["killed"] = sum(1 for row in rows if row["status"] in ("killed", "timeout"))
    record["survived"] = sum(1 for row in rows if row["status"] == "survived")
    record["not_run"] = sum(1 for row in rows if row["status"] == "not-run")
    return record


# What a surviving mutant may be recorded as instead of a test that kills it (advisors panel 2026-10-25, P5): a
# mutation no input the contract allows can tell apart, a change outside product behaviour (a tool's generated file), or
# one no test this runner can run reaches (a remote-only path).  Not a kill-rate target: a test that kills it removes it.
DISPOSITIONS = ("equivalent", "out-of-scope", "not-exercisable")
DISPOSITION_SHAPE = ('{"mutant": "<file:line:column, as the refusal lists it>", "disposition": "equivalent" | '
                     '"out-of-scope" | "not-exercisable", "evidence": "<why it cannot be killed, and where that shows>"}')


class DispositionError(ValueError):
    """A ``mutant_dispositions`` field that is malformed; the message names the field, its shape and the fix."""


def mutant_id(row: Mapping[str, Any]) -> str:
    """How a refusal and a disposition name one mutant: ``file:line:column``."""
    return str(row["file"]) + ":" + str(row["line"]) + ":" + str(row["column"])


def canonical_dispositions(value: Any) -> List[Dict[str, str]]:
    """A test result's ``mutant_dispositions``: one row per surviving mutant it explains (shape only; the mutation
    check matches the rows to its survivors)."""
    if not isinstance(value, list):
        raise DispositionError("mutant_dispositions is a list of " + DISPOSITION_SHAPE)
    rows = []
    for index, row in enumerate(value):
        where = "mutant_dispositions[" + str(index) + "]"
        if not isinstance(row, Mapping) or set(row) != {"mutant", "disposition", "evidence"}:
            raise DispositionError(where + " is " + DISPOSITION_SHAPE)
        if row["disposition"] not in DISPOSITIONS:
            raise DispositionError(where + ".disposition is one of " + ", ".join(DISPOSITIONS))
        for key in ("mutant", "evidence"):
            if not isinstance(row[key], str) or not row[key].strip() or row[key].strip().startswith("<"):
                raise DispositionError(where + "." + key + " needs a real value: " + DISPOSITION_SHAPE)
        rows.append({key: str(row[key]).strip() for key in ("mutant", "disposition", "evidence")})
    return rows


def _reusable(root: Path, state: Mapping[str, Any], work_item: str, action_id: str,
              base_commit: Optional[str]) -> Optional[Dict[str, Any]]:
    """The latest mutation record of this action made on the same candidate tree with the same focused commands, so a
    resubmission that changes only ``mutant_dispositions`` does not run the mutants again (Codex, panel P5)."""
    focused = _focused(state, work_item)
    if not test_loop.reuse_eligible(state, test_loop.STAGES[0], work_item, focused):
        return None
    commands, _skipped = split_remote(focused, test_loop.stateful_targets(state))
    base = lint.read_base(root, work_item)
    if base is None or not commands:
        return None
    if base_commit:
        base = test_loop._at_commit(base, base_commit)
    paths = [test_loop.mutation_check_path(action_id)]
    paths += [mutation_path(action_id, number) for number in range(1, test_loop._mutation_count(root, action_id) + 1)]
    found = []
    for relative in paths:
        try:
            record = store.read_record(root / relative)
        except (OSError, store.StorageError):
            continue
        if isinstance(record, Mapping) and not record.get("skipped") and record.get("mutants"):
            found.append((str(record.get("created_at") or ""), relative, record))
    if not found:
        return None
    created, relative, record = max(found)
    if record.get("commands") != [row["command"] for row in commands]:
        return None
    try:
        current = _current_tree(root, base)
    except lint.LintError:
        return None
    if record.get("candidate_tree") != current:
        return None
    reused = {key: value for key, value in record.items() if key not in ("attempt", "counted", "passed", "disposition",
                                                                        "reused", "advisory", "action", "seconds")}
    reused.update(created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                  reused={"path": relative, "created_at": created})
    return reused


def _describe(row: Mapping[str, Any]) -> str:
    return (str(row["file"]) + ":" + str(row["line"]) + ": " + repr(row["original"]) + " -> "
            + repr(row["replacement"]))


def mutation_check(root: Path, state: Mapping[str, Any], work_item: str, action_id: str,
                   result: Optional[Mapping[str, Any]] = None, *, count: bool = True,
                   base_commit: Optional[str] = None, runner: Any = None,
                   env: Optional[Mapping[str, str]] = None, clock: Optional[Callable[[], float]] = None,
                   **_options: Any) -> List[str]:
    """The test stage's mutation check, after ``loop_run`` passed; raises ``TestLoopError`` with the refusal.

    Writes ``tests/<action>-mutation<N>.md`` (``count=False``: ``tests/<action>-mutation-check.md``, never
    counted) and returns its summary line.  Refused only when at least one mutant ran and none was killed; that
    refusal counts in ``refused_runs``.  ``result`` is accepted for the gate's uniform call and not read.
    """
    root = Path(root)
    refused = test_loop.refused_runs(root, action_id)
    started = time.monotonic()
    previous = _reusable(root, state, work_item, action_id, base_commit) if runner is None else None
    record = previous if previous is not None else _check(root, state, work_item, action_id, base_commit=base_commit,
                                                          runner=runner, env=env, clock=clock)
    record["action"] = action_id
    record["seconds"] = round(time.monotonic() - started, 3)
    # A mixed item left its remote commands out (I2, F3): a mutant in code only they reach survives whatever the local
    # tests assert, so when zero mutants were killed its survivors are recorded, not refused.
    zero_kill_remote_exempt = (
        bool(record["mutants"]) and record["killed"] == 0 and record["survived"] > 0
        and bool(record.get("remote_commands_skipped"))
    )
    refuse = (
        bool(record["mutants"]) and record["killed"] == 0 and record["survived"] > 0
        and not zero_kill_remote_exempt
    )
    # Every survivor the zero-kill rule lets through gets a disposition (advisors panel 2026-10-25, P5) unless the
    # mixed-item remote-skip exemption already recorded a zero-kill run as advisory.
    given = {row.get("mutant") for row in (result or {}).get("mutant_dispositions") or () if isinstance(row, Mapping)}
    undisposed = [] if (refuse or zero_kill_remote_exempt) else [
        row for row in record["mutants"] if row["status"] == "survived" and mutant_id(row) not in given
    ]
    if undisposed:
        record["undisposed"] = [mutant_id(row) for row in undisposed]
    if record["mutants"] and record["killed"] == 0 and record.get("remote_commands_skipped"):
        record["advisory"] = ("no mutant was killed, but the remote commands this check left out may be the only tests "
                              "that reach the mutated code; recorded, not refused")
    # A check that could not judge anything (no focused command, no item base, no mutant, a copy that was not green)
    # passes, and says ``skipped`` so no reader takes it for a proof; one that refused is ``failed`` as before.
    record.update(passed=not refuse and not undisposed,
                  disposition="failed" if refuse or undisposed else "skipped" if record.get("skipped") else "passed")
    if count:
        record["attempt"] = test_loop._next_attempt(root, action_id)
        relative = mutation_path(action_id, test_loop._mutation_count(root, action_id) + 1)
    else:
        record["counted"] = False
        relative = test_loop.mutation_check_path(action_id)
    store.atomic_write_text(root / relative, store.dumps(record, "ShipLoop test mutation check"))
    if record.get("skipped"):
        summary = "mutation: skipped (" + str(record["skipped"]) + ")"
    else:
        summary = ("mutation: " + str(record["killed"]) + " of " + str(len(record["mutants"]))
                   + " mutants of the changed product lines killed by the focused tests"
                   + (" (" + str(record["not_run"]) + " not run)" if record["not_run"] else ""))
    if undisposed:
        lines = ["ShipLoop mutation check: test is not done. " + str(len(undisposed)) + " of " + str(len(record["mutants"]))
                 + " mutants of this item's changed product lines survived the focused tests, with no disposition:"]
        lines += ["- " + mutant_id(row) + ": " + _describe(row) for row in undisposed]
        lines.append("For each, add or strengthen a test so it fails on that mutant (a killed mutant needs no entry), or "
                     "record why it cannot be killed in mutant_dispositions, one entry per mutant: " + DISPOSITION_SHAPE
                     + ". equivalent: no input the contract allows tells them apart; out-of-scope: not product "
                     "behaviour, such as a tool's generated file; not-exercisable: no test this runner can run reaches "
                     "it. Do not weaken an oracle or change required behaviour to lower the count. Then submit done "
                     "again: eligible checkout-only runs are reused while the candidate and focused commands stay "
                     "unchanged; external checks rerun under the shared reuse eligibility rule. Full "
                     "output: " + str(root / relative) + ".")
        raise test_loop.TestLoopError("\n".join(lines))
    if not refuse:
        return [summary + ("; reused the run of " + str(record["reused"]["created_at"]) if record.get("reused") else "")]
    lines = ["ShipLoop mutation check: test is not done. ShipLoop made " + str(len(record["mutants"]))
             + " one-token changes (mutants) to this item's changed product lines, applied each alone in a temporary "
             "copy of the candidate and ran the focused commands; every command still passed for every one, so the "
             "tests catch none of these changes:"]
    lines += ["- " + _describe(row) for row in record["mutants"] if row["status"] == "survived"]
    if count:
        tail = test_loop.refused_note(refused + 1, test_loop.STAGES[0])
    else:
        tail = "This check does not count toward the refused runs."
    lines.append("Add or strengthen assertions that check the behaviour the test spec's oracle states, so a change "
                 "like these makes a focused test fail (a test that only loads the code asserts nothing), start the "
                 "Until Loop again, then submit done again. " + tail + " Full output: " + str(root / relative) + ".")
    raise test_loop.TestLoopError("\n".join(lines))


__all__ = (
    "MUTANT_SAMPLE",
    "OPERATORS",
    "candidates",
    "mutation_check",
    "mutation_path",
    "sample",
)
