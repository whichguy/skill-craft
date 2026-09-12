#!/usr/bin/env python3
"""Focused credential-screening contracts for ShipLoop environment records."""

from __future__ import annotations

import runpy
import sys
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
CLI = SCRIPTS / "shiploop"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_privacy as privacy  # noqa: E402


core = runpy.run_path(str(CLI))


def machine() -> dict[str, Any]:
    return {
        "kind": "greenfield",
        "augment": False,
        "references": [],
        "tools": [],
        "mcp": [],
        "mcp_considered": "none(local fixture)",
        "handles": [],
        "initiation": "none",
        "ui": False,
        "ui_craft": "none(local fixture)",
        "exclusive": [],
    }


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


class EnvironmentPrivacyTests(unittest.TestCase):
    def assert_secret_rejected(self, mutate) -> None:
        secret = "privacy-secret-123"
        value = machine()
        mutate(value, secret)
        gaps = core["validate_machine"](value)
        joined = "\n".join(gaps)
        self.assertIn("sensitive credential material", joined)
        self.assertNotIn(secret, joined)

    def test_rejects_credentials_from_all_projected_generic_environment_fields(self) -> None:
        cases = (
            (
                "tools",
                lambda value, secret: value.update(tools=[f"--token={secret}"]),
            ),
            (
                "mcp",
                lambda value, secret: value.update(
                    mcp=[f"Authorization: Bearer {secret}"]
                ),
            ),
            (
                "mcp_considered",
                lambda value, secret: value.update(
                    mcp_considered=f"none(api_key={secret})"
                ),
            ),
            (
                "reference",
                lambda value, secret: value.update(
                    references=[
                        {
                            "path": f"https://example.invalid/?api_key={secret}",
                            "why": "Selected route documentation.",
                        }
                    ]
                ),
            ),
            (
                "handle metadata",
                lambda value, secret: value.update(
                    handles=[
                        {
                            "source": f"https://user:{secret}@example.invalid",
                            "need": "credential",
                            "resolve": "inspect",
                            "value": "",
                        }
                    ]
                ),
            ),
            (
                "ui craft",
                lambda value, secret: value.update(ui_craft=f"none(api_key={secret})"),
            ),
            (
                "exclusive route",
                lambda value, secret: value.update(
                    tools=["writer-cli"],
                    exclusive=[
                        {
                            "artifact": f"api_key={secret}",
                            "use": "writer-cli",
                            "dont_use": [],
                        }
                    ],
                ),
            ),
            (
                "layout",
                lambda value, secret: value.update(
                    layout={"reserved": [f"api_key={secret}"], "product": ["src/"]}
                ),
            ),
            (
                "routing",
                lambda value, secret: value.update(
                    routing={
                        "user_entrypoint": "/app",
                        "reserved_routes": ["/"],
                        "confirmation": f"--password {secret}",
                        "source": "docs/route.md",
                    }
                ),
            ),
        )
        for label, mutate in cases:
            with self.subTest(field=label):
                self.assert_secret_rejected(mutate)

    def test_credential_handle_reference_remains_a_valid_non_secret_contract(self) -> None:
        value = machine()
        value["handles"] = [
            {
                "source": "env:API_TOKEN",
                "need": "credential",
                "resolve": "inspect",
                "value": "",
            }
        ]
        self.assertEqual(core["validate_machine"](value), [])

    def test_non_string_machine_values_remain_schema_errors(self) -> None:
        value = machine()
        value["tools"] = [None]
        gaps = core["validate_machine"](value)
        self.assertIn("machine.tools[0] must be a nonempty string", "\n".join(gaps))

    def test_handle_planning_diagnostic_uses_an_index_without_echoing_source(self) -> None:
        secret = "privacy-secret-123"
        gaps = core["handles_block_plan"](
            {
                "handles": [
                    {
                        "source": f"Authorization: Bearer {secret}",
                        "need": "credential",
                        "resolve": "ask",
                        "value": "",
                    }
                ]
            }
        )
        self.assertEqual(gaps, ["handle[0] resolve=ask blocks dest plan"])
        self.assertNotIn(secret, "\n".join(gaps))


if __name__ == "__main__":
    unittest.main()
