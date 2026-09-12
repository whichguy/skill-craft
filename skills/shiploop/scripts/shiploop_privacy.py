"""Conservative credential screening for ShipLoop's durable records.

The helpers intentionally recognize only a small set of explicit credential
representations.  They are a defense-in-depth screen, not a claim that every
secret format can be detected.
"""

from __future__ import annotations

import re
from typing import Any


REDACTED_SENSITIVE_VALUE = "[redacted sensitive value]"

_AUTHORIZATION_VALUE = re.compile(
    r"(?i)\bauthorization\s*:\s*(?:(?:bearer|basic|token)\s+"
    r"(?P<credential>[^\s,;]+)|(?P<value>[^\s,;]+))"
)
_BEARER_VALUE = re.compile(r"(?i)\bbearer\s+(?P<value>[^\s,;]+)")
_CLI_CREDENTIAL_ASSIGNMENT = re.compile(
    r"(?i)(?:^|\s)--(?:token|access-token|password|api[-_]key)"
    r"(?:=|\s+)(?P<value>(?:['\"]?)[^\s'\"`]+)"
)
_CREDENTIAL_URL_USERINFO = re.compile(
    r"(?i)\b(?:https?|ssh)://[^/\s:@]+:(?P<value>[^/\s@]+)@"
)
_ASSIGNMENT_SECRET_KEY = (
    r"api[_-]?key|apikey|secret(?:[_-]?key)?|password|passwd|token|"
    r"access[_-]?token|refresh[_-]?token|client[_-]?secret|private[_-]?key|"
    r"auth|bearer|signature|sig"
)
_KEY_VALUE_SECRET = re.compile(
    rf"(?i)\b(?:{_ASSIGNMENT_SECRET_KEY})\b\s*[:=]\s*"
    r"(?P<value>(?:['\"]?)[^\s'\"`&#]+)"
)
_AUTHORIZATION_ASSIGNMENT = re.compile(
    r"(?i)\bauthorization\s*=\s*(?P<value>(?:['\"]?)[^\s'\"`&#]+)"
)
_QUERY_SECRET = re.compile(
    rf"(?i)[?&](?:{_ASSIGNMENT_SECRET_KEY}|authorization|key|"
    r"x-amz-(?:signature|credential|security-token)|"
    r"x-goog-(?:signature|credential))=(?P<value>[^&#\s]+)"
)
_PRIVATE_TOKEN = re.compile(
    r"\b(?:sk|ghp|github_pat|xox[baprs])[_-][A-Za-z0-9_-]{12,}\b|"
    r"\bAKIA[A-Z0-9]{16}\b"
)
_DOCUMENTATION_PLACEHOLDER = re.compile(
    r"^(?:<[^>\s]+>|\[[^\]\s]+\]|\{[^}\s]+\}|\$\{[^}\s]+\}|"
    r"\$[A-Z][A-Z0-9_]*)$"
)
_DOCUMENTATION_FIELD_WORD = re.compile(
    r"(?i)^(?:header|name|string|field|configuration|config|example|sample|value)$"
)


def _documentation_value(value: str) -> bool:
    candidate = value.strip().strip("'\"")
    return (
        _DOCUMENTATION_PLACEHOLDER.fullmatch(candidate) is not None
        or _DOCUMENTATION_FIELD_WORD.fullmatch(candidate) is not None
    )


def _matched_secret(pattern: re.Pattern[str], value: str) -> bool:
    for match in pattern.finditer(value):
        candidate = match.groupdict().get("credential") or match.group("value")
        if not _documentation_value(candidate):
            return True
    return False


def _has_match(pattern: re.Pattern[str], value: str) -> bool:
    return pattern.search(value) is not None


def sensitive_text(value: Any) -> bool:
    """Return whether a string contains an explicit credential representation.

    Non-string values are not text and are left to their owning schema
    validator.  A false result is not a guarantee that the value is safe.
    """
    if not isinstance(value, str):
        return False
    return (
        _matched_secret(_AUTHORIZATION_VALUE, value)
        or _matched_secret(_BEARER_VALUE, value)
        or _matched_secret(_CLI_CREDENTIAL_ASSIGNMENT, value)
        or _has_match(_CREDENTIAL_URL_USERINFO, value)
        or _matched_secret(_KEY_VALUE_SECRET, value)
        or _matched_secret(_AUTHORIZATION_ASSIGNMENT, value)
        or _has_match(_QUERY_SECRET, value)
        or _PRIVATE_TOKEN.search(value) is not None
    )


def redact_text(value: Any) -> str:
    """Return a whole-value redaction for sensitive text.

    Callers should pass strings.  Returning an empty string for other types
    keeps a defensive rendering path from stringifying arbitrary objects.
    """
    if not isinstance(value, str):
        return ""
    return REDACTED_SENSITIVE_VALUE if sensitive_text(value) else value
