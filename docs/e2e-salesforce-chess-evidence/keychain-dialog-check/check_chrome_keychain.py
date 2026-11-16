#!/usr/bin/env python3
"""Does a model-written Chrome launch in the harness's throwaway HOME raise macOS's "Keychain Not Found" dialog? (2026-11-15)

The owner saw "A keychain cannot be found to store "Chrome."" during E2E work. The source, caught live: a Codex session of the stacked
test (~/e2e-runs/stacked-test-20261115/sessions/v2170-ds-battleship/C4) ran its suite's test/browser.test.js, which starts Google
Chrome itself (no Playwright, no --use-mock-keychain) with HOME = the session's throwaway home (no Library/Keychains). Chrome saves
its "Chrome Safe Storage" key at launch; with no keychain under HOME, macOS shows the dialog.

This check builds the environment with the harness's own code (hosts.host("codex").env, which now gives the HOME its own keychain),
starts Chrome with that test's exact argv, and passes when no SecurityAgent process appears and Chrome's key lands in the throwaway
keychain (proof the keychain path was taken, not skipped). A watchdog kills Chrome's own process group the moment a SecurityAgent
appears, so a failure shows the dialog only briefly. The owner's real keychain list and default keychain are read before and after.
No dialog-raising control is run (bbe54a881d7ac3970a2ca63719fba0e86151e451: not rerun unasked); the stored key is the evidence that
the launch reached the keychain.

Usage: python3 -I check_chrome_keychain.py <skill-craft checkout> <scratch folder>
"""
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def run(argv, env=None):
    done = subprocess.run(argv, env=env, capture_output=True, text=True, check=False)
    return done.returncode, (done.stdout + done.stderr).strip()


def security_agents():
    code, out = run(["pgrep", "-x", "SecurityAgent"])
    return set(out.split()) if code == 0 else set()


def real_state():
    return run(["security", "list-keychains", "-d", "user"])[1], run(["security", "default-keychain", "-d", "user"])[1]


def main() -> int:
    checkout, scratch = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    sys.path.insert(0, str(checkout / "test/shiploop_e2e"))
    import hosts  # the harness's own throwaway-HOME builder

    root = Path(tempfile.mkdtemp(prefix="chrome-keychain-", dir=scratch))
    auth = root / "auth.json"
    auth.write_text("{}")
    os.environ["CODEX_HOME"] = str(root)  # the Codex host links auth.json from here; no host is started
    before_real, before_agents = real_state(), security_agents()
    print("chrome:", run([CHROME, "--version"])[1])
    print("SecurityAgent before:", sorted(before_agents) or "none")

    home = root / "home"
    home.mkdir()
    started = time.monotonic()
    env = hosts.host("codex").env(home)
    print(f"hosts.host('codex').env made the HOME in {time.monotonic() - started:.2f} s")
    print("throwaway default keychain:", run(["security", "default-keychain", "-d", "user"], env)[1].replace(str(home), "<home>"))

    profile = tempfile.mkdtemp(prefix="battleship-test-", dir=root)  # the test's own os.tmpdir() profile
    argv = [CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-background-networking", "--no-first-run",
            "--remote-debugging-port=0", f"--user-data-dir={profile}", "about:blank"]
    proc = subprocess.Popen(argv, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    dialog_at = None
    start = time.monotonic()
    while time.monotonic() - start < 8:
        if security_agents() - before_agents:
            dialog_at = time.monotonic() - start
            break
        time.sleep(0.1)
    os.killpg(proc.pid, signal.SIGKILL)  # Chrome's own group only: start_new_session made it the leader
    proc.wait()
    print(f"chrome ran {time.monotonic() - start:.1f} s;",
          f"SecurityAgent appeared at {dialog_at:.1f} s (FAIL)" if dialog_at is not None else "no SecurityAgent appeared")
    code, _ = run(["security", "find-generic-password", "-s", "Chrome Safe Storage", str(home / hosts.THROWAWAY_KEYCHAIN)], env)
    print("Chrome Safe Storage in the throwaway keychain:", code == 0)
    time.sleep(2)
    print("SecurityAgent after 2 s:", sorted(security_agents() - before_agents) or "none new")
    unchanged = real_state() == before_real
    print("owner's keychain list and default unchanged:", unchanged)
    ok = dialog_at is None and code == 0 and unchanged
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
