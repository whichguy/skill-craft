#!/usr/bin/env python3
"""Hermetic guard for opt-in consumer tests; no host CLI is executed here."""
import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("host_smoke", Path(__file__).with_name("marketplace-host-smoke.py"))
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)


def write_fake_codex(path: Path) -> None:
    """Materialize a copied local package and record the CLI boundary it sees."""
    path.write_text(
        r'''#!/usr/bin/env python3
import json
import os
from pathlib import Path
import shutil
import sys


def emit(value):
    print(json.dumps(value, sort_keys=True))


def state_path(home):
    return home / "fake-codex-state.json"


def load_state(home):
    path = state_path(home)
    return json.loads(path.read_text()) if path.exists() else {}


def save_state(home, value):
    state_path(home).write_text(json.dumps(value, sort_keys=True))


def record(args):
    log = Path(os.environ["SKILL_CRAFT_FAKE_CODEX_LOG"])
    credential_keys = sorted(
        key for key in os.environ
        if any(token in key.upper() for token in ("TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "API_KEY", "ACCESS_KEY", "PRIVATE_KEY"))
    )
    git_context_keys = sorted(
        key for key in os.environ
        if key.startswith("GIT_CONFIG_") or key in {
            "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
            "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
            "GIT_CEILING_DIRECTORIES", "GIT_DISCOVERY_ACROSS_FILESYSTEM", "GIT_NAMESPACE",
        }
    )
    value = {
        "argv": args,
        "cwd": os.getcwd(),
        "env": {
            "HOME": os.environ.get("HOME"),
            "CODEX_HOME": os.environ.get("CODEX_HOME"),
            "keys": sorted(os.environ),
            "credential_keys": credential_keys,
            "git_context_keys": git_context_keys,
        },
    }
    with log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True) + "\n")


def main():
    args = sys.argv[1:]
    record(args)
    home = Path(os.environ["CODEX_HOME"])
    if args == ["--version"]:
        emit({"version": "fake-codex-1.0"})
        return 0
    if args[:3] == ["plugin", "marketplace", "add"] and len(args) == 4:
        state = load_state(home)
        state["marketplace"] = args[3]
        save_state(home, state)
        emit({"status": "added"})
        return 0
    if args[:2] == ["plugin", "add"] and len(args) >= 3:
        state = load_state(home)
        market = Path(state["marketplace"])
        source = market / "plugins" / "skill-craft"
        target = home / "plugins" / "cache" / "fake-market" / "skill-craft" / "fixture"
        if target.exists():
            raise RuntimeError("fake Codex fixture cache unexpectedly already exists")
        shutil.copytree(source, target)
        manifest = json.loads((source / ".codex-plugin" / "plugin.json").read_text())
        state.update(installed=True, plugin_id=args[2], version=manifest["version"], cache=str(target))
        save_state(home, state)
        emit({"pluginId": args[2], "status": "installed"})
        return 0
    if args[:2] == ["plugin", "remove"] and len(args) >= 3:
        state = load_state(home)
        if state.get("plugin_id") != args[2]:
            raise RuntimeError("fake Codex remove did not target the installed package")
        state["installed"] = False
        save_state(home, state)
        emit({"pluginId": args[2], "status": "removed"})
        return 0
    if args[:2] == ["plugin", "list"]:
        state = load_state(home)
        installed = []
        if state.get("installed"):
            installed.append({"pluginId": state["plugin_id"], "version": state["version"]})
        emit({"installed": installed})
        return 0
    raise RuntimeError("unsupported fake Codex command: " + repr(args))


if __name__ == "__main__":
    raise SystemExit(main())
''',
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


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

    def test_workspace_helper_environment_removes_context_overrides(self):
        env = smoke.isolated_environment({"PATH": "/usr/bin:/bin"}, Path("/tmp/disposable home"))
        env.update({
            "GIT_DIR": "/untrusted/git-dir",
            "GIT_WORK_TREE": "/untrusted/worktree",
            "GIT_CONFIG_KEY_0": "credential.helper",
            "GIT_CONFIG_VALUE_0": "untrusted-helper",
        })
        helper_env = smoke.workspace_helper_environment(env)
        self.assertEqual(helper_env["HOME"], env["HOME"])
        self.assertEqual(helper_env["CODEX_HOME"], env["CODEX_HOME"])
        self.assertEqual(helper_env["PYTHONDONTWRITEBYTECODE"], "1")
        self.assertEqual(smoke.environment_summary(helper_env)["git_context_overrides"], [])

    def test_fake_codex_installed_ask_agent_consumer_preserves_linked_dirty_caller(self):
        with tempfile.TemporaryDirectory(prefix="fake-codex-ask-agent-") as temporary:
            root = Path(temporary)
            fake = root / "fake-codex"
            log = root / "fake-codex.jsonl"
            write_fake_codex(fake)
            receipt = smoke.run_ask_agent_consumer(
                "codex",
                str(fake),
                extra_environment={"SKILL_CRAFT_FAKE_CODEX_LOG": str(log)},
            )

            self.assertEqual(receipt["status"], "passed")
            self.assertTrue(receipt["caller_is_linked_worktree"])
            self.assertTrue(receipt["caller_worktree_preserved"])
            self.assertTrue(receipt["caller_index_preserved"])
            self.assertTrue(receipt["close_replay_identical"])
            self.assertTrue(receipt["plugin_removed"])
            self.assertTrue(receipt["cache_retained_after_removal"])
            self.assertIn("skills/ask-agent/scripts/ask_agent_workspace.py", receipt["package_files"])
            identity = receipt["selected_package"]
            self.assertEqual(identity["status"], "verified")
            self.assertEqual(identity["schema"], "ask-agent.skill.identity.v1")
            self.assertTrue(identity["skill_card"].endswith("/skills/ask-agent/SKILL.md"))
            self.assertTrue(identity["resolved_helper"].endswith("/scripts/ask_agent_workspace.py"))
            self.assertEqual(receipt["helper_environment"]["git_context_overrides"], [])
            self.assertEqual(receipt["helper_environment"]["credential_keys"], [])
            self.assertIn("CODEX_HOME", receipt["helper_environment"]["keys"])

            events = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
            self.assertGreaterEqual(len(events), 5)
            expected_codex_home = str(Path(receipt["disposable_profile"]) / ".codex")
            self.assertTrue(all(event["env"]["CODEX_HOME"] == expected_codex_home for event in events))
            self.assertTrue(all(not event["env"]["credential_keys"] for event in events))
            self.assertTrue(any(event["argv"][:3] == ["plugin", "marketplace", "add"] for event in events))
            self.assertTrue(any(event["argv"][:2] == ["plugin", "add"] for event in events))
            self.assertTrue(any(event["argv"][:2] == ["plugin", "remove"] for event in events))
            helper_commands = [
                command for command in receipt["commands"]
                if any("ask_agent_workspace.py" in argument for argument in command["argv"])
            ]
            self.assertGreaterEqual(len(helper_commands), 7)
            self.assertTrue(all(command["environment"]["git_context_overrides"] == [] for command in helper_commands))
            self.assertTrue(all(command["environment"]["credential_keys"] == [] for command in helper_commands))


if __name__ == "__main__":
    unittest.main()
