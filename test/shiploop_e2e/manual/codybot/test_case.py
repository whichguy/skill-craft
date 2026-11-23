"""Offline CLI checks for the manual Codybot case."""

import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest


CASE = Path(__file__).resolve().parent
BRIEF = "Codybot-design-prompt.md"


class CodybotCaseTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="codybot case's ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.runs = self.root / "prepared instances"
        self.calls = self.root / "launcher-calls.jsonl"
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        git = shutil.which("git")
        self.assertIsNotNone(git, "these tests require Git")
        self.git = bin_dir / "git"
        self.git.symlink_to(git)

        # Select only this fake launcher, even when the real one is installed.
        fake_code = textwrap.dedent("""\
            import json
            import os
            from pathlib import Path
            import subprocess
            import sys

            args = sys.argv[1:]
            for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_QUARANTINE_PATH"):
                if name in os.environ:
                    raise AssertionError(f"launcher inherited {name}")
            project = args[args.index("--cd") + 1]
            top = subprocess.check_output(["git", "-C", project, "rev-parse", "--show-toplevel"], text=True)
            if top.rstrip("\\n") != project:
                raise AssertionError("launcher cannot resolve the prepared project")
            with open(os.environ["CODYBOT_TEST_CALLS"], "a", encoding="utf-8") as calls:
                calls.write(json.dumps(args) + "\\n")
            Path(args[args.index("--output-last-message") + 1]).write_text(
                "fake final message\\n", encoding="utf-8"
            )
            if sys.stdin.read():
                raise AssertionError("launcher received unexpected stdin")
            print('{"type":"fake_event"}')
            sys.exit(int(os.environ["CODYBOT_TEST_EXIT"]))
            """)
        fake = bin_dir / "shiploop-codex"
        fake.write_text(
            f'#!/bin/sh\nexec {shlex.quote(sys.executable)} -c {shlex.quote(fake_code)} "$@"\n',
            encoding="utf-8",
        )
        fake.chmod(0o755)
        self.env = {
            "HOME": str(self.root),
            "PATH": str(bin_dir),
            "GIT_CONFIG_NOSYSTEM": "1",
            "CODYBOT_TEST_CALLS": str(self.calls),
            "CODYBOT_TEST_EXIT": "17",
        }

    def invoke(self, *args, env=None, cwd=None):
        command = [sys.executable, str(CASE / "run.py"), "--runs-root", str(self.runs), *args]
        return subprocess.run(command, env=env or self.env, cwd=cwd, capture_output=True, text=True, timeout=15)

    def launcher_calls(self):
        return [json.loads(line) for line in self.calls.read_text(encoding="utf-8").splitlines()]

    def assert_prepared(self, instance):
        project = instance / "project"
        expected = (CASE / BRIEF).read_bytes()
        self.assertEqual((project / BRIEF).read_bytes(), expected)
        git = [str(self.git), "-C", str(project)]
        self.assertEqual(
            subprocess.check_output([*git, "ls-tree", "--name-only", "HEAD"], env=self.env),
            f"{BRIEF}\n".encode(),
        )
        self.assertEqual(subprocess.check_output([*git, "show", f"HEAD:{BRIEF}"], env=self.env), expected)
        self.assertEqual(subprocess.check_output([*git, "status", "--porcelain"], env=self.env), b"")
        self.assertTrue((instance / "launch.txt").is_file())
        self.assertFalse((instance / "workspace").exists())

    def assert_launched(self, instance):
        calls = self.launcher_calls()
        self.assertEqual(len(calls), 1)
        (args,) = calls
        self.assertEqual(args[:4], ["exec", "--json", "--cd", str(instance / "project")])
        self.assertEqual(args[4], "-c")
        name, roots = args[5].split("=", 1)
        self.assertEqual(name, "sandbox_workspace_write.writable_roots")
        self.assertEqual(json.loads(roots), [str(instance), str(instance / "project" / ".git")])
        self.assertEqual(args[6:8], ["--output-last-message", str(instance / "last-message.md")])
        self.assertTrue(args[8].startswith("$skill-craft:shiploop "))
        self.assertIn(f"`{BRIEF}`", args[8])
        self.assertEqual((instance / "last-message.md").read_text(), "fake final message\n")

    def test_default_and_prepare_only_create_separate_local_projects(self):
        first = self.invoke()
        self.assertEqual(first.returncode, 0, first.stderr)
        second = self.invoke("--prepare-only")
        self.assertEqual(second.returncode, 0, second.stderr)
        instances = list(self.runs.iterdir())
        self.assertEqual(len(instances), 2)
        self.assertFalse(self.calls.exists())
        for instance in instances:
            with self.subTest(instance=instance):
                self.assert_prepared(instance)
                self.assertFalse((instance / "events.jsonl").exists())
                self.assertFalse((instance / "last-message.md").exists())

    def test_run_launches_once_and_propagates_failure(self):
        result = self.invoke("--run")
        self.assertEqual(result.returncode, 17, result.stderr)
        (instance,) = self.runs.iterdir()
        self.assert_prepared(instance)
        self.assert_launched(instance)
        self.assertEqual((instance / "events.jsonl").read_text(), '{"type":"fake_event"}\n')

    def test_saved_command_targets_its_prepared_project_and_appends_its_log(self):
        self.invoke().check_returncode()
        (instance,) = self.runs.iterdir()
        self.invoke().check_returncode()
        other = next(path for path in self.runs.iterdir() if path != instance)
        events = instance / "events.jsonl"
        events.write_text('{"type":"existing_event"}\n', encoding="utf-8")
        result = subprocess.run(
            ["/bin/sh", str(instance / "launch.txt")],
            cwd=other,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(result.returncode, 17, result.stderr)
        self.assert_launched(instance)
        self.assertEqual(events.read_text(), '{"type":"existing_event"}\n{"type":"fake_event"}\n')
        self.assertFalse((other / "events.jsonl").exists())
        self.assertFalse((other / "last-message.md").exists())

    def test_run_and_prepare_only_conflict_before_preparation(self):
        result = self.invoke("--run", "--prepare-only")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("not allowed with argument", result.stderr)
        self.assertFalse(self.runs.exists())
        self.assertFalse(self.calls.exists())

    def test_preparation_ignores_ambient_git_hooks_and_clean_filters(self):
        hooks = self.root / "hooks"
        hooks.mkdir()
        sentinel = self.root / "hook-ran"
        hook = hooks / "post-index-change"
        hook.write_text('#!/bin/sh\nprintf "hook ran" > "$HOME/hook-ran"\n', encoding="utf-8")
        hook.chmod(0o755)
        attrs = self.root / "global-attributes"
        attrs.write_text("*.md filter=fixture\n", encoding="utf-8")
        for key, value in {
            "core.hooksPath": str(hooks),
            "core.attributesFile": str(attrs),
            "filter.fixture.clean": "printf 'unexpected replacement\\n'",
        }.items():
            subprocess.run([str(self.git), "config", "--global", key, value], env=self.env, check=True)

        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        (instance,) = self.runs.iterdir()
        self.assertFalse(sentinel.exists())
        self.assertFalse(self.calls.exists())
        committed = subprocess.check_output(
            [str(self.git), "-C", str(instance / "project"), "show", f"HEAD:{BRIEF}"],
            env=self.env,
        )
        self.assertEqual(committed, (CASE / BRIEF).read_bytes())

    def test_outer_git_environment_cannot_redirect_preparation_or_either_launch_path(self):
        outer = self.root / "outer"
        outer.mkdir()
        git = [str(self.git), "-C", str(outer)]
        subprocess.run([*git, "init", "--quiet", "--template="], env=self.env, check=True)
        (outer / "outer.txt").write_text("outer repository\n", encoding="utf-8")
        subprocess.run([*git, "add", "--", "outer.txt"], env=self.env, check=True)
        subprocess.run(
            [
                *git, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                "commit", "--quiet", "-m", "Seed unrelated repository",
            ],
            env=self.env,
            check=True,
        )
        head_command = [*git, "rev-parse", "HEAD"]
        outer_head = subprocess.check_output(head_command, env=self.env)
        outer_index = outer / ".git" / "index"
        index_bytes = outer_index.read_bytes()
        alternate_index = self.root / "outer-provided-index"
        alternate_index.write_bytes(index_bytes)
        outer_env = dict(
            self.env,
            GIT_DIR=str(outer / ".git"),
            GIT_WORK_TREE=str(outer),
            GIT_INDEX_FILE=str(alternate_index),
            GIT_QUARANTINE_PATH=str(outer / ".git" / "objects" / "quarantine"),
        )

        self.invoke().check_returncode()
        (saved,) = self.runs.iterdir()
        self.invoke("--prepare-only", env=outer_env, cwd=outer).check_returncode()
        prepared = next(path for path in self.runs.iterdir() if path != saved)
        self.assert_prepared(prepared)
        self.assertFalse(self.calls.exists())

        direct = self.invoke("--run", env=outer_env, cwd=outer)
        self.assertEqual(direct.returncode, 17, direct.stderr)
        launched = next(path for path in self.runs.iterdir() if path not in {saved, prepared})
        self.assert_prepared(launched)
        self.assert_launched(launched)
        self.calls.unlink()

        result = subprocess.run(
            ["/bin/sh", str(saved / "launch.txt")],
            cwd=outer,
            env=outer_env,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(result.returncode, 17, result.stderr)
        self.assert_launched(saved)
        self.assertEqual(subprocess.check_output(head_command, env=self.env), outer_head)
        self.assertEqual(outer_index.read_bytes(), index_bytes)
        self.assertEqual(alternate_index.read_bytes(), index_bytes)


if __name__ == "__main__":
    unittest.main()
