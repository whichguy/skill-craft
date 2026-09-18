"""Conservative, read-only source closure checks for Apps Script HTML output.

This module answers a deliberately narrow question: can the statically visible
``doGet`` entrypoint obtain each JavaScript/CSS dependency through a source path
that HtmlService supports?  It does not deploy an Apps Script project, run
JavaScript, execute template expressions, start a server, or contact an
external resource.  A source route is therefore weaker than hosted execution.

The accepted template/include shape follows Google's documented HTML Service
pattern:
https://developers.google.com/apps-script/guides/html/best-practices
"""
from __future__ import annotations

from html.parser import HTMLParser
import hashlib
from pathlib import Path, PurePosixPath
import re
from typing import Any
from urllib.parse import urlsplit


SCHEMA = "shiploop-e2e-gas-artifact/1"
OFFICIAL_GUIDANCE = "https://developers.google.com/apps-script/guides/html/best-practices"
MAX_SOURCE_BYTES = 4 * 1024 * 1024
MAX_RENDERED_BYTES = 8 * 1024 * 1024
MAX_INCLUDE_DEPTH = 32

_FUNCTION = re.compile(
    r"\bfunction\s+(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)\s*\((?P<args>[^)]*)\)\s*(?P<brace>\{)"
)
_LITERAL_NAME = r"(?P<quote>['\"])(?P<name>[A-Za-z0-9_./ -]+)(?P=quote)"
_QUOTED_VALUE = r"(?:'[^'\\\r\n]*'|\"[^\"\\\r\n]*\")"
_SAFE_TITLE_CHAIN = rf"(?:\s*\.\s*setTitle\s*\(\s*{_QUOTED_VALUE}\s*\))*"
_DIRECT_OUTPUT = re.compile(
    rf"^HtmlService\s*\.\s*createHtmlOutputFromFile\s*\(\s*{_LITERAL_NAME}\s*\){_SAFE_TITLE_CHAIN}$",
    re.DOTALL,
)
_TEMPLATE_OUTPUT = re.compile(
    rf"^HtmlService\s*\.\s*createTemplateFromFile\s*\(\s*{_LITERAL_NAME}\s*\)\s*"
    rf"\.\s*evaluate\s*\(\s*\){_SAFE_TITLE_CHAIN}$",
    re.DOTALL,
)
_SCRIPTLET = re.compile(r"<\?(?P<marker>!?=)?(?P<content>.*?)\?>", re.DOTALL)
_LITERAL_INCLUDE = re.compile(
    r"^(?P<helper>[A-Za-z_$][A-Za-z0-9_$]*)\s*\(\s*(?P<quote>['\"])(?P<name>[A-Za-z0-9_./ -]+)(?P=quote)\s*\)\s*;?$"
)
_CSS_URL = re.compile(r"url\(\s*(?P<value>(?:'[^']*'|\"[^\"]*\"|[^)]*))\s*\)", re.IGNORECASE)
_CSS_IMPORT_STRING = re.compile(r"@import\s+(?P<quote>['\"])(?P<value>[^'\"]+)(?P=quote)", re.IGNORECASE)
_CSS_IMPORT = re.compile(r"@import\b", re.IGNORECASE)
_STATIC_IMPORT = re.compile(
    r"\bimport\s+(?:[^;'\"]+?\s+from\s+)?(?P<quote>['\"])(?P<value>[^'\"]+)(?P=quote)",
    re.MULTILINE,
)
_DYNAMIC_IMPORT = re.compile(r"\bimport\s*\(", re.MULTILINE)
_DYNAMIC_ELEMENT_LOAD = re.compile(
    r"\bdocument\s*\.\s*createElement\s*\(\s*['\"](?:script|link|style)['\"]\s*\)",
    re.IGNORECASE,
)
_DYNAMIC_RUNTIME_LOADERS = (
    ("dynamic-client-resource-or-rpc", "server RPC", re.compile(r"\bgoogle\s*\.\s*script\s*\.\s*run\b")),
    ("dynamic-client-resource-or-rpc", "CommonJS require()", re.compile(r"\brequire\s*\(")),
    ("dynamic-fetch-loader", "fetch()", re.compile(r"\bfetch\s*\(")),
    ("dynamic-xhr-loader", "XMLHttpRequest", re.compile(r"\bXMLHttpRequest\b")),
    ("dynamic-import-scripts", "importScripts()", re.compile(r"\bimportScripts\s*\(")),
    ("dynamic-script-source-assignment", "a dynamic .src assignment",
     re.compile(r"\b[A-Za-z_$][A-Za-z0-9_$]*\s*\.\s*src\s*=")),
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def _line(text: str, offset: int) -> int:
    return text.count("\n", 0, max(0, offset)) + 1


def _mask_javascript(text: str, *, mask_strings: bool) -> str:
    """Mask comments (and optionally quoted strings) while retaining offsets.

    This is intentionally a tiny lexer, not a JavaScript parser.  It is used
    only to avoid treating common comments/strings as function declarations or
    return statements.  Unsupported syntax falls through to an unverified
    result rather than being interpreted.
    """
    out = list(text)
    index = 0
    size = len(text)
    while index < size:
        current = text[index]
        following = text[index + 1] if index + 1 < size else ""
        if current == "/" and following == "/":
            end = text.find("\n", index + 2)
            if end < 0:
                end = size
            for position in range(index, end):
                out[position] = " "
            index = end
            continue
        if current == "/" and following == "*":
            end = text.find("*/", index + 2)
            end = size if end < 0 else end + 2
            for position in range(index, end):
                if out[position] != "\n":
                    out[position] = " "
            index = end
            continue
        if current in ("'", '\"', "`"):
            quote = current
            position = index + 1
            if mask_strings:
                out[index] = " "
            while position < size:
                if text[position] == "\\":
                    if mask_strings:
                        out[position] = " "
                        if position + 1 < size and out[position + 1] != "\n":
                            out[position + 1] = " "
                    position += 2
                    continue
                if text[position] == quote:
                    if mask_strings:
                        out[position] = " "
                    position += 1
                    break
                if mask_strings and out[position] != "\n":
                    out[position] = " "
                position += 1
            index = position
            continue
        index += 1
    return "".join(out)


def _balanced_body(text: str, opening_brace: int) -> str | None:
    """Return a function body when braces close outside comments/strings."""
    depth = 0
    index = opening_brace
    size = len(text)
    while index < size:
        current = text[index]
        following = text[index + 1] if index + 1 < size else ""
        if current == "/" and following == "/":
            ending = text.find("\n", index + 2)
            index = size if ending < 0 else ending
            continue
        if current == "/" and following == "*":
            ending = text.find("*/", index + 2)
            if ending < 0:
                return None
            index = ending + 2
            continue
        if current in ("'", '\"', "`"):
            quote = current
            index += 1
            while index < size:
                if text[index] == "\\":
                    index += 2
                    continue
                if text[index] == quote:
                    index += 1
                    break
                index += 1
            else:
                return None
            continue
        if current == "{":
            depth += 1
        elif current == "}":
            depth -= 1
            if depth == 0:
                return text[opening_brace + 1:index]
        index += 1
    return None


def _single_return_expression(body: str) -> str | None:
    clean = _mask_javascript(body, mask_strings=False)
    match = re.fullmatch(r"\s*return\s+(?P<expression>.*?)\s*;\s*", clean, re.DOTALL)
    if not match:
        return None
    return match.group("expression")


def _normalize_logical_name(value: str) -> str | None:
    """Return a safe Apps Script HTML logical name, without the .html suffix."""
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        return None
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or any(part in ("", ".", "..") for part in candidate.parts):
        return None
    if candidate.suffix.lower() == ".html":
        candidate = candidate.with_suffix("")
    if not candidate.parts or not candidate.name:
        return None
    return candidate.as_posix()


def _strip_css_comments(css: str) -> str:
    result = list(css)
    index = 0
    while index + 1 < len(css):
        if css[index:index + 2] == "/*":
            end = css.find("*/", index + 2)
            end = len(css) if end < 0 else end + 2
            for position in range(index, end):
                if result[position] != "\n":
                    result[position] = " "
            index = end
        else:
            index += 1
    return "".join(result)


class _DependencyParser(HTMLParser):
    """Collect only JS/CSS references from already literal HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.resources: list[dict[str, Any]] = []
        self.embedded_documents: list[dict[str, Any]] = []
        self.css_chunks: list[tuple[int, str]] = []
        self.scripts: list[tuple[int, str]] = []
        self._collect_style = False
        self._collect_script = False
        self._style_parts: list[str] = []
        self._script_parts: list[str] = []
        self._style_line = 0
        self._script_line = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name.lower(): value for name, value in attrs}
        line, _ = self.getpos()
        if tag.lower() == "script":
            source = attributes.get("src")
            if source is not None:
                self.resources.append({"kind": "script", "url": source, "line": line})
            self._collect_script = source is None
            self._script_line = line
            self._script_parts = []
        elif tag.lower() == "link":
            rel = (attributes.get("rel") or "").lower().split()
            href = attributes.get("href")
            is_css = (
                "stylesheet" in rel
                or (attributes.get("as") or "").lower() == "style"
                or (attributes.get("type") or "").lower() == "text/css"
            )
            if href is not None and is_css:
                self.resources.append({"kind": "stylesheet", "url": href, "line": line})
        elif tag.lower() == "style":
            self._collect_style = True
            self._style_line = line
            self._style_parts = []
        elif tag.lower() in ("iframe", "embed", "object"):
            attribute = "data" if tag.lower() == "object" else "src"
            source = attributes.get(attribute)
            if source is not None:
                self.embedded_documents.append({"kind": tag.lower(), "url": source, "line": line})
            elif "srcdoc" in attributes:
                self.embedded_documents.append({"kind": tag.lower(), "url": None, "line": line,
                                                "srcdoc": True})
        style = attributes.get("style")
        if style:
            self.css_chunks.append((line, style))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self._collect_style:
            self._style_parts.append(data)
        if self._collect_script:
            self._script_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "style" and self._collect_style:
            self.css_chunks.append((self._style_line, "".join(self._style_parts)))
            self._collect_style = False
        if tag.lower() == "script" and self._collect_script:
            self.scripts.append((self._script_line, "".join(self._script_parts)))
            self._collect_script = False


class _Inspector:
    def __init__(self, repo: Path, requested_entrypoint: str | None) -> None:
        self.repo_input = repo
        self.repo = repo.resolve()
        self.requested_entrypoint = requested_entrypoint
        self.issues: list[dict[str, Any]] = []
        self.evidence: list[dict[str, Any]] = []
        self.limitations: list[dict[str, Any]] = []
        self.source_hashes: dict[str, str] = {}
        self._external_resources: list[dict[str, Any]] = []

    def issue(self, severity: str, code: str, message: str, *, path: str | None = None,
              line: int | None = None) -> None:
        row: dict[str, Any] = {"severity": severity, "code": code, "message": message}
        if path is not None:
            row["path"] = path
        if line is not None:
            row["line"] = line
        self.issues.append(row)

    def limitation(self, code: str, message: str, *, path: str | None = None,
                   line: int | None = None) -> None:
        row: dict[str, Any] = {"code": code, "message": message}
        if path is not None:
            row["path"] = path
        if line is not None:
            row["line"] = line
        self.limitations.append(row)

    def read(self, candidate: Path) -> tuple[str, str] | None:
        try:
            resolved = candidate.resolve(strict=True)
        except OSError:
            self.issue("fail", "source-file-missing", "Referenced source file does not exist.", path=str(candidate))
            return None
        if not _inside(self.repo, resolved) or not resolved.is_file():
            self.issue("fail", "unsafe-source-path", "Referenced source escapes the inspected repository.", path=str(candidate))
            return None
        try:
            data = resolved.read_bytes()
        except OSError:
            self.issue("unverified", "source-file-unreadable", "Referenced source could not be read.", path=str(resolved))
            return None
        relative = resolved.relative_to(self.repo).as_posix()
        self.source_hashes[relative] = _sha256(data)
        if len(data) > MAX_SOURCE_BYTES:
            self.issue("unverified", "source-file-too-large", "Static source exceeded the conservative inspection limit.", path=relative)
            return None
        try:
            return data.decode("utf-8"), relative
        except UnicodeDecodeError:
            self.issue("unverified", "source-not-utf8", "Static source could not be decoded as UTF-8.", path=relative)
            return None

    def html_path(self, logical_name: str, *, context: str, line: int | None = None) -> Path | None:
        normalized = _normalize_logical_name(logical_name)
        if normalized is None:
            self.issue("fail", "unsafe-html-name", "HTML entrypoint/include name is not a safe relative logical path.",
                       path=context, line=line)
            return None
        base = self.repo.joinpath(*PurePosixPath(normalized).parts)
        candidate = base.parent / f"{base.name}.html"
        try:
            resolved = candidate.resolve(strict=True)
        except OSError:
            self.issue("fail", "html-file-missing", "HTML entrypoint/include file is missing.", path=f"{normalized}.html", line=line)
            return None
        if not _inside(self.repo, resolved):
            self.issue("fail", "unsafe-html-path", "HTML entrypoint/include resolves outside the inspected repository.",
                       path=context, line=line)
            return None
        return resolved

    def _function_records(self) -> list[dict[str, Any]]:
        if not self.repo.is_dir():
            self.issue("unverified", "repository-unavailable", "Artifact repository is not a readable directory.", path=str(self.repo_input))
            return []
        records: list[dict[str, Any]] = []
        for candidate in sorted(self.repo.rglob("*.gs")):
            loaded = self.read(candidate)
            if loaded is None:
                continue
            text, relative = loaded
            masked = _mask_javascript(text, mask_strings=True)
            for match in _FUNCTION.finditer(masked):
                body = _balanced_body(text, match.start("brace"))
                if body is None:
                    records.append({"name": match.group("name"), "args": match.group("args"), "body": None,
                                    "path": relative, "line": _line(text, match.start())})
                else:
                    records.append({"name": match.group("name"), "args": match.group("args"), "body": body,
                                    "path": relative, "line": _line(text, match.start())})
        return records

    def _helper_map(self, records: list[dict[str, Any]]) -> dict[str, str]:
        helpers: dict[str, str] = {}
        for record in records:
            body = record["body"]
            args = [item.strip() for item in record["args"].split(",") if item.strip()]
            expression = _single_return_expression(body) if isinstance(body, str) else None
            if len(args) != 1 or expression is None:
                continue
            parameter = re.escape(args[0])
            if re.fullmatch(
                rf"HtmlService\s*\.\s*createHtmlOutputFromFile\s*\(\s*{parameter}\s*\)\s*"
                r"\.\s*getContent\s*\(\s*\)", expression, re.DOTALL,
            ):
                helpers[record["name"]] = record["path"]
        return helpers

    def select_entrypoint(self) -> tuple[str, str, str, dict[str, str]] | None:
        records = self._function_records()
        do_gets = [record for record in records if record["name"] == "doGet"]
        helpers = self._helper_map(records)
        if len(do_gets) > 1:
            self.issue("unverified", "multiple-doget-functions", "More than one static doGet function was found; the serving entrypoint is ambiguous.")
            return None
        if do_gets:
            record = do_gets[0]
            expression = _single_return_expression(record["body"]) if isinstance(record["body"], str) else None
            direct = _DIRECT_OUTPUT.fullmatch(expression or "")
            template = _TEMPLATE_OUTPUT.fullmatch(expression or "")
            if direct is None and template is None:
                self.issue("unverified", "unresolved-doget-output",
                           "doGet is not a single supported literal HtmlService output expression.",
                           path=record["path"], line=record["line"])
                return None
            selected = direct or template
            assert selected is not None
            name = _normalize_logical_name(selected.group("name"))
            if name is None:
                self.issue("fail", "unsafe-html-name", "doGet uses an unsafe HTML logical name.",
                           path=record["path"], line=record["line"])
                return None
            mode = "direct" if direct is not None else "template"
            requested = _normalize_logical_name(self.requested_entrypoint) if self.requested_entrypoint is not None else None
            if self.requested_entrypoint is not None and requested != name:
                self.limitation("entrypoint-argument-ignored", "A static doGet entrypoint takes precedence over a different caller-supplied entrypoint.",
                                path=record["path"], line=record["line"])
            self.evidence.append({"kind": "doGet", "path": record["path"], "line": record["line"],
                                  "mode": mode, "logical_name": name})
            return name, mode, "doGet", helpers
        if self.requested_entrypoint is None:
            self.issue("unverified", "entrypoint-not-found", "No supported doGet was found and no explicit entrypoint was supplied.")
            return None
        name = _normalize_logical_name(self.requested_entrypoint)
        if name is None:
            self.issue("unverified", "unsafe-entrypoint", "Caller-supplied entrypoint is not a safe relative logical path.")
            return None
        self.evidence.append({"kind": "entrypoint-argument", "logical_name": name})
        return name, "direct", "argument", helpers

    def assemble(self, logical_name: str, *, template: bool, helpers: dict[str, str], stack: tuple[str, ...] = ()) -> tuple[str, str] | None:
        if logical_name in stack:
            self.issue("fail", "include-cycle", "Literal HtmlService includes form a cycle.", path=f"{logical_name}.html")
            return None
        if len(stack) >= MAX_INCLUDE_DEPTH:
            self.issue("unverified", "include-depth-limit", "Literal include nesting exceeded the conservative inspection limit.",
                       path=f"{logical_name}.html")
            return None
        source_path = self.html_path(logical_name, context=f"{logical_name}.html")
        if source_path is None:
            return None
        loaded = self.read(source_path)
        if loaded is None:
            return None
        content, relative = loaded
        if not template:
            return content, relative

        failed = False

        def replace(match: re.Match[str]) -> str:
            nonlocal failed
            marker = match.group("marker")
            content_expression = match.group("content").strip()
            include = _LITERAL_INCLUDE.fullmatch(content_expression) if marker == "!=" else None
            line = _line(content, match.start())
            if include is None:
                failed = True
                self.issue("unverified", "unresolved-template-scriptlet",
                           "Template scriptlet is not a supported literal include.", path=relative, line=line)
                return ""
            helper = include.group("helper")
            if helper not in helpers:
                failed = True
                self.issue("fail", "literal-include-helper-missing",
                           "Literal include calls a helper that does not have the supported HtmlService body.",
                           path=relative, line=line)
                return ""
            included = _normalize_logical_name(include.group("name"))
            if included is None:
                failed = True
                self.issue("fail", "unsafe-html-name", "Literal include uses an unsafe HTML logical name.",
                           path=relative, line=line)
                return ""
            nested = self.assemble(included, template=True, helpers=helpers, stack=stack + (logical_name,))
            if nested is None:
                failed = True
                return ""
            nested_html, nested_path = nested
            self.evidence.append({"kind": "literal-include", "path": relative, "line": line,
                                  "helper": helper, "logical_name": included, "included_path": nested_path})
            return nested_html

        rendered = _SCRIPTLET.sub(replace, content)
        if failed or len(rendered.encode("utf-8")) > MAX_RENDERED_BYTES:
            if not failed:
                self.issue("unverified", "rendered-html-too-large", "Literal template assembly exceeded the conservative size limit.", path=relative)
            return None
        return rendered, relative

    def resource(self, raw_url: str, *, kind: str, path: str, line: int) -> None:
        value = raw_url.strip()
        evidence = {"kind": "resource", "resource_kind": kind, "path": path, "line": line, "url": value}
        if not value or "<?" in value or "{{" in value or "${" in value:
            self.issue("unverified", "dynamic-resource-url", "Resource URL is empty or dynamically assembled.", path=path, line=line)
            return
        if value.startswith("#") or value.startswith("data:"):
            evidence["route"] = "self-contained"
            self.evidence.append(evidence)
            return
        if value.startswith("//"):
            self.issue("unverified", "protocol-relative-resource", "Resource URL does not prove HTTPS delivery.", path=path, line=line)
            return
        try:
            parsed = urlsplit(value)
        except ValueError:
            self.issue("unverified", "malformed-resource-url", "Resource URL could not be parsed without executing it.",
                       path=path, line=line)
            return
        scheme = parsed.scheme.lower()
        if scheme == "https":
            evidence["route"] = "https-external"
            self.evidence.append(evidence)
            external = dict(evidence)
            external["availability"] = "unverified"
            self._external_resources.append(external)
            return
        if scheme == "http":
            self.issue("fail", "insecure-external-resource", "Apps Script HTML Service external JavaScript/CSS resources must use HTTPS.",
                       path=path, line=line)
            return
        if scheme:
            self.issue("unverified", "unsupported-resource-scheme", "Resource URL has a scheme this static source checker does not validate.",
                       path=path, line=line)
            return
        self.issue("fail", "relative-resource-without-gas-route",
                   "A raw relative JavaScript/CSS dependency has no shown HtmlService delivery route.", path=path, line=line)

    def embedded_document(self, document: dict[str, Any], *, path: str) -> None:
        """Classify an iframe/object/embed without fetching or recursively rendering it."""
        line = document["line"]
        if document.get("srcdoc"):
            self.issue("unverified", "embedded-document-not-inspected",
                       "An inline embedded document is outside this entrypoint-only source inspection.",
                       path=path, line=line)
            return
        raw_url = document.get("url")
        value = raw_url.strip() if isinstance(raw_url, str) else ""
        if not value:
            return
        if "<?" in value or "{{" in value or "${" in value:
            self.issue("unverified", "dynamic-embedded-document", "Embedded document URL is dynamically assembled.",
                       path=path, line=line)
            return
        if value.startswith("#"):
            return
        try:
            parsed = urlsplit(value)
        except ValueError:
            self.issue("unverified", "malformed-embedded-document-url",
                       "Embedded document URL could not be parsed without executing it.", path=path, line=line)
            return
        if not parsed.scheme and not value.startswith("//"):
            self.issue("fail", "relative-embedded-document-without-gas-route",
                       "A raw relative iframe/object/embed document has no shown HtmlService delivery route.",
                       path=path, line=line)
            return
        self.issue("unverified", "embedded-document-not-inspected",
                   "Embedded documents are not fetched or recursively rendered by this source-only checker.",
                   path=path, line=line)

    def css(self, css: str, *, path: str, starting_line: int) -> None:
        clean = _strip_css_comments(css)
        for match in _CSS_URL.finditer(clean):
            value = match.group("value").strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '\"'):
                value = value[1:-1]
            self.resource(value, kind="css-url", path=path, line=starting_line + _line(clean, match.start()) - 1)
        for match in _CSS_IMPORT_STRING.finditer(clean):
            self.resource(match.group("value"), kind="css-import", path=path,
                          line=starting_line + _line(clean, match.start()) - 1)
        for match in _CSS_IMPORT.finditer(clean):
            statement_end = clean.find(";", match.start())
            statement_end = len(clean) if statement_end < 0 else statement_end + 1
            has_literal_url = _CSS_URL.search(clean, match.start(), statement_end) is not None
            has_literal_string = _CSS_IMPORT_STRING.search(clean, match.start(), statement_end) is not None
            if not has_literal_url and not has_literal_string:
                self.issue("unverified", "dynamic-css-import", "CSS @import is not a supported literal URL.",
                           path=path, line=starting_line + _line(clean, match.start()) - 1)

    def inspect_html(self, html: str, *, path: str) -> None:
        parser = _DependencyParser()
        try:
            parser.feed(html)
            parser.close()
        except Exception:
            self.issue("unverified", "html-parse-limitation", "HTML could not be inspected with the standard-library parser.", path=path)
            return
        for resource in parser.resources:
            self.resource(resource["url"], kind=resource["kind"], path=path, line=resource["line"])
        for document in parser.embedded_documents:
            self.embedded_document(document, path=path)
        for line, css in parser.css_chunks:
            self.css(css, path=path, starting_line=line)
        for line, script in parser.scripts:
            masked = _mask_javascript(script, mask_strings=False)
            code_only = _mask_javascript(script, mask_strings=True)
            for match in _STATIC_IMPORT.finditer(masked):
                self.resource(match.group("value"), kind="module-import", path=path,
                              line=line + _line(masked, match.start()) - 1)
            if _DYNAMIC_IMPORT.search(code_only):
                self.issue("unverified", "dynamic-module-import", "Client script uses dynamic import(), which is not statically closed.",
                           path=path, line=line)
            if _DYNAMIC_ELEMENT_LOAD.search(masked):
                self.issue("unverified", "dynamic-client-resource-or-rpc",
                           "Client script creates a script/link/style element dynamically; source closure cannot establish its returned content.",
                           path=path, line=line)
            for code, description, pattern in _DYNAMIC_RUNTIME_LOADERS:
                if pattern.search(code_only):
                    self.issue("unverified", code,
                               f"Client script uses {description}; source closure cannot establish its returned content.",
                               path=path, line=line)

    def result(self) -> dict[str, Any]:
        if any(issue["severity"] == "fail" for issue in self.issues):
            status = "fail"
        elif any(issue["severity"] == "unverified" for issue in self.issues):
            status = "unverified"
        else:
            status = "pass"
        return {
            "schema": SCHEMA,
            "status": status,
            "issues": self.issues,
            "evidence": self.evidence,
            "limitations": self.limitations,
            "source_hashes": dict(sorted(self.source_hashes.items())),
            "external_resources": self._external_resources,
            "official_guidance": OFFICIAL_GUIDANCE,
        }


def inspect_artifact(repo: Path, entrypoint: str | None = None) -> dict[str, Any]:
    """Inspect literal GAS HTML resource closure without mutating ``repo``.

    ``pass`` means that the examined static entrypoint has only literal
    HtmlService include/self-contained/HTTPS JavaScript-CSS routes.  It does
    not mean a deployment exists or an HTTPS resource was reachable.  ``fail``
    records a known missing/insecure route.  ``unverified`` records a dynamic
    or unsupported construction that this source-only checker declines to
    interpret.
    """
    inspector = _Inspector(Path(repo), entrypoint)
    selected = inspector.select_entrypoint()
    rendered_html: str | None = None
    entrypoint_row: dict[str, Any] | None = None
    if selected is not None:
        logical_name, mode, selection, helpers = selected
        assembled = inspector.assemble(logical_name, template=mode == "template", helpers=helpers)
        entrypoint_row = {"logical_name": logical_name, "path": f"{logical_name}.html", "mode": mode,
                          "selection": selection}
        if assembled is not None:
            rendered_html, rendered_path = assembled
            entrypoint_row["source_path"] = rendered_path
            inspector.inspect_html(rendered_html, path=rendered_path)
    result = inspector.result()
    result["entrypoint"] = entrypoint_row
    if rendered_html is not None:
        result["rendered_html"] = rendered_html
    return result
