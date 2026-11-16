#!/usr/bin/env python3
"""No-model published Claude install probe. Usage: python3 -B this.py NEW_SCRATCH.

PYTHON selects the supported interpreter; SKILL_CRAFT_CHECKOUT selects the checkout
whose origin/main is compared. Leaves the new scratch directory and full command
logs for inspection. Never removes an existing directory or changes a global profile.
"""

import ast
import io
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import time

ENTRIES = ("shiploop", "shiploop-drive", "shiploop-hook", "shiploop-keepalive-observe",
           "shiploop-keepalive-stop", "shiploop-keepalive-session-end", "shiploop-skill-call",
           "shiploop-status-hook")
HOOKS = ENTRIES[3:]
MINIMUM = (3, 15)
COMMAND_TIMEOUT = 180
CLEANUP_GRACE = 0.2


def owned_run(args, *, timeout, input=b"", **kwargs):
    """Own one POSIX session; finish group cleanup before reaping its leader."""
    process = subprocess.Popen(args, start_new_session=True, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    cleanup = None
    try:
        try:
            stdout, stderr = process.communicate(input, timeout=timeout)
        except BaseException as exc:
            cleanup = []
            exc.cleanup = cleanup
            stdout = getattr(exc, "stdout", None) or b""
            stderr = getattr(exc, "stderr", None) or b""
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.killpg(process.pid, sig)
                    cleanup.append("group %s: %s" % (process.pid, sig.name))
                except ProcessLookupError:
                    cleanup.append("group %s: absent" % process.pid)
                except BaseException as error:
                    # Darwin EPERM can occur for zombie-only groups, but without
                    # positive evidence group cleanup remains unconfirmed.
                    cleanup.append("group %s: %s failed: %s: %s; cleanup unconfirmed" %
                                   (process.pid, sig.name, type(error).__name__, error))
                if sig == signal.SIGTERM:
                    try:
                        time.sleep(CLEANUP_GRACE)
                    except BaseException as error:
                        cleanup.append("cleanup grace failed: %s: %s" %
                                       (type(error).__name__, error))
            try:
                stdout, stderr = process.communicate(timeout=2)
            except subprocess.TimeoutExpired as drain:
                stdout = drain.output if drain.output is not None else stdout
                stderr = drain.stderr if drain.stderr is not None else stderr
                cleanup.append("output drain timed out; cleanup unconfirmed")
            except BaseException as error:
                cleanup.append("output drain failed: %s: %s; cleanup unconfirmed" %
                               (type(error).__name__, error))
            exc.stdout, exc.stderr = stdout, stderr
            raise
        return subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
    finally:
        # Cleanup errors must remain visible without replacing the primary failure.
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                try:
                    stream.close()
                except BaseException as error:
                    if cleanup is None:
                        raise
                    cleanup.append("stream close failed: %s: %s; cleanup unconfirmed" %
                                   (type(error).__name__, error))
        if process.returncode is None:
            try:
                process.wait(timeout=2)
            except BaseException as error:
                if cleanup is None:
                    raise
                cleanup.append("leader reap failed: %s: %s; cleanup unconfirmed" %
                               (type(error).__name__, error))
        if cleanup is not None:
            cleanup.append("leader exit: %s" % process.returncode)


def selected_python():
    selected = shutil.which(os.environ.get("PYTHON", "python3"))
    if not selected:
        raise ValueError("PYTHON (or the selected python3) is unavailable")
    try:
        done = owned_run([selected, "-B", "-c", "import json, sys; print(json.dumps(sys.executable))"],
                         timeout=5)
        actual = json.loads(done.stdout)
        if done.returncode or not isinstance(actual, str) or not Path(actual).is_absolute():
            raise ValueError("selection did not return an absolute interpreter")
        actual = str(Path(actual).resolve(strict=True))
        if not os.access(actual, os.X_OK):
            raise ValueError("selected interpreter is not executable")
        return actual
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise ValueError("invalid PYTHON interpreter selection: %s" % exc) from exc


def published_floor(scripts, card):
    tree = ast.parse((scripts / "shiploop_pyfloor.py").read_text())
    values = [ast.literal_eval(node.value) for node in tree.body
              if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "FLOOR"
                                                      for t in node.targets)]
    if len(values) != 1 or not isinstance(values[0], tuple) or len(values[0]) != 2:
        raise ValueError("published guard must declare one two-part FLOOR")
    floor = values[0]
    if any(type(n) is not int for n in floor) or floor < MINIMUM:
        raise ValueError("published FLOOR must meet the current project minimum 3.15")
    expected = "needs `python3` %d.%d or newer and `git` on PATH" % floor
    if expected not in " ".join(card.read_text().split()):
        raise ValueError("installed card and published guard disagree")
    return floor


def tree_bytes(root):
    result = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in {"__pycache__", ".git", ".in_use"} for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError("unexpected package symlink: %s" % relative)
        if path.is_dir():
            result[relative.as_posix() + "/"] = None
        elif path.is_file():
            result[relative.as_posix()] = path.read_bytes()
    return result


