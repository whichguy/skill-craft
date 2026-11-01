"""Calibrate the round-7 checks of launch.sh on three hand-written slug.py variants, before any live run.

Usage: python3 calibrate_checks.py          (exit 0 when every check gives the expected status on every variant)

The variants: `deferred` (what link 1 asks for: the basic tool, `--max-length` an unknown option that exits 2), `built` (what link 2
should deliver) and `wrong-cut` (cuts but leaves a trailing hyphen, which the request forbids).  The check texts are read out of
launch.sh, so the launcher and the calibration cannot drift apart.  No model is called.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECKS = dict(re.findall(r"^(C_[A-Z0-9_]+)='(.*)'$", (HERE / "launch.sh").read_text(encoding="utf-8"), re.M))

BASE = '''import re, sys


def slug(title):
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def usage():
    print("usage: python3 slug.py TITLE", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    args = sys.argv[1:]
'''
VARIANTS = {
    "deferred": BASE + '''    if len(args) != 1:
        usage()
    print(slug(args[0]))
''',
    "built": BASE + '''    limit = None
    if len(args) == 3 and args[1] == "--max-length":
        limit = int(args[2])
        args = args[:1]
    if len(args) != 1:
        usage()
    out = slug(args[0])
    print(out[:limit].strip("-") if limit is not None else out)
''',
    "wrong-cut": BASE + '''    limit = None
    if len(args) == 3 and args[1] == "--max-length":
        limit = int(args[2])
        args = args[:1]
    if len(args) != 1:
        usage()
    out = slug(args[0])
    print(out[:limit] if limit is not None else out)
''',
}
TEST = '''import unittest
from slug import slug


class SlugTest(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(slug("Hello, World!"), "hello-world")


if __name__ == "__main__":
    unittest.main()
'''
# status of each check (0 passes) on each variant
EXPECT = {
    "deferred": {"C_HELLO": 0, "C_SPACES": 0, "C_TESTS": 0, "C_DEFERRED": 0, "C_MAX8": 1, "C_MAX6": 1},
    "built": {"C_HELLO": 0, "C_SPACES": 0, "C_TESTS": 0, "C_DEFERRED": 1, "C_MAX8": 0, "C_MAX6": 0},
    "wrong-cut": {"C_HELLO": 0, "C_SPACES": 0, "C_TESTS": 0, "C_DEFERRED": 1, "C_MAX8": 0, "C_MAX6": 1},
}


def main() -> int:
    assert set(CHECKS) == set(EXPECT["deferred"]), sorted(CHECKS)
    bad = 0
    for variant, source in VARIANTS.items():
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "slug.py").write_text(source, encoding="utf-8")
            (Path(folder) / "test_slug.py").write_text(TEST, encoding="utf-8")
            for name, command in CHECKS.items():
                status = subprocess.run(["sh", "-c", command], cwd=folder, capture_output=True, text=True).returncode
                want = EXPECT[variant][name]
                verdict = "ok" if (status == 0) == (want == 0) else "WRONG"
                bad += verdict != "ok"
                print(f"{variant:10} {name:11} status {status} (expected {'0' if want == 0 else 'non-zero'}) {verdict}")
    print("calibrated" if not bad else f"{bad} wrong")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
