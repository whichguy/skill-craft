"""Probe for docs/local-validation-journal.md, Round 5 (F21): after `git commit --allow-empty` returns, how often is objects/maintenance.lock still present,
with git's default auto-maintenance and with -c maintenance.auto=false? Each repo is fresh; n commits each; polls up to 300 ms."""
import os, subprocess, sys, tempfile, time
N = int(sys.argv[1]); base = sys.argv[2]
def trial(extra):
    seen = 0; longest = 0.0
    with tempfile.TemporaryDirectory(dir=base) as d:
        subprocess.run(["git", "init", "-q", d], check=True)
        lock = os.path.join(d, ".git", "objects", "maintenance.lock")
        for i in range(N):
            subprocess.run(["git", "-C", d, "-c", "user.name=t", "-c", "user.email=t@example.invalid", *extra, "commit", "--allow-empty", "-qm", f"c{i}"], check=True)
            if os.path.exists(lock):
                seen += 1; t0 = time.monotonic()
                while os.path.exists(lock) and time.monotonic() - t0 < 0.3: time.sleep(0.0005)
                longest = max(longest, time.monotonic() - t0)
        time.sleep(0.4)
    return seen, round(longest * 1000, 1)
print("git", subprocess.run(["git", "--version"], capture_output=True, text=True).stdout.strip())
for label, extra in (("default", []), ("maintenance.auto=false", ["-c", "maintenance.auto=false"])):
    seen, longest_ms = trial(extra)
    print(f"{label:24s} lock present right after commit returned: {seen}/{N}; longest observed hold {longest_ms} ms")
