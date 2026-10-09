#!/usr/bin/env python3
"""A stand-in for `node --test` that needs no node: it reads the delivered sources as text and prints the summary a node test run
prints (TAP), so the mutation runner can be driven without a JavaScript runtime. The same four checks as test/lib.test.js, as text.

Environment, set by a test: BASELINE=red|zero|silent changes what the unmutated copy reports; HANG_ON_SPIN=1 makes the copy
whose `spin` constant is true start a child and hang, as a mutant that loops would; SLOW=<seconds> sleeps before reporting;
ORPHAN=1 starts a child in this process's group that outlives it (a test that leaves a helper behind), recording its pid in
orphans.txt; EXIT_BY=<n> exits with that code after reporting (a failing run)."""
import os, re, subprocess, sys, time

if os.environ.get("SLOW"):
    time.sleep(float(os.environ["SLOW"]))
lib, other = open("lib.js").read(), open("other.js").read()
if os.environ.get("HANG_ON_SPIN") and "const spin = true" in lib:
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])  # same group as this process
    with open("grandchild.pid", "w") as handle:
        handle.write(f"{os.getpid()} {child.pid}")
    time.sleep(60)  # a bounded hang: the harness ends it long before
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
if mode == "zero":
    results = {}
failed = sum(1 for ok in results.values() if not ok) + (1 if mode == "red" else 0)
print("TAP version 13")
print(f"# tests {len(results)}\n# suites 0\n# pass {len(results) - failed}\n# fail {failed}\n# cancelled 0\n# skipped 0\n# todo 0")
sys.exit(1 if failed else 0)
