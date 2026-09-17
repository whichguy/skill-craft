#!/usr/bin/env python3
"""Hermetic guard for opt-in consumer tests; no host CLI is executed here."""
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location("host_smoke", Path(__file__).with_name("marketplace-host-smoke.py"))
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)


class HostIsolationTest(unittest.TestCase):
    def test_allowlist_excludes_credentials_and_config_indirections(self):
        parent = {"PATH": "/usr/bin:/bin", "DEVELOPER_DIR": "/toolchain",
                  "OPENAI_API_KEY": "secret-openai", "ANTHROPIC_AUTH_TOKEN": "secret-claude",
                  "GH_TOKEN": "secret-github", "GOOGLE_APPLICATION_CREDENTIALS": "/personal/key",
                  "GROK_HOME": "/personal/grok", "CLAUDECODE": "parent-session",
                  "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "credential.helper",
                  "GIT_CONFIG_VALUE_0": "personal-helper", "HTTPS_PROXY": "credential-proxy",
                  "NODE_OPTIONS": "--require=/personal/hook", "PYTHONPATH": "/personal/modules"}
        home = Path("/tmp/disposable home")
        env = smoke.isolated_environment(parent, home)
        self.assertEqual(set(parent) & set(env), {"PATH", "DEVELOPER_DIR"})
        self.assertEqual(env["HOME"], str(home))
        self.assertEqual(env["CODEX_HOME"], str(home / ".codex"))
        self.assertEqual(env["GIT_CONFIG_NOSYSTEM"], "1")
        self.assertEqual(env["GIT_TERMINAL_PROMPT"], "0")

    def test_redacts_ambient_and_known_token_shapes(self):
        source = "secret-value Bearer diagnostic-token sk-abcdefghijklmnop ghp_abcdefghijklmnop"
        output = smoke.redact(source, {"CUSTOM_SECRET": "secret-value"})
        for token in ("secret-value", "diagnostic-token", "sk-abcdefghijklmnop", "ghp_abcdefghijklmnop"):
            self.assertNotIn(token, output)
        self.assertEqual(output.count("[REDACTED]"), 4)


if __name__ == "__main__":
    unittest.main()
