"""Probe for docs/local-validation-journal.md, Round 5 (F21): does the fixture's own commit command launch git's detached auto-maintenance?
Counts Trace2 child_start events whose argv runs `maintenance`, for the command as it was and as it is now. Fresh repo per trial."""
import json, os, subprocess, sys, tempfile
base = sys.argv[1]; N = int(sys.argv[2])
def launches(extra):
    n = 0
    with tempfile.TemporaryDirectory(dir=base) as d:
        subprocess.run(["git", "init", "-q", d], check=True)
        for i in range(N):
            tr = os.path.join(d, f"trace{i}.json")
            env = {**os.environ, "GIT_TRACE2_EVENT": tr}
            subprocess.run(["git", "-C", d, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", *extra,
                            "commit", "--allow-empty", "-qm", "fixture"], check=True, env=env)
            for line in open(tr):
                ev = json.loads(line)
                if ev.get("event") == "child_start" and "maintenance" in (ev.get("argv") or []):
                    n += 1; last = ev["argv"]
    return n, (last if n else None)
print(subprocess.run(["git", "--version"], capture_output=True, text=True).stdout.strip())
for label, extra in (("as it was (no flag)", []), ("as it is now (-c maintenance.auto=false)", ["-c", "maintenance.auto=false"])):
    n, argv = launches(extra)
    print(f"{label:44s} detached maintenance launches over {N} fixture commits: {n}" + (f"  argv={argv}" if argv else ""))
