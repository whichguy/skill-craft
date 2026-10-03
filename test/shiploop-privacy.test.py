#!/usr/bin/env python3
"""Focused credential-screening contracts for ShipLoop's privacy helper."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_privacy as privacy  # noqa: E402


class PrivacyHelperTests(unittest.TestCase):
    def test_explicit_credential_forms_are_sensitive_and_redacted_as_a_whole(self) -> None:
        samples = (
            "Authorization: Bearer packet-secret-123",
            "Bearer packet-secret-123",
            "--token=packet-secret-123",
            "--password packet-secret-123",
            "--api-key=packet-secret-123",
            "https://user:packet-secret-123@example.invalid/path",
            "https://example.invalid/download?X-Amz-Signature=packet-secret-123",
            "https://example.invalid/download?api_key=packet-secret-123",
            "api_key=packet-secret-123",
            "github_pat_0123456789abcdefghijklmnop",
            "Authorization: Bearer secret",
            "--token=secret",
            "api_key=secret",
            "https://example.invalid/download?signature=secret",
            "https://user:secret@example.invalid/path",
        )
        for value in samples:
            with self.subTest(value=value.split("=", 1)[0]):
                self.assertTrue(privacy.sensitive_text(value))
                self.assertEqual(
                    privacy.redact_text(value), "[redacted sensitive value]"
                )

    def test_ordinary_labels_and_documentation_urls_are_not_secrets(self) -> None:
        samples = (
            "development-deployer",
            "credential",
            "env:API_TOKEN",
            "primary key: record ID",
            "cache key=value",
            "Authorization: header required",
            "Authorization: Bearer <token>",
            "Authorization: Basic example",
            "api_key: name of configuration field",
            "token: string field",
            "--token=<token>",
            "Authorization: Bearer $TOKEN",
            "--token $TOKEN",
            "api_key=$API_KEY",
            "https://docs.example.invalid/install?section=authentication",
        )
        for value in samples:
            with self.subTest(value=value):
                self.assertFalse(privacy.sensitive_text(value))
                self.assertEqual(privacy.redact_text(value), value)

    def test_a_label_followed_by_a_plain_description_is_not_a_credential(self) -> None:
        # Luna max's discovery completion was refused twice for text like this (batch 1003, F1).
        for value in (
            "session token: opaque UUID",
            "auth: none required",
            "secret=none",
            "signature: n/a",
            "api_key: null",
            "password: optional",
            "token: true",
            "auth: disabled",
            # punctuation and markdown around the described value, and common scheme words
            "Auth: none.",
            "Public endpoints (auth: none)",
            "auth: none, public endpoint",
            "session token: opaque, rotated hourly",
            "signature: n/a.",
            "secret: none;",
            "**auth:** none",
            "auth: *none*",
            "auth: oauth2",
            "auth: jwt",
            "auth: session",
            "auth: anonymous",
            "token: unused",
            "secret: unset",
            "auth: not required",
            "password: ***",
        ):
            with self.subTest(value=value):
                self.assertFalse(privacy.sensitive_text(value))

    def test_a_real_secret_that_merely_starts_with_a_description_word_is_still_flagged(self) -> None:
        for value in (
            "token: nonexistent-abc123456",
            "secret=optional-key-9f8e7d6c",
            "password: truesecret",
            "auth=none123",
            "signature: n/a-8f3a9c1d",
            "Authorization: Bearer abc123def456",
            "password: hunter2hunter2",
            "api_key=sk-live-0123456789",
            "token: 9f8e7d6c5b4a3210",
            "secret: none-but-9f8e7d6c5b4a3210",
        ):
            with self.subTest(value=value):
                self.assertTrue(privacy.sensitive_text(value))

    def test_non_string_values_are_not_stringified_or_reported_as_sensitive(self) -> None:
        for value in (None, 0, False, [], {}):
            with self.subTest(value=type(value).__name__):
                self.assertFalse(privacy.sensitive_text(value))
                self.assertEqual(privacy.redact_text(value), "")


if __name__ == "__main__":
    unittest.main()
