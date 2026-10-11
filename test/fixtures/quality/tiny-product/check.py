#!/usr/bin/env python3
"""A stand-in for `node --test` that needs no node: it reads the delivered sources as text and prints the summary a node test run
prints (TAP), so the mutation runner can be driven without a JavaScript runtime. The same four checks as test/lib.test.js, as text.

Environment, set by a test: BASELINE=red|zero|silent changes what the unmutated copy reports; HANG_ON_SPIN=1 makes the copy
whose `spin` constant is true start a child and hang, as a mutant that loops would; SLOW=<seconds> sleeps before reporting;
ORPHAN=1 starts a child in this process's group that outlives it (a test that leaves a helper behind), recording its pid in
orphans.txt; DUMP_ENV=1 writes the guard variables it was given to env.txt; REFUSE_BASELINE=1, REFUSE_ON_ADULT=1 and REFUSE_ON_SPIN=1 record a refused
declared-port bind (the line the port-refusing preload writes) in the unmutated copy and in the copy whose `spin` is true, the
second then exiting 1 as a server that met EADDRINUSE would; FLAKY_ONCE=1 makes the first run of the copy whose adult check is
broken fail and every later one pass (a failure that does not repeat). A failing check prints `not ok - <name>`, as node does."""
import os, re, subprocess, sys, time

if os.environ.get("SLOW"):
    time.sleep(float(os.environ["SLOW"]))
lib, other = open("lib.js").read(), open("other.js").read()
if os.environ.get("HANG_ON_SPIN") and "const spin = true" in lib:
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])  # same group as this process
    with open("grandchild.pid", "w") as handle:
        handle.write(f"{os.getpid()} {child.pid}")
    time.sleep(60)  # a bounded hang: the harness ends it long before
def refuse():
    with open(os.environ["SHIPLOOP_E2E_REFUSE_LOG"], "a") as handle:
        handle.write(f"{os.getpid()} listen 3000\n")


if os.environ.get("DUMP_ENV"):
    with open("env.txt", "w") as handle:
        handle.write(f"{os.environ.get('NODE_OPTIONS')}|{os.environ.get('SHIPLOOP_E2E_REFUSE_PORTS')}|{os.environ.get('SHIPLOOP_E2E_REFUSE_LOG')}")
if os.environ.get("REFUSE_BASELINE") and "const spin = false" in lib:
    refuse()
if os.environ.get("REFUSE_ON_ADULT") and "age > 18" in lib:  # the first mutant the runner tries
    refuse()
    sys.exit(1)
if os.environ.get("REFUSE_ON_SPIN") and "const spin = true" in lib:
    refuse()
    sys.exit(1)
if os.environ.get("ORPHAN"):
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # same group, 60 s at most
    with open("orphans.txt", "a") as handle:
        handle.write(f"{child.pid}\n")
mode = os.environ.get("BASELINE")
if mode == "silent":
    print("ok")
    sys.exit(0)
results = {
    "an adult is 18 or more": "age >= 18" in lib,
    "the small bucket joins its two bounds with and": re.search(r"if \(n [<>=]+ \d+ && n [<>=]+ \d+\)", lib) is not None,
    "sum adds": "a + b" in other,
    "spin is off": "const spin = false" in lib,
}
if os.environ.get("FLAKY_ONCE") and "age > 18" in lib:
    if os.path.exists("flaky.seen"):
        results["an adult is 18 or more"] = True  # the second time it passes
    else:
        open("flaky.seen", "w").close()
if mode == "zero":
    results = {}
failed = sum(1 for ok in results.values() if not ok) + (1 if mode == "red" else 0)
print("TAP version 13")
for name, ok in results.items():
    print(f"{'ok' if ok else 'not ok'} - {name}")
print(f"# tests {len(results)}\n# suites 0\n# pass {len(results) - failed}\n# fail {failed}\n# cancelled 0\n# skipped 0\n# todo 0")
sys.exit(1 if failed else 0)
