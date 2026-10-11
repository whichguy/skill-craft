"""Small helpers for isolated real-Git test fixtures."""

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock


def isolate_git_environment(test_case, home: str | Path) -> None:
    """Use a private HOME/XDG tree and remove inherited Git context until cleanup."""
    home_path = Path(home)
    home_path.mkdir(parents=True, exist_ok=True)
    xdg_config = home_path / ".config"
    xdg_config.mkdir(parents=True, exist_ok=True)

    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update({
        "HOME": str(home_path),
        "XDG_CONFIG_HOME": str(xdg_config),
        "XDG_STATE_HOME": str(home_path / ".state"),
    })
    isolated = mock.patch.dict(os.environ, environment, clear=True)
    test_case.addCleanup(isolated.stop)
    isolated.start()
