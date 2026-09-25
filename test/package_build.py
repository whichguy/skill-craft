"""Plugin packages built from source, for tests.

The committed plugins/ tree is release output and may lag the source between
releases, so package tests read a fresh build instead. Each test process
builds once into a temporary directory that is removed when it exits; set
SKILL_CRAFT_PACKAGES to a build-packages.py output to reuse one build.
"""

import atexit
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = "SKILL_CRAFT_PACKAGES"
_built = None


def build_into(out):
    subprocess.run([sys.executable, "-B", str(ROOT / "scripts/build-packages.py"), str(out)],
                   check=True, stdout=subprocess.DEVNULL)
    return out


def packages_root():
    """Directory holding generated plugins/, catalogs and README.md."""
    global _built
    if os.environ.get(ENV):
        return Path(os.environ[ENV])
    if _built is None:
        parent = Path(tempfile.mkdtemp(prefix="skill-craft-packages-"))
        atexit.register(shutil.rmtree, parent, True)
        _built = build_into(parent / "build")
    return _built


def plugins():
    return packages_root() / "plugins"
