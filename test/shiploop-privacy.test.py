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

    def test_non_string_values_are_not_stringified_or_reported_as_sensitive(self) -> None:
        for value in (None, 0, False, [], {}):
            with self.subTest(value=type(value).__name__):
                self.assertFalse(privacy.sensitive_text(value))
                self.assertEqual(privacy.redact_text(value), "")


if __name__ == "__main__":
    unittest.main()
