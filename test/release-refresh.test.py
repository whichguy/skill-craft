#!/usr/bin/env python3
"""Hermetic tests for multi-host post-release refresh and verification."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

sys.dont_write_bytecode = True

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "release-refresh.py"


class ReleaseRefreshTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="release-refresh-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "repo"
        self.home = self.root / "home"
        self.bin_dir = self.root / "bin"
        self.state_dir = self.root / "host-state"
        self.log_file = self.root / "commands.jsonl"
        self.ps_file = self.root / "ps.txt"
        for d in (self.repo, self.home, self.bin_dir, self.state_dir):
            d.mkdir(parents=True, exist_ok=True)
        self.ps_file.write_text("", encoding="utf-8")

        self._write_repo(
            plugin_version="4.20.0",
            skills={"shiploop": "2.21.0", "skill-interop": "0.2.6", "improve": "0.7.5"},
        )
        # Seed every host initially at old release 4.19.0 (missing skill-interop or older shiploop).
        self._seed_host_trees(
            plugin_version="4.19.0",
            skills={"shiploop": "2.20.0", "improve": "0.7.5"},
        )
        self._write_fake_clis()

        self.env = {
            k: v
            for k, v in os.environ.items()
            if not k.startswith(("CLAUDE", "CODEX", "GROK", "ANTIGRAVITY", "AGY_", "CURSOR_"))
        }
        self.env.update(
            HOME=str(self.home),
            XDG_CONFIG_HOME=str(self.home / ".config"),
            XDG_STATE_HOME=str(self.home / ".local" / "state"),
            PATH=f"{self.bin_dir}{os.pathsep}{self.env.get('PATH', os.defpath)}",
            PYTHONDONTWRITEBYTECODE="1",
            FAKE_STATE_DIR=str(self.state_dir),
            FAKE_RELEASE_REPO=str(self.repo),
            FAKE_COMMAND_LOG=str(self.log_file),
            RELEASE_REFRESH_PS_FILE=str(self.ps_file),
        )

    def _write_skill_tree(
        self, base: Path, skills: dict[str, str], *, with_agy_hook: bool = False, clean: bool = True
    ) -> None:
        if clean and base.exists():
            shutil.rmtree(base)
        elif (base / "skills").exists():
            shutil.rmtree(base / "skills")
        (base / "skills").mkdir(parents=True, exist_ok=True)
        for leaf, version in skills.items():
            leaf_dir = base / "skills" / leaf
            leaf_dir.mkdir(parents=True, exist_ok=True)
            (leaf_dir / "SKILL.md").write_text(
                f"---\nname: {leaf}\ndescription: {leaf} skill\nversion: {version}\nlicense: MIT\n---\n\n# {leaf}\n",
                encoding="utf-8",
            )
        if with_agy_hook:
            (base / ".antigravity-plugin").mkdir(parents=True, exist_ok=True)
            (base / ".antigravity-plugin" / "plugin.json").write_text(
                json.dumps({"name": "skill-craft", "version": "4.20.0"}),
                encoding="utf-8",
            )
            (base / "hooks.json").write_text(
                json.dumps({"shiploop": {"Stop": [{"type": "command", "command": "./skills/shiploop/scripts/stop"}]}}),
                encoding="utf-8",
            )

    def _write_repo(self, *, plugin_version: str, skills: dict[str, str], sync_exit: int = 0) -> None:
        (self.repo / "catalog").mkdir(parents=True, exist_ok=True)
        (self.repo / "catalog" / "skill-craft-plugin.json").write_text(
            json.dumps({"name": "skill-craft", "version": plugin_version, "description": "Skill Craft bundle"}) + "\n",
            encoding="utf-8",
        )
        self._write_skill_tree(self.repo, skills, clean=False)
        self._write_skill_tree(self.repo / "plugins" / "skill-craft", skills, with_agy_hook=True)
        scripts_dir = self.repo / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        sync = scripts_dir / "sync-plugin-views.sh"
        sync.write_text(
            f"#!/usr/bin/env bash\nif [[ \"${{1:-}}\" == \"--check\" ]]; then exit {sync_exit}; fi\nexit 0\n",
            encoding="utf-8",
        )
        sync.chmod(0o755)

    def _seed_host_trees(self, *, plugin_version: str, skills: dict[str, str]) -> None:
        # Claude cache + installed_plugins.json (which Cursor also reads).
        claude_pkg = self.home / ".claude" / "plugins" / "cache" / "whichguy" / "skill-craft" / plugin_version
        self._write_skill_tree(claude_pkg, skills)
        claude_inv = self.home / ".claude" / "plugins" / "installed_plugins.json"
        claude_inv.parent.mkdir(parents=True, exist_ok=True)
        claude_inv.write_text(
            json.dumps({
                "version": 2,
                "plugins": {
                    "skill-craft@whichguy": [{
                        "scope": "user",
                        "installPath": str(claude_pkg),
                        "version": plugin_version,
                    }]
                },
            }),
            encoding="utf-8",
        )
        (self.state_dir / "claude.json").write_text(
            json.dumps({"catalog_refreshed": False, "version": plugin_version, "path": str(claude_pkg)}),
            encoding="utf-8",
        )

        # Codex cache + .tmp/marketplaces clone.
        codex_cache = self.home / ".codex" / "plugins" / "cache" / "whichguy" / "skill-craft" / plugin_version
        codex_mp = self.home / ".codex" / ".tmp" / "marketplaces" / "whichguy" / "plugins" / "skill-craft"
        self._write_skill_tree(codex_cache, skills)
        self._write_skill_tree(codex_mp, skills)
        (self.state_dir / "codex.json").write_text(
            json.dumps({"version": plugin_version, "mp_path": str(codex_mp)}),
            encoding="utf-8",
        )

        # Antigravity global plugins directory.
        agy_pkg = self.home / ".gemini" / "config" / "plugins" / "skill-craft"
        self._write_skill_tree(agy_pkg, skills, with_agy_hook=True)
        (self.state_dir / "agy.json").write_text(
            json.dumps({"version": plugin_version, "path": str(agy_pkg), "skills": sorted(skills)}),
            encoding="utf-8",
        )

        # Grok installed-plugins directory.
        grok_pkg = self.home / ".grok" / "installed-plugins" / "skill-craft-b923f37c"
        self._write_skill_tree(grok_pkg, skills)
        (self.state_dir / "grok.json").write_text(
            json.dumps({"catalog_refreshed": False, "version": plugin_version, "path": str(grok_pkg)}),
            encoding="utf-8",
        )

    def _write_fake_clis(self) -> None:
        driver = self.root / "fake_host_cli.py"
        driver.write_text(
            textwrap.dedent("""\
                import json
                import os
                from pathlib import Path
                import shutil
                import sys

                host = sys.argv[1]
                args = sys.argv[2:]
                state_dir = Path(os.environ["FAKE_STATE_DIR"])
                repo = Path(os.environ["FAKE_RELEASE_REPO"])
                home = Path(os.environ["HOME"])
                with Path(os.environ["FAKE_COMMAND_LOG"]).open("a", encoding="utf-8") as log:
                    log.write(json.dumps({"host": host, "args": args}) + "\\n")

                bundle = json.loads((repo / "catalog" / "skill-craft-plugin.json").read_text(encoding="utf-8"))
                target_ver = bundle["version"]
                src_pkg = repo / "plugins" / "skill-craft"
                leaves = sorted(p.parent.name for p in (src_pkg / "skills").glob("*/SKILL.md"))

                def copy_pkg(dest: Path) -> None:
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(src_pkg, dest)

                if host == "claude":
                    st = json.loads((state_dir / "claude.json").read_text(encoding="utf-8"))
                    if args == ["plugin", "marketplace", "update", "whichguy"]:
                        st["catalog_refreshed"] = True
                        (state_dir / "claude.json").write_text(json.dumps(st), encoding="utf-8")
                    elif args == ["plugin", "update", "skill-craft@whichguy", "--scope", "user"]:
                        # Mirrors real Claude Code: plugin update only advances if marketplace update ran first!
                        if st.get("catalog_refreshed"):
                            dest = home / ".claude" / "plugins" / "cache" / "whichguy" / "skill-craft" / target_ver
                            copy_pkg(dest)
                            st["version"] = target_ver
                            st["path"] = str(dest)
                            (state_dir / "claude.json").write_text(json.dumps(st), encoding="utf-8")
                            inv = home / ".claude" / "plugins" / "installed_plugins.json"
                            inv.write_text(json.dumps({
                                "version": 2,
                                "plugins": {"skill-craft@whichguy": [{
                                    "scope": "user", "installPath": str(dest), "version": target_ver,
                                }]},
                            }), encoding="utf-8")
                    elif args == ["plugin", "list", "--json"]:
                        print(json.dumps([{
                            "id": "skill-craft@whichguy",
                            "version": st["version"],
                            "scope": "user",
                            "enabled": True,
                            "installPath": st["path"],
                        }]))
                    else:
                        sys.exit(f"unexpected claude args: {args}")

                elif host == "codex":
                    st = json.loads((state_dir / "codex.json").read_text(encoding="utf-8"))
                    if args == ["plugin", "marketplace", "upgrade", "whichguy"]:
                        cache_parent = home / ".codex" / "plugins" / "cache" / "whichguy" / "skill-craft"
                        if cache_parent.exists():
                            shutil.rmtree(cache_parent)
                        copy_pkg(cache_parent / target_ver)
                        mp = Path(st["mp_path"])
                        copy_pkg(mp)
                        st["version"] = target_ver
                        (state_dir / "codex.json").write_text(json.dumps(st), encoding="utf-8")
                    elif args == ["plugin", "list", "--marketplace", "whichguy", "--json"]:
                        print(json.dumps({
                            "installed": [{
                                "pluginId": "skill-craft@whichguy",
                                "name": "skill-craft",
                                "marketplaceName": "whichguy",
                                "version": st["version"],
                                "installed": True,
                                "enabled": True,
                                "source": {"source": "local", "path": st["mp_path"]},
                            }],
                            "available": [],
                        }))
                    else:
                        sys.exit(f"unexpected codex args: {args}")

                elif host == "agy":
                    st = json.loads((state_dir / "agy.json").read_text(encoding="utf-8"))
                    if len(args) == 3 and args[:2] == ["plugin", "install"]:
                        dest = Path(st["path"])
                        copy_pkg(dest)
                        st["version"] = target_ver
                        st["skills"] = leaves
                        (state_dir / "agy.json").write_text(json.dumps(st), encoding="utf-8")
                    elif args == ["plugin", "list", "--json"]:
                        print(json.dumps([{
                            "name": "skill-craft",
                            "enabled": True,
                            "version": st["version"],
                            "source": "antigravity",
                            "path": st["path"],
                            "skills": st["skills"],
                            "agents": ["shiploop"],
                            "hooks": ["shiploop"],
                        }]))
                    else:
                        sys.exit(f"unexpected agy args: {args}")

                elif host == "grok":
                    st = json.loads((state_dir / "grok.json").read_text(encoding="utf-8"))
                    if args == ["plugin", "marketplace", "update", "whichguy"]:
                        st["catalog_refreshed"] = True
                        (state_dir / "grok.json").write_text(json.dumps(st), encoding="utf-8")
                    elif args == ["plugin", "update", "skill-craft"]:
                        if st.get("catalog_refreshed"):
                            dest = Path(st["path"])
                            copy_pkg(dest)
                            st["version"] = target_ver
                            (state_dir / "grok.json").write_text(json.dumps(st), encoding="utf-8")
                    elif args == ["plugin", "list", "--json"]:
                        print(json.dumps([{
                            "status": "installed",
                            "name": "skill-craft",
                            "repo_key": "skill-craft-b923f37c",
                            "version": st["version"],
                            "path": st["path"],
                            "marketplace": "whichguy",
                        }]))
                    else:
                        sys.exit(f"unexpected grok args: {args}")
            """),
            encoding="utf-8",
        )
        for cli in ("claude", "codex", "agy", "grok"):
            wrapper = self.bin_dir / cli
            wrapper.write_text(
                f"#!/bin/sh\nexec {json.dumps(sys.executable)} -B {json.dumps(str(driver))} {cli} \"$@\"\n",
                encoding="utf-8",
            )
            wrapper.chmod(0o755)

    def invoke(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--repo", str(self.repo), *args],
            env=env or self.env,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def logged_commands(self) -> list[dict]:
        if not self.log_file.is_file():
            return []
        return [json.loads(line) for line in self.log_file.read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_check_only_detects_stale_versions_and_missing_new_skills_without_mutating(self) -> None:
        result = self.invoke("--check-only")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = json.loads(result.stderr)
        self.assertEqual(report["status"], "blocked")
        for host in ("claude", "codex", "antigravity", "grok", "cursor"):
            self.assertEqual(report["hosts"][host]["status"], "failed", host)
        # Only list commands ran; no update/upgrade/install command executed.
        for entry in self.logged_commands():
            self.assertIn("list", entry["args"], entry)

    def test_refreshes_all_hosts_together_and_verifies_shiploop_and_new_skills(self) -> None:
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "refreshed")
        self.assertEqual(report["expected"]["plugin_version"], "4.20.0")
        self.assertEqual(report["expected"]["shiploop_version"], "2.21.0")
        self.assertEqual(report["expected"]["skills"], ["improve", "shiploop", "skill-interop"])
        for host in ("claude", "codex", "antigravity", "grok", "cursor"):
            info = report["hosts"][host]
            self.assertEqual(info["status"], "ok", info)
            self.assertEqual(info["version"], "4.20.0")
            self.assertEqual(info["shiploop_version"], "2.21.0")
            self.assertEqual(info["skill_count"], 3)

        # Follow-up --check-only now passes cleanly.
        checked = self.invoke("--check-only")
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(json.loads(checked.stdout)["status"], "verified")

    def test_check_only_catches_inner_shiploop_version_drift_even_when_bundle_version_matches(self) -> None:
        self.assertEqual(self.invoke().returncode, 0)
        agy_shiploop = self.home / ".gemini" / "config" / "plugins" / "skill-craft" / "skills" / "shiploop" / "SKILL.md"
        agy_shiploop.write_text(agy_shiploop.read_text(encoding="utf-8").replace("2.21.0", "2.20.0"), encoding="utf-8")
        checked = self.invoke("--check-only", "--host", "antigravity")
        self.assertEqual(checked.returncode, 1)
        report = json.loads(checked.stderr)
        self.assertEqual(report["hosts"]["antigravity"]["status"], "failed")
        self.assertEqual(
            report["hosts"]["antigravity"]["tree"]["version_mismatches"],
            {"shiploop": {"expected": "2.21.0", "installed": "2.20.0"}},
        )

    def test_live_run_guard_protects_real_profiles_and_ignores_throwaway_e2e_homes(self) -> None:
        # Throwaway E2E home does NOT block refreshing the user's real Codex profile.
        self.ps_file.write_text(
            "41001 python3 /tmp/e2e-run/home/.codex/plugins/cache/whichguy/skill-craft/4.19.0/skills/shiploop/scripts/shiploop next\n",
            encoding="utf-8",
        )
        ok_res = self.invoke("--host", "codex")
        self.assertEqual(ok_res.returncode, 0, ok_res.stderr)

        # Real profile live processes block Codex, Antigravity, and Grok unless --allow-live is set.
        codex_live = self.home / ".codex" / "plugins" / "cache" / "whichguy" / "skill-craft" / "4.20.0" / "skills/shiploop/scripts/shiploop"
        agy_live = self.home / ".gemini" / "config" / "plugins" / "skill-craft" / "skills/shiploop/scripts/shiploop"
        grok_live = self.home / ".grok" / "installed-plugins" / "skill-craft-b923f37c" / "skills/shiploop/scripts/shiploop"
        self.ps_file.write_text(
            f"42001 python3 {codex_live} view --serve\n"
            f"42002 python3 {agy_live} next\n"
            f"42003 python3 {grok_live} complete\n",
            encoding="utf-8",
        )
        blocked = self.invoke("--host", "codex", "--host", "antigravity", "--host", "grok")
        self.assertEqual(blocked.returncode, 1)
        report = json.loads(blocked.stderr)
        for host in ("codex", "antigravity", "grok"):
            self.assertEqual(report["hosts"][host]["status"], "blocked", host)
            self.assertEqual(len(report["hosts"][host]["live_processes"]), 1)

        allowed = self.invoke("--host", "codex", "--host", "antigravity", "--host", "grok", "--allow-live")
        self.assertEqual(allowed.returncode, 0, allowed.stderr)

    def test_refuses_pending_change_notes_or_unsynced_views_without_override(self) -> None:
        note = self.repo / "changes" / "shiploop" / "pending.md"
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text("---\nbump: patch\n---\npending change\n", encoding="utf-8")
        blocked = self.invoke("--dry-run")
        self.assertEqual(blocked.returncode, 1)
        self.assertIn("pending unreleased change notes", blocked.stderr)
        self.assertEqual(self.logged_commands(), [])

        override = self.invoke("--dry-run", "--allow-unreleased")
        self.assertEqual(override.returncode, 0, override.stderr)
        self.assertEqual(json.loads(override.stdout)["status"], "dry-run")
        self.assertEqual(self.logged_commands(), [])

    def test_cursor_local_shadow_is_rejected(self) -> None:
        self.assertEqual(self.invoke("--host", "claude").returncode, 0)
        shadow = self.home / ".cursor" / "plugins" / "local" / "skill-craft"
        shadow.mkdir(parents=True)
        blocked = self.invoke("--check-only", "--host", "cursor")
        self.assertEqual(blocked.returncode, 1)
        self.assertIn("shadows Claude Code", blocked.stderr)

    def test_optional_grok_absence_vs_required_antigravity_absence(self) -> None:
        bash_bin = shutil.which("bash")
        assert bash_bin is not None
        (self.bin_dir / "bash").symlink_to(Path(bash_bin).resolve())
        (self.bin_dir / "grok").unlink()
        env = dict(self.env, PATH=str(self.bin_dir))
        # Under --host all, missing optional grok is reported as unavailable without failing.
        ok_all = self.invoke(env=env)
        self.assertEqual(ok_all.returncode, 0, ok_all.stderr)
        self.assertEqual(json.loads(ok_all.stdout)["hosts"]["grok"]["status"], "unavailable")

        # Explicitly asking for --host grok when missing fails.
        explicit_grok = self.invoke("--host", "grok", env=env)
        self.assertEqual(explicit_grok.returncode, 1)

        # Missing required antigravity (`agy`) fails --host all.
        (self.bin_dir / "agy").unlink()
        missing_agy = self.invoke(env=env)
        self.assertEqual(missing_agy.returncode, 1)
        self.assertEqual(json.loads(missing_agy.stderr)["hosts"]["antigravity"]["status"], "failed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
