#!/usr/bin/env python3
"""What a delivered JavaScript product looks like, read by script: its code (M7a) and its documents (M6). No model, no run.

    python3 static.py TREE BASE OUT.json [--entry PATH ...]

TREE is a product folder (a Git work tree at the commit to read); BASE is the commit the delivery started from, in TREE's
history ("-" for a delivery that started from nothing). What the delivery added or changed is read from `git diff BASE`:
code measures cover the product files it added or changed, the comment measure covers the functions whose first line it
added or changed, and the documentation measure covers the public surfaces that are in the product now and were not at
BASE (for a new build: all of them).

Product files are JavaScript (.js, .cjs, .mjs) outside node_modules, test folders (test, tests, __tests__, system),
`*.test.*` and `*.spec.*` files, and the two arms' process folders (docs/shiploop, ratchet, acceptance). User documents
are Markdown files outside those folders and outside node_modules; process documents are the Markdown files inside
docs/shiploop and ratchet.

Public surfaces: environment variables the product reads (`process.env.X`, `process.env["X"]`, `{ X } = process.env`),
HTTP paths and query parameters it names (string literals, `searchParams.get("x")`, and anchored regular expressions of the form /^\\/a\\/b/ that look like a URL path;
static file names such as /app.js are left out), its npm scripts, the command-line flags it names (literals like
--flag), and the names exported by its entry modules (package.json main and bin, plus the modules named with --entry,
which come from the request). A surface is documented when the documents name it: the variable, flag or exported name
as a word, `npm start`/`npm test`/`npm run NAME` for a script, a path with any spelling of its parameters.

The JavaScript reading is a small lexer (comments, strings, template literals, regular expressions), not a parser: it
is checked on archived deliveries of both arms before use (journal section 4) and its limits are listed in the journal.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

CODE, COMMENT, STRING = 0, 1, 2
EXCLUDED_DIRS = {"node_modules", "test", "tests", "__tests__", "system", "acceptance", ".git", ".shiploop-runs"}
PROCESS_DIRS = (("docs", "shiploop"), ("ratchet",), ("acceptance",))
JS = (".js", ".cjs", ".mjs")
REGEX_BEFORE_WORDS = {"return", "typeof", "case", "do", "else", "in", "of", "new", "delete", "void", "throw", "yield", "await"}
REGEX_AFTER = set("(,=:[!&|?{};+-*%<>~^")
KEYWORDS = {"if", "for", "while", "switch", "catch", "function", "return", "else", "do", "try", "with", "new", "typeof"}
DECISION_WORDS = {"if", "for", "while", "case", "catch"}
STATIC_FILE = re.compile(r"\.(html?|js|mjs|cjs|css|ico|png|jpe?g|gif|svg|json|map|txt|woff2?|ttf|webmanifest)$", re.IGNORECASE)
SYSTEM_PATH = re.compile(r"^/(dev|tmp|usr|etc|bin|var|private|Users|home|opt|proc|sys|Library|System)(/|$)")
PATH_LITERAL = re.compile(r"^/[A-Za-z0-9_\-./:{}*]*[A-Za-z][A-Za-z0-9_\-./:{}*]*$")


# ------------------------------------------------------------------ the lexer
def classify(text: str) -> bytearray:
    """One class per character: CODE (whitespace included), COMMENT or STRING (quotes, templates, regex literals)."""
    n = len(text)
    kind = bytearray(n)
    stack = ["C"]  # "C" code, "T" template text, ["E", depth] a template's ${ } expression
    last, i = "", 0
    while i < n:
        top = stack[-1]
        c = text[i]
        if top == "T":
            if c == "\\":
                kind[i:i + 2] = bytes([STRING]) * len(kind[i:i + 2])
                i += 2
            elif c == "`":
                kind[i] = STRING
                stack.pop()
                last, i = "x", i + 1
            elif c == "$" and text.startswith("{", i + 1):
                kind[i:i + 2] = bytes([STRING, STRING])
                stack.append(["E", 0])
                last, i = "(", i + 2
            else:
                kind[i] = STRING
                i += 1
            continue
        nxt = text[i + 1] if i + 1 < n else ""
        if c in " \t\r\n\f\v":
            i += 1
            continue
        if c == "/" and nxt == "/":
            end = text.find("\n", i)
            end = n if end < 0 else end
            kind[i:end] = bytes([COMMENT]) * (end - i)
            i = end
            continue
        if c == "/" and nxt == "*":
            end = text.find("*/", i + 2)
            end = n if end < 0 else end + 2
            kind[i:end] = bytes([COMMENT]) * (end - i)
            i = end
            continue
        if c in "'\"":
            j = i + 1
            while j < n and text[j] != c and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            j = min(n, j + 1)
            kind[i:j] = bytes([STRING]) * (j - i)
            last, i = "x", j
            continue
        if c == "`":
            kind[i] = STRING
            stack.append("T")
            i += 1
            continue
        if c == "/" and (last == "" or last in REGEX_AFTER or last == "kw"):
            j, in_class = i + 1, False
            while j < n and text[j] != "\n":
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == "[":
                    in_class = True
                elif text[j] == "]":
                    in_class = False
                elif text[j] == "/" and not in_class:
                    break
                j += 1
            if j < n and text[j] == "/":
                j += 1
                while j < n and text[j].isalpha():
                    j += 1
                kind[i:j] = bytes([STRING]) * (j - i)
                last, i = "x", j
                continue
        if c.isalnum() or c in "_$":
            j = i
            while j < n and (text[j].isalnum() or text[j] in "_$"):
                j += 1
            last = "kw" if text[i:j] in REGEX_BEFORE_WORDS else "x"
            i = j
            continue
        if isinstance(top, list):
            if c == "{":
                top[1] += 1
            elif c == "}":
                if top[1] == 0:
                    stack.pop()
                    kind[i] = STRING
                    last, i = "x", i + 1
                    continue
                top[1] -= 1
        last = c if c not in ")]" else "x"
        if c == "}":
            last = "}"
        i += 1
    return kind


def blanked(text: str, kind: bytearray) -> str:
    """The text with comments turned to spaces and string contents to underscores (newlines kept), same length."""
    out = []
    for c, k in zip(text, kind):
        if k == CODE or c == "\n":
            out.append(c)
        elif k == COMMENT:
            out.append(" ")
        else:
            out.append("_" if c not in "'\"`/" else c)
    return "".join(out)


def line_starts(text: str) -> list[int]:
    starts = [0]
    for index, c in enumerate(text):
        if c == "\n":
            starts.append(index + 1)
    return starts


def code_lines(text: str, kind: bytearray) -> dict[int, int]:
    """{line number (1-based): offset of its first code or string character} for lines that hold any."""
    found, line = {}, 1
    for index, c in enumerate(text):
        if c == "\n":
            line += 1
        elif not c.isspace() and kind[index] != COMMENT and line not in found:
            found[line] = index
    return found


# ------------------------------------------------------------------ functions
FUNCTION = re.compile(r"\bfunction\b\s*\*?\s*([A-Za-z_$][\w$]*)?\s*\(")
ARROW = re.compile(r"(\((?:[^()]|\([^()]*\))*\)|\b[A-Za-z_$][\w$]*)\s*=>")
METHOD = re.compile(r"^[ \t]*(?:(?:static|async|get|set)\s+|\*\s*)*([A-Za-z_$#][\w$]*)\s*\(([^()]|\([^()]*\))*\)\s*\{", re.MULTILINE)
NAME_BEFORE = re.compile(r"(?:(?:const|let|var)\s+([A-Za-z_$][\w$]*)|([A-Za-z_$][\w$.]*)|['\"]([\w$ -]+)['\"])\s*[:=]\s*(?:async\s*)?$")


def match_brace(code: str, open_at: int) -> int:
    depth = 0
    for index in range(open_at, len(code)):
        if code[index] == "{":
            depth += 1
        elif code[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    return len(code) - 1


def expression_end(code: str, start: int) -> int:
    depth = 0
    for index in range(start, len(code)):
        c = code[index]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if depth < 0:
                return index - 1
        elif depth == 0 and c in ",;\n":
            return index - 1
    return len(code) - 1


def functions(text: str, kind: bytearray) -> list[dict]:
    """Every function found: name (None for an unnamed one), start and end offsets, the line it starts on."""
    code = blanked(text, kind)
    starts = line_starts(text)
    found = {}

    def line_of(offset):
        low, high = 0, len(starts) - 1
        while low < high:
            mid = (low + high + 1) // 2
            if starts[mid] <= offset:
                low = mid
            else:
                high = mid - 1
        return low + 1

    def name_before(offset):
        line_start = starts[line_of(offset) - 1]
        found_name = NAME_BEFORE.search(code[line_start:offset])
        return next((group for group in found_name.groups() if group), None) if found_name else None

    for hit in FUNCTION.finditer(code):
        paren = hit.end() - 1
        close = expression_end(code, paren + 1)
        brace = code.find("{", close)
        if brace < 0:
            continue
        name = hit.group(1) or name_before(hit.start())
        found[hit.start()] = {"name": name, "start": hit.start(), "end": match_brace(code, brace)}
    for hit in ARROW.finditer(code):
        body = hit.end()
        while body < len(code) and code[body] in " \t\r\n":
            body += 1
        end = match_brace(code, body) if body < len(code) and code[body] == "{" else expression_end(code, body)
        found.setdefault(hit.start(), {"name": name_before(hit.start()), "start": hit.start(), "end": end})
    for hit in METHOD.finditer(code):
        name = hit.group(1)
        if name in KEYWORDS:
            continue
        start = hit.start(1)
        if any(row["start"] <= start <= row["end"] and row["start"] != start and code[row["start"]:start].strip() == ""
               for row in found.values()):
            continue
        found.setdefault(start, {"name": name, "start": start, "end": match_brace(code, hit.end() - 1)})
    rows = sorted(found.values(), key=lambda row: row["start"])
    for row in rows:
        row["line"] = line_of(row["start"])
        row["end_line"] = line_of(max(row["start"], row["end"]))
    return rows


def complexity(code: str, start: int, end: int, holes: list[tuple[int, int]]) -> int:
    """1 + decision points (if, for, while, case, catch, &&, ||, ??, ?:) in code[start:end], nested functions left out."""
    parts, cursor = [], start
    for hole_start, hole_end in sorted(holes):
        if hole_start > cursor:
            parts.append(code[cursor:hole_start])
        cursor = max(cursor, hole_end + 1)
    parts.append(code[cursor:end + 1])
    body = " ".join(parts)
    count = sum(1 for word in re.findall(r"[A-Za-z_$][\w$]*", body) if word in DECISION_WORDS)
    count += len(re.findall(r"&&|\|\||\?\?", body))
    count += len(re.findall(r"(?<![?])\?(?![?.])", body))
    return 1 + count


def comment_above(text: str, kind: bytearray, starts: list[int], line: int) -> bool:
    """Whether the line directly above `line` ends inside a comment (a JSDoc block or a // line)."""
    if line < 2:
        return False
    above_start, above_end = starts[line - 2], starts[line - 1] - 1
    segment = text[above_start:above_end].rstrip()
    if not segment:
        return False
    return kind[above_start + len(segment) - 1] == COMMENT


# ------------------------------------------------------------------ files and history
def git(tree: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(tree), *args], capture_output=True, text=True, check=False)
    return done.stdout if done.returncode == 0 else ""


