"""Keep the user's own skills out of a Codex subject or judge session.

Codex 0.171.0 lists every skill under the account's real home (`~/.codex/skills`, `~/.agents/skills`) to the model
whatever `HOME` and `CODEX_HOME` say: with only `HOME`, `CODEX_HOME` and `PATH` set, the model-visible prompt input
still names both roots (measured 2026-11-20 with `codex debug prompt-input`, no model call). The E2E harness's
throwaway profile (`hosts.CodexHost.env`) therefore isolates config, plugins and state, and not skills. No feature
flag tried removes them (`skip_host_skill_discovery`, `skill_search` off, `plugins` off). What does: turning each
skill off by its SKILL.md path with a `skills.config` override, which removes the skills and both roots.

  flags()            the `-c skills.config=[...]` override for every user-level skill found now
  preflight(env)     renders the prompt input a session would get, with no model call, and returns what it still
                     shows from the real home; an empty list is the proof a round needs before it spends a call
"""
import os
import re
import subprocess
import tempfile
from pathlib import Path

REAL_HOME = Path.home()
ROOTS = (REAL_HOME / ".codex" / "skills", REAL_HOME / ".agents" / "skills")


def user_skill_files():
    """Every SKILL.md under the real home's two skill roots, following symlinked skill folders, system skills left out."""
    found = set()
    for root in ROOTS:
        for folder, names, files in os.walk(root, followlinks=True):
            names[:] = [name for name in names if name != ".system"]
            if "SKILL.md" in files:
                found.add(str(Path(folder) / "SKILL.md"))
    return sorted(found)


def flags():
    files = user_skill_files()
    if not files:
        return []
    quoted = (name.replace("\\", "\\\\").replace('"', '\\"') for name in files)
    table = ",".join(f'{{path="{name}",enabled=false}}' for name in quoted)
    return ["-c", f"skills.config=[{table}]"]


def preflight(env):
    """What a Codex session started with `env` and flags() is still shown from the real home. [] means none."""
    with tempfile.TemporaryDirectory(prefix="codex-preflight-") as work:
        done = subprocess.run(["codex", "debug", "prompt-input", *flags(), "hello"], cwd=work,
                              stdin=subprocess.DEVNULL, capture_output=True, text=True, env=env, timeout=180,
                              check=False)
    if done.returncode != 0:
        return [f"codex debug prompt-input failed ({done.returncode}): {done.stderr.strip()[-300:]}"]
    text = done.stdout
    seen = [root for root in re.findall(r"`r\d+` = `([^`]+)`", text) if any(root.startswith(str(r)) for r in ROOTS)]
    seen += sorted({f"skill listed: {Path(name).parent.name}" for name in user_skill_files()
                    if re.search(rf"/{re.escape(Path(name).parent.name)}/SKILL\.md", text)})
    return seen