def probe(scratch, checkout, python):
    # mkdir (without parents/exist_ok) refuses existing paths, including symlinks.
    scratch.mkdir()
    scratch = scratch.resolve()
    config = scratch / "claude-config"
    config.mkdir()
    install_env = dict(os.environ, CLAUDE_CONFIG_DIR=str(config), PYTHONDONTWRITEBYTECODE="1")
    sequence = 0

    def run(args, *, env=None, expected=0, quiet=False, input=b"", check=True):
        nonlocal sequence
        sequence += 1
        prefix = scratch / ("%02d" % sequence)
        prefix.with_suffix(".command.json").write_text(json.dumps([str(a) for a in args]))
        try:
            done = owned_run([str(a) for a in args], cwd=scratch, env=env or install_env,
                             input=input, timeout=COMMAND_TIMEOUT)
        except BaseException as exc:
            prefix.with_suffix(".stdout").write_bytes(getattr(exc, "stdout", None) or b"")
            prefix.with_suffix(".stderr").write_bytes(getattr(exc, "stderr", None) or b"")
            timed_out = isinstance(exc, subprocess.TimeoutExpired)
            prefix.with_suffix(".exit").write_text("TIMEOUT\n" if timed_out else "INTERRUPTED/FAILED\n")
            prefix.with_suffix(".cleanup.json").write_text(json.dumps(getattr(exc, "cleanup", [])))
            if timed_out:
                raise ValueError("command %02d timed out; inspect %s.*" % (sequence, prefix)) from exc
            raise
        prefix.with_suffix(".stdout").write_bytes(done.stdout)
        prefix.with_suffix(".stderr").write_bytes(done.stderr)
        prefix.with_suffix(".exit").write_text(str(done.returncode) + "\n")
        if check and (done.returncode != expected or quiet and (done.stdout or done.stderr)):
            raise ValueError("command %02d: exit %s (expected %s); inspect %s.*" %
                             (sequence, done.returncode, expected, prefix))
        return done

    claude = shutil.which("claude")
    git = shutil.which("git")
    if not claude or not git:
        raise ValueError("Claude CLI and Git on PATH are required")
    git = str(Path(git).resolve())
    print("## native Claude install into %s" % config, flush=True)
    # Capture and check each command BEFORE summarizing its output.
    run([claude, "plugin", "marketplace", "add", "whichguy/skill-craft"])
    run([claude, "plugin", "install", "skill-craft@whichguy"])
    listed = json.loads(run([claude, "plugin", "list", "--json"]).stdout)
    installed = [p for p in listed if p.get("id") == "skill-craft@whichguy" and p.get("enabled")]
    if len(installed) != 1:
        raise ValueError("expected one enabled skill-craft@whichguy install")
    package = config / "plugins/cache/whichguy/skill-craft" / str(installed[0]["version"])
    scripts = package / "skills/shiploop/scripts"
    print("## installed tree vs origin/main plugins/skill-craft", flush=True)
    revision = run([git, "-C", checkout, "rev-parse", "origin/main"]).stdout.decode().strip()
    print("published comparison commit: %s" % revision, flush=True)
    archive = run([git, "-C", checkout, "archive", revision, "plugins/skill-craft"]).stdout
    published = scratch / "published"
    published.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        stream.extractall(published, filter="data")
    if tree_bytes(package) != tree_bytes(published / "plugins/skill-craft"):
        raise ValueError("installed package differs from origin/main (excluding cache metadata)")
    for name in ENTRIES:
        mode = stat.S_IMODE((scripts / name).stat().st_mode)
        if mode != 0o755:
            raise ValueError("%s mode %o, expected 755" % (name, mode))
    floor = published_floor(scripts, package / "skills/shiploop/SKILL.md")
    if sys.version_info[:2] < floor:
        raise ValueError("selected interpreter is below the published FLOOR %s" % (floor,))
    print("PASS tree, eight executable modes, FLOOR/card %d.%d" % floor, flush=True)
    repo = scratch / "repo"
    home = scratch / "home"
    home.mkdir()
    bin_dir = scratch / "bin"
    bin_dir.mkdir()
    (bin_dir / "python3").symlink_to(python)
    (bin_dir / "git").symlink_to(git)
    # Equivalent to env -i; the absolute interpreter survives environment clearing.
    clean = {"HOME": str(home), "PATH": str(bin_dir) + os.pathsep + os.defpath,
             "PYTHONDONTWRITEBYTECODE": "1", "SHIPLOOP_PROGRESS": "off"}
    run([git, "init", "-q", repo], env=clean)
    run([git, "-C", repo, "-c", "user.name=probe", "-c", "user.email=probe@invalid",
         "commit", "-q", "--allow-empty", "-m", "init"], env=clean)
    run([python, "-B", scripts / "shiploop", "--help"], env=clean)
    packet = run([python, "-B", scripts / "shiploop", "workspace", "start", "--repo", repo,
                  "--prompt", "Create hello.py that prints Hello, world!"], env=clean)
    if not packet.stdout:
        raise ValueError("workspace start returned an empty packet")
    print("PASS clean environment help/workspace start; packet_bytes=%d" % len(packet.stdout), flush=True)
    no_python = scratch / "nopython"
    no_python.mkdir()
    for tool in ("cat", "dirname", "sh", "grep", "tr", "head", "env", "sed"):
        target = shutil.which(tool)
        if not target:
            raise ValueError("missing hook probe utility: %s" % tool)
        (no_python / tool).symlink_to(Path(target).resolve())
    for name in HOOKS:
        run(["/bin/sh", scripts / name], env={"HOME": str(home), "PATH": str(no_python)},
            input=b"{}\n", quiet=True)
    print("PASS five hooks quiet without Python", flush=True)
    docker = shutil.which("docker")
    if not docker:
        print("SKIP real old-interpreter check: Docker CLI unavailable", flush=True)
        return
    for args, reason in (([docker, "info"], "Docker daemon unavailable"),
                         ([docker, "image", "inspect", "node:14"], "local node:14 image unavailable (no pull)")):
        if run(args, check=False).returncode:
            print("SKIP real old-interpreter check: " + reason, flush=True)
            return
    # Runs only an already-local image, without network; syntax accepted by Python 3.7.
    old_code = '''import subprocess, sys
floor = tuple(map(int, sys.argv[1:3]))
if sys.version_info[:2] >= floor:
    print("SKIP real old-interpreter check: image Python is not below published FLOOR")
    sys.exit(77)
root = "/plug/skills/shiploop/scripts/"
for name in sys.argv[3:]:
    p = subprocess.run(["/bin/sh", root + name], input=b"{}", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert (p.returncode, p.stdout, p.stderr) == (0, b"", b""), (name, p.returncode, p.stdout, p.stderr)
p = subprocess.run([sys.executable, root + "shiploop", "--help"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
assert p.returncode == 2 and not p.stdout and len(p.stderr.splitlines()) == 1, (p.returncode, p.stdout, p.stderr)
assert ("ShipLoop needs Python %d.%d or newer" % floor).encode() in p.stderr, p.stderr
p = subprocess.run([sys.executable, root + "shiploop-hook", "observe", "--host", "auto"], input=b"{}", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
assert (p.returncode, p.stdout, p.stderr) == (0, b"", b""), (p.returncode, p.stdout, p.stderr)
print("PASS real old-interpreter CLI refusal (2) and hook silence (0); Python " + sys.version.split()[0])
'''
    cidfile = scratch / "old-interpreter.cid"
    container_failed = True
    try:
        done = run([docker, "run", "--cidfile", cidfile, "--rm", "--pull=never", "--network=none", "-v", str(package) + ":/plug:ro",
                    "node:14", "/bin/sh", "-c",
                    'command -v python3 >/dev/null 2>&1 || { echo "SKIP real old-interpreter check: image has no Python"; exit 77; }; exec python3 -B "$@"',
                    "probe", "-c", old_code, *map(str, floor), *HOOKS], check=False)
        container_failed = done.returncode not in (0, 77)
    finally:
        if container_failed and cidfile.is_file():
            cid = cidfile.read_text().strip()
            # Docker writes a full hexadecimal ID. Never remove a name or an unrecorded container.
            if len(cid) == 64 and all(c in "0123456789abcdef" for c in cid):
                try:
                    removed = run([docker, "rm", "--force", cid], check=False)
                    cleanup = {"cid": cid, "returncode": removed.returncode}
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    cleanup = {"cid": cid, "error": str(exc)}
                (scratch / "container-cleanup.json").write_text(json.dumps(cleanup))
            else:
                (scratch / "container-cleanup.json").write_text(json.dumps({"error": "invalid owned CID"}))
    if done.returncode == 77:
        print(done.stdout.decode(), end="", flush=True)
    elif done.returncode:
        raise ValueError("old-interpreter container failed; inspect final command logs")
    else:
        print(done.stdout.decode(), end="", flush=True)


def main():
    python = selected_python()
    if Path(sys.executable).resolve() != Path(python):
        os.environ["PYTHON"] = python
        os.execv(python, [python, "-B", str(Path(__file__).resolve()), *sys.argv[1:]])
    if sys.version_info[:2] < MINIMUM:
        raise ValueError("probe needs Python 3.15 or newer; select it with PYTHON or PATH")
    if len(sys.argv) != 2:
        raise ValueError("usage: published-install-smoke.py NEW_SCRATCH")
    checkout = Path(os.environ.get("SKILL_CRAFT_CHECKOUT", Path(__file__).resolve().parents[1])).resolve()
    probe(Path(sys.argv[1]).absolute(), checkout, python)
    print("PASS required published clean-install checks; optional checks reported separately")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError, tarfile.TarError) as exc:
        print("FAIL: %s" % exc, file=sys.stderr)
        sys.exit(1)