def excluded(relative: Path) -> bool:
    parts = relative.parts
    if any(part in EXCLUDED_DIRS for part in parts[:-1]):
        return True
    return any(parts[:len(prefix)] == prefix for prefix in PROCESS_DIRS)


def product_files(tree: Path) -> list[Path]:
    listed = git(tree, "ls-files", "--cached", "--others", "--exclude-standard").splitlines()
    rows = []
    for name in listed:
        relative = Path(name)
        if relative.suffix not in JS or excluded(relative) or re.search(r"\.(test|spec)\.[cm]?js$", relative.name):
            continue
        if (tree / relative).is_file():
            rows.append(relative)
    return sorted(rows)


def markdown_files(tree: Path) -> tuple[list[Path], list[Path]]:
    listed = git(tree, "ls-files", "--cached", "--others", "--exclude-standard").splitlines()
    user, process = [], []
    for name in listed:
        relative = Path(name)
        if relative.suffix.lower() not in (".md", ".markdown") or not (tree / relative).is_file():
            continue
        if "node_modules" in relative.parts:
            continue
        if any(relative.parts[:len(prefix)] == prefix for prefix in PROCESS_DIRS[:2]):
            process.append(relative)
        elif not any(part in EXCLUDED_DIRS for part in relative.parts[:-1]):
            user.append(relative)
    return sorted(user), sorted(process)


