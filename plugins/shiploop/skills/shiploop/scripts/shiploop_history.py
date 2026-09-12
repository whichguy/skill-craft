"""Bounded, receipt-backed Git commit-message paging for ShipLoop.

The protocol owns Git access and Markdown transactions.  This module only
normalizes one already-read commit body into a bounded Unicode-code-point
fragment and records contiguous coverage in a caller-owned Markdown receipt.
Until coverage reaches the complete body, this data is deliberately separate
from the existing ``history.pages`` evidence consumed by review gates.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any


VERSION = 1
MAX_CHARS = 4000
NAVIGATION_SUBJECT_CHARS = 160

_ACTION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{1,160}\Z")
_SHA_RE = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_DIGEST_RE = re.compile(r"[0-9a-f]{64}\Z")


class HistoryPagingError(ValueError):
    """A bounded history continuation is stale, incomplete, or malformed."""


def _need(ok: bool, message: str) -> None:
    if not ok:
        raise HistoryPagingError(message)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _row(row: Any) -> tuple[str, str]:
    _need(isinstance(row, Mapping), "history row is invalid")
    sha, body = row.get("sha"), row.get("body")
    _need(
        isinstance(sha, str) and _SHA_RE.fullmatch(sha),
        "history commit SHA is invalid",
    )
    _need(
        isinstance(body, str) and bool(body.strip()),
        "history requires a complete nonempty commit body",
    )
    return sha, body


def _identity(*, action: str, head: str, skip: int, sha: str, body: str) -> str:
    _need(isinstance(action, str) and _ACTION_RE.fullmatch(action), "history action is invalid")
    _need(isinstance(head, str) and _SHA_RE.fullmatch(head), "history HEAD is invalid")
    _need(isinstance(skip, int) and skip >= 0, "history skip is invalid")
    return _sha256(
        _canonical(
            {
                "version": VERSION,
                "action": action,
                "head": head,
                "skip": skip,
                "sha": sha,
                "body_sha256": _sha256(body.encode("utf-8")),
                "total_chars": len(body),
            }
        )
    )


def _check_request(
    *,
    action: str,
    head: str,
    identity: str,
    offset: int,
    supplied_head: str,
    supplied_digest: str,
) -> None:
    _need(isinstance(offset, int) and offset >= 0, "history offset must be nonnegative")
    _need(isinstance(supplied_head, str), "history continuation HEAD is invalid")
    _need(isinstance(supplied_digest, str), "history continuation digest is invalid")
    if offset:
        _need(
            supplied_head == head,
            "history HEAD changed between pages; do not continue this action",
        )
        _need(
            supplied_digest == identity,
            "history digest changed between pages; do not continue this action",
        )
        return
    _need(
        not supplied_head or supplied_head == head,
        "history HEAD changed between pages; do not continue this action",
    )
    _need(
        not supplied_digest or supplied_digest == identity,
        "history digest changed between pages; do not continue this action",
    )
    _need(
        bool(supplied_head) == bool(supplied_digest),
        "history continuation requires both --head and --digest",
    )
    # ``action`` is deliberately an input to the identity; this local use
    # makes that non-obvious binding explicit to future callers.
    _need(bool(action), "history action is invalid")


def _read_paging(iteration: dict[str, Any], *, action: str, head: str) -> dict[str, Any]:
    value = iteration.get("history_paging")
    if value is None:
        value = {"version": VERSION, "action": action, "head": head, "pages": []}
        iteration["history_paging"] = value
        return value
    _need(isinstance(value, dict), "history paging receipt is malformed")
    _need(
        type(value.get("version")) is int and value["version"] == VERSION,
        "history paging receipt version is unsupported",
    )
    _need(
        value.get("action") == action,
        "history action changed between pages; do not continue this action",
    )
    _need(
        value.get("head") == head,
        "history HEAD changed between pages; do not continue this action",
    )
    _need(isinstance(value.get("pages"), list), "history paging pages are malformed")
    return value


def _page_for(
    paging: dict[str, Any],
    *,
    skip: int,
    sha: str,
    body: str,
    identity: str,
) -> dict[str, Any]:
    pages = paging["pages"]
    matches = [page for page in pages if isinstance(page, dict) and page.get("skip") == skip]
    _need(len(matches) <= 1, "history paging receipt repeats a skip")
    body_digest = _sha256(body.encode("utf-8"))
    if not matches:
        page = {
            "skip": skip,
            "sha": sha,
            "body_sha256": body_digest,
            "total_chars": len(body),
            "identity_sha256": identity,
            "fragments": [],
        }
        pages.append(page)
        pages.sort(key=lambda item: item["skip"])
        return page
    page = matches[0]
    _need(
        page.get("sha") == sha
        and page.get("body_sha256") == body_digest
        and page.get("total_chars") == len(body)
        and page.get("identity_sha256") == identity,
        "history source changed between pages; do not continue this action",
    )
    _need(isinstance(page.get("fragments"), list), "history paging fragments are malformed")
    return page


def _contiguous_end(page: Mapping[str, Any], body: str) -> int:
    fragments = page.get("fragments")
    _need(isinstance(fragments, list), "history paging fragments are malformed")
    total = page.get("total_chars")
    _need(isinstance(total, int) and total > 0, "history paging total is invalid")
    expected = 0
    for fragment in sorted(fragments, key=lambda item: item.get("offset", -1) if isinstance(item, Mapping) else -1):
        _need(isinstance(fragment, Mapping), "history paging fragment is malformed")
        offset, end, fragment_digest = (
            fragment.get("offset"),
            fragment.get("end"),
            fragment.get("sha256"),
        )
        _need(
            isinstance(offset, int)
            and isinstance(end, int)
            and offset == expected
            and offset < end <= total
            and isinstance(fragment_digest, str)
            and _DIGEST_RE.fullmatch(fragment_digest),
            "history paging fragments are not contiguous",
        )
        _need(
            fragment_digest == _sha256(body[offset:end].encode("utf-8")),
            "history paging fragment digest is stale",
        )
        expected = end
    return expected


def record_bounded_page(
    iteration: dict[str, Any],
    row: Any,
    *,
    action: str,
    head: str,
    skip: int,
    offset: int,
    max_chars: int,
    supplied_head: str = "",
    supplied_digest: str = "",
) -> dict[str, Any]:
    """Store one bounded fragment and report whether its body is complete.

    ``max_chars`` and offsets count Python Unicode code points, not UTF-8
    bytes.  The caller upgrades the existing full-body proof only when this
    function reports ``complete``.
    """
    _need(isinstance(iteration, dict), "history iteration receipt is malformed")
    _need(
        isinstance(max_chars, int) and 1 <= max_chars <= MAX_CHARS,
        f"history max chars must be 1..{MAX_CHARS} Unicode characters",
    )
    sha, body = _row(row)
    identity = _identity(action=action, head=head, skip=skip, sha=sha, body=body)
    paging = _read_paging(iteration, action=action, head=head)
    page = _page_for(
        paging, skip=skip, sha=sha, body=body, identity=identity
    )
    _check_request(
        action=action,
        head=head,
        identity=identity,
        offset=offset,
        supplied_head=supplied_head,
        supplied_digest=supplied_digest,
    )
    _need(offset < len(body), "history offset is past available content; do not skip a page")
    contiguous = _contiguous_end(page, body)
    end = min(len(body), offset + max_chars)
    fragment_digest = _sha256(body[offset:end].encode("utf-8"))
    fragments = page["fragments"]
    exact = next(
        (
            fragment
            for fragment in fragments
            if fragment.get("offset") == offset and fragment.get("end") == end
        ),
        None,
    )
    replayed = exact is not None
    if exact is not None:
        _need(
            exact.get("sha256") == fragment_digest,
            "history fragment changed between replays; do not continue this action",
        )
    else:
        _need(
            offset == contiguous,
            "history fragment has a gap or overlap; copy the printed continuation",
        )
        fragments.append(
            {"offset": offset, "end": end, "sha256": fragment_digest}
        )
        fragments.sort(key=lambda item: item["offset"])
        contiguous = _contiguous_end(page, body)
    return {
        "action": action,
        "head": head,
        "sha": sha,
        "body": body,
        "body_sha256": _sha256(body.encode("utf-8")),
        "identity_sha256": identity,
        "offset": offset,
        "end": end,
        "total_chars": len(body),
        "fragment": body[offset:end],
        "complete": contiguous == len(body),
        "replayed": replayed,
    }


def navigation_line(row: Any, *, limit: int = NAVIGATION_SUBJECT_CHARS) -> str:
    """Return a bounded, explicitly truncated subject-only navigation line."""
    _need(isinstance(row, Mapping), "history row is invalid")
    sha, body = row.get("sha"), row.get("body")
    _need(
        isinstance(sha, str) and _SHA_RE.fullmatch(sha),
        "history commit SHA is invalid",
    )
    _need(isinstance(body, str), "history commit body is invalid")
    _need(isinstance(limit, int) and limit >= 32, "history navigation limit is invalid")
    subject = next((line for line in body.splitlines() if line.strip()), "(blank subject)")
    subject = subject.replace("\t", " ").replace("\r", " ")
    suffix = " … [truncated]"
    if len(subject) > limit:
        subject = subject[: limit - len(suffix)] + suffix
    return f"{sha} {subject}"