def changed_lines(tree: Path, base: str | None, relative: Path) -> set[int] | None:
    """Lines of `relative` the delivery added or changed since `base`; None means the whole file is new."""
    if not base:
        return None
    present = subprocess.run(["git", "-C", str(tree), "cat-file", "-e", f"{base}:{relative.as_posix()}"],
                             capture_output=True, check=False).returncode == 0
    if not present:
        return None
    diff = git(tree, "diff", "--unified=0", "--no-color", base, "--", relative.as_posix())
    lines = set()
    for hunk in re.finditer(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", diff, re.MULTILINE):
        first, count = int(hunk.group(1)), int(hunk.group(2) if hunk.group(2) is not None else 1)
        lines.update(range(first, first + count))
    return lines


# ------------------------------------------------------------------ surfaces
def surfaces_of(text: str, kind: bytearray, entry: bool) -> dict[str, set[str]]:
    code = blanked(text, kind)
    # process.env itself, a name given it (`const env = process.env`, a parameter `env = process.env`,
    # `const { env } = process`), and a parameter or variable called env or environment (a settings function that
    # is handed process.env): calibrated on the archived Grokbot deliveries, whose settings code reads `env.PORT`
    aliases = {"env", "environment"} | set(re.findall(r"\b([A-Za-z_$][\w$]*)\s*=\s*process\.env\b(?!\.)", code))
    owners = r"(?:process\.env|" + "|".join(re.escape(name) for name in sorted(aliases)) + r")"
    env = set(re.findall(rf"(?<![\w$.]){owners}\.([A-Z_][A-Z0-9_]*)\b", code))
    env |= set(re.findall(rf"(?<![\w$.]){owners}\[\s*['\"]([A-Z_][A-Z0-9_]*)['\"]\s*\]", text))
    for group in re.findall(rf"\{{([^{{}}]*)\}}\s*=\s*{owners}\b", code):
        env |= {part.split(":")[0].split("=")[0].strip() for part in group.split(",") if part.strip()}
    env = {name for name in env if re.fullmatch(r"[A-Z_][A-Z0-9_]*", name)}
    query = set(re.findall(r"\b(?:searchParams|params|query|qs)\.(?:get|has|getAll)\(\s*['\"]([\w.\-\[\]]+)['\"]", text))
    paths, flags = set(), set()
    index, n = 0, len(text)
    while index < n:
        if kind[index] != STRING:
            index += 1
            continue
        end = index
        while end < n and kind[end] == STRING:
            end += 1
        literal = text[index:end]
        index = end
        quote = literal[:1]
        if quote in "'\"`" and literal.endswith(quote) and len(literal) >= 2:
            inner = literal[1:-1]
            if quote == "`":
                inner = re.sub(r"\$\{[^}]*\}", ":p", inner)
            if re.fullmatch(r"--[a-z][a-z0-9-]*", inner):
                flags.add(inner)
            route = normal_path(inner)
            if route:
                paths.add(route)
        elif quote == "/" and literal.startswith("/^\\/"):
            body = literal[2:literal.rfind("/")]
            body = re.sub(r"\\/\?\$$|/\?\$$|\$$", "", body)
            body = re.sub(r"\((?:[^()]|\([^()]*\))*\)", ":p", body).replace("\\/", "/").replace("\\", "")
            route = normal_path(body)
            if route:
                paths.add(route)
    exported = set()
    if entry:
        for group in re.findall(r"module\.exports\s*=\s*\{([^{}]*)\}", code):
            for part in group.split(","):
                name = part.split(":")[0].strip().lstrip(".")
                if re.fullmatch(r"[A-Za-z_$][\w$]*", name):
                    exported.add(name)
        exported |= set(re.findall(r"\bmodule\.exports\.([A-Za-z_$][\w$]*)\s*=", code))
        exported |= set(re.findall(r"(?<![.\w])exports\.([A-Za-z_$][\w$]*)\s*=", code))
        exported |= set(re.findall(r"\bmodule\.exports\s*=\s*([A-Za-z_$][\w$]*)\s*;?\s*$", code, re.MULTILINE))
        exported |= set(re.findall(r"\bexport\s+(?:default\s+)?(?:async\s+)?(?:function\*?|class|const|let|var)\s+([A-Za-z_$][\w$]*)", code))
        for group in re.findall(r"\bexport\s*\{([^{}]*)\}", code):
            exported |= {part.split(" as ")[-1].strip() for part in group.split(",") if part.strip()}
    return {"env": env, "paths": paths, "query": query, "flags": flags, "exports": exported}


def normal_path(inner: str) -> str | None:
    if not inner.startswith("/") or " " in inner or not PATH_LITERAL.match(inner) or SYSTEM_PATH.match(inner):
        return None
    if STATIC_FILE.search(inner) or "//" in inner:
        return None
    inner = re.sub(r"\?.*$", "", inner)
    parts = [":p" if part.startswith(":") or (part.startswith("{") and part.endswith("}")) or part == "*" else part
             for part in inner.split("/")]
    route = "/".join(parts).rstrip("/") or "/"
    return route if route != "/" else None


def documented(kind_name: str, surface: str, docs: str) -> bool:
    if kind_name in ("env", "exports", "query"):
        return re.search(rf"(?<![\w$]){re.escape(surface)}(?![\w$])", docs) is not None
    if kind_name == "flags":
        return re.search(rf"(?<![\w-]){re.escape(surface)}(?![\w-])", docs) is not None
    if kind_name == "scripts":
        if surface in ("start", "test", "stop", "restart"):
            return re.search(rf"\bnpm\s+(?:run\s+)?{re.escape(surface)}\b", docs) is not None
        return re.search(rf"\bnpm\s+run\s+{re.escape(surface)}(?![\w:-])", docs) is not None
    pattern = "/".join(r"[^/\s`'\")\]]+" if part == ":p" else re.escape(part) for part in surface.split("/"))
    return re.search(rf"{pattern}(?![\w-])", docs) is not None


# ------------------------------------------------------------------ the whole reading
def duplication(lines_by_file: dict[str, list[str]], window: int = 6) -> dict:
    seen, windows = {}, 0
    for name, lines in lines_by_file.items():
        normal = [re.sub(r"\s+", " ", line).strip() for line in lines]
        normal = [line for line in normal if line and not re.fullmatch(r"[{}()\[\];,]*", line)]
        for index in range(len(normal) - window + 1):
            key = "\n".join(normal[index:index + window])
            seen.setdefault(key, []).append((name, index))
            windows += 1
    repeated = sum(len(places) for places in seen.values() if len(places) > 1)
    return {"windows": windows, "repeated": repeated, "share": round(repeated / windows, 4) if windows else None}


def read(tree: Path, base: str | None, entries: list[str]) -> dict:
    tree = tree.resolve()
    files = product_files(tree)
    package = {}
    if (tree / "package.json").is_file():
        try:
            package = json.loads((tree / "package.json").read_text())
        except ValueError:
            package = {}
    entry_names = set(entries)
    if isinstance(package.get("main"), str):
        entry_names.add(package["main"].lstrip("./"))
    bins = package.get("bin")
    if isinstance(bins, str):
        entry_names.add(bins.lstrip("./"))
    elif isinstance(bins, dict):
        entry_names |= {value.lstrip("./") for value in bins.values() if isinstance(value, str)}

    per_file, all_functions, lines_by_file = [], [], {}
    kinds = ("env", "paths", "query", "flags", "exports")
    now, before = {k: set() for k in kinds}, {k: set() for k in kinds}
    syntax_failures = []
    for relative in files:
        text = (tree / relative).read_text(errors="replace")
        kind = classify(text)
        changed = changed_lines(tree, base, relative)
        if changed is not None and not changed:
            new_file, touched = False, False
        else:
            new_file, touched = changed is None, True
        entry = relative.as_posix() in entry_names
        for key, values in surfaces_of(text, kind, entry).items():
            now[key] |= values
        if base and not new_file:
            old = git(tree, "show", f"{base}:{relative.as_posix()}")
            if old:
                old_kind = classify(old)
                for key, values in surfaces_of(old, old_kind, entry).items():
                    before[key] |= values
        if not touched:
            continue
        code = blanked(text, kind)
        lines = code_lines(text, kind)
        starts = line_starts(text)
        found = functions(text, kind)
        for row in found:
            holes = [(other["start"], other["end"]) for other in found
                     if other is not row and row["start"] < other["start"] and other["end"] <= row["end"]]
            row["complexity"] = complexity(code, row["start"], row["end"], holes)
            row["length"] = row["end_line"] - row["line"] + 1
            row["file"] = relative.as_posix()
            row["new"] = changed is None or row["line"] in changed
            row["commented"] = comment_above(text, kind, starts, row["line"]) if row["name"] else None
        all_functions += [row for row in found if row["new"]]
        lines_by_file[relative.as_posix()] = text.splitlines()
        check = subprocess.run(["node", "--check", str(tree / relative)], capture_output=True, text=True, check=False)
        if check.returncode != 0 and relative.suffix != ".mjs":
            syntax_failures.append(relative.as_posix())
        per_file.append({"file": relative.as_posix(), "new_file": new_file, "code_lines": len(lines),
                         "changed_code_lines": len(lines) if changed is None else len([line for line in lines if line in changed]),
                         "functions": len(found)})

    scripts_now = set((package.get("scripts") or {}).keys())
    base_package = git(tree, "show", f"{base}:package.json") if base else ""
    try:
        scripts_before = set((json.loads(base_package).get("scripts") or {}).keys()) if base_package else set()
    except ValueError:
        scripts_before = set()
    surfaces = {key: sorted(now[key] - before[key]) for key in now}
    surfaces["scripts"] = sorted(scripts_now - scripts_before)

    user_docs, process_docs = markdown_files(tree)
    user_text = "\n".join((tree / name).read_text(errors="replace") for name in user_docs)
    all_text = user_text + "\n" + "\n".join((tree / name).read_text(errors="replace") for name in process_docs)
    docs_rows = {}
    for scope, text in (("user", user_text), ("all", all_text)):
        named = {key: [value for value in values if documented(key, value, text)] for key, values in surfaces.items()}
        total = sum(len(values) for values in surfaces.values())
        hit = sum(len(values) for values in named.values())
        docs_rows[scope] = {"surfaces": total, "documented": hit, "share": round(hit / total, 4) if total else None,
                            "missing": {key: sorted(set(surfaces[key]) - set(named[key])) for key in surfaces if
                                        set(surfaces[key]) - set(named[key])}}
    named_functions = [row for row in all_functions if row["name"]]
    commented = [row for row in named_functions if row["commented"]]
    lengths = [row["length"] for row in all_functions]
    complexities = [row["complexity"] for row in all_functions]
    words = lambda names: sum(len(re.findall(r"\S+", (tree / name).read_text(errors="replace"))) for name in names)
    return {
        "product_files": [row["file"] for row in per_file],
        "files": per_file,
        "code": {
            "files": len(per_file), "code_lines": sum(row["code_lines"] for row in per_file),
            "changed_code_lines": sum(row["changed_code_lines"] for row in per_file),
            "functions": len(all_functions), "named_functions": len(named_functions),
            "longest_function": max(lengths) if lengths else None,
            "longest_function_at": max(all_functions, key=lambda row: row["length"])["file"] if all_functions else None,
            "over_50_lines": round(sum(1 for value in lengths if value > 50) / len(lengths), 4) if lengths else None,
            "complexity_mean": round(sum(complexities) / len(complexities), 2) if complexities else None,
            "complexity_max": max(complexities) if complexities else None,
            "complexity_over_10": round(sum(1 for value in complexities if value > 10) / len(complexities), 4) if complexities else None,
            "duplication": duplication(lines_by_file), "syntax_failures": syntax_failures,
        },
        "comments": {"named_functions": len(named_functions), "with_comment_above": len(commented),
                     "share": round(len(commented) / len(named_functions), 4) if named_functions else None},
        "surfaces": surfaces,
        "docs": dict(docs_rows, user_files=[name.as_posix() for name in user_docs],
                     process_files=[name.as_posix() for name in process_docs],
                     user_words=words(user_docs), process_words=words(process_docs)),
        "entries": sorted(entry_names),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tree", type=Path)
    parser.add_argument("base")
    parser.add_argument("out", type=Path)
    parser.add_argument("--entry", action="append", default=[])
    args = parser.parse_args(argv)
    result = read(args.tree, None if args.base == "-" else args.base, args.entry)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    code, docs = result["code"], result["docs"]
    print(f"{args.tree}: {code['files']} files, {code['code_lines']} code lines, {code['functions']} functions "
          f"(complexity mean {code['complexity_mean']}, max {code['complexity_max']}); comments {result['comments']['share']}; "
          f"docs user {docs['user']['documented']}/{docs['user']['surfaces']}, all {docs['all']['documented']}/{docs['all']['surfaces']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
